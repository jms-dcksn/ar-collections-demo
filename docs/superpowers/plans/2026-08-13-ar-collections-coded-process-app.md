# AR Collections Coded Process App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a UiPath Apollo Coded Web App where collections users monitor active AR dispute Flow instances, review their tenant-scoped Data Fabric records, and approve or reject a record to trigger the Flow event lifecycle.

**Architecture:** A Vite React application uses a PKCE-backed `UiPath` SDK instance from `uipath.json`. Typed Data Fabric and Maestro services project SDK responses into a stable `DisputeRow` view model, joining visible active instances to entity records only by the Flow `caseId` global variable. The dashboard and detail routes consume those services through page hooks; components render Apollo primitives and never expose raw SDK data.

**Tech Stack:** Vite, React 19, TypeScript, React Router, Vitest, Testing Library, Tailwind 4, UiPath Apollo Wind/Core, Lucide, UiPath TypeScript SDK, UiPath Coded Apps Dev plugin.

## Global Constraints

- App folder: `ar-collections-app` at repository root; it is a Coded Web App, not part of `solution/ARCollectionsDemo/ARCollectionsDemo.uipx`.
- Public PKCE client ID: `57201488-1566-4f9b-a696-1b3773c2af33`; do not request, store, or use a client secret.
- `uipath.json` uses `uipathlabs`, `Playground`, `https://api.uipath.com`, and `http://localhost:5173`.
- Request exactly: `OR.Administration.Read OR.Assets.Read OR.Buckets OR.Buckets.Read OR.Buckets.Write OR.Execution OR.Execution.Read OR.Folders.Read OR.Jobs OR.Jobs.Read OR.Jobs.Write OR.Queues.Read OR.Tasks OR.Tasks.Read OR.Tasks.Write PIMS Traces.Api DataFabric.Data.Read DataFabric.Data.Write DataFabric.Schema.Read ConversationalAgents`.
- Use tenant-scoped `JDARCollectionsEntity` ID `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`.
- Use `new UiPath()` and `getAppBase()`; `vite.config.ts` must set `base: './'`.
- Use `@uipath/apollo-wind` semantic tokens and components; do not use raw color values for application surfaces or statuses.
- All SDK collection reads pass an explicit page size and use cursor pagination; dashboard tables paginate 25 rows at a time.
- Treat an instance as active only when `completedTime === null`; filter completed instances before Data Fabric correlation and metric calculation.
- Correlate a Flow instance to a record only with exact `caseId`; never infer from customer, invoice, or display name.
- Enable decisions only when `lifecycleState === 'Awaiting approval'`; write only `approvalDecision`, `approvalComments`, and `lifecycleState` via `updateRecordById`.
- After every JavaScript or TypeScript change run `npm test`; before completion run `npm run build`.

---

## File Structure

```text
ar-collections-app/
├── package.json                         # scripts and app/test dependencies
├── uipath.json                          # non-secret UiPath runtime metadata
├── vite.config.ts                       # relative-assets and coded-apps-dev config
├── vitest.config.ts                     # browser-like unit-test environment
├── src/
│   ├── main.tsx                         # theme, router, and root render
│   ├── index.css                        # Tailwind/Apollo token imports and shell utilities
│   ├── App.tsx                          # authenticated route tree
│   ├── config.ts                        # immutable entity/process constants and required fields
│   ├── types.ts                         # SDK-independent domain/view-model types
│   ├── lib/paginate.ts                  # typed cursor loop and page-slice helper
│   ├── lib/evidence.ts                  # safe evidence parsing and display rows
│   ├── services/dataFabric.ts           # schema, entity records, and approval write boundary
│   ├── services/maestro.ts              # process discovery, active instance pages, variables
│   ├── services/correlation.ts          # bounded page correlation by exact caseId
│   ├── hooks/useAuth.tsx                # PKCE SDK provider and sign-in/out actions
│   ├── hooks/usePolling.ts              # non-flickering polling state
│   ├── hooks/useDisputeDashboard.ts     # active page/filter/search state and refresh
│   ├── hooks/useDisputeDetail.ts        # keyed detail data and decision mutation state
│   ├── components/AppShell.tsx          # persistent header and navigation rail
│   ├── components/StatusBadge.tsx       # lifecycle and Flow-status semantics
│   ├── components/MetricCard.tsx        # dashboard summary presentation
│   ├── components/DisputeTable.tsx      # accessible, paginated active-instance table
│   ├── components/ApprovalCard.tsx      # validated decision form and outcome feedback
│   ├── components/SectionCard.tsx       # reusable labelled detail section
│   └── pages/
│       ├── DashboardPage.tsx            # live instance dashboard
│       ├── DisputeDetailPage.tsx        # decision workspace
│       └── PlaceholderPage.tsx          # display-only shell destinations
├── src/**/*.test.ts(x)                  # unit/component tests adjacent to implementation
└── README.md                            # concise local verification instructions
```

