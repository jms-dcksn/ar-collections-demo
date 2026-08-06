import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
TRIAGE = ROOT / "knowledge/triage/ar-dispute-taxonomy-and-examples.txt"
PAYMENT = ROOT / "knowledge/payment/payment-misapplication-resolution-playbook.txt"

TRIAGE_RULES = (
    "Return po_mismatch only when invoice and purchase-order price, quantity, tax, or authorized amount conflict.",
    "Return missing_pod only when payment is blocked because delivery evidence is requested or missing.",
    "Return payment_misapplication only when the customer reports payment but the target invoice remains open because application is absent or incorrect.",
    "Return unsupported when the evidence does not establish one supported category.",
    "Return unsupported and request manual triage when confidence is below 0.75.",
    "Never infer payment-system application details from a customer's statement alone.",
)
TRIAGE_SECTION_HEADINGS = (
    "Definition",
    "Positive signals",
    "Exclusions",
    "Example 1",
    "Example 2",
)
PAYMENT_HEADINGS = (
    "Required evidence",
    "Matching rules",
    "Controls before reallocation",
    "Resolution steps",
    "Customer communication",
    "Worked example 1",
    "Worked example 2",
)
REALLOCATION_GATE = (
    "Reallocation may be recommended only when all of the following are true: "
    "the payment amount matches; the payment reference matches; the remittance matches; "
    "the wrong applied invoice is identified; the intended target invoice is identified; "
    "and the source evidence reports MISAPPLIED."
)


def article(path: Path) -> str:
    assert path.is_file()
    return path.read_text()


def lines_between(text: str, start_heading: str, end_heading: str | None) -> list[str]:
    lines = text.splitlines()
    assert lines.count(start_heading) == 1
    start = lines.index(start_heading)
    if end_heading is None:
        return lines[start + 1 :]
    assert lines.count(end_heading) == 1
    end = lines.index(end_heading, start + 1)
    return lines[start + 1 : end]


def identifiers(text: str) -> dict[str, set[str]]:
    return {
        "cases": set(re.findall(r"\bAR-PAY-\d+\b", text)),
        "accounts": set(re.findall(r"customer account ([A-Z]+-\d+)", text)),
        "payments": set(re.findall(r"(?<!AR-)\bPAY-\d+\b", text)),
        "invoices": set(re.findall(r"\bINV-\d+\b", text)),
    }


def test_triage_article_enforces_exact_classification_rules():
    text = article(TRIAGE)
    for rule in TRIAGE_RULES:
        assert rule in text


def test_each_supported_triage_type_has_its_required_local_structure():
    text = article(TRIAGE)
    section_bounds = (
        ("po_mismatch", "missing_pod"),
        ("missing_pod", "payment_misapplication"),
        ("payment_misapplication", "Ambiguous and unsupported guidance"),
    )

    for start_heading, end_heading in section_bounds:
        section = lines_between(text, start_heading, end_heading)
        for heading in TRIAGE_SECTION_HEADINGS:
            assert heading in section
        positions = [section.index(heading) for heading in TRIAGE_SECTION_HEADINGS]
        assert positions == sorted(positions)

    ambiguous = "\n".join(
        lines_between(text, "Ambiguous and unsupported guidance", None)
    )
    assert "AR-AMB-004" in ambiguous
    assert "return unsupported and request manual triage" in ambiguous


def test_payment_article_enforces_headings_and_full_reallocation_gate():
    text = article(PAYMENT)
    lines = text.splitlines()
    for heading in PAYMENT_HEADINGS:
        assert lines.count(heading) == 1
    positions = [lines.index(heading) for heading in PAYMENT_HEADINGS]
    assert positions == sorted(positions)

    controls = "\n".join(
        lines_between(text, "Controls before reallocation", "Resolution steps")
    )
    assert REALLOCATION_GATE in controls


def test_first_payment_example_contains_all_approved_lookup_values():
    text = article(PAYMENT)
    example = "\n".join(lines_between(text, "Worked example 1", "Worked example 2"))
    for required in (
        "AR-PAY-003",
        "payment reference PAY-77821",
        "paymentAmount 36800",
        "paymentDate 2026-07-02",
        "appliedInvoiceNumber INV-30909",
        "targetInvoiceNumber INV-30915",
        "applicationStatus MISAPPLIED",
        "matchedRemittance true",
        "recommendedAction REALLOCATE_PAYMENT",
        "sourceSystem MockCashApplication",
    ):
        assert required in example


def test_second_payment_example_uses_distinct_identifiers():
    text = article(PAYMENT)
    first = "\n".join(lines_between(text, "Worked example 1", "Worked example 2"))
    second = "\n".join(lines_between(text, "Worked example 2", None))
    first_identifiers = identifiers(first)
    second_identifiers = identifiers(second)

    for identifier_type in ("cases", "accounts", "payments"):
        assert len(second_identifiers[identifier_type]) == 1
        assert first_identifiers[identifier_type].isdisjoint(
            second_identifiers[identifier_type]
        )
    assert len(second_identifiers["invoices"]) >= 2
    assert first_identifiers["invoices"].isdisjoint(second_identifiers["invoices"])
