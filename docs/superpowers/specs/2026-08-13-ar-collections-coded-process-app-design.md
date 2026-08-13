# AR Collections Coded Process App

## Purpose

Build a UiPath Coded Web App for internal collections users to monitor active AR dispute resolution Flow instances, review the linked Data Fabric dispute record, and record an approval decision that advances the event-driven Flow.

The app is a polished demo-grade operations workspace: visually confident and enterprise-appropriate, without adding production-only complexity or duplicating authoritative data.

## Authoritative contracts

### Authentication and runtime configuration

- UiPath environment: production cloud (`https://api.uipath.com`).
- Organization and tenant: `uipathlabs` / `Playground`.
- OAuth client: `57201488-1566-4f9b-a696-1b3773c2af33` (`UiPathLabs-ExternalApp-SDKforUsers_2`).
- Client type: public external application using authorization-code + PKCE. No client secret is requested, stored, or used.
- Local redirect URI: `http://localhost:5173`.
- Deployed redirect URI: `https://uipathlabs.uipath.host/ar-collections-app`.
- Runtime scope string contains exactly the granted scopes provided for the external application.

### Data Fabric

The tenant-scoped Data Fabric entity is `JDARCollectionsEntity` (`bc0fc734-bf94-f111-9b32-000d3ab5d4c4`). It is the system of record for the case, triage, specialist recommendation, approval, update result, and audit state.

The app reads the case fields (`caseId`, customer and invoice identifiers, balance, reason, opened date, and evidence), lifecycle and triage fields (`lifecycleState`, `disputeType`, `triageRationale`, `triageConfidence`), recommendation fields (`evidenceSummary`, `rootCause`, `recommendedAction`, `actionCode`, `adjustmentAmount`, `specialistConfidence`, `approvalSummary`), and audit fields (`updateResult`, `emailSent`, `auditSummary`).

The only business fields the approval action writes are:

- `approvalDecision` — `Approved` or `Rejected`.
- `approvalComments` — optional collector rationale.
- `lifecycleState` — `Approved` or `Rejected`, matching the decision.

The app uses `updateRecordById`, rather than bulk update, so the Data Fabric event triggers the downstream Flow. The entity's built-in `UpdatedBy` and `UpdateTime` fields retain the platform audit of the update; the app does not write `approvedBy`, because the granted OAuth scopes do not include a user-profile read. No Flow state is duplicated into Data Fabric.

### Flow correlation

The entity has no stored Maestro instance identifier. The application correlates each active `ARCollectionsDisputeResolution` instance with a Data Fabric record by its `caseId` global Flow variable:

1. Discover the published Maestro process by its name through `MaestroProcesses.getAll()`.
2. Page through `ProcessInstances.getAll({ processKey })`.
3. Resolve the `caseId` global variable for each instance in the visible page, with bounded parallelism.
4. Query the entity once using those case IDs and an `In` filter, then join only on exact `caseId` values.
5. Refresh the selected instance's variables and exact entity record on its detail route.

The dashboard must not infer a record from customer, invoice, or display text. If a correlation cannot be established, it shows the instance with a clear “Record unavailable” state and does not permit an approval action.

### Visual demo fallback

The app includes a small, fictional mock-data fixture set for local testing and visual inspection. It activates when the Data Fabric entity is unavailable, returns no case records, or an active Flow instance has no usable `caseId`. The dashboard then shows the fictional cases with a persistent “Demo data preview” banner and an explicit read-only state.

Mock records never call Data Fabric or Maestro mutation APIs. Their approve/reject controls are disabled and explain that a live correlated record is required. This preserves a useful visual preview without making an outage or missing correlation appear to be a real operational decision.

## User experience

### App shell

The React/TypeScript Coded Web App uses the UiPath Apollo v4 design system through `@uipath/apollo-wind` and `@uipath/apollo-core`. Apollo's semantic tokens, typography, spacing, and components create the visual foundation; the app uses a restrained navy-and-indigo operations palette with compact status color accents.

The shell consists of:

