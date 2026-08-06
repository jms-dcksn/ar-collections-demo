import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = REPO_ROOT / "solution" / "ARCollectionsDemo" / "LookupPaymentApplication"
WORKFLOW_PATH = PROJECT_DIR / "Workflow.json"

EXPECTED_INPUT_TYPES = {
    "caseId": "string",
    "customerAccountId": "string",
    "invoiceNumber": "string",
    "paymentReference": "string",
}
EXPECTED_OUTPUT_TYPES = {
    "paymentReference": "string",
    "paymentAmount": "number",
    "paymentDate": "string",
    "appliedInvoiceNumber": "string",
    "targetInvoiceNumber": "string",
    "applicationStatus": "string",
    "matchedRemittance": "boolean",
    "recommendedAction": "string",
    "sourceSystem": "string",
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
FORBIDDEN_NETWORK_PATTERNS = {
    "browser network API": re.compile(
        r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(",
        re.IGNORECASE,
    ),
    "sendBeacon": re.compile(r"\bnavigator\s*\.\s*sendBeacon\s*\(", re.IGNORECASE),
    "Node network module": re.compile(
        r"\brequire\s*\(\s*['\"](?:node:)?(?:http|https|net|tls)['\"]\s*\)",
        re.IGNORECASE,
    ),
    "network client method": re.compile(
        r"\b(?:axios|http|https|net|tls)\s*\.\s*(?:get|post|request|connect)\s*\(",
        re.IGNORECASE,
    ),
}


def walk_json(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def assert_exact_schema(workflow, contract_name, expected_types):
    schema = workflow[contract_name]["schema"]["document"]
    actual_types = {
        property_name: property_schema["type"]
        for property_name, property_schema in schema["properties"].items()
    }

    assert actual_types == expected_types
    assert set(schema["required"]) == set(expected_types)


def test_lookup_payment_has_exact_contract_and_no_external_calls():
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    objects = [node for node in walk_json(workflow) if isinstance(node, dict)]

    assert_exact_schema(workflow, "input", EXPECTED_INPUT_TYPES)
    assert_exact_schema(workflow, "output", EXPECTED_OUTPUT_TYPES)
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

    script_content = "\n".join(
        node["run"]["script"]["code"]
        for node in objects
        if isinstance(node.get("run"), dict)
        and isinstance(node["run"].get("script"), dict)
        and isinstance(node["run"]["script"].get("code"), str)
    )
    matched_network_primitives = {
        label
        for label, pattern in FORBIDDEN_NETWORK_PATTERNS.items()
        if pattern.search(script_content)
    }
    assert not matched_network_primitives
