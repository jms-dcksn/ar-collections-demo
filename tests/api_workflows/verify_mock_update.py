import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = (
    ROOT / "solution" / "ARCollectionsDemo" / "MockUpdateDispute" / "Workflow.json"
)
INPUT_PATH = Path(__file__).with_name("mock-update-input.json")
EXPECTED_PATH = Path(__file__).with_name("mock-update-expected.json")
WORKFLOW_TIMEOUT_SECONDS = 60


def normalize_business_output(value, expected_keys: set[str]):
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


def find_business_output(value, expected_keys: set[str]):
    normalized = normalize_business_output(value, expected_keys)
    if normalized is not None:
        return normalized

    if isinstance(value, dict):
        for child in value.values():
            found = find_business_output(child, expected_keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_business_output(child, expected_keys)
            if found is not None:
                return found
    return None


def extract_business_output(envelope, expected_keys: set[str]):
    data = envelope.get("Data", envelope.get("data", envelope))
    known_candidates = [data]
    if isinstance(data, dict):
        for wrapper in (
            "Output",
            "output",
            "Response",
            "response",
            "Result",
            "result",
            "Value",
            "value",
        ):
            if wrapper in data:
                known_candidates.append(data[wrapper])

    for candidate in known_candidates:
        normalized = normalize_business_output(candidate, expected_keys)
        if normalized is not None:
            return normalized

    return find_business_output(data, expected_keys)


def main():
    workflow_input = json.loads(INPUT_PATH.read_text())
    expected = json.loads(EXPECTED_PATH.read_text())
    environment = os.environ.copy()
    environment["UIPATH_CLI_DISABLE_VERSION_SYNC"] = "1"

    try:
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
            check=True,
            capture_output=True,
            text=True,
            env=environment,
            timeout=WORKFLOW_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        raise AssertionError(
            "MockUpdateDispute verification timed out after "
            f"{WORKFLOW_TIMEOUT_SECONDS} seconds"
        ) from error

    envelope = json.loads(completed.stdout)
    if envelope.get("Result", envelope.get("result")) != "Success":
        raise AssertionError(f"Workflow returned a failure envelope: {envelope}")

    actual = extract_business_output(envelope, set(expected))
    if actual is None:
        raise AssertionError(f"Could not locate business output in CLI envelope: {envelope}")
    if actual != expected:
        raise AssertionError(
            "MockUpdateDispute output mismatch:\n"
            f"expected={json.dumps(expected, sort_keys=True)}\n"
            f"actual={json.dumps(actual, sort_keys=True)}"
        )

    print("MockUpdateDispute fixture passed")


if __name__ == "__main__":
    main()
