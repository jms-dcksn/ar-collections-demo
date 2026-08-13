# Data Fabric Demo Record Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three one-command shell scripts that each insert one fresh, deterministic scenario fixture into the existing tenant-level AR collections entity.

**Architecture:** Each standalone script owns one fictional scenario payload and invokes `uip df records insert` exactly once. A UTC date plus UUID suffix makes the business case ID fresh while retaining a recognizable scenario prefix; pytest runs the real scripts against a temporary fake `uip` executable so no live Data Fabric writes occur during automated testing.

**Tech Stack:** POSIX shell, UiPath CLI Data Fabric extension, `jq`, `uuidgen`, Python 3.11, pytest, `uv`.

## Global Constraints

- Use tenant-level entity `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`; never pass `--folder-key`.
- Create exactly one record per invocation and never update or delete records.
- Require recipient email as the only positional argument.
- Set `UIPATH_CLI_DISABLE_VERSION_SYNC=1` for every `uip` invocation.
- Keep the three scripts standalone and directly executable.
- Do not modify the user's existing Flow or connection changes.

---

## File Structure

- Create `scripts/create-payment-misapplication-record.sh` for the payment fixture.
- Create `scripts/create-missing-pod-record.sh` for the missing-proof-of-delivery fixture.
- Create `scripts/create-po-mismatch-record.sh` for the purchase-order mismatch fixture.
- Create `tests/platform/test_demo_record_scripts.py` for script contract and command-capture tests.
- Modify `docs/runbooks/ar-collections-data-fabric-lifecycle.md` with copy-paste usage.

### Task 1: Define and implement the three script contracts

**Files:**
- Create: `tests/platform/test_demo_record_scripts.py`
- Create: `scripts/create-payment-misapplication-record.sh`
- Create: `scripts/create-missing-pod-record.sh`
- Create: `scripts/create-po-mismatch-record.sh`

**Interfaces:**
- Consumes: one positional recipient email and an authenticated `uip` CLI session.
- Produces: one `uip df records insert <entity-id> --body <json> --output json` call and the CLI JSON response.

- [ ] **Step 1: Write failing parametrized tests**

Create tests that install a temporary fake `uip` executable on `PATH`, capture its arguments and `UIPATH_CLI_DISABLE_VERSION_SYNC`, invoke each real script, decode the `--body` value, and assert:

```python
SCENARIOS = {
    "create-payment-misapplication-record.sh": ("AR-PAY-", "Summit Medical Distribution"),
    "create-missing-pod-record.sh": ("AR-POD-", "Northstar Health Systems"),
    "create-po-mismatch-record.sh": ("AR-PO-", "Fabrikam Components"),
}

assert args[:4] == [
    "df", "records", "insert", "bc0fc734-bf94-f111-9b32-000d3ab5d4c4"
]
assert args[-2:] == ["--output", "json"]
assert body["caseId"].startswith(prefix)
assert body["customerName"] == customer_name
assert body["recipientEmail"] == "james.dickson@uipath.com"
assert captured_version_sync == "1"
```

Add a second parametrized test that invokes each script without an email, expects a nonzero exit, finds `Usage:` on stderr, and confirms the fake `uip` was not called.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_demo_record_scripts.py -q
```

Expected: FAIL because the three scripts do not exist.

- [ ] **Step 3: Implement the three standalone scripts**

Each script starts with this argument and execution structure:

```sh
#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <recipient-email>" >&2
  exit 64
fi

recipient_email=$1
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records insert \
  bc0fc734-bf94-f111-9b32-000d3ab5d4c4 \
  --body "$body" \
  --output json