### Task 1: Scaffold the authenticated Coded Web App

**Files:**
- Create: `ar-collections-app/` Vite project files, `package.json`, `vite.config.ts`, `vitest.config.ts`, `uipath.json`, `src/main.tsx`, `src/index.css`, `src/App.tsx`, `src/hooks/useAuth.tsx`, `src/config.ts`, `src/types.ts`, `README.md`
- Test: `ar-collections-app/src/config.test.ts`

**Interfaces:**
- Produces `ENTITY_ID`, `PROCESS_NAME`, `REQUIRED_ENTITY_FIELDS`, `AuthProvider`, and `useAuth()` for every later task.
- `useAuth()` returns `{ sdk: UiPath; isAuthenticated: boolean; isLoading: boolean; error: string | null; login(): Promise<void>; logout(): void }`.

- [ ] **Step 1: Create the Vite project and install app dependencies**

Run from the repository root:

```bash
npx --yes create-vite@latest ar-collections-app --template react-ts
cd ar-collections-app
npm install @uipath/uipath-typescript @uipath/apollo-wind @uipath/apollo-core @uipath/coded-apps-dev react-router-dom lucide-react next-themes
npm install -D tailwindcss@4 @tailwindcss/postcss postcss autoprefixer vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 2: Add the failing configuration contract test**

```ts
import { describe, expect, it } from 'vitest'
import { ENTITY_ID, PROCESS_NAME, REQUIRED_ENTITY_FIELDS } from './config'

