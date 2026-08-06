import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = (
    ROOT / "solution" / "ARCollectionsDemo" / "MockUpdateDispute" / "Workflow.json"
)

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


def test_mock_update_exposes_exact_input_and_output_contracts():
    workflow = load_workflow()

    assert schema_types(workflow, "input") == EXPECTED_INPUT_TYPES
    assert schema_types(workflow, "output") == EXPECTED_OUTPUT_TYPES
    assert required_fields(workflow, "input") == set(EXPECTED_INPUT_TYPES)
    assert required_fields(workflow, "output") == set(EXPECTED_OUTPUT_TYPES)


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
