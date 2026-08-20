import json
import re
from collections import defaultdict, deque
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FLOW_PATH = (
    ROOT
    / "solution/ARCollectionsDemo/ARCollectionsDisputeResolution"
    / "ARCollectionsDisputeResolution.flow"
)
BINDINGS_PATH = (
    ROOT
    / "solution/ARCollectionsDemo/ARCollectionsDisputeResolution"
    / "bindings_v2.json"
)
AGENT_MAPPING_PATH = ROOT / "config/agent-projects.json"
EVAL_SET_PATH = (
    FLOW_PATH.parent
    / "evals/2af1fdaa-b414-460f-9f42-b099f793059c/eval-sets/evaluation-set.json"
)

SUPPORTED_ROUTES = {
    "po_mismatch": "poMismatch",
    "missing_pod": "missingPod",
    "payment_misapplication": "paymentMisapplication",
}
# missingPod is an in-solution coded agent; the other two specialists remain
# inline low-code agents. Both implementations honour the same Flow I/O contract.
INLINE_SPECIALISTS = {"poMismatch", "paymentMisapplication"}
CODED_SPECIALISTS = {"missingPod"}
PROPOSAL_FIELDS = {
    "caseId": "string",
    "disputeType": "string",
    "evidenceSummary": "string",
    "rootCause": "string",
    "recommendedAction": "string",
    "actionCode": "string",
    "adjustmentAmount": "number",
    "confidence": "number",
    "approvalSummary": "string",
    "emailSubject": "string",
    "emailBody": "string",
    "resourcesUsed": "string",
}
RESULT_FIELDS = {
    "status",
    "resultCaseId",
    "disputeType",
    "triageRationale",
    "triageConfidence",
    "recommendedAction",
    "approvalDecision",
    "approvalComments",
    "updateResult",
    "emailSent",
    "resourcesUsed",
    "auditSummary",
}
ARTIFACT_PORTS = {"context", "tool", "escalation", "memory"}


def load_json(path: Path):
    assert path.is_file(), f"missing required JSON file: {path}"
    return json.loads(path.read_text())


def load_contract():
    flow = load_json(FLOW_PATH)
    mapping = load_json(AGENT_MAPPING_PATH)["agents"]
    nodes = {node["id"]: node for node in flow["nodes"]}
    assert len(nodes) == len(flow["nodes"]), "Flow node IDs must be unique"
    return flow, mapping, nodes


def coded_agent_config(logical_name):
    return load_json(AGENT_MAPPING_PATH)["codedAgents"][logical_name]


def specialist_node(flow, mapping, logical_name):
    """Resolve a specialist node by logical name, inline or coded."""
    if logical_name in INLINE_SPECIALISTS:
        matches = [
            node
            for node in flow["nodes"]
            if node.get("inputs", {}).get("source") == mapping[logical_name]
        ]
    else:
        node_type = coded_agent_config(logical_name)["nodeType"]
        matches = nodes_of_type(flow, node_type)
    assert len(matches) == 1, f"expected one {logical_name} specialist node"
    return matches[0]


def nodes_of_type(flow, node_type):
    return [node for node in flow["nodes"] if node["type"] == node_type]


def node_with_label(flow, label):
    matches = [
        node
        for node in flow["nodes"]
        if node.get("display", {}).get("label", "").casefold() == label.casefold()
    ]
    assert len(matches) == 1, f"expected one node labelled {label!r}, got {len(matches)}"
    return matches[0]


def sequential_edges(flow):
    return [
        edge
        for edge in flow["edges"]
        if edge.get("sourcePort") not in ARTIFACT_PORTS
    ]


def adjacency(flow):
    graph = defaultdict(set)
    for edge in sequential_edges(flow):
        graph[edge["sourceNodeId"]].add(edge["targetNodeId"])
    return graph


def reachable(flow, start_node_id):
    graph = adjacency(flow)
    seen = set()
    pending = deque([start_node_id])
    while pending:
        node_id = pending.popleft()
        if node_id in seen:
            continue
        seen.add(node_id)
        pending.extend(graph[node_id] - seen)
    return seen


def outgoing(flow, node_id, source_port=None):
    edges = [
        edge
        for edge in sequential_edges(flow)
        if edge["sourceNodeId"] == node_id
    ]
    if source_port is not None:
        edges = [edge for edge in edges if edge["sourcePort"] == source_port]
    return edges


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def string_array_sets(script):
    arrays = []
    for body in re.findall(r"\[([^\[\]]*)\]", script, flags=re.DOTALL):
        strings = re.findall(r"['\"]([^'\"]+)['\"]", body)
        if strings:
            arrays.append(strings)
    return arrays


