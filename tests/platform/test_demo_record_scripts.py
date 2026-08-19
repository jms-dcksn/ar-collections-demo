import json
import os
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ENTITY_ID = "81a5f874-d79b-f111-9b33-6045bdd6658d"
RECIPIENT = "james.dickson@uipath.com"

SCENARIOS = {
    "create-payment-misapplication-record.sh": {
        "prefix": "AR-PAY-",
        "customerName": "Summit Medical Distribution",
        "customerAccountId": "SUMMIT-4402",
        "invoiceNumber": "INV-30915",
        "outstandingBalance": 36800,
        "customerReason": "We paid this invoice, but the balance is still open.",
        "openedDate": "2026-07-14",
        "evidence": {
            "reportedPaymentAmount": 36800,
            "paymentReference": "PAY-77821",
            "paymentAmount": 36800,
            "paymentDate": "2026-07-02",
            "appliedInvoiceNumber": "INV-30909",
            "targetInvoiceNumber": "INV-30915",
            "applicationStatus": "MISAPPLIED",
            "matchedRemittance": True,
            "sourceSystem": "MockCashApplication",
        },
    },
    "create-missing-pod-record.sh": {
        "prefix": "AR-POD-",
        "customerName": "Riverbend Retail",
        "customerAccountId": "RIVERBEND-2904",
        "invoiceNumber": "INV-20482",
        "outstandingBalance": 22400,
        "customerReason": (
            "Payment is on hold until proof of delivery is provided."
        ),
        "openedDate": "2026-07-10",
        "evidence": {
            "deliveryDate": "2026-06-18",
            "signer": "M. Chen",
            "shipmentQuantity": 120,
            "invoiceQuantity": 120,
        },
    },
    "create-po-mismatch-record.sh": {
        "prefix": "AR-PO-",
        "customerName": "Northstar Manufacturing",
        "customerAccountId": "NORTHSTAR-1701",
        "invoiceNumber": "INV-10471",
        "outstandingBalance": 48750,
        "customerReason": (
            "The invoice exceeds the purchase-order-authorized amount."
        ),
        "openedDate": "2026-07-07",
        "evidence": {
            "invoiceAmount": 48750,
            "poAuthorizedAmount": 47250,
            "difference": 1500,
        },
    },
}