```

Before the `uip` call, the payment script builds this exact ID and payload:

```sh
case_id="AR-PAY-$(date -u +%Y%m%d)-$(uuidgen | tr '[:lower:]' '[:upper:]' | tr -d '-' | cut -c1-8)"
body=$(jq -cn --arg case_id "$case_id" --arg recipient_email "$recipient_email" '{caseId:$case_id,customerName:"Summit Medical Distribution",customerAccountId:"SUMMIT-4402",invoiceNumber:"INV-30915",outstandingBalance:36800,customerReason:"We paid this invoice, but the balance is still open.",openedDate:"2026-07-14",evidence:"{\"reportedPaymentAmount\":36800,\"paymentReference\":\"PAY-77821\"}",recipientEmail:$recipient_email}')
```

The missing-POD script builds this exact ID and payload:

```sh
case_id="AR-POD-$(date -u +%Y%m%d)-$(uuidgen | tr '[:lower:]' '[:upper:]' | tr -d '-' | cut -c1-8)"
body=$(jq -cn --arg case_id "$case_id" --arg recipient_email "$recipient_email" '{caseId:$case_id,customerName:"Riverbend Retail",customerAccountId:"RIVERBEND-2904",invoiceNumber:"INV-20482",outstandingBalance:22400,customerReason:"Payment is on hold until proof of delivery is provided.",openedDate:"2026-07-10",evidence:"{\"deliveryDate\":\"2026-06-18\",\"signer\":\"M. Chen\",\"shipmentQuantity\":120,\"invoiceQuantity\":120}",recipientEmail:$recipient_email}')
```

The PO-mismatch script builds this exact ID and payload:

```sh
case_id="AR-PO-$(date -u +%Y%m%d)-$(uuidgen | tr '[:lower:]' '[:upper:]' | tr -d '-' | cut -c1-8)"
body=$(jq -cn --arg case_id "$case_id" --arg recipient_email "$recipient_email" '{caseId:$case_id,customerName:"Northstar Manufacturing",customerAccountId:"NORTHSTAR-1701",invoiceNumber:"INV-10471",outstandingBalance:48750,customerReason:"The invoice exceeds the purchase-order-authorized amount.",openedDate:"2026-07-07",evidence:"{\"invoiceAmount\":48750,\"poAuthorizedAmount\":47250,\"difference\":1500}",recipientEmail:$recipient_email}')
```

Keep `evidence` as compact JSON text, not a nested object. Mark all scripts executable.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_demo_record_scripts.py -q
```

Expected: all script tests pass without contacting UiPath Cloud.

- [ ] **Step 5: Commit the scripts and tests**

```bash
git add scripts/create-payment-misapplication-record.sh scripts/create-missing-pod-record.sh scripts/create-po-mismatch-record.sh tests/platform/test_demo_record_scripts.py
git commit -m "feat: add Data Fabric demo record scripts"
```

### Task 2: Document commands and verify the repository

**Files:**
- Modify: `docs/runbooks/ar-collections-data-fabric-lifecycle.md`

**Interfaces:**
- Consumes: the three executable scripts from Task 1.
- Produces: three copy-paste commands plus trigger and case-ID behavior notes.

- [ ] **Step 1: Update the lifecycle runbook**

Add a concise section containing the three commands, state that each invocation creates one fresh record and can trigger the deployed Flow, and explain that the current Flow may replace the seeded case ID with its Maestro instance ID.

- [ ] **Step 2: Check script syntax**

Run:

```bash
sh -n scripts/create-payment-misapplication-record.sh scripts/create-missing-pod-record.sh scripts/create-po-mismatch-record.sh
```

Expected: exit code 0 with no output.

- [ ] **Step 3: Run full verification**

Run:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
git diff --check
```

Expected: the complete Python suite passes and `git diff --check` reports no errors.

- [ ] **Step 4: Commit the documentation**

```bash
git add docs/runbooks/ar-collections-data-fabric-lifecycle.md tests/platform/test_demo_record_scripts.py docs/superpowers/plans/2026-08-13-data-fabric-demo-record-scripts.md
git commit -m "docs: explain Data Fabric scenario seeding"
```

## Plan Self-Review

- Coverage: all three approved scenarios, mandatory email, tenant entity, fresh IDs, single inserts, tests, and commands are assigned to tasks.
- Safety: automated tests replace `uip` on `PATH`; they cannot create live records. No delete, update, schema, Flow, or connection operation is included.
- Consistency: script names and commands match the approved design and test table.