def values_named(value, name):
    """Return configured values for a key or [key, value] parameter pair."""
    values = []

    def visit(current):
        if isinstance(current, dict):
            for key, child in current.items():
                if key.casefold() == name.casefold():
                    values.append(child)
                visit(child)
        elif isinstance(current, list):
            if (
                len(current) == 2
                and isinstance(current[0], str)
                and current[0].casefold() == name.casefold()
            ):
                values.append(current[1])
            for child in current:
                visit(child)
        elif isinstance(current, str) and current.startswith("=jsonString:"):
            visit(json.loads(current.removeprefix("=jsonString:")))

    visit(value)
    return values


def end_with_status(flow, status):
    matches = [
        node
        for node in nodes_of_type(flow, "core.control.end")
        if status.casefold() in json.dumps(node.get("outputs", {}).get("status")).casefold()
    ]
    assert len(matches) == 1, f"expected one End with status {status!r}"
    return matches[0]


def bindings_in(value):
    return [
        f"=js:{binding}"
        for binding in re.findall(r"=js:\(?(\$vars\.[A-Za-z0-9_.-]+)", json.dumps(value))
    ]


def test_data_fabric_record_created_trigger_starts_the_dispute_lifecycle():
    flow, _, _ = load_contract()
    created = nodes_of_type(
        flow, "uipath.connector.trigger.uipath-uipath-dataservice.record-created"
    )
    waits = nodes_of_type(
        flow, "uipath.connector.event.uipath-uipath-dataservice.record-updated"
    )
    assert len(created) == len(waits) == 1
    assert created[0]["id"] == "recordCreated"
    assert waits[0]["id"] == "waitForApprovalUpdate"
    assert not nodes_of_type(flow, "core.trigger.manual")
    assert not nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")

    triage = node_with_label(flow, "Grounded Dispute Triage")
    stamp_case_id = node_with_label(flow, "Update Case ID on record")
    start_edges = outgoing(flow, created[0]["id"], "output")
    assert len(start_edges) == 1
    assert start_edges[0]["targetNodeId"] == stamp_case_id["id"]
    assert start_edges[0]["targetPort"] == "input"
    stamp_edges = outgoing(flow, stamp_case_id["id"], "output")
    assert len(stamp_edges) == 1
    assert stamp_edges[0]["targetNodeId"] == triage["id"]
    assert stamp_edges[0]["targetPort"] == "input"


def test_flow_uses_all_mapped_inline_agents_with_exact_runtime_contracts():
    flow, mapping, _ = load_contract()
    agents = nodes_of_type(flow, "uipath.agent.autonomous")
    by_source = {node.get("inputs", {}).get("source"): node for node in agents}
    assert len(agents) == 3
    assert set(by_source) == set(mapping.values())

    triage = by_source[mapping["triage"]]
    triage_inputs = {
        item["id"]: item for item in triage["inputs"]["agentInputVariables"]
    }
    assert set(triage_inputs) == {"recordCreated__output"}
    assert triage_inputs["recordCreated__output"]["type"] == "object"
    assert (
        triage_inputs["recordCreated__output"]["binding"]
        == "=$vars.recordCreated.output"
    )
    assert {item["id"]: item["type"] for item in triage["inputs"]["agentOutputVariables"]} == {
        "disputeType": "string",
        "rationale": "string",
        "confidence": "number",
    }

    specialist_inputs = {
        "recordCreated__output": ("object", "=$vars.recordCreated.output"),
        "triageAgent__output__disputeType": (
            "string",
            "=$vars.triageAgent.output.disputeType",
        ),
        "triageAgent__output__rationale": (
            "string",
            "=$vars.triageAgent.output.rationale",
        ),
        "triageAgent__output__confidence": (
            "number",
            "=$vars.triageAgent.output.confidence",
        ),
    }
    for logical_name in INLINE_SPECIALISTS:
        specialist = by_source[mapping[logical_name]]
        inputs = {
            item["id"]: (item["type"], item["binding"])
            for item in specialist["inputs"]["agentInputVariables"]
        }
        outputs = {
            item["id"]: item["type"]
            for item in specialist["inputs"]["agentOutputVariables"]
        }
        assert inputs == specialist_inputs
        assert outputs == PROPOSAL_FIELDS


