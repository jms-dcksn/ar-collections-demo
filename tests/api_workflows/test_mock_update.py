import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = (
    ROOT / "solution" / "ARCollectionsDemo" / "MockUpdateDispute" / "Workflow.json"
)
ENTRY_POINTS_PATH = WORKFLOW_PATH.with_name("entry-points.json")
VERIFIER_PATH = Path(__file__).with_name("verify_mock_update.py")

EXPECTED_INPUT_TYPES = {
    "caseId": "string",
    "disputeType": "string",
    "actionCode": "string",
    "adjustmentAmount": "number",
    "approvedBy": "string",
    "approvalComments": "string",
}
EXPECTED_OUTPUT_TYPES = {
    "updateId": "string",
    "status": "string",
    "updatedAt": "string",
    "message": "string",
}
FORBIDDEN_RESOURCE_KEYS = {
    "connectionId",
    "connectionResourceId",
    "resourceKey",
    "savedResourceSelections",
    "solutionResourceKey",
}
APPROVED_ACTION_CODES = {"ISSUE_CREDIT", "PROVIDE_POD", "REALLOCATE_PAYMENT"}


def load_workflow() -> dict:
    return json.loads(WORKFLOW_PATH.read_text())


def walk_json(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def schema_types(workflow: dict, contract: str) -> dict[str, str]:
    schema = workflow.get(contract, {}).get("schema", {}).get("document", {})
    properties = schema.get("properties", {})
    return {name: definition.get("type") for name, definition in properties.items()}


def required_fields(workflow: dict, contract: str) -> set[str]:
    schema = workflow.get(contract, {}).get("schema", {}).get("document", {})
    return set(schema.get("required", []))


def load_verifier_module():
    spec = importlib.util.spec_from_file_location("verify_mock_update_under_test", VERIFIER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mock_update_exposes_exact_input_and_output_contracts():
    workflow = load_workflow()

    assert schema_types(workflow, "input") == EXPECTED_INPUT_TYPES
    assert schema_types(workflow, "output") == EXPECTED_OUTPUT_TYPES
    assert required_fields(workflow, "input") == set(EXPECTED_INPUT_TYPES)
    assert required_fields(workflow, "output") == set(EXPECTED_OUTPUT_TYPES)


def test_mock_update_entry_point_exposes_the_workflow_argument_contract():
    workflow = load_workflow()
    entry_points = json.loads(ENTRY_POINTS_PATH.read_text())
    entry_point = entry_points["entryPoints"][0]

    assert entry_point["input"] == workflow["input"]["schema"]["document"]
    assert entry_point["output"] == workflow["output"]["schema"]["document"]


def test_mock_update_has_a_terminating_response_activity():
    workflow = load_workflow()
    response_activities = [
        node
        for node in walk_json(workflow)
        if isinstance(node, dict)
        and node.get("metadata", {}).get("activityType") == "Response"
    ]

    assert response_activities, "Workflow must contain a Response activity"
    assert all("response" in activity for activity in response_activities)
    assert all(activity.get("then") == "end" for activity in response_activities)


def test_mock_update_contains_no_connector_or_network_resource_binding():
    workflow = load_workflow()

    for node in walk_json(workflow):
        if not isinstance(node, dict):
            continue
        assert "call" not in node
        assert not (FORBIDDEN_RESOURCE_KEYS & node.keys())


def test_mock_update_protects_action_validation_and_receipt_construction():
    workflow = load_workflow()
    js_activities = [
        node
        for node in walk_json(workflow)
        if isinstance(node, dict)
        and node.get("metadata", {}).get("activityType") == "JsInvoke"
    ]

    assert len(js_activities) == 1
    script = js_activities[0]["run"]["script"]["code"]
    action_set = re.search(r"new Set\(\[(.*?)\]\)", script, re.DOTALL)
    assert action_set, "JsInvoke must declare the approved action-code set"
    declared_actions = re.findall(r"['\"]([A-Z_]+)['\"]", action_set.group(1))

    assert len(declared_actions) == len(APPROVED_ACTION_CODES)
    assert set(declared_actions) == APPROVED_ACTION_CODES
    assert "const { caseId, actionCode } = $workflow.input;" in script
    assert re.search(
        r"if \(!allowedActionCodes\.has\(actionCode\)\) \{\s*"
        r"throw new Error\(`MockUpdateDispute does not support actionCode "
        r"\$\{actionCode\}\.`\);\s*\}",
        script,
    )
    assert "`UPD-${caseId}-${actionCode}`" in script
    assert "status: 'UPDATED'" in script
    assert "updatedAt: '2026-08-06T12:00:00Z'" in script
    assert "`Recorded ${actionCode} for ${caseId} in MockARDisputeSystem.`" in script


def test_verifier_rejects_unexpected_business_output_fields():
    verifier = load_verifier_module()
    payload = {
        "UpdateId": "UPD-AR-PAY-003-REALLOCATE_PAYMENT",
        "Status": "UPDATED",
        "UpdatedAt": "2026-08-06T12:00:00Z",
        "Message": "Recorded REALLOCATE_PAYMENT for AR-PAY-003 in MockARDisputeSystem.",
        "UnexpectedField": "must not be ignored",
    }

    assert verifier.find_business_output(
        payload, {"updateId", "status", "updatedAt", "message"}
    ) is None


def test_verifier_bounds_runtime_and_reports_timeout_concisely(monkeypatch):
    verifier = load_verifier_module()

    def raise_timeout(command, **kwargs):
        assert kwargs["timeout"] == 60
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(verifier.subprocess, "run", raise_timeout)

    with pytest.raises(
        AssertionError,
        match="MockUpdateDispute verification timed out after 60 seconds",
    ):
        verifier.main()
