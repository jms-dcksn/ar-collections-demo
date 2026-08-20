# Repository Working Agreements

## Project Purpose

This repository is a demo-grade, event-driven accounts-receivable dispute
resolution solution built on UiPath. A Data Fabric case record starts a Maestro
Flow that triages the dispute, routes it to a specialist agent, persists a
resolution proposal, waits for a collector decision, and completes approved or
rejected paths with auditable state.

Prefer simple implementations that clearly demonstrate the UiPath product
integration. Do not add production hardening unless it is required for the demo
to work.

## Architecture

- **System of record:** Tenant-level Data Fabric entity
  `JDARCollectionsEntity` stores the case packet, triage result, specialist
  proposal, approval decision, update result, email status, and audit summary.
- **Orchestration:** `ARCollectionsDisputeResolution` is a long-running Maestro
  Flow triggered by entity record creation. It persists lifecycle state and
  waits for an update to the same record before resuming.
- **Agents:** The Flow contains one triage agent and specialist agents for PO
  mismatch, missing proof of delivery, and payment misapplication. Triage and
  payment resolution use attached Context Grounding indexes; payment resolution
  also calls the deterministic `LookupPaymentApplication` API Workflow.
- **Deterministic tools:** `LookupPaymentApplication` supplies mock cash-
  application evidence. `MockUpdateDispute` simulates the approved downstream
  update without writing to an external financial system.
- **Human decision:** The Coded App lists the Data Fabric records whose
  `lifecycleState` is still in flight (`triaging`, `awaiting_approval`,
  `approved`, `updating`) and records approve/reject decisions by Data Fabric
  record ID, which emits the update event that resumes the Flow. It does **not**
  list Maestro instances: `ProcessInstances.getAll()` cannot see this Flow's
  instances (see "SDK traps"), so the record is the row and the Flow instance
  shown in the UI is derived from it for display only.
- **Approved side effect:** Only an approved, correctly correlated case may call
  `MockUpdateDispute` and send the prepared message through the configured
  Microsoft Outlook 365 connection. Rejection and manual triage do neither.
- **Presentation layer:** `ar-collections-app` is a React/TypeScript UiPath Coded
  App. It uses authenticated UiPath SDK clients for Maestro and Data Fabric and
  has an explicitly labeled, read-only fictional-data fallback.

## Repository Map

| Path | Responsibility |
| --- | --- |
| `solution/ARCollectionsDemo` | UiPath solution manifest, Maestro Flow, inline agents, API Workflows, bindings, and solution resources |
| `ar-collections-app` | React/TypeScript Coded App for monitoring and approval |
| `config` | Checked-in platform resource and agent project contracts |
| `knowledge` | Context Grounding source content for triage and payment resolution |
| `tests` | Python contract tests for agents, Flow, API Workflows, knowledge, and platform manifests |
| `docs/runbooks` | Demo operation and verification procedures |
| `docs/MIGRATE.md` | Organization / tenant migration procedure and expected editor churn |
| `docs/context/data-fabric-record-creation.md` | Entity identity, demo record scripts, and Coded App creation flow |
| `docs/superpowers/specs` | Approved architecture and feature designs |

`solution/ARCollectionsDemo/AGENTS.md` is authoritative for files under the
UiPath solution directory. Follow it for solution membership, resource refresh,
pack, publish, deploy, and Studio Web operations; do not hand-edit the `.uipx`
manifest.

## Data Flow and Ownership

1. Creating a `JDARCollectionsEntity` record starts the deployed Flow through
   the Data Fabric record-created trigger.
2. The Flow retains the built-in Data Fabric record `Id` and uses it for every
   later record update and wait/resume correlation check.
3. The triage agent classifies the case as `po_mismatch`, `missing_pod`,
   `payment_misapplication`, or `unsupported`. Supported, sufficiently confident
   cases route to exactly one specialist.
