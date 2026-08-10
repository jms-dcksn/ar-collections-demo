# AR Collections Data Fabric Flow Wait/Resume Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Start AR dispute resolution from a tenant-scoped Data Fabric record, persist lifecycle data to that record, and safely resume after a Process App approval decision.

**Architecture:** \`JDARCollectionsEntity\` holds the input packet and Flow lifecycle fields. Data Fabric Record Created replaces the manual entry point. Data Fabric update activities write each lifecycle transition. A Record Updated wait loops until its event \`Id\` matches the originating record and provides an approval decision.

**Tech Stack:** UiPath Data Fabric, UiPath Maestro Flow JSON and CLI, Integration Service Data Fabric connector, Python 3.11, pytest, uv.

## Global Constraints

- Use tenant entity \`JDARCollectionsEntity\` (\`bc0fc734-bf94-f111-9b32-000d3ab5d4c4\`) and Data Fabric connection \`6cd4c047-ab49-4aad-8cfa-5681db3db20b\`.
- Retain eight required case-packet fields. Add required \`recipientEmail\`; every lifecycle, proposal, approval, and completion field is optional.
- \`approvalDecision\` is \`approved\` or \`rejected\`; only the matching approved route can invoke \`MockUpdateDispute\` or Outlook.
- Correlate every write and wait-resume decision with the Data Fabric record \`Id\`, never \`caseId\`.
- CLI owns all Data Fabric connector trigger, wait, and update nodes. Never hand-author their \`inputs.detail\`.
- Use \`uv\` for Python. Run \`npm test\` after any standalone JavaScript-file change.
- Do not run Flow debug, publish, deploy, or upload.

---

## File Structure

- Modify: \`config/platform-resources.json\` — tenant entity ID and complete schema.
- Modify: \`tests/platform/test_platform_manifest.py\` — schema assertions.
- Modify: \`solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow\` — event trigger, updates, wait loop, and paths.
- Modify: \`solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json\` — generated Data Fabric binding.
- Modify: \`tests/flow/test_flow_contract.py\` — event-driven Flow contract.
- Create: \`docs/runbooks/ar-collections-data-fabric-lifecycle.md\` — presenter instructions.

### Task 1: Extend and record the Data Fabric entity contract

**Files:**
- Modify: \`tests/platform/test_platform_manifest.py\`
- Modify: \`config/platform-resources.json\`

**Interfaces:**
- Consumes: tenant entity ID \`bc0fc734-bf94-f111-9b32-000d3ab5d4c4\`.
- Produces: \`dataFabricEntities[0]\` with \`folderKey: null\`, the new entity ID, and 29 fields.

- [ ] **Step 1: Write the failing schema test**

\`\`\`python
assert entity["entityKey"] == "bc0fc734-bf94-f111-9b32-000d3ab5d4c4"
assert entity["folderKey"] is None
fields = {field["name"]: field for field in entity["fields"]}
assert fields["recipientEmail"]["required"] is True
assert fields["triageConfidence"]["decimalPrecision"] == 4
assert fields["adjustmentAmount"]["decimalPrecision"] == 2
assert fields["emailSent"]["type"] == "BOOLEAN"
\`\`\`

- [ ] **Step 2: Run it and verify RED**

Run: \`UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_platform_manifest.py -q\`

Expected: FAIL because the manifest references the deleted folder entity and lacks lifecycle fields.

- [ ] **Step 3: Add the approved schema**

Run \`uip df entities update bc0fc734-bf94-f111-9b32-000d3ab5d4c4 --body\` with \`addFields\` for: \`recipientEmail\` (required \`STRING\`); \`lifecycleState\`, \`disputeType\`, \`triageRationale\`, \`triageConfidence\` (\`DECIMAL\`, precision 4), \`evidenceSummary\`, \`rootCause\`, \`recommendedAction\`, \`actionCode\`, \`adjustmentAmount\` (\`DECIMAL\`, precision 2), \`specialistConfidence\` (\`DECIMAL\`, precision 4), \`approvalSummary\`, \`emailSubject\`, \`emailBody\`, \`resourcesUsed\`, \`approvalDecision\`, \`approvedBy\`, \`approvalComments\`, \`updateResult\`, \`emailSent\` (\`BOOLEAN\`), and \`auditSummary\`. Record the complete 29-field schema in the manifest.

- [ ] **Step 4: Verify GREEN**

Run:

\`\`\`bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip df entities get bc0fc734-bf94-f111-9b32-000d3ab5d4c4 --output json
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_platform_manifest.py -q
\`\`\`

Expected: tenant scope, 29 business fields, and PASS.

- [ ] **Step 5: Commit**

\`\`\`bash
git add config/platform-resources.json tests/platform/test_platform_manifest.py
git commit -m "feat: extend AR collections Data Fabric lifecycle"
\`\`\`

### Task 2: Define the event-driven Flow contract

**Files:**
- Modify: \`tests/flow/test_flow_contract.py\`

**Interfaces:**
- Consumes: \`recordCreated.output.Id\`, case fields, and \`waitForApprovalUpdate.output.{Id,approvalDecision,approvedBy,approvalComments}\`.
- Produces: tests for correlation, persistence, and side-effect isolation.

- [ ] **Step 1: Write failing Flow tests**

\`\`\`python
created = nodes_of_type(flow, "uipath.connector.trigger.uipath-uipath-dataservice.record-created")
waits = nodes_of_type(flow, "uipath.connector.event.uipath-uipath-dataservice.record-updated")
assert len(created) == len(waits) == 1
assert not nodes_of_type(flow, "core.trigger.manual")
assert not nodes_of_type(flow, "uipath.human-in-the-loop.quick-form")

correlation = node_with_label(flow, "Updated record matches this dispute?")
assert "$vars.recordCreated.output.Id" in correlation["inputs"]["expression"]
assert "$vars.waitForApprovalUpdate.output.Id" in correlation["inputs"]["expression"]
\`\`\`

Add assertions that each Data Fabric Update Entity Record binds \`recordId\` to \`=js:$vars.recordCreated.output.Id\`; mismatched or decisionless events return to the wait; rejection and manual triage cannot reach API or Outlook.

- [ ] **Step 2: Run it and verify RED**

Run: \`UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/flow/test_flow_contract.py -q\`

Expected: FAIL because the Flow is still manual and uses a quick form.

- [ ] **Step 3: Keep valid assertions**

Retain grounded-agent, route, normalized-proposal, API Workflow, Outlook, and End output checks. Change their data bindings to the created trigger and wait event as required.

- [ ] **Step 4: Commit the red contract**

\`\`\`bash
git add tests/flow/test_flow_contract.py
git commit -m "test: define Data Fabric Flow lifecycle contract"
\`\`\`

### Task 3: Implement the Flow lifecycle

**Files:**
- Modify: \`solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow\`
- Modify: \`solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json\`

**Interfaces:**
- Consumes: record-created \`Id\` and entity fields; record-updated \`Id\`, \`approvalDecision\`, \`approvedBy\`, and \`approvalComments\`.
- Produces: same-record writes and End outputs matching \`RESULT_FIELDS\`.

- [ ] **Step 1: Discover current metadata**

Use Record Created, Record Updated, and Update Entity Record registry/describe commands against the approved connection and \`JDARCollectionsEntity\`. Use the returned event fields and \`uip is resources describe ... --operation Replace -f entityName=JDARCollectionsEntity\` verbatim.

- [ ] **Step 2: Replace manual inputs**

Use \`uip maestro flow node add\` and \`node configure\` to replace \`core.trigger.manual\` with \`uipath.connector.trigger.uipath-uipath-dataservice.record-created\`. Remove \`Load Sample Case\`; bind agent case packets to the created-event output.

- [ ] **Step 3: Persist lifecycle state**

Use CLI-owned Update Entity Record nodes for \`triaging\`, \`needs_manual_triage\`, \`awaiting_approval\` with the normalized proposal, \`approved\`, \`rejected\`, \`updating\`, and \`resolved\` with API result, email result, and audit summary. Every node sets \`entityName: JDARCollectionsEntity\` and \`recordId: =js:$vars.recordCreated.output.Id\`.

- [ ] **Step 4: Add the safe wait/resume loop**

Add \`uipath.connector.event.uipath-uipath-dataservice.record-updated\` as \`waitForApprovalUpdate\`. Add decisions labelled \`Updated record matches this dispute?\` and \`Approval decision supplied?\`. Their false branches loop to the wait. The approved branch maps wait output \`approvedBy\` and \`approvalComments\` to the API Workflow; the rejected branch writes a terminal state.

- [ ] **Step 5: Guard side effects**

Bind Outlook to \`recordCreated.output.recipientEmail\`. Only matching approval reaches API and Outlook. Manual triage and rejection persist their terminal state and end without either side effect.

- [ ] **Step 6: Verify GREEN**

Run:

\`\`\`bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow format solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/flow/test_flow_contract.py -q
\`\`\`

Expected: validator has no warnings and test passes.

- [ ] **Step 7: Commit**

\`\`\`bash
git add solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json
git commit -m "feat: trigger AR disputes from Data Fabric"
\`\`\`

### Task 4: Document and verify the lifecycle

**Files:**
- Create: \`docs/runbooks/ar-collections-data-fabric-lifecycle.md\`

**Interfaces:**
- Consumes: a Process App-created entity record and its matching approval/rejection update.
- Produces: a repeatable demo procedure.

- [ ] **Step 1: Write the runbook**

Document record creation with all required fields and \`recipientEmail\`; verify \`awaiting_approval\`; update that record with \`approvalDecision\`, \`approvedBy\`, and \`approvalComments\`; and verify terminal state. Include rejection/manual-triage side-effect checks and an unrelated-record update being ignored.

- [ ] **Step 2: Run full verification**

\`\`\`bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
npm test
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
git diff --check
\`\`\`

Expected: all tests and validation pass with no whitespace errors.

- [ ] **Step 3: Commit**

\`\`\`bash
git add docs/runbooks/ar-collections-data-fabric-lifecycle.md
git commit -m "docs: add Data Fabric dispute lifecycle runbook"
\`\`\`

## Plan Self-Review

- Coverage: entity schema, event trigger, record-ID wait loop, persistence, side-effect isolation, tests, and runbook are all covered.
- Scope: Process App implementation, deployment, publish/upload, live debug, retention, and RBAC changes are excluded.
- Consistency: the tenant entity ID, connection, decision values, and record-ID correlation are constant across tasks.
