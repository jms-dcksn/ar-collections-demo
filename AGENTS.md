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
- **Human decision:** The Coded App presents active Maestro instances and their
  correlated Data Fabric records. It records approve/reject decisions by Data
  Fabric record ID, which emits the update event that resumes the Flow.
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

- Organization / tenant: `uipathlabs / Playground`.
- Solution deployment folder: `JD_Demos/demos`.
- Data Fabric entity: `JDARCollectionsEntity` / `JD AR Collections Entity`.
- Entity scope: tenant-level; do not pass a folder key for entity record CRUD.
- Entity ID: `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`.
- Outlook connection: `james.dickson@uipath.com`.
- Integration Service connection key: `c61c5442-c5d6-4cb2-9c02-f4a541f01e4c`.
- Canonical checked-in resource contract: `config/platform-resources.json`.

### Verified Sample Record

- Entity: `JDARCollectionsEntity`
  (`bc0fc734-bf94-f111-9b32-000d3ab5d4c4`), tenant-level.
- Record ID: `2D7F2D6A-1897-F111-9B33-7C1E522150AC`.
- Case ID: `AR-PAY-20260813-01`.
- Scenario: payment misapplication for Summit Medical Distribution, invoice
  `INV-30915`, balance `36800.00`, payment reference `PAY-77821`.
- Recipient: `james.dickson@uipath.com`.

This is current test data, not a reusable constant. The Flow may update the row.
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
