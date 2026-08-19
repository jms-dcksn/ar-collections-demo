#!/bin/sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 4 ]; then
  echo "Usage: $0 <record-id> [approved|rejected] [comments] [approved-by]" >&2
  exit 64
fi

record_id=$1
decision=${2:-approved}
comments=${3:-}
approved_by=${4:-}

case $decision in
  approved | rejected) ;;
  *)
    echo "Invalid decision '$decision'." >&2
    echo "The Flow resumes only on 'approved' or 'rejected'; anything else leaves it waiting." >&2
    exit 64
    ;;
esac

if [ -z "$comments" ]; then
  comments="Decision '$decision' supplied from the CLI."
fi

body=$(jq -cn \
  --arg id "$record_id" \
  --arg decision "$decision" \
  --arg comments "$comments" \
  --arg approved_by "$approved_by" \
  '{
    Id: $id,
    approvalDecision: $decision,
    approvalComments: $comments,
    lifecycleState: $decision
  }
  + (if $approved_by == "" then {} else {approvedBy: $approved_by} end)')

UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records update \
  81a5f874-d79b-f111-9b33-6045bdd6658d \
  --body "$body" \
  --output json
