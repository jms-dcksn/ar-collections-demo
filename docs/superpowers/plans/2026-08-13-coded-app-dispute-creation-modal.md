# Coded App Dispute Creation Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an authenticated dashboard modal that creates one script-equivalent `JDARCollectionsEntity` record for a selected fictional dispute scenario and recipient email.

**Architecture:** Keep scenario fixtures and payload generation in a pure typed module, route insertion through the existing Data Fabric service and authenticated workspace provider, and render the modal as a focused dashboard component. Record creation uses tenant-level `insertRecordById`; Maestro starts asynchronously from the existing record-created trigger.

**Tech Stack:** React 19, TypeScript 6, Vite 8, Vitest, Testing Library, UiPath TypeScript SDK 1.6.1, Data Fabric.

## Global Constraints

- Preserve the exact fixed payload data in `scripts/create-po-mismatch-record.sh`, `scripts/create-missing-pod-record.sh`, and `scripts/create-payment-misapplication-record.sh`.
- Require and trim a user-entered recipient email; do not use a fixed default.
- Insert into tenant-level entity `bc0fc734-bf94-f111-9b32-000d3ab5d4c4` without a folder key.
- Confirm record creation only; do not claim that the asynchronous Flow instance is already running.
- Do not create a live Data Fabric record, start/debug a Flow, send email, publish, or deploy during implementation or verification.
- Do not modify the Flow, Data Fabric schema, solution resources, scripts, or `uipath.json`.
- Preserve unrelated working-tree changes.
- Run `npm --prefix ar-collections-app test -- --run` and `npm --prefix ar-collections-app run build` after TypeScript changes.

---

### Task 1: Scenario payload contract and Data Fabric insertion

**Files:**
- Create: `ar-collections-app/src/lib/disputeScenarios.ts`
- Create: `ar-collections-app/src/lib/disputeScenarios.test.ts`
- Modify: `ar-collections-app/src/services/dataFabric.ts`
- Modify: `ar-collections-app/src/services/dataFabric.test.ts`
- Modify: `ar-collections-app/src/services/liveWorkspace.ts`
- Modify: `ar-collections-app/src/services/liveWorkspace.test.ts`

**Interfaces:**
- Produces: `ScenarioId`, `CreateDisputeInput`, `CreateDisputePayload`, `DISPUTE_SCENARIOS`, `isValidRecipientEmail`, and `buildDisputePayload(input, now?, randomUUID?)`.
- Produces: `DataFabricService.createDispute(input): Promise<DisputeRecord>`.
- Produces: `liveDataFabricClient(sdk).insertRecordById(entityId, data)`.

- [ ] **Step 1: Write failing pure-contract tests**

Create `disputeScenarios.test.ts` with table-driven assertions that each scenario yields the exact script fields, compact JSON evidence, trimmed email, correct `AR-PO` / `AR-POD` / `AR-PAY` UTC ID, and an uppercase eight-character suffix. Add validation assertions for empty and malformed emails and distinct UUID inputs.

- [ ] **Step 2: Run the contract test and verify RED**

Run: `npm --prefix ar-collections-app test -- --run src/lib/disputeScenarios.test.ts`

Expected: FAIL because `./disputeScenarios` does not exist.

- [ ] **Step 3: Implement the pure scenario module**

Define the three immutable fixtures and this API:

```ts
export type ScenarioId = 'po_mismatch' | 'missing_pod' | 'payment_misapplication'

export interface CreateDisputeInput {
  scenarioId: ScenarioId
  recipientEmail: string
}

export interface CreateDisputePayload {
  caseId: string
  customerName: string
  customerAccountId: string
  invoiceNumber: string
  outstandingBalance: number
  customerReason: string
  openedDate: string
  evidence: string
  recipientEmail: string
}

export function isValidRecipientEmail(value: string): boolean
export function buildDisputePayload(
  input: CreateDisputeInput,
  now?: Date,
  randomUUID?: () => string,
): CreateDisputePayload
```

Use `crypto.randomUUID` only as the default injected generator. Throw `Enter a valid recipient email.` before generating an ID when validation fails.

- [ ] **Step 4: Run the contract test and verify GREEN**

Run: `npm --prefix ar-collections-app test -- --run src/lib/disputeScenarios.test.ts`

Expected: all scenario and validation tests PASS.

- [ ] **Step 5: Write failing Data Fabric insertion tests**

Extend `dataFabric.test.ts` so `createDispute` must call:

```ts
insertRecordById(ENTITY_ID, expectedPayload)
```

Extend the hoisted SDK mock in `liveWorkspace.test.ts` with `insertRecordById` and assert that `liveDataFabricClient({}).insertRecordById(...)` delegates to `Entities.insertRecordById` and maps the response.

- [ ] **Step 6: Run service tests and verify RED**

Run: `npm --prefix ar-collections-app test -- --run src/services/dataFabric.test.ts src/services/liveWorkspace.test.ts`

Expected: FAIL because the client and service expose no insertion method.

- [ ] **Step 7: Implement insertion adapters**

Add `insertRecordById` to `DataFabricClient`, implement `DataFabricService.createDispute` using `buildDisputePayload`, and expose the SDK insertion method from `liveDataFabricClient`. Keep the existing approval update unchanged.

- [ ] **Step 8: Run service tests and verify GREEN**

Run: `npm --prefix ar-collections-app test -- --run src/services/dataFabric.test.ts src/services/liveWorkspace.test.ts`