describe('AR collections configuration', () => {
  it('pins the approved entity and Flow contract', () => {
    expect(ENTITY_ID).toBe('bc0fc734-bf94-f111-9b32-000d3ab5d4c4')
    expect(PROCESS_NAME).toBe('ARCollectionsDisputeResolution')
    expect(REQUIRED_ENTITY_FIELDS).toEqual(expect.arrayContaining([
      'caseId', 'lifecycleState', 'approvalDecision', 'approvalComments', 'recommendedAction',
    ]))
  })
})
```

- [ ] **Step 3: Run the test to confirm it fails because configuration is absent**

Run: `npm test -- --run src/config.test.ts`

Expected: FAIL because `src/config.ts` cannot be resolved.

- [ ] **Step 4: Implement configuration, OAuth metadata, and the PKCE provider**

```ts
// src/config.ts
export const ENTITY_ID = 'bc0fc734-bf94-f111-9b32-000d3ab5d4c4'
export const PROCESS_NAME = 'ARCollectionsDisputeResolution'
export const REQUIRED_ENTITY_FIELDS = [
  'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
  'customerReason', 'openedDate', 'evidence', 'lifecycleState', 'disputeType',
  'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
  'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
  'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
  'emailSent', 'auditSummary',
] as const
```

Create `uipath.json` with the exact scope string from Global Constraints and:

```json
{
  "clientId": "57201488-1566-4f9b-a696-1b3773c2af33",
  "orgName": "uipathlabs",
  "tenantName": "Playground",
  "baseUrl": "https://api.uipath.com",
  "redirectUri": "http://localhost:5173"
}
```

Configure the Vite plugin and `base: './'`. Implement `AuthProvider` from the coded-app template: instantiate `new UiPath()`, handle `isInOAuthCallback()`/`completeOAuth()`, call `initialize()` only from `login()`, and implement `logout()` with `sdk.logout()`. Do not add `StrictMode` to `main.tsx`.

- [ ] **Step 5: Configure tests and app scripts**

Set package scripts to:

```json
{
  "dev": "vite",
  "build": "tsc -b && vite build",
  "test": "vitest"
}
```

Configure Vitest with `environment: 'jsdom'`, `globals: true`, and a setup file importing `@testing-library/jest-dom/vitest`. Replace Vite default UI with an authenticated router shell that uses `BrowserRouter basename={getAppBase()}`.

- [ ] **Step 6: Run the test and compile check**

Run:

```bash
npm test -- --run src/config.test.ts
npm run build
```

Expected: PASS and a generated `dist/` directory.

- [ ] **Step 7: Commit the scaffold**

```bash
git add ar-collections-app
git commit -m "feat: scaffold AR collections coded app"
```

### Task 2: Implement typed Data Fabric access and approval writes

**Files:**
- Create: `ar-collections-app/src/services/dataFabric.ts`, `ar-collections-app/src/services/dataFabric.test.ts`
- Modify: `ar-collections-app/src/types.ts`, `ar-collections-app/src/config.ts`

**Interfaces:**
- Produces `DataFabricService` with `validateSchema()`, `getRecordsByCaseIds(caseIds)`, `getRecord(recordId)`, and `recordDecision(record, decision, comments)`.
- `recordDecision()` accepts `ApprovalDecision = 'Approved' | 'Rejected'` and returns the SDK-updated record.

- [ ] **Step 1: Add failing tests for schema validation and the decision payload**

```ts
it('rejects a schema missing an approval field', () => {
  expect(() => validateEntitySchema({ fields: [{ name: 'caseId' }] } as never))
    .toThrow('Data Fabric entity is missing required fields: approvalComments')
})

it('writes only the decision fields through the single-record API', async () => {
  const updateRecordById = vi.fn().mockResolvedValue({ Id: 'record-1' })
  const service = new DataFabricService({ updateRecordById } as never)
  await service.recordDecision({ Id: 'record-1' }, 'Approved', 'Evidence confirmed')
  expect(updateRecordById).toHaveBeenCalledWith(ENTITY_ID, 'record-1', {
    approvalDecision: 'Approved',
    approvalComments: 'Evidence confirmed',
    lifecycleState: 'Approved',
  })
})
```

- [ ] **Step 2: Run the Data Fabric tests to verify they fail**

Run: `npm test -- --run src/services/dataFabric.test.ts`

Expected: FAIL because `DataFabricService` and `validateEntitySchema` do not exist.

- [ ] **Step 3: Implement the Data Fabric boundary**

```ts
export function validateEntitySchema(entity: Pick<EntityGetResponse, 'fields'>) {
  const available = new Set(entity.fields.map((field) => field.name))
  const missing = REQUIRED_ENTITY_FIELDS.filter((field) => !available.has(field))
  if (missing.length) throw new Error(`Data Fabric entity is missing required fields: ${missing.join(', ')}`)
}