def test_coded_specialists_receive_the_same_four_flow_inputs():
    """The coded agent must consume the identical Flow variables the inline
    specialists do, so routing behaviour is unchanged by the implementation swap."""
    flow, mapping, _ = load_contract()
    expected_expressions = {
        "recordCreated__output": ("object", "{{ $vars.recordCreated.output }}"),
        "triageAgent__output__disputeType": (
            "string",
            "{{ $vars.triageAgent.output.disputeType }}",
        ),
        "triageAgent__output__rationale": (
            "string",
            "{{ $vars.triageAgent.output.rationale }}",
        ),
        "triageAgent__output__confidence": (
            "number",
            "{{ $vars.triageAgent.output.confidence }}",
        ),
    }

    for logical_name in CODED_SPECIALISTS:
        node = specialist_node(flow, mapping, logical_name)
        inputs = node["inputs"]
        assert {
            name: (spec["fieldType"], spec["expression"])
            for name, spec in inputs.items()
        } == expected_expressions
        # Agent inputs must use the literal/expression form, never `=js:`.
        for spec in inputs.values():
            assert spec["type"] == "literal"
            assert not spec["expression"].startswith("=js:")

        # The proposal must surface as `output` so Normalize Proposal can read it.
        assert node["outputs"]["output"]["var"] == "output"
        assert node["outputs"]["output"]["source"] == "=result.response"
        assert node["outputs"]["error"]["var"] == "error"


def test_coded_specialist_node_is_registered_in_the_solution():
    """The node type, bindings, and definition must all come from the local
    resource key minted by `uip solution projects add` — never hand-invented."""
    flow, _, _ = load_contract()
    config = coded_agent_config("missingPod")
    resource_key = config["resourceKey"]
    assert config["nodeType"] == f"uipath.core.agent.{resource_key}"

    resource = load_json(
        FLOW_PATH.parents[1]
        / "resources/solution_folder/process/agent"
        / f"{config['projectDir']}.json"
    )
    assert resource["resource"]["key"] == resource_key
    assert resource["resource"]["projectKey"] == config["projectKey"]
    assert resource["resource"]["spec"]["type"] == "Agent"

    definitions = [
        definition
        for definition in flow["definitions"]
        if definition["nodeType"] == config["nodeType"]
    ]
    assert len(definitions) == 1
    definition = definitions[0]
    assert definition["model"]["serviceType"] == "Orchestrator.StartAgentJob"
    assert definition["model"]["bindings"]["resourceKey"] == resource_key
    assert definition["model"]["bindings"]["resourceSubType"] == "Agent"

    bindings = [
        binding for binding in flow["bindings"] if binding["resourceKey"] == resource_key
    ]
    assert {binding["propertyAttribute"] for binding in bindings} == {
        "name",
        "folderPath",
    }
    assert len(bindings) == 2
    assert all(binding["resourceSubType"] == "Agent" for binding in bindings)


def test_inline_agent_delivery_schema_and_prompt_inputs_are_aligned():
    flow, _, _ = load_contract()

    for node in nodes_of_type(flow, "uipath.agent.autonomous"):
        delivered = {
            item["id"]: item["type"]
            for item in node["inputs"]["agentInputVariables"]
        }
        agent = load_json(FLOW_PATH.parent / node["inputs"]["source"] / "agent.json")
        declared = {
            name: definition.get("type")
            for name, definition in agent["inputSchema"]["properties"].items()
        }
        prompt = "\n".join(message["content"] for message in agent["messages"])
        prompt_variables = [
            token["rawString"]
            for message in agent["messages"]
            for token in message["contentTokens"]
            if token["type"] == "variable"
        ]

        assert declared == delivered, node["id"]
        assert set(prompt_variables) == {
            f"input.{input_id}" for input_id in delivered
        }, node["id"]
        for input_id in delivered:
            assert prompt.count(f"{{{{input.{input_id}}}}}") == 1, node["id"]


def test_eval_set_targets_the_data_fabric_record_created_entrypoint():
    flow, _, _ = load_contract()
    eval_set = load_json(EVAL_SET_PATH)
    entrypoint = eval_set["selectedEntrypoint"]

    assert eval_set["target"] == {"kind": "flow", "entrypoint": entrypoint}
    matching_nodes = [node for node in flow["nodes"] if node["id"] == entrypoint]
    assert len(matching_nodes) == 1
    assert matching_nodes[0]["type"].startswith("uipath.connector.trigger.")