4. The Flow normalizes and persists the specialist proposal, sets
   `lifecycleState` to `awaiting_approval`, and waits for a record-updated event.
5. Updates for a different record or without an approval decision are ignored;
   the Flow returns to the wait state.
6. A rejection ends as `rejected`. Unsupported or low-confidence work ends as
   `needs_manual_triage`. Neither path performs the mock update or sends email.
7. Approval progresses through `approved` and `updating`, invokes
   `MockUpdateDispute`, sends the approved Outlook message, and persists the
   terminal `resolved` state, update result, email status, and audit summary.

The Data Fabric record `Id` is the authoritative mutation and lifecycle
correlation key. `caseId` is a business identifier and is used by the Coded App
to join a Maestro instance's global variable to a record for display; it must
not replace record `Id` in update or wait/resume operations.

The Flow owns lifecycle, triage, proposal, update-result, email, and audit
fields. The Coded App writes only the approval decision, optional approval
comments, and the matching approval lifecycle value through
`updateRecordById`.

## Platform Contracts

- Base URL / organization / tenant: `https://staging.uipath.com` — `uipathstgSS_updated /
  UiPathDefault`.
- Solution deployment folder: `JD/demos`
  (`e716bfc7-4c75-4921-ab5b-e5a3bc0d4c2c`).
- Data Fabric entity: `JDARCollectionsEntity` / `JD AR Collections Entity`.
- Entity scope: tenant-level; do not pass a folder key for entity record CRUD.
- Entity ID: `81a5f874-d79b-f111-9b33-6045bdd6658d`.
- Outlook connection: `james.dickson@uipath.com`
  (`8643408a-62b4-4d36-ba1e-bc9b68d4fce9`).
- Data Fabric connection: `james.dickson@uipath.com`
  (`b2a02899-3708-4bb6-810a-02321afb77f6`).
- Both connections live in `JD/demos` (`e716bfc7-4c75-4921-ab5b-e5a3bc0d4c2c`) —
  the same folder as the resources, so the Flow's `connectionFolderKey` and its
  index / process `folderKey` are all the one key.
- Canonical checked-in resource contract: `config/platform-resources.json`.

### Deployed Maestro process

The Flow is deployed to the solution subfolder `JD/demos/AR Collections Dispute
Flow` (`ff31878b-35b2-438f-8051-4e1461534d91`), not to the parent `JD/demos`.

- Process key: `33534c74-5c67-402d-a96f-0f9dc9e156c6` (equals the Orchestrator
  release key).
- Package ID: `AR.Collections.Dispute.Flow.flow.ARCollectionsDisputeResolution`.
- Release name: `ARCollectionsDisputeResolution`.

Read these back with
`uip maestro flow process list --folder-key ff31878b-35b2-438f-8051-4e1461534d91`.

### SDK traps the Coded App works around

All verified in-browser against the real TypeScript methods on 2026-08-19, in the live
`uipathstgSS_updated / UiPathDefault` session. Do not "simplify" any of them back.

1. **`sdk-shims.d.ts` is deleted — never reintroduce it.** It re-declared the SDK modules with
   widened types and thereby hid traps 2 and 3 from `tsc`. The app compiles against the real
   typings with zero errors. A shim that widens an SDK type converts a compile error into a
   runtime one.
2. **`Entities.queryRecordsById()` never resolves to a bare array.** With `pageSize` it is a
   `PaginatedResponse`, without it a `NonPaginatedResponse`, and *both* wrap rows in `items`.
   `(await queryRecordsById(...)).map(...)` throws. Read `.items`, follow `hasNextPage` /
   `nextCursor`.
3. **`getVariables()` returns `globalVariables` as an ARRAY** of
   `{ id, name, type, elementId, value }` — 24 entries on a live instance, never indexable by
   variable name.
4. **`Entities.getAll()` and `MaestroProcesses.getAll()` are page-capped with no pagination
   option.** Resolve a known entity with `getById(ENTITY_ID)`. For the process summary, the
   unfiltered call returned 21 processes excluding this Flow, and `{ processKey }` returned 0 —
   it can only produce a false negative, so the app never calls it.
