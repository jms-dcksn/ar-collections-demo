# Coded App Dispute Creation Modal

## Purpose

Extend the AR Collections Coded Web App dashboard with a modal that creates one
tenant-level `JDARCollectionsEntity` record from a selected fictional scenario.
Creating the record emits the Data Fabric record-created event that starts the
deployed `ARCollectionsDisputeResolution` Flow. The app does not start Maestro
directly.

This design intentionally extends the earlier Coded Process App design, whose
original scope limited Data Fabric writes to approval decisions. The approved
creation action below is the only additional write operation.

## User experience

The dashboard adds a `Create dispute` primary action beside `Refresh workspace`.
The action is enabled only for an authenticated user and while no creation is
in progress.

Activating it opens an accessible modal containing:

- A required scenario selector with purchase-order mismatch, missing proof of
  delivery, and payment misapplication options.
- A required recipient email field. The app trims the value and rejects an
  empty or invalid email before calling Data Fabric.
- A read-only preview of the selected scenario's customer, account, invoice,
  outstanding balance, customer reason, opened date, and evidence summary.
- Cancel and `Create dispute` controls.

The modal traps focus, has an accessible title and description, closes through
Cancel or Escape when idle, and restores focus to the dashboard action. While
submitting, its inputs and dismissal controls are disabled to prevent duplicate
records.

On success, the modal shows the generated case ID and confirms that the Flow
will appear after the record-created trigger is processed. The user can close
the modal, and the workspace refreshes once immediately without implying that
the asynchronous Flow instance must already be visible. On failure, the modal
stays open, retains the selections, and presents a concise actionable error.

## Scenario contract

The application owns typed scenario templates that reproduce the business
payloads in the three scripts under `scripts/`. Each insertion contains only:

- `caseId`
- `customerName`
- `customerAccountId`
- `invoiceNumber`
- `outstandingBalance`
- `customerReason`
- `openedDate`
- `evidence`
- `recipientEmail`

The fixed fictional values remain identical to their corresponding scripts:

- Purchase-order mismatch: Northstar Manufacturing, `NORTHSTAR-1701`,
  `INV-10471`, USD 48,750, opened `2026-07-07`, with the invoice, authorized PO,
  and USD 1,500 difference evidence.
- Missing proof of delivery: Riverbend Retail, `RIVERBEND-2904`, `INV-20482`,
  USD 22,400, opened `2026-07-10`, with delivery date, signer, and quantity
  evidence.
- Payment misapplication: Summit Medical Distribution, `SUMMIT-4402`,
  `INV-30915`, USD 36,800, opened `2026-07-14`, with reported payment amount and
  `PAY-77821` evidence.

Evidence is serialized as the same compact JSON string used by the scripts.
The modal does not expose the fixed scenario fields for editing.

## Case ID generation

The browser generates a new ID immediately before submission using the same
shape as the scripts:

```text
<scenario-prefix>-<current UTC YYYYMMDD>-<eight-character random suffix>
```

The prefixes are `AR-PO`, `AR-POD`, and `AR-PAY`. The suffix is derived from
`crypto.randomUUID()`, with hyphens removed and the first eight hexadecimal
characters uppercased. A new ID is generated for each submission attempt; it
is not reused after a failed insert.

## Architecture and data flow

Scenario definitions and payload construction live in a small typed module so
the service and UI do not duplicate fixture data. The Data Fabric client gains
an `insertRecordById` adapter, and `DataFabricService.createDispute` inserts the
constructed payload into entity
`bc0fc734-bf94-f111-9b32-000d3ab5d4c4`. The entity is tenant-level, so no folder
key is supplied.

The workspace provider exposes a `createDispute` operation backed by the same
authenticated `UiPath` session used for reads and approval updates. It rejects
creation when unauthenticated and never mutates fictional preview rows. The
dashboard modal calls this operation, presents the returned record/case ID,
then asks the workspace to refresh.

The existing `DataFabric.Data.Write` OAuth scope already authorizes
`insertRecordById`; `DataFabric.Schema.Read` continues to support entity schema
validation. No change to `uipath.json`, solution resources, the Flow, or the
shell scripts is required.

## Error handling and safety

- Client validation prevents empty scenario and invalid recipient email calls.
- A pending guard and disabled controls prevent repeated submissions.
- SDK errors are normalized to a user-readable message without exposing tokens
  or raw platform response bodies.
- A failed insert creates no local substitute and does not claim that a Flow
  started.
- A successful insert confirms record creation only. Flow startup is explicitly
  described as asynchronous.
- Closing and reopening the modal resets scenario, recipient, success, and
  error state.
- Implementation and verification do not insert a live Data Fabric record,
  deploy the app, run the Flow, or send email.

## Testing and verification

Implementation follows test-driven development. Automated tests cover:

- Exact payload construction for all three script-equivalent scenarios.
- UTC case ID prefixes, date segment, suffix format, and a fresh ID per attempt.
- Recipient email trimming and validation.
- The exact `insertRecordById` entity ID and payload.
- Modal open/close behavior, scenario preview, signed-out and pending states.
- Successful submission, case-ID confirmation, and workspace refresh.
- Failed submission with retained inputs and retry capability.

After TypeScript changes, run the complete Coded App test suite with
`npm --prefix ar-collections-app test -- --run`, then run
`npm --prefix ar-collections-app run build` and `git diff --check`.

## Out of scope

- Editing the fictional scenario data in the modal.
- Creating custom scenarios or persisting user defaults.
- Starting Maestro directly or polling until the new Flow instance appears.
- Changing the Flow, Data Fabric schema, shell scripts, solution resources, or
  deployment configuration.
- Publishing or deploying the Coded App.