Expected: PASS.

### Task 2: Authenticated workspace creation operation

**Files:**
- Modify: `ar-collections-app/src/workspace.tsx`
- Create: `ar-collections-app/src/workspace.test.tsx`

**Interfaces:**
- Consumes: `DataFabricService.createDispute(input)`.
- Produces: `WorkspaceContextValue.createDispute(input): Promise<DisputeRecord>`.

- [ ] **Step 1: Write failing workspace tests**

Mock `UiPath`, `liveDataFabricClient`, and `DataFabricService`. Render a small context consumer and assert that `createDispute` rejects with `Sign in to create a dispute.` when unauthenticated, and delegates with the selected scenario/email when authenticated.

- [ ] **Step 2: Run the workspace test and verify RED**

Run: `npm --prefix ar-collections-app test -- --run src/workspace.test.tsx`

Expected: FAIL because the context exposes no `createDispute` operation.

- [ ] **Step 3: Implement the workspace operation**

Add the typed callback:

```ts
createDispute: (input: CreateDisputeInput) => Promise<DisputeRecord>
```

Check `sdk.isAuthenticated()` immediately before insertion, then create the record through `new DataFabricService(liveDataFabricClient(sdk)).createDispute(input)`. Do not synthesize or append a preview row.

- [ ] **Step 4: Run the workspace test and verify GREEN**

Run: `npm --prefix ar-collections-app test -- --run src/workspace.test.tsx`

Expected: PASS.

### Task 3: Dashboard modal and interaction states

**Files:**
- Create: `ar-collections-app/src/components/CreateDisputeModal.tsx`
- Create: `ar-collections-app/src/components/CreateDisputeModal.test.tsx`
- Modify: `ar-collections-app/src/pages/DashboardPage.tsx`
- Modify: `ar-collections-app/src/index.css`

**Interfaces:**
- Consumes: `DISPUTE_SCENARIOS`, `ScenarioId`, `isValidRecipientEmail`, `useWorkspace().createDispute`, `authenticated`, and `refresh`.
- Produces: `CreateDisputeModal` with `open`, `onClose`, and `onCreated` props.

- [ ] **Step 1: Write failing modal behavior tests**

Use Testing Library to cover scenario preview changes, required email validation, cancel and Escape dismissal, disabled controls while a pending promise is unresolved, success confirmation containing the returned case ID, retained inputs/error after rejection, and retry. Stub `crypto.randomUUID` only where deterministic IDs are required.

- [ ] **Step 2: Run the modal test and verify RED**

Run: `npm --prefix ar-collections-app test -- --run src/components/CreateDisputeModal.test.tsx`

Expected: FAIL because `CreateDisputeModal` does not exist.

- [ ] **Step 3: Implement the modal**

Render an accessible `role="dialog"`, scenario radio/select controls, recipient email input, scenario preview, validation/error `role="alert"`, success `role="status"`, and cancel/create controls. Use a pending guard in the submit handler. On success call `onCreated(record.caseId)`; keep the confirmation visible until the user closes the modal. Add Escape handling, initial focus, and focus restoration without adding a dependency.

- [ ] **Step 4: Run the modal test and verify GREEN**

Run: `npm --prefix ar-collections-app test -- --run src/components/CreateDisputeModal.test.tsx`

Expected: PASS.

- [ ] **Step 5: Write a failing dashboard integration test**

Add `DashboardPage.test.tsx`, mock `useWorkspace`, and assert that signed-out users see a disabled `Create dispute` action, signed-in users can open the modal, and successful creation invokes one workspace refresh.

- [ ] **Step 6: Run the dashboard test and verify RED**

Run: `npm --prefix ar-collections-app test -- --run src/pages/DashboardPage.test.tsx`

Expected: FAIL because the dashboard has no creation action or modal.

- [ ] **Step 7: Integrate and style the modal**

Add the primary dashboard action, modal state, one refresh after successful insertion, and responsive styles for overlay, dialog, scenario choices, preview grid, validation, success, and action row. Keep existing dashboard filtering and refresh behavior intact.

- [ ] **Step 8: Run the dashboard test and verify GREEN**

Run: `npm --prefix ar-collections-app test -- --run src/pages/DashboardPage.test.tsx`

Expected: PASS.

### Task 4: Full verification

**Files:**
- Verify all changed Coded App files and the implementation plan.

**Interfaces:**
- Consumes: all previous task outputs.
- Produces: a locally tested and built Coded Web App; no live platform mutation.

- [ ] **Step 1: Run the complete app tests**

Run: `npm --prefix ar-collections-app test -- --run`

Expected: all tests PASS with no unhandled errors.

- [ ] **Step 2: Build the app**

Run: `npm --prefix ar-collections-app run build`

Expected: TypeScript and Vite build complete successfully and `ar-collections-app/dist/` exists.

- [ ] **Step 3: Validate patch hygiene**

Run: `git diff --check` and inspect `git status --short` plus the scoped diff under `ar-collections-app` and this plan.

Expected: no whitespace errors; unrelated pre-existing Flow, resource, and plan changes remain untouched.

- [ ] **Step 4: Request code review**

Use `superpowers:requesting-code-review` to review the implementation against the approved design and correct any material issue before completion.

- [ ] **Step 5: Commit the implementation if repository state permits**

Stage only the implementation plan and the feature files under `ar-collections-app`, then commit with:

```bash
git commit -m "feat: create AR disputes from coded app"
```