def test_supported_decision_and_switch_route_exclusively_to_one_specialist():
    flow, mapping, nodes = load_contract()
    switches = nodes_of_type(flow, "core.logic.switch")
    assert len(switches) == 1
    decision = node_with_label(flow, "Supported and confident?")
    assert decision["type"] == "core.logic.decision"
    switch = switches[0]

    expression = compact(decision["inputs"]["expression"])
    assert "$vars.triageagent.output.confidence" in expression
    assert re.search(r"confidence>=0?\.75", expression)
    assert "$vars.triageagent.output.disputetype" in expression
    assert "&&" in expression
    for dispute_type in SUPPORTED_ROUTES:
        assert dispute_type in expression
    assert "unsupported" not in expression

    true_edges = outgoing(flow, decision["id"], "true")
    assert len(true_edges) == 1
    assert true_edges[0]["targetNodeId"] == switch["id"]
    assert true_edges[0]["targetPort"] == "input"

    cases = switch["inputs"]["cases"]
    assert len(cases) == 3
    assert len({case["id"] for case in cases}) == 3
    route_cases = {}
    for case in cases:
        case_expression = compact(case["expression"])
        assert "$vars.triageagent.output.disputetype" in case_expression
        matched = [route for route in SUPPORTED_ROUTES if route in case_expression]
        assert len(matched) == 1
        route_cases[matched[0]] = case
    assert set(route_cases) == set(SUPPORTED_ROUTES)

    switch_edges = outgoing(flow, switch["id"])
    assert {edge["sourcePort"] for edge in switch_edges} == {
        f"case-{case['id']}" for case in cases
    }

    specialist_ids = {
        logical_name: specialist_node(flow, mapping, logical_name)["id"]
        for logical_name in SUPPORTED_ROUTES.values()
    }
    normalize = node_with_label(flow, "Normalize Proposal")
    for dispute_type, logical_name in SUPPORTED_ROUTES.items():
        case = route_cases[dispute_type]
        route_edges = outgoing(flow, switch["id"], f"case-{case['id']}")
        assert len(route_edges) == 1
        assert route_edges[0]["targetNodeId"] == specialist_ids[logical_name]
        assert route_edges[0]["targetPort"] == "input"
        reached = reachable(flow, route_edges[0]["targetNodeId"])
        reached_specialists = set(specialist_ids.values()) & reached
        assert reached_specialists == {specialist_ids[logical_name]}
        assert normalize["id"] in reached
        assert all(node_id in nodes for node_id in reached)


def test_normalize_proposal_selects_one_branch_and_verifies_exact_contract():
    flow, mapping, _ = load_contract()
    normalize = node_with_label(flow, "Normalize Proposal")
    assert normalize["type"] == "core.action.script"
    script = normalize["inputs"]["script"]
    normalized = compact(script)

    specialist_nodes = [
        specialist_node(flow, mapping, logical_name)
        for logical_name in SUPPORTED_ROUTES.values()
    ]
    assert len(specialist_nodes) == 3
    for node in specialist_nodes:
        assert f"$vars.{node['id']}.output".casefold() in script.casefold()

    assert ".filter(" in normalized
    assert re.search(r"\.length(!==|!=)1", normalized)
    assert "throw" in normalized
    assert "object.keys" in normalized
    assert ".every(" in normalized or ".foreach(" in normalized
    assert any(
        len(values) == len(PROPOSAL_FIELDS) and set(values) == set(PROPOSAL_FIELDS)
        for values in string_array_sets(script)
    )


def test_manual_triage_is_side_effect_free_and_every_end_maps_result_contract():
    flow, _, nodes = load_contract()
    decision = node_with_label(flow, "Supported and confident?")
    assert decision["type"] == "core.logic.decision"
    false_edges = outgoing(flow, decision["id"], "false")
    assert len(false_edges) == 1
    assert false_edges[0]["targetPort"] == "input"

    manual_persistence = node_with_label(flow, "Persist Needs Manual Triage")
    assert (
        manual_persistence["type"]
        == "uipath.connector.uipath-uipath-dataservice.update-entity-record"
    )
    assert false_edges[0]["targetNodeId"] == manual_persistence["id"]
    persistence_edges = outgoing(flow, manual_persistence["id"])
    assert len(persistence_edges) == 1
    assert persistence_edges[0]["targetPort"] == "input"

    manual_end = nodes[persistence_edges[0]["targetNodeId"]]
    assert manual_end["type"] == "core.control.end"
    assert "needs_manual_triage" in json.dumps(manual_end).casefold()
    manual_reachable = reachable(flow, manual_persistence["id"])

    agent_ids = {
        node["id"]
        for node in nodes_of_type(flow, "uipath.agent.autonomous")
    }
    wait = node_with_label(flow, "Wait for Approval Update")
    outlook = node_with_label(flow, "Send Email")

    def is_forbidden(node):
        return (
            node["id"] in agent_ids
            or node["type"].startswith("uipath.core.api-workflow.")
            or node["id"] in {wait["id"], outlook["id"]}
        )

    assert not any(is_forbidden(nodes[node_id]) for node_id in manual_reachable)
    assert manual_reachable == {manual_persistence["id"], manual_end["id"]}

    outputs = manual_end["outputs"]
    assert set(outputs) == RESULT_FIELDS
    assert "needs_manual_triage" in json.dumps(outputs["status"]).casefold()
    assert "false" in json.dumps(outputs["emailSent"]).casefold()
    assert "null" in json.dumps(outputs["approvalDecision"]).casefold()
    assert "null" in json.dumps(outputs["updateResult"]).casefold()
    audit_source = json.dumps(outputs["auditSummary"]).casefold()
    assert "no specialist" in audit_source
    assert "side effect" in audit_source

    ends = nodes_of_type(flow, "core.control.end")
    assert ends
    for end in ends:
        assert set(end.get("outputs", {})) == RESULT_FIELDS
        assert "=js:$vars.recordCreated.output.caseId" in json.dumps(
            end["outputs"]["resultCaseId"]
        )


