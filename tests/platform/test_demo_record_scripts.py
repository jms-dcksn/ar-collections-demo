import json
import os
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
ENTITY_ID = "bc0fc734-bf94-f111-9b32-000d3ab5d4c4"
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
