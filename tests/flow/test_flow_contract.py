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

SUPPORTED_ROUTES = {
    "po_mismatch": "poMismatch",
    "missing_pod": "missingPod",
    "payment_misapplication": "paymentMisapplication",
}
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
    start_edges = outgoing(flow, created[0]["id"], "output")
    assert len(start_edges) == 1
    assert start_edges[0]["targetNodeId"] == triage["id"]
    assert start_edges[0]["targetPort"] == "input"


def test_flow_uses_all_mapped_inline_agents_with_exact_runtime_contracts():
    flow, mapping, _ = load_contract()
    agents = nodes_of_type(flow, "uipath.agent.autonomous")
    by_source = {node.get("inputs", {}).get("source"): node for node in agents}
    assert len(agents) == 4
    assert set(by_source) == set(mapping.values())

    triage = by_source[mapping["triage"]]
    triage_inputs = {
        item["id"]: item for item in triage["inputs"]["agentInputVariables"]
    }
    assert set(triage_inputs) == {"recordCreated__output__output"}
    assert triage_inputs["recordCreated__output__output"]["type"] == "object"
    assert (
        triage_inputs["recordCreated__output__output"]["binding"]
        == "=$vars.recordCreated.output"
    )
    assert {item["id"]: item["type"] for item in triage["inputs"]["agentOutputVariables"]} == {
        "disputeType": "string",
        "rationale": "string",
        "confidence": "number",
    }

    specialist_inputs = {
        "recordCreated__output__output": ("object", "=$vars.recordCreated.output"),
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
    for logical_name in SUPPORTED_ROUTES.values():
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
        logical_name: next(
            node["id"]
            for node in flow["nodes"]
            if node.get("inputs", {}).get("source") == mapping[logical_name]
        )
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
        node
        for node in nodes_of_type(flow, "uipath.agent.autonomous")
        if node.get("inputs", {}).get("source")
        in {mapping[name] for name in SUPPORTED_ROUTES.values()}
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
    }
    for data_fabric_update in data_fabric_updates:
        record_ids = values_named(data_fabric_update, "recordId")
        assert record_ids, f"missing recordId input on {data_fabric_update['id']}"
        assert "=js:$vars.recordCreated.output.Id" in json.dumps(record_ids)

    assert wait["id"] in reachable(flow, normalize["id"])
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

    assert flow_binding["default"] == "JD_Demos/demos/ARCollectionsDemo"
    assert solution_binding["value"]["folderPath"]["defaultValue"] == (
        "JD_Demos/demos/ARCollectionsDemo"
    )


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
        "triageTaxonomyContext": (
            "uipath.agent.resource.context.index.ar-dispute-triage-index.9e46f4a3-6c15-4cab-9030-08def39d8059",
            "deb897d4-bdfb-4ba0-8cbc-63b7d36bb6d3",
            "triageAgent",
            "context",
        ),
        "paymentResolutionContext": (
            "uipath.agent.resource.context.index.ar-payment-resolution-index.469965c2-8382-4521-9031-08def39d8059",
            "3164f987-7d12-47bd-ba72-815bdc1dbbcd",
            "paymentMisapplicationAgent",
            "context",
        ),
        "lookupPaymentTool": (
            "uipath.agent.resource.tool.api.cc99e8d4-57b5-4c6a-b563-29d6fb143b9b",
            "01605eeb-d428-49af-81b4-0d5ca844af2f",
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

    api_resource_key = "cc99e8d4-57b5-4c6a-b563-29d6fb143b9b"
    api_definition = definitions[
        (expected_resources["lookupPaymentTool"][0], "1.0.0")
    ]
    assert api_definition["model"]["bindings"]["resourceKey"] == api_resource_key
    expected_lookup_bindings = [
        {
            "id": "bLookupPaymentName",
            "name": "name",
            "type": "string",
            "resource": "process",
            "resourceKey": api_resource_key,
            "default": "LookupPaymentApplication",
            "propertyAttribute": "name",
            "resourceSubType": "Api",
        },
        {
            "id": "bLookupPaymentFolderPath",
            "name": "folderPath",
            "type": "string",
            "resource": "process",
            "resourceKey": api_resource_key,
            "default": "solution_folder",
            "propertyAttribute": "folderPath",
            "resourceSubType": "Api",
        },
    ]
    mock_update_key = "e0be5a37-e1a7-4871-ae3c-d9a0e8398cbd"
    expected_mock_update_bindings = [
        {
            "id": "bMockUpdateDisputeName",
            "name": "name",
            "type": "string",
            "resource": "process",
            "resourceKey": mock_update_key,
            "default": "MockUpdateDispute",
            "propertyAttribute": "name",
            "resourceSubType": "Api",
        },
        {
            "id": "bMockUpdateDisputeFolderPath",
            "name": "folderPath",
            "type": "string",
            "resource": "process",
            "resourceKey": mock_update_key,
            "default": "JD_Demos/demos/ARCollectionsDemo",
            "propertyAttribute": "folderPath",
            "resourceSubType": "Api",
        },
    ]
    assert [
        binding for binding in flow["bindings"] if binding["resource"] == "process"
    ] == expected_lookup_bindings + expected_mock_update_bindings

    connection_bindings = [
        binding for binding in flow["bindings"] if binding["resource"] == "connection"
    ]
    assert [
        (binding["name"], binding["resourceKey"], binding["propertyAttribute"])
        for binding in connection_bindings
    ] == [
        (
            "uipath-microsoft-outlook365 connection",
            "c61c5442-c5d6-4cb2-9c02-f4a541f01e4c",
            "ConnectionId",
        ),
        (
            "FolderKey",
            "c61c5442-c5d6-4cb2-9c02-f4a541f01e4c",
            "FolderKey",
        ),
        (
            "uipath-uipath-dataservice connection",
            "6cd4c047-ab49-4aad-8cfa-5681db3db20b",
            "ConnectionId",
        ),
        (
            "FolderKey",
            "6cd4c047-ab49-4aad-8cfa-5681db3db20b",
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
