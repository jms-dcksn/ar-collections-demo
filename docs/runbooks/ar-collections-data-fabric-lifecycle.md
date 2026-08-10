# AR Collections Data Fabric Lifecycle Demo

## Purpose and scope

Use this procedure to demonstrate the Data Fabric-driven lifecycle for the
tenant-scoped `JDARCollectionsEntity` (`JD AR Collections Entity`). The Process
App creates and later updates the record; the Flow owns lifecycle, proposal,
update, email, and audit fields. Do not publish, deploy, upload, or run a live
Flow debug as part of this procedure.

## Create a dispute record

In the Process App, create one `JDARCollectionsEntity` record with all required
case-packet fields and a safe demo recipient:

| Field | Example value |
| --- | --- |
| `caseId` | A unique supported demo case ID, such as `AR-PAY-003` |
| `customerName` | `Harbor Clinical Supply` |
| `customerAccountId` | `HARBOR-7710` |
| `invoiceNumber` | `INV-88042` |
| `outstandingBalance` | `12450.00` |
| `customerReason` | The case's supported payment-misapplication reason |
| `openedDate` | A valid date |
| `evidence` | JSON text for the case evidence |
| `recipientEmail` | A monitored, permitted demo mailbox |

Record the Data Fabric-generated `Id` immediately. It is the only correlation
key for this lifecycle: do not use `caseId` to identify the record or approval
update.

For a supported, confident case, wait for the Flow to persist
`lifecycleState: awaiting_approval`. Confirm that the same record now contains
the normalized proposal fields, including the recommendation and email preview.

## Prove wait and resume correlation

While the first record is awaiting approval, create or update a second record.
Its update must be ignored by the waiting instance; the first record remains
`awaiting_approval` and neither side effect runs. The Flow compares the update
event `Id` to the original record `Id`, then loops back to the wait for an
unrelated or decisionless event.

In the Process App, update the original record with all three approval fields:

| Field | Approved example | Rejected example |
| --- | --- | --- |
| `approvalDecision` | `approved` | `rejected` |
| `approvedBy` | `Demo Collector` | `Demo Collector` |
| `approvalComments` | `Approved during demo verification.` | `Needs correction before approval.` |

The update must be made through the Process App against the original Data
Fabric record. This is the action that resumes the Flow; it is not a new record
and it must retain the same `Id`.

## Verify terminal behavior

### Approved

Confirm the record progresses through `approved` and `updating`, then reaches
`resolved`. Verify `updateResult`, `emailSent: true`, and `auditSummary` are
persisted on that same record. Confirm `MockUpdateDispute` ran and Outlook sent
the approved email only to the record's `recipientEmail`.

### Rejected

Use a separate supported record, wait for `awaiting_approval`, then submit the
rejected update above. Confirm its terminal `lifecycleState` is `rejected`,
`emailSent` is `false`, and its audit summary states that no API workflow or
email side effect ran. Confirm neither `MockUpdateDispute` nor Outlook was
called.

### Manual triage

Create an unsupported or low-confidence record (for example, `AR-AMB-004`).
Confirm its terminal `lifecycleState` is `needs_manual_triage`, `emailSent` is
`false`, and its audit summary says no specialist, API workflow, approval, or
email side effect ran. Confirm it never waits for or consumes an approval
update, and neither `MockUpdateDispute` nor Outlook was called.

## Expected state model

Intermediate states are `triaging`, `awaiting_approval`, `approved`, and
`updating`. Terminal states are `needs_manual_triage`, `rejected`, and
`resolved`. Each Flow-owned write targets the original tenant-scoped
`JDARCollectionsEntity` record by its Data Fabric `Id`.

## Local verification

Run the repository checks without live execution:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
npm test
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
git diff --check
```

The Flow validator may report the known shared-connection warning. Accept that
warning only when validation reports `Valid`; it does not authorize a live Flow
debug, publish, deploy, or upload.
