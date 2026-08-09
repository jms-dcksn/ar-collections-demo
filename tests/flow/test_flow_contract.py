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
COMMON_CASE_FIELDS = {
    "caseId",
    "customerName",
    "customerAccountId",
    "invoiceNumber",
    "outstandingBalance",
    "customerReason",
    "openedDate",
    "evidence",
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


def fixture_sections(script):
    positions = []
    for case_id in ("AR-PO-001", "AR-POD-002", "AR-PAY-003", "AR-AMB-004"):
        assert case_id in script
        positions.append((script.index(case_id), case_id))
    positions.sort()
    sections = {}
    for index, (start, case_id) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(script)
        sections[case_id] = script[start:end]
    return sections


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


def test_start_contract_and_deterministic_loader_cover_all_approved_fixtures():
    flow, _, _ = load_contract()
    starts = nodes_of_type(flow, "core.trigger.manual")
    assert len(starts) == 1
    start = starts[0]

    globals_ = flow.get("variables", {}).get("globals", [])
    start_inputs = {
        variable["id"]: variable
        for variable in globals_
        if variable.get("direction") in {"in", "inout"}
    }
    assert set(start_inputs) == {"caseId", "recipientEmail"}
    for variable in start_inputs.values():
        assert variable["direction"] == "in"
        assert variable["type"] == "string"
        assert variable["triggerNodeId"] == start["id"]

    loader = node_with_label(flow, "Load Sample Case")
    assert loader["type"] == "core.action.script"
    script = loader["inputs"]["script"]
    sections = fixture_sections(script)
    for section in sections.values():
        for field in COMMON_CASE_FIELDS:
            assert field.casefold() in section.casefold()

    expected_values = {
        "AR-PO-001": (
            "Northstar Manufacturing",
            "NORTHSTAR-1701",
            "INV-10471",
            "48750",
            "2026-07-07",
            "invoiceAmount",
            "poAuthorizedAmount",
            "47250",
            "difference",
            "1500",
        ),
        "AR-POD-002": (
            "Riverbend Retail",
            "RIVERBEND-2904",
            "INV-20482",
            "22400",
            "2026-07-10",
            "2026-06-18",
            "M. Chen",
            "quantitiesMatch",
            "true",
        ),
        "AR-PAY-003": (
            "Summit Medical Distribution",
            "SUMMIT-4402",
            "INV-30915",
            "36800",
            "2026-07-14",
            "reportedPayment",
            "PAY-77821",
        ),
        "AR-AMB-004": (
            "Lakeshore Components",
            "INV-40102",
            "12800",
            "The balance does not look right; please investigate",
        ),
    }
    for case_id, values in expected_values.items():
        section = sections[case_id].casefold()
        for value in values:
            assert value.casefold() in section

    payment_section = sections["AR-PAY-003"].casefold()
    assert "applicationstatus" not in payment_section
    assert "appliedinvoicenumber" not in payment_section
    assert "evidence:{}" in compact(sections["AR-AMB-004"])
    assert "throw" in script.casefold()
    assert "caseid" in script.casefold()

    start_to_loader = outgoing(flow, start["id"], "output")
    assert len(start_to_loader) == 1
    assert start_to_loader[0]["targetNodeId"] == loader["id"]
    assert start_to_loader[0]["targetPort"] == "input"


def test_sample_case_loader_serializes_evidence_for_data_fabric():
    flow, _, _ = load_contract()
    script = node_with_label(flow, "Load Sample Case")["inputs"]["script"]

    assert "JSON.stringify(cases[caseId].evidence)" in script
    assert "return { ...cases[caseId], evidence:" in script


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
    assert set(triage_inputs) == {"loadSampleCase__output__output"}
    assert triage_inputs["loadSampleCase__output__output"]["type"] == "object"
    assert (
        triage_inputs["loadSampleCase__output__output"]["binding"]
        == "=$vars.loadSampleCase.output"
    )
    assert {item["id"]: item["type"] for item in triage["inputs"]["agentOutputVariables"]} == {
        "disputeType": "string",
        "rationale": "string",
        "confidence": "number",
    }

    specialist_inputs = {
        "loadSampleCase__output__output": ("object", "=$vars.loadSampleCase.output"),
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
    decisions = nodes_of_type(flow, "core.logic.decision")
    switches = nodes_of_type(flow, "core.logic.switch")
    assert len(decisions) == 2
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
    flow, mapping, nodes = load_contract()
    decision = node_with_label(flow, "Supported and confident?")
    assert decision["type"] == "core.logic.decision"
    false_edges = outgoing(flow, decision["id"], "false")
    assert len(false_edges) == 1
    assert false_edges[0]["targetPort"] == "input"

    manual_end = nodes[false_edges[0]["targetNodeId"]]
    assert manual_end["type"] == "core.control.end"
    assert "needs_manual_triage" in json.dumps(manual_end).casefold()
    manual_reachable = reachable(flow, manual_end["id"])

    specialist_sources = {mapping[name] for name in SUPPORTED_ROUTES.values()}

    def is_forbidden(node):
        node_type = node["type"]
        return (
            node.get("inputs", {}).get("source") in specialist_sources
            or node_type.startswith("uipath.core.api-workflow.")
            or node_type == "uipath.human-in-the-loop.quick-form"
            or node_type.startswith("uipath.connector.")
        )

    assert not any(is_forbidden(nodes[node_id]) for node_id in manual_reachable)

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
    start = nodes_of_type(flow, "core.trigger.manual")[0]
    for end in ends:
        assert set(end.get("outputs", {})) == RESULT_FIELDS
        assert f"=js:$vars.{start['id']}.output.caseId" in json.dumps(
            end["outputs"]["resultCaseId"]
        )


def test_collector_approval_routes_rejection_and_approval_to_their_business_exits():
    flow, _, nodes = load_contract()
    normalize = node_with_label(flow, "Normalize Proposal")
    quick_forms = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")
    assert len(quick_forms) == 1
    quick_form = quick_forms[0]

    fields = {field["id"]: field for field in quick_form["inputs"]["schema"]["fields"]}
    expected_input_fields = {
        "customerName": ("string", "vars.loadSampleCase.output.customerName"),
        "invoiceNumber": ("string", "vars.loadSampleCase.output.invoiceNumber"),
        "outstandingBalance": ("number", "vars.loadSampleCase.output.outstandingBalance"),
        "disputeType": ("string", "vars.triageAgent.output.disputeType"),
        "triageRationale": ("string", "vars.triageAgent.output.rationale"),
        "triageConfidence": ("number", "vars.triageAgent.output.confidence"),
        "evidenceSummary": ("string", "vars.normalizeProposal.output.evidenceSummary"),
        "rootCause": ("string", "vars.normalizeProposal.output.rootCause"),
        "recommendedAction": ("string", "vars.normalizeProposal.output.recommendedAction"),
        "actionCode": ("string", "vars.normalizeProposal.output.actionCode"),
        "adjustmentAmount": ("number", "vars.normalizeProposal.output.adjustmentAmount"),
        "specialistConfidence": ("number", "vars.normalizeProposal.output.confidence"),
        "emailSubject": ("string", "vars.normalizeProposal.output.emailSubject"),
        "emailBody": ("string", "vars.normalizeProposal.output.emailBody"),
    }
    assert set(fields) == set(expected_input_fields) | {"approvedBy", "approvalComments"}
    for field_id, (field_type, binding) in expected_input_fields.items():
        assert fields[field_id]["type"] == field_type
        assert fields[field_id]["direction"] == "input"
        assert fields[field_id]["binding"] == binding
        assert fields[field_id]["label"].strip()
    for field_id, variable in {
        "approvedBy": "vars.approvedBy",
        "approvalComments": "vars.approvalCommentsInput",
    }.items():
        assert fields[field_id]["type"] == "string"
        assert fields[field_id]["direction"] == "output"
        assert fields[field_id]["variable"] == variable
        assert fields[field_id]["required"] is True
        assert fields[field_id]["label"].strip()
    assert quick_form["inputs"]["schema"]["outcomes"] == [
        {
            "id": "approve",
            "name": "Approve",
            "type": "string",
            "isPrimary": True,
            "action": "Continue",
        },
        {
            "id": "reject",
            "name": "Reject",
            "type": "string",
            "isPrimary": False,
            "action": "End",
        },
    ]

    normalize_edges = outgoing(flow, normalize["id"], "success")
    assert len(normalize_edges) == 1
    assert normalize_edges[0]["targetNodeId"] == quick_form["id"]
    assert normalize_edges[0]["targetPort"] == "input"

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

    completed_edges = outgoing(flow, quick_form["id"], "completed")
    assert len(completed_edges) == 1
    completed_edge = completed_edges[0]
    assert completed_edge["targetPort"] == "input"
    approval_decision = nodes[completed_edge["targetNodeId"]]
    assert approval_decision["type"] == "core.logic.decision"

    rejection_edges = outgoing(flow, approval_decision["id"], "false")
    assert len(rejection_edges) == 1
    rejection_edge = rejection_edges[0]
    assert rejection_edge["targetNodeId"] == needs_rework["id"]
    rejection_reachable = reachable(flow, rejection_edge["targetNodeId"])
    assert {
        node_id for node_id in rejection_reachable if nodes[node_id]["type"] == "core.control.end"
    } == {needs_rework["id"]}
    assert update["id"] not in rejection_reachable
    assert outlook["id"] not in rejection_reachable

    approval_edges = outgoing(flow, approval_decision["id"], "true")
    assert len(approval_edges) == 1
    approval_edge = approval_edges[0]
    assert approval_edge["targetNodeId"] == update["id"]
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
    assert outlook_edges[0]["targetNodeId"] == resolved["id"]

    expected_update_bindings = {
        "caseId": f"=js:$vars.{normalize['id']}.output.caseId",
        "disputeType": f"=js:$vars.{normalize['id']}.output.disputeType",
        "actionCode": f"=js:$vars.{normalize['id']}.output.actionCode",
        "adjustmentAmount": f"=js:$vars.{normalize['id']}.output.adjustmentAmount",
        "approvedBy": f"=js:$vars.{quick_form['id']}.output.approvedBy",
        "approvalComments": f"=js:$vars.{quick_form['id']}.output.approvalCommentsInput",
    }
    for input_name, expected_binding in expected_update_bindings.items():
        configured_values = values_named(update, input_name)
        assert configured_values, f"missing MockUpdateDispute input {input_name}"
        assert expected_binding in json.dumps(configured_values)

    start = nodes_of_type(flow, "core.trigger.manual")[0]
    recipient_binding = f"=js:$vars.{start['id']}.output.recipientEmail"
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
    assert f"$vars.{quick_form['id']}.output.approvalCommentsInput" in json.dumps(
        rework_outputs["approvalComments"]
    )

    for node in flow["nodes"]:
        node_text = f"{node['type']} {node.get('display', {}).get('label', '')}".casefold()
        assert "retry" not in node_text
        assert "catch" not in node_text
        assert "technical error" not in node_text


def test_mock_update_uses_the_generated_quick_form_output_property():
    flow, _, _ = load_contract()
    quick_form = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")[0]
    update = next(
        node
        for node in flow["nodes"]
        if node["type"].startswith("uipath.core.api-workflow.")
    )

    comment_field = next(
        field
        for field in quick_form["inputs"]["schema"]["fields"]
        if field["id"] == "approvalComments"
    )
    generated_property = comment_field["variable"].removeprefix("vars.")

    assert update["inputs"]["approvalComments"] == (
        f"=js:$vars.{quick_form['id']}.output.{generated_property}"
    )


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


def test_quick_form_omits_labels_that_break_app_tasks_external_tag_validation():
    flow, _, _ = load_contract()
    quick_form = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")[0]

    assert "labels" not in quick_form["inputs"]


def test_quick_form_is_rebuilt_with_fresh_canonical_task_metadata():
    flow, _, _ = load_contract()
    quick_form = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")[0]
    inputs = quick_form["inputs"]
    schema = inputs["schema"]

    assert quick_form["id"] != "reviewArDisputeResolution1"
    assert inputs["type"] == "quick"
    assert "id" in schema
    assert "schemaId" not in schema
    assert inputs["recipient"]["channels"] == ["ActionCenter"]
    assert inputs["recipient"]["connections"] == {}


def test_quick_form_routes_only_through_its_declared_completed_handle():
    flow, _, _ = load_contract()
    quick_form = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")[0]

    assert [edge["sourcePort"] for edge in outgoing(flow, quick_form["id"])] == [
        "completed"
    ]


def test_agent_resources_registry_bindings_and_generated_variables_are_complete():
    flow, _, nodes = load_contract()
    quick_form = nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")[0]
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

    outlook_bindings = [
        binding for binding in flow["bindings"] if binding["resource"] == "connection"
    ]
    assert len(outlook_bindings) == 2
    assert {binding["propertyAttribute"] for binding in outlook_bindings} == {
        "ConnectionId",
        "FolderKey",
    }
    assert {binding["resourceKey"] for binding in outlook_bindings} == {
        binding["default"]
        for binding in outlook_bindings
        if binding["propertyAttribute"] == "ConnectionId"
    }

    node_variables = flow["variables"]["nodes"]
    assert len({variable["id"] for variable in node_variables}) == len(node_variables)
    generated_bindings = {
        (variable["binding"]["nodeId"], variable["binding"]["outputId"]): variable["id"]
        for variable in node_variables
    }
    required_bindings = {
        ("start", "output"),
        ("loadSampleCase", "output"),
        ("loadSampleCase", "error"),
        ("triageAgent", "error"),
        ("poMismatchAgent", "error"),
        ("missingPodAgent", "error"),
        ("paymentMisapplicationAgent", "error"),
        ("normalizeProposal", "output"),
        ("normalizeProposal", "error"),
        (quick_form["id"], "output"),
        (quick_form["id"], "status"),
        ("isResolutionApproved", "matchedCase"),
        ("isResolutionApproved", "matchedCaseId"),
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
