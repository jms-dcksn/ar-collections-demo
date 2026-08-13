#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <recipient-email>" >&2
  exit 64
fi

recipient_email=$1
case_id="AR-PO-$(date -u +%Y%m%d)-$(uuidgen | tr -d '-' | cut -c1-8)"
body=$(jq -cn \
  --arg case_id "$case_id" \
  --arg recipient_email "$recipient_email" \
  '{
    caseId: $case_id,
    customerName: "Northstar Manufacturing",
    customerAccountId: "NORTHSTAR-1701",
    invoiceNumber: "INV-10471",
    outstandingBalance: 48750,
    customerReason: "The invoice exceeds the purchase-order-authorized amount.",
    openedDate: "2026-07-07",
    evidence: "{\"invoiceAmount\":48750,\"poAuthorizedAmount\":47250,\"difference\":1500}",
    recipientEmail: $recipient_email
  }')

UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records insert \
  bc0fc734-bf94-f111-9b32-000d3ab5d4c4 \
  --body "$body" \
  --output json
