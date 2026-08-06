import json
import os
import subprocess
from pathlib import Path


repo_root = Path(__file__).resolve().parents[2]
workflow_path = (
    repo_root
    / "solution"
    / "ARCollectionsDemo"
    / "LookupPaymentApplication"
    / "Workflow.json"
)
input_path = repo_root / "tests" / "api_workflows" / "lookup-payment-input.json"
expected_path = repo_root / "tests" / "api_workflows" / "lookup-payment-expected.json"

workflow_input = json.loads(input_path.read_text(encoding="utf-8"))
expected = json.loads(expected_path.read_text(encoding="utf-8"))
environment = os.environ.copy()
environment["UIPATH_CLI_DISABLE_VERSION_SYNC"] = "1"

completed = subprocess.run(
    [
        "uip",
        "api-workflow",
        "run",
        str(workflow_path),
        "--input-arguments",
        json.dumps(workflow_input, separators=(",", ":")),
        "--no-auth",
        "--output",
        "json",
    ],
    cwd=repo_root,
    env=environment,
    check=True,
    capture_output=True,
    text=True,
    timeout=120,
)

cli_response = json.loads(completed.stdout)
result = cli_response.get("Result", cli_response.get("result"))
if result is not None and result != "Success":
    raise AssertionError(f"Workflow run did not succeed: {cli_response}")

actual = cli_response
for wrapper_name in ("Data", "data", "Output", "output", "Response", "response"):
    if isinstance(actual, dict) and wrapper_name in actual:
        actual = actual[wrapper_name]

if isinstance(actual, str):
    actual = json.loads(actual)

if not isinstance(actual, dict):
    raise AssertionError(
        f"LookupPaymentApplication returned {type(actual).__name__}, expected object"
    )

actual_keys = set(actual)
expected_keys = set(expected)
if actual_keys != expected_keys:
    raise AssertionError(
        "LookupPaymentApplication output keys mismatch:\n"
        f"missing={sorted(expected_keys - actual_keys)}\n"
        f"unexpected={sorted(actual_keys - expected_keys)}"
    )

if actual != expected:
    raise AssertionError(
        "LookupPaymentApplication fixture mismatch:\n"
        f"expected={json.dumps(expected, sort_keys=True)}\n"
        f"actual={json.dumps(actual, sort_keys=True)}"
    )

print("LookupPaymentApplication fixture passed")