def install_fake_uip(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_path = tmp_path / "uip-call.json"
    fake_uip = bin_dir / "uip"
    fake_uip.write_text(
        "#!/bin/sh\n"
        "python3 - \"$UIP_CAPTURE_PATH\" \"$@\" <<'PY'\n"
        "import json, os, sys\n"
        "capture_path, *args = sys.argv[1:]\n"
        "with open(capture_path, 'a') as stream:\n"
        "    json.dump({\n"
        "        'args': args,\n"
        "        'version_sync': os.environ.get('UIPATH_CLI_DISABLE_VERSION_SYNC'),\n"
        "    }, stream)\n"
        "    stream.write('\\n')\n"
        "print(json.dumps({'Result': 'Success', 'Code': 'RecordInserted'}))\n"
        "PY\n"
    )
    fake_uip.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["UIP_CAPTURE_PATH"] = str(capture_path)
    return capture_path, env


@pytest.mark.parametrize(("script_name", "scenario"), SCENARIOS.items())
def test_script_inserts_one_complete_scenario_record(
    tmp_path: Path, script_name: str, scenario: dict[str, object]
) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = subprocess.run(
        [str(SCRIPTS / script_name), RECIPIENT],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in capture_path.read_text().splitlines()]
    assert len(calls) == 1
    call = calls[0]
    args = call["args"]
    assert args[:4] == ["df", "records", "insert", ENTITY_ID]
    assert args[-2:] == ["--output", "json"]
    assert args.count("--body") == 1
    assert "--folder-key" not in args
    body = json.loads(args[args.index("--body") + 1])
    assert body == {
        "caseId": body["caseId"],
        "customerName": scenario["customerName"],
        "customerAccountId": scenario["customerAccountId"],
        "invoiceNumber": scenario["invoiceNumber"],
        "outstandingBalance": scenario["outstandingBalance"],
        "customerReason": scenario["customerReason"],
        "openedDate": scenario["openedDate"],
        "evidence": json.dumps(scenario["evidence"], separators=(",", ":")),
        "recipientEmail": RECIPIENT,
    }
    assert re.fullmatch(
        rf"{re.escape(str(scenario['prefix']))}\d{{8}}-[A-F0-9]{{8}}",
        body["caseId"],
    )
    assert call["version_sync"] == "1"


def test_each_invocation_generates_a_distinct_case_id(tmp_path: Path) -> None:
    capture_path, env = install_fake_uip(tmp_path)
    script = SCRIPTS / "create-payment-misapplication-record.sh"

    for _ in range(2):
        result = subprocess.run(
            [str(script), RECIPIENT],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    calls = [json.loads(line) for line in capture_path.read_text().splitlines()]
    case_ids = {
        json.loads(call["args"][call["args"].index("--body") + 1])["caseId"]
        for call in calls
    }
    assert len(calls) == 2
    assert len(case_ids) == 2


APPROVAL_SCRIPT = "supply-approval-decision.sh"
RECORD_ID = "2D7F2D6A-1897-F111-9B33-7C1E522150AC"


def run_approval(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPTS / APPROVAL_SCRIPT), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def sole_update_body(capture_path: Path) -> dict[str, object]:
    calls = [json.loads(line) for line in capture_path.read_text().splitlines()]
    assert len(calls) == 1
    args = calls[0]["args"]
    assert args[:4] == ["df", "records", "update", ENTITY_ID]
    assert args[-2:] == ["--output", "json"]
    assert args.count("--body") == 1
    # Entity record CRUD is tenant-scoped; a folder key would break correlation.
    assert "--folder-key" not in args
    assert calls[0]["version_sync"] == "1"
    return json.loads(args[args.index("--body") + 1])


@pytest.mark.parametrize("decision", ["approved", "rejected"])
def test_approval_script_writes_only_the_app_owned_fields(
    tmp_path: Path, decision: str
) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = run_approval(env, RECORD_ID, decision, "Reviewed at the desk.")

    assert result.returncode == 0, result.stderr
    assert sole_update_body(capture_path) == {
        "Id": RECORD_ID,
        "approvalDecision": decision,
        "approvalComments": "Reviewed at the desk.",
        "lifecycleState": decision,
    }


def test_approval_script_defaults_to_approved(tmp_path: Path) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = run_approval(env, RECORD_ID)

    assert result.returncode == 0, result.stderr
    body = sole_update_body(capture_path)
    assert body["approvalDecision"] == "approved"
    assert body["lifecycleState"] == "approved"
    assert body["approvalComments"]


def test_approval_script_omits_approved_by_unless_supplied(tmp_path: Path) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    assert run_approval(env, RECORD_ID, "approved").returncode == 0
    assert "approvedBy" not in sole_update_body(capture_path)


def test_approval_script_includes_approved_by_when_supplied(tmp_path: Path) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = run_approval(env, RECORD_ID, "approved", "Fine.", RECIPIENT)

    assert result.returncode == 0, result.stderr
    assert sole_update_body(capture_path)["approvedBy"] == RECIPIENT


@pytest.mark.parametrize(
    "args",
    [
        (),
        (RECORD_ID, "Approved!"),
        (RECORD_ID, "approve"),
        (RECORD_ID, "APPROVED"),
        (RECORD_ID, "a", "b", "c", "d"),
    ],
)
def test_approval_script_rejects_input_the_flow_would_not_resume_on(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = run_approval(env, *args)

    assert result.returncode != 0
    assert not capture_path.exists()


@pytest.mark.parametrize("script_name", SCENARIOS)
def test_script_requires_recipient_email_and_does_not_call_uip(
    tmp_path: Path, script_name: str
) -> None:
    capture_path, env = install_fake_uip(tmp_path)

    result = subprocess.run(
        [str(SCRIPTS / script_name)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Usage:" in result.stderr
    assert not capture_path.exists()
