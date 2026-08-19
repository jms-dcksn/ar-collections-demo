"""Mock remittance-advice service for the AR collections payment-misapplication agent.

The Data Fabric case packet and the LookupPaymentApplication API workflow both describe
what the ERP *did* with a payment. This server supplies the complementary evidence: what
the payer *said* to do with it, as stated on the remittance advice that accompanied the
funds. Comparing the two is how a misapplication is proven.

Demo-grade: the remittance store is a hard-coded dictionary, no external system is called.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Remittance Advice Server")

# Keyed by payment reference. PAY-77821 is the reference carried by the
# scripts/create-payment-misapplication-record.sh demo case: the payer named INV-30915
# while cash application posted the funds to INV-30909.
REMITTANCE_ADVICES: dict[str, dict[str, Any]] = {
    "PAY-77821": {
        "remittanceDocumentId": "RA-2026-0702-4471",
        "receivedDate": "2026-07-02",
        "receiptChannel": "lockbox",
        "payerName": "Summit Medical Distribution",
        "payerAccountId": "SUMMIT-4402",
        "currency": "USD",
        "totalRemittedAmount": 36800.00,
        "lineItems": [
            {
                "invoiceNumber": "INV-30915",
                "invoiceAmount": 36800.00,
                "amountRemitted": 36800.00,
                "deductionCode": None,
                "deductionAmount": 0.00,
                "note": "Paid in full per statement dated 2026-06-30.",
            }
        ],
        "payerNote": "Remittance detail keyed from lockbox scan, confidence high.",
    },
    "PAY-77902": {
        "remittanceDocumentId": "RA-2026-0715-4498",
        "receivedDate": "2026-07-15",
        "receiptChannel": "email",
        "payerName": "Northgate Clinical Supply",
        "payerAccountId": "NORTHGATE-2210",
        "currency": "USD",
        "totalRemittedAmount": 18250.00,
        "lineItems": [
            {
                "invoiceNumber": "INV-31044",
                "invoiceAmount": 19000.00,
                "amountRemitted": 18250.00,
                "deductionCode": "SHORT-PAY-DAMAGE",
                "deductionAmount": 750.00,
                "note": "Deduction taken for two damaged cartons, claim CLM-8871.",
            }
        ],
        "payerNote": "Remittance detail transcribed from payer email attachment.",
    },
    "PAY-77655": {
        "remittanceDocumentId": "RA-2026-0621-4402",
        "receivedDate": "2026-06-21",
        "receiptChannel": "edi_820",
        "payerName": "Summit Medical Distribution",
        "payerAccountId": "SUMMIT-4402",
        "currency": "USD",
        "totalRemittedAmount": 51200.00,
        "lineItems": [
            {
                "invoiceNumber": "INV-30702",
                "invoiceAmount": 29400.00,
                "amountRemitted": 29400.00,
                "deductionCode": None,
                "deductionAmount": 0.00,
                "note": "Paid in full.",
            },
            {
                "invoiceNumber": "INV-30744",
                "invoiceAmount": 21800.00,
                "amountRemitted": 21800.00,
                "deductionCode": None,
                "deductionAmount": 0.00,
                "note": "Paid in full.",
            },
        ],
        "payerNote": "Single EDI 820 covering two invoices.",
    },
}


@mcp.tool()
def get_remittance_advice(payment_reference: str) -> dict[str, Any]:
    """Look up the remittance advice the payer sent with a payment.

    Use this to establish payer intent when a payment appears to have been applied to the
    wrong invoice. The remittance advice lists the invoice numbers the payer named, the
    amount allocated to each, and any deduction they took. Compare the invoice numbers
    here against the invoice the ERP actually credited: a mismatch is direct evidence of
    a misapplication rather than a customer error.

    Args:
        payment_reference: The payment reference from the case packet, e.g. "PAY-77821".

    Returns:
        A dict with `found` set to True and the remittance advice detail — payer,
        receipt channel, total remitted, and a `lineItems` list of the invoices the payer
        named. When no advice exists for the reference, `found` is False and `reason`
        explains the miss; an absent remittance advice is itself meaningful, since it
        means payer intent cannot be established from documentation.
    """
    reference = payment_reference.strip().upper()
    advice = REMITTANCE_ADVICES.get(reference)

    if advice is None:
        return {
            "found": False,
            "paymentReference": reference,
            "reason": (
                "No remittance advice on file for this payment reference. The payment may "
                "have arrived without remittance detail, or the reference may be wrong."
            ),
            "sourceSystem": "MockRemittanceAdvice",
        }

    return {
        "found": True,
        "paymentReference": reference,
        **advice,
    }


if __name__ == "__main__":
    mcp.run()