- A persistent dark navigation rail with Disputes, Analytics, Activity, and Settings destinations. Analytics, Activity, and Settings are realistic display-only demo routes.
- A persistent header with a concise workspace label, authenticated-user menu, and sign-out control.
- A spacious light content canvas with calm hierarchy, generous grouping, and no decorative customer-data imagery.

### Active instances dashboard

The default route is an instance-first operations workspace. It includes:

- Summary cards for active, awaiting-approval, decisions recorded, and attention-needed counts.
- Lifecycle filter tabs and a case/customer search field.
- A “Live” indicator, last-updated time, and manual refresh. Data refreshes without tearing down the table or flickering rows.
- A paginated table of active Flow instances. Its columns are case ID, customer, outstanding balance, lifecycle state, Flow run status, elapsed time, and triage confidence.
- Clear loading, no-results, missing-correlation, and service-error states.
- A distinct demo-data preview state when live correlation cannot supply a displayable case.

Selecting an instance opens its detail route.

### Dispute detail and approval

The detail route presents the decision context in structured sections, never as raw JSON:

- Case summary: customer, account, invoice, balance, reason, and opened date.
- Resolution context: triage rationale, confidence, evidence summary, root cause, recommended action, action code, and adjustment amount.
- Flow monitor: current run status, started/completed times, active live state, and link/correlation identifier. The displayed Flow information remains inside the user's authenticated UiPath context.
- Audit panel: previous approval data, update result, email status, and audit summary.
- Approval card: Approve and Reject controls, an optional comments field, confirmation copy that explains the event-triggered update, a pending state that disables duplicate submission, and accessible success/error feedback.

Only records with `lifecycleState` exactly `Awaiting approval` enable the decision controls. `Approved`, `Rejected`, `Resolved`, and `Failed` records display read-only history; `New` and `In review` remain visible but cannot be decided in the app.

## Architecture

The app uses Vite, React, TypeScript, Tailwind 4, `@uipath/apollo-wind`, and `@uipath/uipath-typescript`.

- `uipath.json` is the committed, non-secret runtime OAuth configuration.
- An authentication provider initializes `new UiPath()` and exposes the authenticated session.
- A typed Data Fabric service validates the live entity schema at startup, exposes paginated list/detail queries, and constructs the explicit approval update payload.
- A typed Maestro service discovers the target process and retrieves paginated active instances. Detail polling is keyed to the selected instance and retains prior data during refreshes.
- A correlation layer joins only on `caseId` after obtaining the detail instance's global variables.
- Page-level hooks own loading/error/refetch state; presentational components receive typed view models rather than SDK response objects.

All list APIs paginate. Dynamic tables use a page size of 25–50 and show a “Showing X–Y of Z” summary with previous/next controls.

## Error handling and validation

- Startup validates that the entity exists and includes all required read/write fields. A missing or renamed field produces a specific configuration error instead of silently dropping writes.
- Authentication and authorization failures guide the user to sign in again without exposing tokens.
- A failed Flow lookup, record correlation, Data Fabric read, or approval update stays isolated to the relevant panel and preserves safely rendered data.
- A Data Fabric schema/read failure or zero-record result can fall back to the fictional, read-only preview data; the banner identifies the reason for the fallback.
- Approval requires a valid decision, prevents duplicate submissions, and refreshes the record and Flow status after success.
- Multiline evidence is parsed defensively and rendered in labeled key/value sections when valid; malformed evidence is shown as a concise unavailable state.

## Verification

- Automated tests cover schema requirements, `caseId` correlation, lifecycle filtering, status presentation, and exact approval update payloads.
- `npm test` runs after JavaScript or TypeScript edits.
- `npm run build` verifies the Coded App bundle and SDK imports.
- The README gives concise local setup and `npm run dev` instructions for `http://localhost:5173`.

## Out of scope

- Creating, editing, or deleting Data Fabric schema or records beyond the approved decision update.
- Starting, pausing, cancelling, or otherwise controlling Maestro instances.
- Customer communication, direct email sending, and external customer-data export.
- Production-specific authorization administration, archival, or analytics beyond the demo routes.