def test_data_fabric_approval_events_are_correlated_persisted_and_isolated():
    flow, _, nodes = load_contract()
    normalize = node_with_label(flow, "Normalize Proposal")
    waits = nodes_of_type(
        flow, "uipath.connector.event.uipath-uipath-dataservice.record-updated"
    )
    assert len(waits) == 1
    wait = waits[0]
    assert wait["id"] == "waitForApprovalUpdate"
    correlation = node_with_label(flow, "Updated record matches this dispute?")
    assert correlation["type"] == "core.logic.decision"
    correlation_expression = compact(correlation["inputs"]["expression"])
    created_record_id = r"\$vars\.recordcreated\.output\.id"
    updated_record_id = r"\$vars\.waitforapprovalupdate\.output\.id"
    assert re.search(
        rf"(?:{created_record_id}(?:===|==){updated_record_id}|"
        rf"{updated_record_id}(?:===|==){created_record_id})",
        correlation_expression,
    )

    data_fabric_updates = nodes_of_type(
        flow, "uipath.connector.uipath-uipath-dataservice.update-entity-record"
    )
    assert {
        update["display"]["label"] for update in data_fabric_updates
    } == {
        "Persist Triaging",
        "Persist Needs Manual Triage",
        "Persist Awaiting Approval",
        "Persist Approved",
        "Persist Rejected",
        "Persist Updating",
        "Persist Resolved",
        "Update Case ID on record",
    }
    for data_fabric_update in data_fabric_updates:
        record_ids = values_named(data_fabric_update, "recordId")
        assert record_ids, f"missing recordId input on {data_fabric_update['id']}"
        # the editor may or may not parenthesize the expression body
        assert re.search(
            r"=js:\(?\$vars\.recordCreated\.output\.Id\)?",
            json.dumps(record_ids),
        ), data_fabric_update["id"]

    triage = node_with_label(flow, "Grounded Dispute Triage")
    triaging_persistence = node_with_label(flow, "Persist Triaging")
    triage_edges = outgoing(flow, triage["id"], "success")
    assert len(triage_edges) == 1
    assert triage_edges[0]["targetNodeId"] == triaging_persistence["id"]
    triaging_edges = outgoing(flow, triaging_persistence["id"])
    assert len(triaging_edges) == 1
    assert triaging_edges[0]["targetNodeId"] == node_with_label(
        flow, "Supported and confident?"
    )["id"]

    awaiting_approval_persistence = node_with_label(flow, "Persist Awaiting Approval")
    normalize_edges = outgoing(flow, normalize["id"], "success")
    assert len(normalize_edges) == 1
    assert normalize_edges[0]["targetNodeId"] == awaiting_approval_persistence["id"]
    awaiting_approval_edges = outgoing(flow, awaiting_approval_persistence["id"])
    assert len(awaiting_approval_edges) == 1
    assert awaiting_approval_edges[0]["targetNodeId"] == wait["id"]

    wait_edges = outgoing(flow, wait["id"])
    assert len(wait_edges) == 1
    assert wait_edges[0]["targetNodeId"] == correlation["id"]
    assert wait_edges[0]["targetPort"] == "input"

    mismatched_edges = outgoing(flow, correlation["id"], "false")
    assert len(mismatched_edges) == 1
    assert mismatched_edges[0]["targetNodeId"] == wait["id"]
    assert mismatched_edges[0]["targetPort"] == "input"

    decision_present = node_with_label(flow, "Approval decision supplied?")
    assert decision_present["type"] == "core.logic.decision"
    assert "$vars.waitForApprovalUpdate.output.approvalDecision" in decision_present[
        "inputs"
    ]["expression"]
    matched_edges = outgoing(flow, correlation["id"], "true")
    assert len(matched_edges) == 1
    assert matched_edges[0]["targetNodeId"] == decision_present["id"]
    assert matched_edges[0]["targetPort"] == "input"
    decisionless_edges = outgoing(flow, decision_present["id"], "false")
    assert len(decisionless_edges) == 1
    assert decisionless_edges[0]["targetNodeId"] == wait["id"]
    assert decisionless_edges[0]["targetPort"] == "input"

    update_nodes = [
        node
        for node in flow["nodes"]
        if node["type"].startswith("uipath.core.api-workflow.")
    ]
    assert len(update_nodes) == 1
    update = update_nodes[0]

    outlook_nodes = [
        node
        for node in flow["nodes"]
        if node["type"].startswith("uipath.connector.")
        and "uipath-microsoft-outlook365" in node["type"].casefold()
        and "send-email" in node["type"].casefold()
    ]
    assert len(outlook_nodes) == 1
    outlook = outlook_nodes[0]

    needs_rework = end_with_status(flow, "needs_rework")
    resolved = end_with_status(flow, "resolved")
    ends = nodes_of_type(flow, "core.control.end")
    assert len(ends) == 3
    assert {
        end["id"] for end in ends
    } == {
        end_with_status(flow, "needs_manual_triage")["id"],
        needs_rework["id"],
        resolved["id"],
    }

    approval_decision = node_with_label(flow, "Resolution approved?")
    assert approval_decision["type"] == "core.logic.decision"
    assert "$vars.waitForApprovalUpdate.output.approvalDecision" in approval_decision[
        "inputs"
    ]["expression"]
    decision_edges = outgoing(flow, decision_present["id"], "true")
    assert len(decision_edges) == 1
    assert decision_edges[0]["targetNodeId"] == approval_decision["id"]
    assert decision_edges[0]["targetPort"] == "input"

    rejection_edges = outgoing(flow, approval_decision["id"], "false")
    assert len(rejection_edges) == 1
    rejection_edge = rejection_edges[0]
    rejected_persistence = node_with_label(flow, "Persist Rejected")
    assert rejection_edge["targetNodeId"] == rejected_persistence["id"]
    rejected_edges = outgoing(flow, rejected_persistence["id"])
    assert len(rejected_edges) == 1
    assert rejected_edges[0]["targetNodeId"] == needs_rework["id"]
    rejection_reachable = reachable(flow, rejection_edge["targetNodeId"])
    assert {
        node_id for node_id in rejection_reachable if nodes[node_id]["type"] == "core.control.end"
    } == {needs_rework["id"]}
    assert update["id"] not in rejection_reachable
    assert outlook["id"] not in rejection_reachable
    assert wait["id"] not in rejection_reachable

    approval_edges = outgoing(flow, approval_decision["id"], "true")
    assert len(approval_edges) == 1
    approval_edge = approval_edges[0]
    approved_persistence = node_with_label(flow, "Persist Approved")
    updating_persistence = node_with_label(flow, "Persist Updating")
    resolved_persistence = node_with_label(flow, "Persist Resolved")
    assert approval_edge["targetNodeId"] == approved_persistence["id"]
    approved_edges = outgoing(flow, approved_persistence["id"])
    assert len(approved_edges) == 1
    assert approved_edges[0]["targetNodeId"] == updating_persistence["id"]
    updating_edges = outgoing(flow, updating_persistence["id"])
    assert len(updating_edges) == 1
    assert updating_edges[0]["targetNodeId"] == update["id"]
    approval_reachable = reachable(flow, approval_edge["targetNodeId"])
    assert {
        node_id for node_id in approval_reachable if nodes[node_id]["type"] == "core.control.end"
    } == {resolved["id"]}
    assert {node_id for node_id in approval_reachable if node_id == update["id"]} == {
        update["id"]
    }
    assert {node_id for node_id in approval_reachable if node_id == outlook["id"]} == {
        outlook["id"]
    }

    update_edges = outgoing(flow, update["id"])
    assert len(update_edges) == 1
    assert update_edges[0]["targetNodeId"] == outlook["id"]
    outlook_edges = outgoing(flow, outlook["id"])
    assert len(outlook_edges) == 1
    assert outlook_edges[0]["targetNodeId"] == resolved_persistence["id"]
    resolved_edges = outgoing(flow, resolved_persistence["id"])
    assert len(resolved_edges) == 1
    assert resolved_edges[0]["targetNodeId"] == resolved["id"]

    expected_update_bindings = {
        "caseId": f"=js:$vars.{normalize['id']}.output.caseId",
        "disputeType": f"=js:$vars.{normalize['id']}.output.disputeType",
        "actionCode": f"=js:$vars.{normalize['id']}.output.actionCode",
        "adjustmentAmount": f"=js:$vars.{normalize['id']}.output.adjustmentAmount",
        "approvedBy": "=js:$vars.waitForApprovalUpdate.output.approvedBy",
        "approvalComments": "=js:$vars.waitForApprovalUpdate.output.approvalComments",
    }
    for input_name, expected_binding in expected_update_bindings.items():
        configured_values = values_named(update, input_name)
        assert configured_values, f"missing MockUpdateDispute input {input_name}"
        assert expected_binding in json.dumps(configured_values)

    recipient_binding = "=js:$vars.recordCreated.output.recipientEmail"
    to_values = values_named(outlook, "message.toRecipients")
    assert to_values
    assert bindings_in(to_values) == [recipient_binding]
    assert "caseid" not in json.dumps(to_values).casefold()
    assert "customer" not in json.dumps(to_values).casefold()

    subject_values = values_named(outlook, "message.subject")
    body_values = values_named(outlook, "message.body.content")
    assert subject_values
    assert body_values
    assert bindings_in(subject_values) == [
        f"=js:$vars.{normalize['id']}.output.emailSubject"
    ]
    assert bindings_in(body_values) == [f"=js:$vars.{normalize['id']}.output.emailBody"]
    assert values_named(outlook, "saveAsDraft") == [False]

    resolved_outputs = resolved["outputs"]
    assert "true" in json.dumps(resolved_outputs["emailSent"]).casefold()
    assert f"=js:$vars.{update['id']}.output" in json.dumps(
        resolved_outputs["updateResult"]
    )

    rework_outputs = needs_rework["outputs"]
    assert "false" in json.dumps(rework_outputs["emailSent"]).casefold()
    assert "null" in json.dumps(rework_outputs["updateResult"]).casefold()
    assert "$vars.waitForApprovalUpdate.output.approvalComments" in json.dumps(
        rework_outputs["approvalComments"]
    )
    for outputs in (rework_outputs, resolved_outputs):
        assert "$vars.waitForApprovalUpdate.output.approvalDecision" in json.dumps(
            outputs["approvalDecision"]
        )
        assert "$vars.waitForApprovalUpdate.output.approvalComments" in json.dumps(
            outputs["approvalComments"]
        )

    for node in flow["nodes"]:
        node_text = f"{node['type']} {node.get('display', {}).get('label', '')}".casefold()
        assert "retry" not in node_text
        assert "catch" not in node_text
        assert "technical error" not in node_text


