import importlib.util
import json
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_DIR = REPO_ROOT / "solution" / "ARCollectionsDemo" / "LookupPaymentApplication"
WORKFLOW_PATH = PROJECT_DIR / "Workflow.json"
ENTRY_POINTS_PATH = PROJECT_DIR / "entry-points.json"
VERIFIER_PATH = Path(__file__).with_name("verify_lookup_payment.py")

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


def load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "verify_lookup_payment_under_test", VERIFIER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_lookup_script(workflow_input):
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    script = workflow["do"][0]["Sequence_1"]["do"][1]["Javascript_1"]["run"][
        "script"
    ]["code"]
    program = (
        "const $workflow = { input: JSON.parse(process.argv[1]) };"
        f"const result = (() => {{ {script} }})();"
        "process.stdout.write(JSON.stringify(result));"
    )
    return subprocess.run(
        ["node", "-e", program, json.dumps(workflow_input)],
        check=False,
        capture_output=True,
        text=True,
    )


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


def test_lookup_payment_entry_point_exposes_the_workflow_argument_contract():
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    entry_points = json.loads(ENTRY_POINTS_PATH.read_text(encoding="utf-8"))
    entry_point = entry_points["entryPoints"][0]

    assert entry_point["input"] == workflow["input"]["schema"]["document"]
    assert entry_point["output"] == workflow["output"]["schema"]["document"]


def test_lookup_payment_accepts_a_fresh_script_case_id():
    result = run_lookup_script(
        {
            "caseId": "AR-PAY-20260814-A1B2C3D4",
            "customerAccountId": "SUMMIT-4402",
            "invoiceNumber": "INV-30915",
            "paymentReference": "PAY-77821",
        }
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == json.loads(
        Path(__file__).with_name("lookup-payment-expected.json").read_text(
            encoding="utf-8"
        )
    )


def test_lookup_payment_rejects_a_fresh_case_with_an_unrelated_fixture():
    result = run_lookup_script(
        {
            "caseId": "AR-PAY-20260814-A1B2C3D4",
            "customerAccountId": "SUMMIT-4402",
            "invoiceNumber": "INV-99999",
            "paymentReference": "PAY-77821",
        }
    )

    assert result.returncode != 0
    assert "supports only the curated payment demo fixture" in result.stderr


def test_verifier_normalizes_pascal_case_business_keys_exactly():
    verifier = load_verifier_module()
    expected = {
        "paymentReference": "PAY-77821",
        "paymentAmount": 36800,
        "paymentDate": "2026-07-02",
        "appliedInvoiceNumber": "INV-30909",
        "targetInvoiceNumber": "INV-30915",
        "applicationStatus": "MISAPPLIED",
        "matchedRemittance": True,
        "recommendedAction": "REALLOCATE_PAYMENT",
        "sourceSystem": "MockCashApplication",
    }
    runtime_response = {
        "Data": {
            key[0].upper() + key[1:]: value
            for key, value in expected.items()
        }
    }

    assert verifier.extract_business_output(runtime_response, set(expected)) == expected
