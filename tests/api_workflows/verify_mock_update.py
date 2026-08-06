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


def find_business_output(value, expected_keys: set[str]):
    if isinstance(value, dict):
        expected_by_casefold = {key.casefold(): key for key in expected_keys}
        normalized = {
            expected_by_casefold[key.casefold()]: child
            for key, child in value.items()
            if isinstance(key, str) and key.casefold() in expected_by_casefold
        }
        if normalized.keys() == expected_keys:
            return normalized

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


def main():
    workflow_input = json.loads(INPUT_PATH.read_text())
    expected = json.loads(EXPECTED_PATH.read_text())
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
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    envelope = json.loads(completed.stdout)
    if envelope.get("Result", envelope.get("result")) != "Success":
        raise AssertionError(f"Workflow returned a failure envelope: {envelope}")

    actual = find_business_output(envelope.get("Data", envelope), set(expected))
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
