# Data Fabric Record Creation Context

This page is the quick reference for the Data Fabric entity and the two ways
this repository creates demo dispute records. The canonical platform resource
contract remains [`config/platform-resources.json`](../../config/platform-resources.json),
and the scripts and Coded App source remain the executable definitions.

## Entity contract

- System name: `JDARCollectionsEntity`
- Display name: `JD AR Collections Entity`
- Entity ID: `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`
- Scope: tenant-level; record CRUD must not include a folder key
- Organization / tenant: `uipathlabs / Playground`
- Solution deployment folder: `JD_Demos/demos`

Creating a record in this entity emits the event that starts the deployed
`ARCollectionsDisputeResolution` Flow. Record creation is therefore a live
platform action even though the payloads contain fictional demo data. Neither
the scripts nor the Coded App starts a Maestro instance directly.

Data Fabric assigns the record `Id`. That `Id` is the authoritative key for all
later record updates and wait/resume correlation. The generated `caseId` is a
business identifier used to associate the Flow instance with a record for
display; it must not replace the record `Id` for mutations.

## Shell scripts

The three scripts create the supported demo scenarios:

| Script | Scenario | Case ID prefix |
| --- | --- | --- |
| `scripts/create-po-mismatch-record.sh` | Purchase-order mismatch | `AR-PO` |
| `scripts/create-missing-pod-record.sh` | Missing proof of delivery | `AR-POD` |
| `scripts/create-payment-misapplication-record.sh` | Payment misapplication | `AR-PAY` |

Each script requires exactly one recipient email argument. For example:

```bash
./scripts/create-payment-misapplication-record.sh collector@example.com
```

The script builds a fixed fictional case packet for its scenario, adds the
supplied `recipientEmail`, and generates a unique case ID in the form
`<prefix>-<UTC YYYYMMDD>-<first 8 UUID hex characters>`. It serializes the
payload with `jq` and performs one tenant-level insertion:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df records insert \
  bc0fc734-bf94-f111-9b32-000d3ab5d4c4 \
  --body "$body" \
  --output json
```

The recipient is not hard-coded because the approved Flow path can ultimately
send email to that address. Use only a monitored, permitted demo mailbox.

## Coded App creation flow

The dashboard's **Create dispute** action is enabled only for an authenticated
UiPath session. It opens a modal where the user:

1. Selects one of the same three fictional scenarios used by the scripts.
2. Enters and validates the recipient email.
3. Reviews the fixed customer, invoice, balance, date, reason, and evidence.
4. Submits the new Data Fabric record.

Scenario payloads and case ID generation live in
[`ar-collections-app/src/lib/disputeScenarios.ts`](../../ar-collections-app/src/lib/disputeScenarios.ts).
They intentionally mirror the shell-script payloads. The app trims and
validates the email, serializes the scenario evidence, and generates the same
case ID shape with `crypto.randomUUID()`.

The request path is:

```text
DashboardPage
  -> CreateDisputeModal
  -> WorkspaceProvider.createDispute
  -> DataFabricService.createDispute
  -> Entities.insertRecordById
```

Before insertion, the live Data Fabric client retrieves the configured entity
and verifies that its fields match the app's required schema, including
`recipientEmail`. The SDK insertion uses the entity ID above without a folder
key. On success, the dashboard refreshes; the record and Flow instance may not
appear immediately because the record-created trigger is asynchronous.

Relevant implementation files:

- [`ar-collections-app/src/components/CreateDisputeModal.tsx`](../../ar-collections-app/src/components/CreateDisputeModal.tsx)
- [`ar-collections-app/src/pages/DashboardPage.tsx`](../../ar-collections-app/src/pages/DashboardPage.tsx)
- [`ar-collections-app/src/workspace.tsx`](../../ar-collections-app/src/workspace.tsx)
- [`ar-collections-app/src/services/dataFabric.ts`](../../ar-collections-app/src/services/dataFabric.ts)
- [`ar-collections-app/src/services/liveWorkspace.ts`](../../ar-collections-app/src/services/liveWorkspace.ts)
- [`ar-collections-app/src/config.ts`](../../ar-collections-app/src/config.ts)

For the end-to-end operator procedure after record creation, see
[`docs/runbooks/ar-collections-data-fabric-lifecycle.md`](../runbooks/ar-collections-data-fabric-lifecycle.md).
