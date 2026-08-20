# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

`AGENTS.md` in this directory holds the working agreements (platform contracts, ownership
rules, live-action policy) and is authoritative where the two overlap.
`solution/ARCollectionsDemo/AGENTS.md` is authoritative for anything under the UiPath
solution directory.

## What this is

A demo-grade, event-driven accounts-receivable dispute resolution solution on UiPath.
Creating a Data Fabric record starts a Maestro Flow that triages the dispute, routes it to a
specialist agent, persists a proposal, waits for a human decision made in a React Coded App,
and completes the approved or rejected path with auditable state.

Prefer simple implementations that demonstrate the product integration. Do not add
production hardening unless the demo needs it.

## Commands

```bash
# Python contract tests (uv only — never pip)
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/flow/test_flow_contract.py -q
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q -k mock_update   # single test by name

# Coded App (from repo root)
npm --prefix ar-collections-app test -- --run          # vitest, one shot
npm --prefix ar-collections-app test -- --run src/services/liveWorkspace.test.ts
npm --prefix ar-collections-app run build              # tsc -b && vite build
npm --prefix ar-collections-app run lint               # oxlint
npm --prefix ar-collections-app run dev                # localhost:5173, the registered OAuth redirect

# Pull the solution back down from Studio Web (overwrites local artifacts)
uip solution download 87ef25b1-a4a1-460c-e55f-08defde97196 \
  -d <scratch-dir> -n solution --extract   # then rsync over solution/ARCollectionsDemo

# Artifact validation (offline, no login required)
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate \
  solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate \
  solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate \
  solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json
```

Run checks proportional to the change. Documentation-only edits need only path/identifier
verification plus `git diff --check`. Run the JS suite after touching any `.ts`/`.tsx`.

`UIPATH_CLI_DISABLE_VERSION_SYNC=1` is used on every `uip` invocation in this repo.

## Architecture

Three cooperating artifacts share one Data Fabric entity as the system of record.

**Data Fabric entity `JDARCollectionsEntity`** (tenant-level, ID
`81a5f874-d79b-f111-9b33-6045bdd6658d`) — the case packet plus every lifecycle field. Its
full field contract is checked in at `config/platform-resources.json`; the Coded App mirrors
the subset it needs in `ar-collections-app/src/config.ts`. Entity record CRUD is
tenant-scoped: never pass a folder key.

**Maestro Flow `ARCollectionsDisputeResolution`** — the orchestrator, a single 6.6k-line
`.flow` JSON. Node graph:

```
recordCreated (Data Fabric record-created trigger) -> updateEntityRecord1
  -> triageAgent            (context: triageTaxonomyContext index)
  -> persistTriaging1 -> isSupportedTriage
       [false] -> persistNeedsManualTriage1 -> needsManualTriage (end)
       [true]  -> routeByDisputeType
                    -> poMismatchAgent | missingPodAgent | paymentMisapplicationAgent
                       (payment agent also gets paymentResolutionContext + lookupPaymentTool)
  -> normalizeProposal (script) -> persistAwaitingApproval1
  -> waitForApprovalUpdate (record-updated event)
       updatedRecordMatchesThisDispute1 [false] -> back to wait
       approvalDecisionSupplied1        [false] -> back to wait
  -> isResolutionApproved
       [false] -> persistRejected1 -> needsRework (end)
       [true]  -> persistApproved1 -> persistUpdating1
                  -> mockUpdateDispute1 -> sendEmail1 (Outlook 365)
                  -> persistResolved1 -> resolved (end)
```

Three inline low-code agents live in GUID-named subdirectories of the Flow project;
`config/agent-projects.json` maps logical names (`triage`, `poMismatch`,
`paymentMisapplication`) to those GUIDs and pins the model. Tests read that mapping, so
change it and the agent directories together.

`missingPodAgent` is **not** inline — it is an in-solution Python coded agent, the sibling
project `solution/ARCollectionsDemo/MissingPodCodedAgent`. LangChain/LangGraph, with the
smallest possible topology (`START -> agent -> END`, where `agent` is the compiled
`create_agent()` subgraph); input-message construction and structured-result validation
live in `before_agent` / `after_agent` middleware inside that subgraph. The model is
`UiPathAzureChatOpenAI(model="gpt-5.6-terra", temperature=0)`, built inside the
`make_graph()` factory so importing `main.py` needs no auth. The Flow references it as
`uipath.core.agent.<resourceKey>`, where `<resourceKey>` is the local key minted by
`uip solution projects add` and recorded under `codedAgents` in
`config/agent-projects.json`. Never hand-invent that key — read it from
`resources/solution_folder/process/agent/MissingPodCodedAgent.json` or
`uip maestro flow registry list --local`.

The solution manifest is `AR Collections Dispute Flow.uipx` (the Studio Web name). Some
`uip` commands regenerate a junk `ARCollectionsDemo.uipx` stub named after the directory —
it is gitignored; delete it if a `uip solution` command complains about multiple manifests.

**API Workflows** — `LookupPaymentApplication` (mock cash-application evidence, exposed to
the payment agent as a tool) and `MockUpdateDispute` (simulated downstream write). Both are
deterministic JSON workflows; neither touches a real financial system.