async recordDecision(record: Pick<DisputeRecord, 'Id'>, decision: ApprovalDecision, comments: string) {
  return this.entities.updateRecordById(ENTITY_ID, record.Id, {
    approvalDecision: decision,
    approvalComments: comments.trim(),
    lifecycleState: decision,
  })
}
```

Use `Entities` from `@uipath/uipath-typescript/entities`. `getRecordsByCaseIds` must return immediately for an empty list and otherwise issue `queryRecordsById` with `QueryFilterOperator.In`, `fieldName: 'caseId'`, `valueList: caseIds`, selected dashboard fields, `pageSize: 25`, and a cursor loop. `getRecord` calls `getRecordById` so detail multiline values are available.

- [ ] **Step 4: Run Data Fabric tests and the complete JavaScript test suite**

Run:

```bash
npm test -- --run src/services/dataFabric.test.ts
npm test -- --run
```

Expected: PASS.

- [ ] **Step 5: Commit the service boundary**

```bash
git add ar-collections-app/src/config.ts ar-collections-app/src/types.ts ar-collections-app/src/services/dataFabric.ts ar-collections-app/src/services/dataFabric.test.ts
git commit -m "feat: add Data Fabric dispute service"
```

### Task 3: Implement Maestro discovery and deterministic correlation

**Files:**
- Create: `ar-collections-app/src/lib/paginate.ts`, `ar-collections-app/src/services/maestro.ts`, `ar-collections-app/src/services/correlation.ts`, and their `.test.ts` files
- Modify: `ar-collections-app/src/types.ts`

**Interfaces:**
- Produces `MaestroService.getActiveInstances(page)` and `MaestroService.getCaseId(instance)`.
- Produces `correlateInstancePage(instances, getCaseId, getRecordsByCaseIds): Promise<DisputeRow[]>`.
- `DisputeRow` has `{ instance, caseId: string | null, record: DisputeRecord | null, correlation: 'matched' | 'missing-case-id' | 'record-unavailable' }`.

- [ ] **Step 1: Add a failing correlation test**

```ts
it('joins a Flow instance only to the record with the same caseId', async () => {
  const rows = await correlateInstancePage(
    [instance('instance-1'), instance('instance-2')],
    async (flowInstance) => flowInstance.instanceId === 'instance-1' ? 'AR-PAY-003' : null,
    async (caseIds) => caseIds.includes('AR-PAY-003') ? [{ Id: 'record-1', caseId: 'AR-PAY-003' }] : [],
  )
  expect(rows.map(({ correlation, record }) => [correlation, record?.Id])).toEqual([
    ['matched', 'record-1'], ['missing-case-id', undefined],
  ])
})
```

- [ ] **Step 2: Run the correlation test to verify it fails**

Run: `npm test -- --run src/services/correlation.test.ts`

Expected: FAIL because `correlateInstancePage` does not exist.

- [ ] **Step 3: Implement pagination, process discovery, and bounded correlation**

```ts
const target = (await maestroProcesses.getAll()).find((process) => process.name === PROCESS_NAME)
if (!target) throw new Error(`Maestro process not found: ${PROCESS_NAME}`)
const page = await processInstances.getAll({ processKey: target.processKey, pageSize: 25, cursor })
```

Filter the SDK page to `completedTime === null` before correlation. Read case ID from `globalVariables.find(({ name }) => name === 'caseId')?.value`, accepting only non-empty strings. Use a concurrency limit of five for variable reads. Make one Data Fabric `In` query for the current page's resolved case IDs, build a `Map<string, DisputeRecord>`, and return an explicit unmatched state without enabling approval.

- [ ] **Step 4: Run correlation tests and all JavaScript tests**

Run:

```bash
npm test -- --run src/lib/paginate.test.ts src/services/maestro.test.ts src/services/correlation.test.ts
npm test -- --run
```

Expected: PASS.

- [ ] **Step 5: Commit the Flow integration layer**

```bash
git add ar-collections-app/src/lib ar-collections-app/src/services/maestro.ts ar-collections-app/src/services/maestro.test.ts ar-collections-app/src/services/correlation.ts ar-collections-app/src/services/correlation.test.ts ar-collections-app/src/types.ts
git commit -m "feat: correlate active Flow instances to disputes"
```

### Task 4: Build the Apollo dashboard and persistent app shell

**Files:**
- Create: `ar-collections-app/src/hooks/usePolling.ts`, `ar-collections-app/src/hooks/useDisputeDashboard.ts`, `ar-collections-app/src/components/AppShell.tsx`, `MetricCard.tsx`, `StatusBadge.tsx`, `DisputeTable.tsx`, `ar-collections-app/src/pages/DashboardPage.tsx`, `PlaceholderPage.tsx`, and component tests
- Modify: `ar-collections-app/src/App.tsx`, `src/index.css`, `src/main.tsx`

**Interfaces:**
- Consumes `DisputeRow` and `MaestroService` from Task 3.
- Produces the `/disputes` dashboard route and `/analytics`, `/activity`, `/settings` display-only routes.
- `DisputeTable` accepts `{ rows: DisputeRow[]; page: number; totalCount: number; onPageChange(page: number): void }`.

- [ ] **Step 1: Add failing dashboard interaction tests**

```tsx
it('filters rows by lifecycle and opens the selected detail route', async () => {
  const user = userEvent.setup()
  render(<DashboardPage loader={resolvedDashboardLoader} />)
  await user.click(screen.getByRole('tab', { name: 'Awaiting approval' }))
  expect(screen.getByText('AR-PAY-003')).toBeVisible()
  expect(screen.queryByText('AR-POD-002')).not.toBeInTheDocument()
  await user.click(screen.getByRole('link', { name: /AR-PAY-003/i }))
  expect(mockNavigate).toHaveBeenCalledWith('/disputes/instance-1')
})
```

- [ ] **Step 2: Run the dashboard test to verify it fails**

Run: `npm test -- --run src/pages/DashboardPage.test.tsx`

Expected: FAIL because the page and table components do not exist.

- [ ] **Step 3: Implement the shell, live dashboard, and table**

Use Apollo `Button`, `Card`, `Badge`, `Input`, `Tabs`, `EmptyState`, `Skeleton`, `Alert`, and `Toaster` primitives. Use semantic classes such as `bg-background`, `bg-card`, `text-muted-foreground`, and `border-border`; add only minimal layout utilities to `index.css`.

The polling hook must retain visible table data during refresh and update state only when the serialized response changes. `DashboardPage` polls at 15 seconds when authenticated, exposes a refresh button, filters by lifecycle in memory after correlation, and searches case ID/customer name. Render 25-row previous/next pagination controls with “Showing X–Y of Z”. Status badges use semantic variants for `Awaiting approval`, `Approved`, `Rejected`, `Resolved`, `Failed`, and non-final Flow statuses.

- [ ] **Step 4: Run component tests and all JavaScript tests**

Run:

```bash
npm test -- --run src/components src/pages/DashboardPage.test.tsx
npm test -- --run
```

Expected: PASS.

- [ ] **Step 5: Commit the dashboard**

```bash
git add ar-collections-app/src/App.tsx ar-collections-app/src/main.tsx ar-collections-app/src/index.css ar-collections-app/src/hooks ar-collections-app/src/components ar-collections-app/src/pages
git commit -m "feat: add AR dispute operations dashboard"
```

### Task 5: Build the decision workspace and local verification guide

**Files:**
- Create: `ar-collections-app/src/hooks/useDisputeDetail.ts`, `src/lib/evidence.ts`, `src/components/ApprovalCard.tsx`, `src/components/SectionCard.tsx`, `src/pages/DisputeDetailPage.tsx`, and their tests
- Modify: `ar-collections-app/src/App.tsx`, `README.md`

**Interfaces:**
- Consumes `DataFabricService.recordDecision()` and `MaestroService.getCaseId()`.
- Produces `/disputes/:instanceId`, which takes the selected instance ID and renders a typed detail view.
- `ApprovalCard` accepts `{ lifecycleState?: string; isSubmitting: boolean; onSubmit(decision: ApprovalDecision, comments: string): Promise<void> }`.

- [ ] **Step 1: Add failing approval behavior tests**

```tsx
it('submits an approved decision only for an awaiting-approval record', async () => {
  const submit = vi.fn().mockResolvedValue(undefined)
  const user = userEvent.setup()
  render(<ApprovalCard lifecycleState="Awaiting approval" isSubmitting={false} onSubmit={submit} />)
  await user.type(screen.getByLabelText('Comments'), 'Supported by payment evidence')
  await user.click(screen.getByRole('button', { name: 'Approve resolution' }))
  expect(submit).toHaveBeenCalledWith('Approved', 'Supported by payment evidence')
})

