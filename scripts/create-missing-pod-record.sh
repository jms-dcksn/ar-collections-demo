#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <recipient-email>" >&2
  exit 64
fi

recipient_email=$1
case_id="AR-POD-$(date -u +%Y%m%d)-$(uuidgen | tr -d '-' | cut -c1-8)"
body=$(jq -cn \
  --arg case_id "$case_id" \
  --arg recipient_email "$recipient_email" \
  '{
    caseId: $case_id,
    customerName: "Riverbend Retail",
    customerAccountId: "RIVERBEND-2904",
    invoiceNumber: "INV-20482",
    outstandingBalance: 22400,
    customerReason: "Payment is on hold until proof of delivery is provided.",
    openedDate: "2026-07-10",
    evidence: "{\"deliveryDate\":\"2026-06-18\",\"signer\":\"M. Chen\",\"shipmentQuantity\":120,\"invoiceQuantity\":120}",
    recipientEmail: $recipient_email
  }')

UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records insert \
  bc0fc734-bf94-f111-9b32-000d3ab5d4c4 \
  --body "$body" \
  --output json