**Coded App `ar-collections-app`** — React 19 / Vite / TypeScript, published as a UiPath
Coded App. `WorkspaceProvider` (`src/workspace.tsx`) owns all state and holds the `UiPath`
SDK instance; OAuth is PKCE with the public external app in `uipath.json`, no client secret.
`src/services/liveWorkspace.ts` drives the dashboard from Data Fabric records, filtered to the
in-flight lifecycle states. It does **not** list Maestro instances — `ProcessInstances.getAll()`
cannot see this Flow's instances because PIMS scopes that listing by a folder-key header the SDK
never sends. It instead reads the Maestro instance ID the Flow writes onto the record's `caseId`
field and calls `getById(instanceId, SOLUTION_FOLDER_KEY)` per in-flight record for real run
status, and `getVariables` on demand from the detail page for the Flow globals. A record the Flow
has not stamped yet, or an instance PIMS refuses, degrades to an instance derived from the record
(`FlowInstance.instanceSource` says which). The app compiles against the real SDK typings; there
is no `sdk-shims.d.ts` and reintroducing one hides real breakage. See `AGENTS.md`, "SDK traps the Coded App works around". `src/services/dataFabric.ts`
validates the entity schema before writes. When no correlated live data exists the app falls
back to `src/lib/mockData.ts` with an explicit on-screen notice — that fallback is
deliberate, keep it labeled and read-only.

### The two identifiers

The Data Fabric record `Id` is the only correlation key for mutations, for the Flow's
wait/resume match, and for app routes. `caseId` starts as a business identifier and the Flow
then overwrites it with its own Maestro instance ID — that is deliberate and is the app's only
source of an instance ID. Never substitute `caseId` for `Id` in an update or a correlation
check, and never pass `caseId` to PIMS without `maestroInstanceIdOf()`: before the Flow stamps
it, the value is still `AR-PO-...` and not an instance ID.

### Coded App target

`ar-collections-app` reads the current tenant. `src/config.ts` pins the live
entity ID `81a5f874-d79b-f111-9b33-6045bdd6658d`, the solution subfolder key
`ff31878b-35b2-438f-8051-4e1461534d91`, and the Maestro process key
`33534c74-5c67-402d-a96f-0f9dc9e156c6`. `uipath.json` targets
`uipathstgSS_updated / UiPathDefault`. `config/platform-resources.json` remains
the authority.

The Flow is deployed to `JD/demos/AR Collections Dispute Flow`, a solution
subfolder of `JD/demos` — the app must use the child key, not the parent.
`MaestroProcesses.getAll()` reports each `name` as the `packageId`, so the app
matches on `processKey` alone.

App and Flow share one lifecycle vocabulary: the snake_case values the Flow
writes. `LIFECYCLE` in `src/config.ts` is the single source; `lifecycleLabel()`
renders them for display. `ApprovalDecision` is `'approved' | 'rejected'`.

Sign-in uses the public external application `ar-collections-app`
(`39a05889-3cc2-4de6-9616-fd847692d2c0`) in `uipathstgSS_updated`, redirect URI
`http://localhost:5173`. Add the deployed app URL as a second redirect URI before
publishing.

### Field ownership

The Flow owns lifecycle, triage, proposal, update-result, email, and audit fields. The Coded
App writes only `approvalDecision`, `approvalComments`, and the matching `lifecycleState`,
via `updateRecordById`. Nothing else writes to the entity.

Only an approved, correctly correlated case invokes `MockUpdateDispute` and sends Outlook
mail. Rejection and manual triage perform neither side effect.

## Tests

`tests/` is Python (pytest + jsonschema) contract testing over the checked-in JSON artifacts
— there is no Python runtime code here. `tests/flow/test_flow_contract.py` is the heavyweight
one: it walks the `.flow` node graph and asserts reachability, exclusive specialist routing,
the exact proposal field contract, wait/resume correlation and isolation, and that manual
triage and rejection paths are side-effect free. `tests/platform/` asserts the checked-in
manifests and demo scripts still match. Changing Flow structure means updating this test.

The Coded App uses Vitest + Testing Library with a jsdom environment.

## Live platform actions

`scripts/create-{po-mismatch,missing-pod,payment-misapplication}-record.sh <recipient-email>`
insert a real record into the tenant entity, which starts the deployed Flow and can end in a
real email to the recipient address.

`scripts/supply-approval-decision.sh <record-id> [approved|rejected] [comments] [approved-by]`
is the CLI stand-in for the Coded App's approval gate: it updates the record so
`waitForApprovalUpdate` resumes. It writes only the app-owned fields — `approvalDecision`,
`approvalComments`, and the matching `lifecycleState` — plus `approvedBy` when you pass it.
An `approved` decision drives the Flow through `MockUpdateDispute` and a real Outlook send;
`rejected` ends at `needsRework` with no side effects.

Use only a monitored demo mailbox. Treat record creation, approval supply, publish, deploy,
upload, and live Flow debug as live actions — do not perform them unless the task explicitly
calls for it.

Verify actual repository state, `uip` CLI behavior, active login target, and folder scope
before making platform claims. Update `config/platform-resources.json` whenever an approved
resource identifier or scope changes.

## Docs

- `docs/MIGRATE.md` — the org/tenant migration procedure and the editor churn it provokes
- `docs/context/data-fabric-record-creation.md` — entity identity and both record-creation paths
- `docs/runbooks/ar-collections-data-fabric-lifecycle.md` — the end-to-end demo procedure
- `docs/superpowers/specs/` — approved designs; `docs/superpowers/plans/` — implementation plans
- `docs/build-evidence/` — deployment, smoke, and Context Grounding evidence

Keep documentation concise and free of emojis.

## GitHub issues

Well-scoped implementation issues get both `enhancement` and `ready for agent`. Use
`ready for human` instead when human access, approval, or a decision is the blocking step.
