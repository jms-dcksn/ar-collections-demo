# AR Collections Data Fabric Entity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision the approved folder-scoped Data Fabric entity and serialize Flow evidence as JSON text.

**Architecture:** `config/platform-resources.json` holds the provisioned entity's immutable ID and exact schema, with Python contract tests. The Flow returns the selected sample case unchanged except that `evidence` is JSON text matching the `MULTILINE_TEXT` entity column.

**Tech Stack:** UiPath CLI Data Fabric extension, Maestro Flow JSON, Python 3.11, pytest, uv.

## Global Constraints

- Use folder `JD_Demos/demos/ARCollectionsDemo` (`bbe64c10-b957-4adf-a535-77109c673e5a`).
- Use display name `JD AR Collections Entity` and system name `JDARCollectionsEntity`.
- Create only the eight approved fields, all required; `caseId` is unique and `outstandingBalance` is `DECIMAL` precision 2.
- Persist `evidence` as JSON text in `MULTILINE_TEXT`; do not add deferred lifecycle, approval, routing, recommendation, update-result, audit, or mapping fields.
- Keep sample cases in `Load Sample Case`, serializing only `evidence` with `JSON.stringify`.
- Use `uv` for Python commands; run `npm test` after any JavaScript-file modification.

---

## File Structure

- Modify: `config/platform-resources.json` — checked-in entity identity and schema.
- Modify: `tests/platform/test_platform_manifest.py` — manifest schema assertions.
- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow` — evidence serialization.
- Modify: `tests/flow/test_flow_contract.py` — loader serialization assertion.

### Task 1: Declare the approved entity contract

**Files:**
- Modify: `tests/platform/test_platform_manifest.py`
- Modify: `config/platform-resources.json`

**Interfaces:**
- Consumes: the approved names, folder ID, fields, and constraints from the design spec.
- Produces: `dataFabricEntities[0]` with `folderKey`, `displayName`, `systemName`, `entityKey`, and `fields`.

- [ ] **Step 1: Write the failing test**

```python
def test_platform_manifest_declares_the_approved_data_fabric_entity():
    manifest = json.loads(MANIFEST.read_text())
    entity = manifest.get("dataFabricEntities", [{}])[0]
    assert entity["folderKey"] == "bbe64c10-b957-4adf-a535-77109c673e5a"
    assert entity["displayName"] == "JD AR Collections Entity"
    assert entity["systemName"] == "JDARCollectionsEntity"
    assert [field["name"] for field in entity["fields"]] == [
        "caseId", "customerName", "customerAccountId", "invoiceNumber",
        "outstandingBalance", "customerReason", "openedDate", "evidence",
    ]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_platform_manifest.py -q`

Expected: FAIL because `dataFabricEntities` is not yet present.

- [ ] **Step 3: Write minimal configuration**

```json
"dataFabricEntities": [{
  "folderKey": "bbe64c10-b957-4adf-a535-77109c673e5a",
  "displayName": "JD AR Collections Entity",
  "systemName": "JDARCollectionsEntity",
  "entityKey": "b6ea47fa-9f93-f111-9b32-000d3ab5d4c4",
  "fields": [
    {"name": "caseId", "type": "STRING", "required": true, "unique": true},
    {"name": "customerName", "type": "STRING", "required": true, "unique": false},
    {"name": "customerAccountId", "type": "STRING", "required": true, "unique": false},
    {"name": "invoiceNumber", "type": "STRING", "required": true, "unique": false},
    {"name": "outstandingBalance", "type": "DECIMAL", "required": true, "unique": false, "decimalPrecision": 2},
    {"name": "customerReason", "type": "MULTILINE_TEXT", "required": true, "unique": false},
    {"name": "openedDate", "type": "DATE", "required": true, "unique": false},
    {"name": "evidence", "type": "MULTILINE_TEXT", "required": true, "unique": false}
  ]
}]
```

Extend the manifest validation allow-list and validate `entityKey` as a canonical UUID.

- [ ] **Step 4: Run the focused test**

Run: `UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_platform_manifest.py -q`

Expected: PASS after the entity is created and its real ID is recorded.

- [ ] **Step 5: Commit**

```bash
git add config/platform-resources.json tests/platform/test_platform_manifest.py
git commit -m "feat: declare AR collections Data Fabric entity"
```

### Task 2: Serialize Flow evidence for the text field

**Files:**
- Modify: `tests/flow/test_flow_contract.py`
- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`