5. **`ProcessInstances.getAll()` cannot see this Flow's instances at all.** PIMS scopes instance
   listing by the `x-uipath-folderkey` header, which `getAll` never sends and offers no way to
   supply. Measured:

   | call | items | ours |
   | --- | --- | --- |
   | `{ processKey, pageSize: 200 }` | 0 | 0 |
   | `{ packageId, pageSize: 200 }` | 0 | 0 |
   | `{ folderKey, pageSize: 200 }` (param is ignored) | 200 | 0 |
   | `{ pageSize: 200 }`, list exhausted over 3 pages | 527 | **0** |
   | `{}` | 50 (server default cap) | 0 |

   `getById(instanceId, folderKey)` and `getVariables(instanceId, folderKey)` **do** work — both
   send the folder header. The missing piece was only ever the ID, and the Flow now supplies it.
   Note on how this was first verified: the `getById` / `getVariables` check used a single instance
   ID obtained from `uip maestro flow instance list --folder-key ...`, hard-coded into a temporary
   diagnostic. It proved those methods work on an ID you already hold.

   **`caseId` is the instance-ID carrier — by decision, not by accident.** The Flow writes its own
   Maestro instance ID onto the record's `caseId` field once the instance is running. That was
   originally observed as a destructive overwrite of the business identifier; the demo now relies
   on it instead of adding a dedicated `maestroInstanceId` field. Consequences the app must own:

   - `maestroInstanceIdOf(caseId)` in `src/config.ts` gates every instance call — a GUID shape is
     the only signal the value is an instance ID and not the `AR-PO-...` identifier the app
     inserted. Never hand a non-GUID `caseId` to PIMS.
   - `liveWorkspace.instanceFor()` calls `getById(instanceId, SOLUTION_FOLDER_KEY)` per in-flight
     record and falls back to the derived instance when the record is unstamped or PIMS refuses.
     `FlowInstance.instanceSource` records which of the two produced the row.
   - `loadInstanceVariables()` calls `getVariables(instanceId, SOLUTION_FOLDER_KEY)`; the detail
     page requests it on demand, never the dashboard.
   - `caseId` is no longer a display label. `caseLabel()` renders the invoice number in its place
     once the value is a GUID, and routes use `record.Id`, which never changes mid-flight.

6. **This Flow declares no `caseId` global.** Confirmed from the live instance: the globals are
   one `output` / `error` pair per node plus `resultCaseId`, `status`, `resourcesUsed`,
   `approvalComments`, `emailSent`, and `resultCaseId` is set only on the manual-triage path.

`insertRecordById` and `updateRecordById` return the record directly, so the write path needs no
unwrapping.

**Verify SDK behaviour with the SDK, not the CLI.** The `uip` CLI hits different endpoints with
different parameters and PascalCases every object key in its JSON output. The real `getById`
response is camelCase (`name`, `displayName`, `fields`, `id`), with user field names camelCase
(`caseId`) and system field names PascalCase (`Id`, `CreateTime`, `RecordOwner`). `mapRecord`
still reads case-insensitively. Chrome DevTools MCP against the running dev server is the way to
check this — it exercises the real methods in the real session without handling any token.

### Coded App state

`ar-collections-app` reads the current tenant. `src/config.ts` pins the live
entity ID, the solution subfolder key, and the process key;
`ar-collections-app/uipath.json` targets `uipathstgSS_updated / UiPathDefault`.
The app and the
Flow now share one lifecycle vocabulary — the snake_case values the Flow writes
(`triaging`, `awaiting_approval`, `approved`, `rejected`, `updating`, `resolved`,
`needs_manual_triage`). `LIFECYCLE` in `src/config.ts` is the single source for
those values; `lifecycleLabel()` renders them for display. Never reintroduce
display-style lifecycle strings into comparisons.

