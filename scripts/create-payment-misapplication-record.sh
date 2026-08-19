#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <recipient-email>" >&2
  exit 64
fi

recipient_email=$1
case_id="AR-PAY-$(date -u +%Y%m%d)-$(uuidgen | tr -d '-' | cut -c1-8)"
body=$(jq -cn \
  --arg case_id "$case_id" \
  --arg recipient_email "$recipient_email" \
  '{
    caseId: $case_id,
    customerName: "Summit Medical Distribution",
    customerAccountId: "SUMMIT-4402",
    invoiceNumber: "INV-30915",
    outstandingBalance: 36800,
    customerReason: "We paid this invoice, but the balance is still open.",
    openedDate: "2026-07-14",
    evidence: "{\"reportedPaymentAmount\":36800,\"paymentReference\":\"PAY-77821\",\"paymentAmount\":36800,\"paymentDate\":\"2026-07-02\",\"appliedInvoiceNumber\":\"INV-30909\",\"targetInvoiceNumber\":\"INV-30915\",\"applicationStatus\":\"MISAPPLIED\",\"matchedRemittance\":true,\"sourceSystem\":\"MockCashApplication\"}",
    recipientEmail: $recipient_email
  }')

UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records insert \
  81a5f874-d79b-f111-9b33-6045bdd6658d \
  --body "$body" \
  --output json
