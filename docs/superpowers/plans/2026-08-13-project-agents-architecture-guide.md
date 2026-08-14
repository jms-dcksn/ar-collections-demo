# Project AGENTS Architecture Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the root `AGENTS.md` into a concise operating map for the AR collections demo, including its verified Data Fabric test record, architecture, technology stack, ownership boundaries, and validation commands.

**Architecture:** Keep the root guide focused on repository-wide contracts and stable component relationships. Delegate solution-lifecycle details to `solution/ARCollectionsDemo/AGENTS.md`, and link to checked-in manifests, specifications, and runbooks instead of duplicating them.

**Tech Stack:** Markdown, UiPath Solution, Maestro Flow, low-code agents, API Workflows, Data Fabric, Context Grounding, Integration Service, Outlook, React, TypeScript, Vite, Apollo, Tailwind CSS, UiPath TypeScript SDK, Vitest, Python, pytest, and `uv`.

## Global Constraints

- Modify only the repository-root `AGENTS.md` during implementation.
- Preserve the existing GitHub issue-label guidance verbatim.
- Preserve the unrelated local edit in `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`.
- Treat `solution/ARCollectionsDemo/AGENTS.md` as authoritative for solution operations below that directory; do not duplicate its generated lifecycle reference.
- Use `JD_Demos/demos` as the deployment folder contract.
- Use tenant-level entity `JDARCollectionsEntity` with UUID `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`.
- Treat Data Fabric record `Id` as the update and wait/resume correlation key; use `caseId` only for business identity and Coded App display correlation.
- Do not claim that inserting a Data Fabric record is side-effect free; a deployed record-created trigger can start the Flow.
- Do not use emojis in documentation.

---

### Task 1: Expand the Repository Operating Guide

**Files:**
- Modify: `AGENTS.md`
- Reference: `config/platform-resources.json`
- Reference: `solution/ARCollectionsDemo/ARCollectionsDemo.uipx`
- Reference: `solution/ARCollectionsDemo/AGENTS.md`
- Reference: `docs/runbooks/ar-collections-data-fabric-lifecycle.md`
- Reference: `docs/superpowers/specs/2026-08-10-ar-collections-data-fabric-flow-wait-resume-design.md`
- Reference: `docs/superpowers/specs/2026-08-13-ar-collections-coded-process-app-design.md`

**Interfaces:**
- Consumes: Checked-in resource identifiers, component paths, lifecycle contracts, and the verified sample record from the current task context.
- Produces: A repository-wide guide for future agents; no runtime or package interface changes.

- [ ] **Step 1: Replace the minimal root guide with the approved durable structure**

Retain `# Repository Working Agreements` and the existing `## GitHub Issues` section. Add these sections before GitHub Issues:

1. `## Project Purpose` — explain that this is a demo-grade, event-driven AR dispute-resolution solution.
2. `## Architecture` — map Data Fabric, Maestro Flow, inline triage/specialist agents, Context Grounding, API Workflows, Outlook, and the Coded App.
3. `## Repository Map` — identify `solution/ARCollectionsDemo`, `ar-collections-app`, `config`, `knowledge`, `tests`, and `docs/runbooks`.
4. `## Data Flow and Ownership` — document record-created startup, triage/routing, proposal persistence, record-ID wait/resume, rejection/manual-triage safety, and approved-path side effects.
5. `## Platform Contracts` — record the active organization/tenant, deployment folder, entity identifiers, Outlook binding, and the verified test row.
6. `## Technology Stack` — summarize UiPath and web/test technologies.
7. `## Working Rules` — state the nested-AGENTS precedence, resource-manifest authority, correlation rules, safe demo implementation preference, and test-record trigger warning.
8. `## Validation` — list the exact commands below.

The sample-record subsection must contain:

```markdown
- Entity: `JDARCollectionsEntity` (`bc0fc734-bf94-f111-9b32-000d3ab5d4c4`), tenant-level.
- Record ID: `2D7F2D6A-1897-F111-9B33-7C1E522150AC`.
- Case ID: `AR-PAY-20260813-01`.
- Scenario: payment misapplication for Summit Medical Distribution, invoice `INV-30915`, balance `36800.00`, payment reference `PAY-77821`.
- Recipient: `james.dickson@uipath.com`.
```

Immediately follow it with a warning that the row may be updated by the Flow and that creating another row can start the deployed record-created trigger.

- [ ] **Step 2: Include exact validation commands**

Use this command block:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
npm --prefix ar-collections-app test -- --run
npm --prefix ar-collections-app run build
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json
git diff --check
```

State that `npm test` is mandatory after JavaScript or TypeScript edits and that Python dependency management must use `uv`, never `pip`.

- [ ] **Step 3: Verify factual and scope constraints**

Run:

```bash
rg -n "JD_Demos/demos|JDARCollectionsEntity|bc0fc734-bf94-f111-9b32-000d3ab5d4c4|2D7F2D6A-1897-F111-9B33-7C1E522150AC|AR-PAY-20260813-01|Data Fabric record.*Id|caseId" AGENTS.md
git diff --check
git diff -- AGENTS.md
git status --short
```

Expected:

- Every stable platform identifier and the sample record appear once in the appropriate section.
- The guide distinguishes record `Id` from `caseId`.
- `git diff --check` exits successfully.
- The only implementation file changed is `AGENTS.md`; the pre-existing Flow edit remains present but untouched.

- [ ] **Step 4: Commit only the root guide**

```bash
git add AGENTS.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs: document AR collections project architecture"
```

Expected staged file list: `AGENTS.md` only.