def test_mock_update_uses_the_deployed_api_workflow_folder():
    """The flow resolves MockUpdateDispute in the deployed solution folder, but the
    solution binding must stay solution-relative.

    Naming the live folder in bindings_v2.json makes `uip solution pack` look the
    process up in Orchestrator and bind to the release the deployment already owns
    (resource `MockUpdateDispute_1`). Deploying that package back over the same
    deployment fails with Orchestrator 4010 — "contains resources which have already
    been installed by the current deployment".
    """
    flow, _, _ = load_contract()
    flow_binding = next(
        binding
        for binding in flow["bindings"]
        if binding["id"] == "bMockUpdateDisputeFolderPath"
    )
    bindings = load_json(BINDINGS_PATH)
    solution_binding = next(
        binding
        for binding in bindings["resources"]
        if binding["key"] == flow_binding["resourceKey"]
    )

    assert flow_binding["default"] == "JD/demos"
    assert solution_binding["value"]["folderPath"]["defaultValue"] == "solution_folder"


def test_mock_update_definition_exposes_the_api_workflow_argument_contract():
    flow, _, _ = load_contract()
    definition = next(
        definition
        for definition in flow["definitions"]
        if definition["nodeType"].startswith("uipath.core.api-workflow.")
    )

    assert {
        name: schema["type"]
        for name, schema in definition["inputDefinition"]["properties"].items()
    } == {
        "caseId": "string",
        "disputeType": "string",
        "actionCode": "string",
        "adjustmentAmount": "number",
        "approvedBy": "string",
        "approvalComments": "string",
    }
    assert definition["inputDefaults"]["adjustmentAmount"] == 0
    assert definition["outputDefinition"]["output"]["schema"]["properties"] == {
        "updateId": {"type": "string"},
        "status": {"type": "string"},
        "updatedAt": {"type": "string"},
        "message": {"type": "string"},
    }


