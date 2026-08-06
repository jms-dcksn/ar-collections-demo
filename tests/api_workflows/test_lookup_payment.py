import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = REPO_ROOT / "solution" / "ARCollectionsDemo" / "LookupPaymentApplication"
WORKFLOW_PATH = PROJECT_DIR / "Workflow.json"

EXPECTED_INPUTS = {
    "caseId",
    "customerAccountId",
    "invoiceNumber",
    "paymentReference",
}
EXPECTED_OUTPUTS = {
    "paymentReference",
    "paymentAmount",
    "paymentDate",
    "appliedInvoiceNumber",
    "targetInvoiceNumber",
    "applicationStatus",
    "matchedRemittance",
    "recommendedAction",
    "sourceSystem",
}
FORBIDDEN_ACTIVITY_TYPES = {
    "Connector",
    "HttpRequest",
    "UiPath.Http",
    "UiPath.IntSvc",
}
FORBIDDEN_RESOURCE_KEYS = {
    "call",
    "connectionId",
    "connectionResourceId",
    "connector",
    "savedResourceSelections",
}


def walk_json(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def schema_properties(workflow, contract_name):
    return set(
        workflow[contract_name]["schema"]["document"]["properties"]
    )


def test_lookup_payment_has_exact_contract_and_no_external_calls():
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    objects = [node for node in walk_json(workflow) if isinstance(node, dict)]

    assert schema_properties(workflow, "input") == EXPECTED_INPUTS
    assert schema_properties(workflow, "output") == EXPECTED_OUTPUTS
    assert any(
        node.get("metadata", {}).get("activityType") == "Response"
        and "response" in node
        for node in objects
    )

    activity_types = {
        node.get("metadata", {}).get("activityType") for node in objects
    }
    assert activity_types.isdisjoint(FORBIDDEN_ACTIVITY_TYPES)
    assert all(
        FORBIDDEN_RESOURCE_KEYS.isdisjoint(node)
        for node in objects
    )