**Interfaces:**
- Consumes: `cases[caseId]` from `Load Sample Case`.
- Produces: the selected case packet with `evidence` replaced by JSON text.

- [ ] **Step 1: Write the failing test**

```python
def test_sample_case_loader_serializes_evidence_for_data_fabric():
    flow, _, _ = load_contract()
    script = node_with_label(flow, "Load Sample Case")["inputs"]["script"]
    assert "JSON.stringify(cases[caseId].evidence)" in script
    assert "return { ...cases[caseId], evidence:" in script
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/flow/test_flow_contract.py -q`

Expected: FAIL because `evidence` is currently returned as an object.

- [ ] **Step 3: Write minimal implementation**

```javascript
return { ...cases[caseId], evidence: JSON.stringify(cases[caseId].evidence) };
```

Replace only the loader's existing `return cases[caseId];`.

- [ ] **Step 4: Run the focused test**

Run: `UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/flow/test_flow_contract.py -q`

Expected: PASS with existing Flow-contract assertions intact.

- [ ] **Step 5: Commit**

```bash
git add solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow tests/flow/test_flow_contract.py
git commit -m "feat: serialize AR collections case evidence"
```

### Task 3: Provision and verify the Data Fabric entity

**Files:**
- Modify: `config/platform-resources.json`
- Modify: `tests/platform/test_platform_manifest.py`

**Interfaces:**
- Consumes: Task 1's manifest entry and the authenticated `uip` CLI session.
- Produces: one native `JDARCollectionsEntity` in the approved folder, referenced by `entityKey`.

- [ ] **Step 1: Verify folder and entity absence**

Run:

```bash
uip or folders list --output json
uip df entities list --folder-key bbe64c10-b957-4adf-a535-77109c673e5a --native-only --output json
```

Expected: the folder ID resolves to the approved path and no same-name entity exists.

- [ ] **Step 2: Create the exact schema**

```bash
uip df entities create JDARCollectionsEntity --folder-key bbe64c10-b957-4adf-a535-77109c673e5a --body '{"displayName":"JD AR Collections Entity","fields":[{"fieldName":"caseId","type":"STRING","isRequired":true,"isUnique":true},{"fieldName":"customerName","type":"STRING","isRequired":true},{"fieldName":"customerAccountId","type":"STRING","isRequired":true},{"fieldName":"invoiceNumber","type":"STRING","isRequired":true},{"fieldName":"outstandingBalance","type":"DECIMAL","isRequired":true,"decimalPrecision":2},{"fieldName":"customerReason","type":"MULTILINE_TEXT","isRequired":true},{"fieldName":"openedDate","type":"DATE","isRequired":true},{"fieldName":"evidence","type":"MULTILINE_TEXT","isRequired":true}]}' --output json
```

Use `isRequired: true` on all fields, `isUnique: true` only on `caseId`, and `decimalPrecision: 2` only on `outstandingBalance`.

- [ ] **Step 3: Read back and record the entity ID**

Run: `uip df entities get b6ea47fa-9f93-f111-9b32-000d3ab5d4c4 --folder-key bbe64c10-b957-4adf-a535-77109c673e5a --output json`

Expected: the returned entity has exactly the eight approved business fields, their required/unique constraints, and decimal precision 2. Store its ID in `entityKey`.

- [ ] **Step 4: Run full verification**

Run:

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest tests/platform/test_platform_manifest.py tests/flow/test_flow_contract.py -q
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/2026-08-08-ar-collections-data-fabric-entity.md config/platform-resources.json tests/platform/test_platform_manifest.py solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow tests/flow/test_flow_contract.py
git commit -m "feat: provision AR collections Data Fabric entity"
```

## Plan Self-Review

- Coverage: Task 1 records the entire approved schema; Task 2 maps Flow evidence to the text representation; Task 3 creates and reads back the live entity.
- Scope: no deferred fields or persistence nodes are included.
- Consistency: the Flow's `JSON.stringify` output is exactly the manifest's `MULTILINE_TEXT` evidence type.