def test_agent_resources_registry_bindings_and_generated_variables_are_complete():
    flow, _, nodes = load_contract()
    expected_resources = {
        "arDisputeTriageIndex1": (
            "uipath.agent.resource.context.index.ar-dispute-triage-index.a1b7fb4e-cfb3-43a8-b29e-08defd736a4b",
            "b77b72f2-60cf-408c-af9d-28f742a7b3bc",
            "triageAgent",
            "context",
        ),
        "arPaymentResolutionIndex1": (
            "uipath.agent.resource.context.index.ar-payment-resolution-index.9745fa62-cff9-45d4-b29f-08defd736a4b",
            "1ad2e73a-662b-4fbc-8efe-771a5c4f4897",
            "paymentMisapplicationAgent",
            "context",
        ),
        "lookuppaymentapplication1": (
            "uipath.agent.resource.tool.api.e2a2f52e-30ba-4ce0-a1b0-0a45a7b04898",
            "544b3390-6e9b-4314-b3ef-5a5a45b282c4",
            "paymentMisapplicationAgent",
            "tool",
        ),
    }
    definitions = {
        (definition["nodeType"], definition["version"]): definition
        for definition in flow["definitions"]
    }
    artifact_edges = {
        (
            edge["sourceNodeId"],
            edge["sourcePort"],
            edge["targetNodeId"],
            edge["targetPort"],
        )
        for edge in flow["edges"]
        if edge["sourcePort"] in ARTIFACT_PORTS
    }

    assert len(artifact_edges) == len(expected_resources)
    for node_id, (node_type, source, parent_id, parent_port) in expected_resources.items():
        node = nodes[node_id]
        assert node["type"] == node_type
        assert node["inputs"] == {"source": source}
        definition = definitions[(node_type, node["typeVersion"])]
        assert definition["model"]["source"] is True
        assert (parent_id, parent_port, node_id, "input") in artifact_edges

    api_resource_key = "JD/demos.LookupPaymentApplication"
    api_definition = definitions[
        (expected_resources["lookuppaymentapplication1"][0], "1.0.0")
    ]
    assert api_definition["model"]["bindings"]["resourceKey"] == api_resource_key
    # Binding ids are CLI-generated and churn on every editor save, so the contract
    # is the semantic tuple, not the id.
    mock_update_key = "e0be5a37-e1a7-4871-ae3c-d9a0e8398cbd"
    assert [
        (
            binding["resourceKey"],
            binding["propertyAttribute"],
            binding.get("default"),
            binding["resourceSubType"],
        )
        for binding in flow["bindings"]
        if binding["resource"] == "process"
    ] == [
        (mock_update_key, "name", "MockUpdateDispute", "Api"),
        (mock_update_key, "folderPath", "JD/demos", "Api"),
        (api_resource_key, "name", "LookupPaymentApplication", "Api"),
        (api_resource_key, "folderPath", "JD/demos", "Api"),
        (
            api_resource_key,
            "folderKey",
            "e716bfc7-4c75-4921-ab5b-e5a3bc0d4c2c",
            "Api",
        ),
    ]

    connection_bindings = [
        binding for binding in flow["bindings"] if binding["resource"] == "connection"
    ]
    assert [
        (binding["name"], binding["resourceKey"], binding["propertyAttribute"])
        for binding in connection_bindings
    ] == [
        (
            "uipath-microsoft-outlook365 connection",
            "8643408a-62b4-4d36-ba1e-bc9b68d4fce9",
            "ConnectionId",
        ),
        (
            "FolderKey",
            "8643408a-62b4-4d36-ba1e-bc9b68d4fce9",
            "FolderKey",
        ),
        (
            "uipath-uipath-dataservice connection",
            "b2a02899-3708-4bb6-810a-02321afb77f6",
            "ConnectionId",
        ),
        (
            "FolderKey",
            "b2a02899-3708-4bb6-810a-02321afb77f6",
            "FolderKey",
        ),
    ]

    node_variables = flow["variables"]["nodes"]
    assert len({variable["id"] for variable in node_variables}) == len(node_variables)
    generated_bindings = {
        (variable["binding"]["nodeId"], variable["binding"]["outputId"]): variable["id"]
        for variable in node_variables
    }
    required_bindings = {
        ("recordCreated", "output"),
        ("triageAgent", "error"),
        ("poMismatchAgent", "error"),
        ("missingPodAgent", "error"),
        ("paymentMisapplicationAgent", "error"),
        ("normalizeProposal", "output"),
        ("normalizeProposal", "error"),
        ("waitForApprovalUpdate", "output"),
        ("mockUpdateDispute1", "output"),
        ("mockUpdateDispute1", "error"),
        ("sendEmail1", "output"),
        ("sendEmail1", "error"),
    }
    assert required_bindings <= set(generated_bindings)
    for node_id, output_id in required_bindings:
        assert generated_bindings[(node_id, output_id)] == f"{node_id}.{output_id}"
    for end in nodes_of_type(flow, "core.control.end"):
        for output_id in RESULT_FIELDS:
            assert generated_bindings[(end["id"], output_id)] == (
                f"{end['id']}.{output_id}"
            )