it('does not show decision controls for a resolved record', () => {
  render(<ApprovalCard lifecycleState="Resolved" isSubmitting={false} onSubmit={vi.fn()} />)
  expect(screen.queryByRole('button', { name: 'Approve resolution' })).not.toBeInTheDocument()
})
```

- [ ] **Step 2: Run the approval tests to verify they fail**

Run: `npm test -- --run src/components/ApprovalCard.test.tsx`

Expected: FAIL because `ApprovalCard` does not exist.

- [ ] **Step 3: Implement structured details and the approval mutation**

Render case, resolution, Flow monitor, evidence, and audit sections as labelled cards. Parse `evidence` only when it is JSON; flatten a valid object into key/value display rows and show “Evidence details are unavailable” for malformed or non-object values. Do not render raw JSON.

`useDisputeDetail` must use `instanceId` as a polling dependency and key. It resolves the instance, case ID, and entity record; surfaces an actionable missing-record state; posts exactly the decision payload defined in Task 2; disables both decision buttons during submission; then refetches the record and instance.

- [ ] **Step 4: Run detail tests, all JavaScript tests, and the bundle build**

Run:

```bash
npm test -- --run src/components/ApprovalCard.test.tsx src/pages/DisputeDetailPage.test.tsx src/lib/evidence.test.ts
npm test -- --run
npm run build
```

Expected: PASS and `dist/` exists.

- [ ] **Step 5: Add concise local verification instructions**

README content must state:

```markdown
## Local verification

