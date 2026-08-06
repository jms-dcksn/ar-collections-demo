from pathlib import Path

ROOT = Path(__file__).parents[2]
TRIAGE = ROOT / "knowledge/triage/ar-dispute-taxonomy-and-examples.txt"
PAYMENT = ROOT / "knowledge/payment/payment-misapplication-resolution-playbook.txt"


def normalized(path: Path) -> str:
    assert path.is_file()
    return path.read_text().lower()


def test_triage_article_covers_taxonomy_examples_and_manual_gate():
    text = normalized(TRIAGE)
    for required in (
        "po_mismatch",
        "missing_pod",
        "payment_misapplication",
        "unsupported",
        "positive signals",
        "exclusions",
        "example 1",
        "example 2",
        "0.75",
        "manual triage",
    ):
        assert required in text


def test_payment_article_covers_evidence_controls_and_demo_case():
    text = normalized(PAYMENT)
    for required in (
        "payment reference",
        "remittance",
        "target invoice",
        "control",
        "reallocation",
        "customer communication",
        "worked example 1",
        "worked example 2",
        "ar-pay-003",
        "pay-77821",
        "inv-30909",
        "inv-30915",
    ):
        assert required in text