`ApprovalDecision` is `'approved' | 'rejected'`, which matches what
`scripts/supply-approval-decision.sh` writes.

#### Known cosmetic mismatch — deliberate, do not "fix" unasked

The dashboard is record-driven but still carries instance-flavoured labels: the metric reads
"Active resolution flows" (it counts in-flight records), the "FLOW STATUS" column is derived from
`lifecycleState` by `runStatusFor()` rather than fetched from Maestro, and the detail page's
"Flow monitor" panel shows the record's `caseId` as "Instance" and its `CreateTime` as "Started".
Record `c989298e` also renders a raw GUID in the Dispute column because of the `caseId` overwrite
bug. James chose on 2026-08-19 to leave all of this and narrate it during the demo. Do not
relabel or filter without asking.

`config/platform-resources.json` stays the canonical platform contract.

#### OAuth client

The app signs in with the public (non-confidential) external application
`ar-collections-app` (`39a05889-3cc2-4de6-9616-fd847692d2c0`) in
`uipathstgSS_updated`, redirect URI `http://localhost:5173`, carrying all 21
`uipath.json` scopes as user (delegated) scopes. Add the deployed app URL as a
second redirect URI before publishing.

### Verified Sample Record

- Entity: `JDARCollectionsEntity`
  (`81a5f874-d79b-f111-9b33-6045bdd6658d`), tenant-level.
- No sample record exists yet in `uipathstgSS_updated / UiPathDefault`. The
  entity was created empty during the 2026-08-19 move; run one of the
  `scripts/create-*-record.sh` scripts to seed one.
- Samples from both retired environments (`cloud.uipath.com` record
  `2D7F2D6A-1897-F111-9B33-7C1E522150AC`, case `AR-PAY-20260813-01`, and
  anything created under `uipathlabs / Playground`) are no longer reachable.

Record data is current test data, not a reusable constant. The Flow may update
the row.
Creating another record can start the deployed record-created trigger and must
be treated as a live platform action.

## Technology Stack

- UiPath Solution (`.uipx`) targeting Studio 2025.10 or later.
- UiPath Maestro Flow with inline low-code agents and wait/resume event handling.
- UiPath Data Fabric, Context Grounding, Integration Service, and Microsoft
  Outlook 365.
- UiPath API Workflows for deterministic lookup and mocked update operations.
- React 19, TypeScript, Vite, React Router, and the UiPath TypeScript SDK.
- UiPath Apollo (`@uipath/apollo-core`, `@uipath/apollo-wind`), Tailwind CSS 4,
  and Lucide React for the Coded App UI.
- Vitest and Testing Library for the Coded App.
- Python contract tests with pytest; Python dependencies and commands use `uv`.

## Working Rules

- Inspect the actual repository artifact, generated metadata, installed `uip`
  CLI behavior, active login target, and folder scope before making UiPath
  platform claims or changes.
- Treat `config/platform-resources.json` as the checked-in platform contract and
  update it when an approved resource identifier or scope changes.
- Do not publish, deploy, upload, execute a live Flow debug, create Data Fabric
  records, or send email unless the task explicitly requires the live action.
- Never substitute `caseId` for the Data Fabric record `Id` when mutating a row.
- Run `npm test` after modifying JavaScript or TypeScript files.
- Use `uv` for Python package management and execution; never use `pip`.
- Keep README files concise and do not use emojis in documentation.

## Validation

Run checks proportional to the files changed. The full repository validation is:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
npm --prefix ar-collections-app test -- --run
npm --prefix ar-collections-app run build
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json
git diff --check
```

For a documentation-only change, validate referenced paths and identifiers and
run `git diff --check`; JavaScript and Python test suites are not required when
their source files are unchanged.

## GitHub Issues

When creating a well-scoped implementation issue for this repository, apply both `enhancement` and `ready for agent` labels. Use `ready for human` instead when human access, approval, or a decision is the blocking next action.