1. Run `npm install` in `ar-collections-app`.
2. Run `npm test -- --run`.
3. Run `npm run dev` and open `http://localhost:5173`.
4. Sign in with UiPath, select an awaiting-approval dispute, and approve or reject it.
5. Confirm the lifecycle and Flow status refresh after the Data Fabric event update.
```

- [ ] **Step 6: Commit the detail workspace and docs**

```bash
git add ar-collections-app
git commit -m "feat: add dispute approval workspace"
```

### Task 6: Final verification and Coded App packaging readiness

**Files:**
- Modify: `ar-collections-app/README.md` only if a verification result requires a correction

**Interfaces:**
- Verifies the completed application without publishing or deploying it.

- [ ] **Step 1: Run the required JavaScript tests**

Run: `cd ar-collections-app && npm test -- --run`

Expected: all Vitest tests PASS.

- [ ] **Step 2: Run the production build and inspect its output**

Run:

```bash
cd ar-collections-app
npm run build
test -d dist
```

Expected: PASS and `dist/` is present.

- [ ] **Step 3: Run the repository regression tests**

Run from repository root: `uv run pytest`

Expected: existing Python contract tests PASS.

- [ ] **Step 4: Verify the deploy prerequisites without publishing**

Run:

```bash
uip login status --output json
uip codedapp --help
```

Expected: logged into `uipathlabs` / `Playground` and the coded-app command is available. Do not package, publish, or deploy unless the user asks.

- [ ] **Step 5: Commit any final verification correction**

```bash
git status --short
git add ar-collections-app/README.md
git commit -m "docs: finalize coded app verification" 
```

Commit only if Step 2–4 required a README correction; otherwise do not create an empty commit.
