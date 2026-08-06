import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = (
    REPO_ROOT
    / "solution"
    / "ARCollectionsDemo"
    / "LookupPaymentApplication"
    / "Workflow.json"
)
INPUT_PATH = Path(__file__).with_name("lookup-payment-input.json")
EXPECTED_PATH = Path(__file__).with_name("lookup-payment-expected.json")
WORKFLOW_TIMEOUT_SECONDS = 120


def normalize_business_output(value, expected_keys):
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None

    expected_by_casefold = {key.casefold(): key for key in expected_keys}
    values_by_casefold = {key.casefold(): child for key, child in value.items()}
    if len(values_by_casefold) != len(value):
        return None
    if set(values_by_casefold) != set(expected_by_casefold):
        return None

    return {
        expected_by_casefold[key]: values_by_casefold[key]
        for key in expected_by_casefold
    }


def extract_business_output(cli_response, expected_keys):
    actual = cli_response
    for wrapper_name in ("Data", "data", "Output", "output", "Response", "response"):
        if isinstance(actual, dict) and wrapper_name in actual:
            actual = actual[wrapper_name]
    if isinstance(actual, str):
        actual = json.loads(actual)
    return normalize_business_output(actual, expected_keys)


def main():
    workflow_input = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    environment = os.environ.copy()
    environment["UIPATH_CLI_DISABLE_VERSION_SYNC"] = "1"

    completed = subprocess.run(
        [
            "uip",
            "api-workflow",
            "run",
            str(WORKFLOW_PATH),
            "--input-arguments",
            json.dumps(workflow_input, separators=(",", ":")),
            "--no-auth",
            "--output",
            "json",
        ],
        cwd=REPO_ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=WORKFLOW_TIMEOUT_SECONDS,
    )

    cli_response = json.loads(completed.stdout)
    result = cli_response.get("Result", cli_response.get("result"))
    if result is not None and result != "Success":
        raise AssertionError(f"Workflow run did not succeed: {cli_response}")

    expected_keys = set(expected)
    actual = extract_business_output(cli_response, expected_keys)
    if actual is None:
        raise AssertionError(
            "LookupPaymentApplication did not return the exact expected business fields"
        )

    if actual != expected:
        raise AssertionError(
            "LookupPaymentApplication fixture mismatch:\n"
            f"expected={json.dumps(expected, sort_keys=True)}\n"
            f"actual={json.dumps(actual, sort_keys=True)}"
        )

    print("LookupPaymentApplication fixture passed")


if __name__ == "__main__":
    main()
