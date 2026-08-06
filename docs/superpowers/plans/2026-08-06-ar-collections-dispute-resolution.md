# AR Collections Dispute Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, package, and deploy a demo-grade UiPath solution that resolves one of three curated AR disputes through grounded agent triage, a specialist recommendation, collector approval, a mocked update, and a real presenter-addressed Outlook email.

**Architecture:** One Maestro Flow owns deterministic case loading, grounded triage, exclusive specialist routing, the human approval, side-effect ordering, and business exits. Four inline agents perform triage and specialist reasoning; the payment specialist alone uses a grounded playbook plus an agent-callable API Workflow. A second API Workflow is invoked by the Flow only after approval. Two version-controlled text articles back two Context Grounding indexes in `JD_Demos/demos`.

**Tech Stack:** UiPath CLI 1.198.0, UiPath Maestro Flow, UiPath inline Agents, UiPath API Workflows, Context Grounding, Orchestrator storage buckets, Action Center Quick Form, Microsoft Outlook 365 Integration Service, Python 3.11, pytest 8, jsonschema, uv, Git.

## Global Constraints

- Treat [the approved design](../specs/2026-08-05-ar-collections-dispute-resolution-design.md) as authoritative.
- Target tenant `uipathlabs`, tenant `Playground`, and parent folder `JD_Demos/demos`.
- Support exactly `AR-PO-001`, `AR-POD-002`, and `AR-PAY-003`; retain `AR-AMB-004` only as a hidden negative fixture.
- Keep the canvas to one explicit exception path: unsupported or triage confidence below `0.75` goes to `needs_manual_triage`. Collector rejection is a designed business path, not an error path.
- Side effects are ordered `Quick Form approval -> MockUpdateDispute -> Outlook Send Email`. Rejection and manual triage must reach neither side-effect node.
- Hand-author Flow-native nodes and inline-agent resources only from registry/scaffold output. Add and configure Integration Service connector nodes with `uip maestro flow node add/configure`; do not invent connector node definitions.
- Run `UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip login status --output json` before any live UiPath operation. Stop if the organization, tenant, or auth target differs.
- Use `uv` for Python setup and execution. No JavaScript files are planned; if one is introduced, run `npm test` before its commit.
- Do not run the deployed Flow or send email until the user gives explicit approval for the live smoke test and supplies the internal recipient address.
- Use fictional case/customer data only. Never derive the email recipient from a sample customer record.
- Preserve CLI-generated UUIDs. Record them in configuration files instead of renaming generated inline-agent directories.
- After each Flow edit, run `uip maestro flow format` and `uip maestro flow validate`. After each agent edit, run `uip agent refresh` and `uip agent validate`.

## Expected Repository Layout

```text
ar-collections-demo/
├── .gitignore
├── pyproject.toml
├── uv.lock
├── config/
│   ├── agent-projects.json
│   └── platform-resources.json
├── knowledge/
│   ├── payment/payment-misapplication-resolution-playbook.txt
│   └── triage/ar-dispute-taxonomy-and-examples.txt
├── solution/ARCollectionsDemo/
│   ├── ARCollectionsDemo.uipx
│   ├── ARCollectionsDisputeResolution/
│   │   ├── ARCollectionsDisputeResolution.flow
│   │   ├── bindings_v2.json
│   │   ├── project.uiproj
│   │   └── <four CLI-generated UUID directories recorded in config/agent-projects.json>/
│   │       ├── agent.json
│   │       ├── bindings_v2.json
│   │       └── resources/<CLI-generated resource UUID>/resource.json
│   ├── LookupPaymentApplication/
│   │   ├── Workflow.json
│   │   ├── bindings_v2.json
│   │   ├── entry-points.json
│   │   └── project.uiproj
│   └── MockUpdateDispute/
│       ├── Workflow.json
│       ├── bindings_v2.json
│       ├── entry-points.json
│       └── project.uiproj
├── tests/
│   ├── agents/test_agent_contracts.py
│   ├── api_workflows/
│   │   ├── lookup-payment-input.json
│   │   ├── lookup-payment-expected.json
│   │   ├── mock-update-input.json
│   │   ├── mock-update-expected.json
│   │   ├── test_api_workflows.py
│   │   └── verify_fixture_runs.py
│   ├── flow/test_flow_contract.py
│   ├── knowledge/test_knowledge_articles.py
│   ├── platform/test_platform_manifest.py
│   └── test_solution_structure.py
└── docs/
    ├── build-evidence/
    │   ├── context-grounding.md
    │   └── deployment-and-smoke.md
    └── demo-runbook.md
```

The UUID directory names cannot be known before `uip agent init` runs. `config/agent-projects.json` is the stable source of truth that maps the four logical names to the exact generated IDs and therefore makes every later file operation deterministic.

---

## Task 1: Establish the Test Harness and UiPath Solution Skeleton

**Files:**

- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `uv.lock`
- Create: `tests/test_solution_structure.py`
- Create: `solution/ARCollectionsDemo/ARCollectionsDemo.uipx`
- Create: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`
- Create: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/project.uiproj`
- Create: `solution/ARCollectionsDemo/LookupPaymentApplication/{Workflow.json,bindings_v2.json,entry-points.json,project.uiproj}`
- Create: `solution/ARCollectionsDemo/MockUpdateDispute/{Workflow.json,bindings_v2.json,entry-points.json,project.uiproj}`

- [ ] **Step 1: Add the Python test project and ignore rules**

Create `pyproject.toml` with this exact baseline:

```toml
[project]
name = "ar-collections-demo-tests"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[dependency-groups]
dev = [
  "jsonschema>=4.23,<5",
  "pytest>=8.3,<9",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

Create `.gitignore` with `.venv/`, `__pycache__/`, `.pytest_cache/`, `.local/`, `dist/`, `*.nupkg`, and `*.zip`. Then run:

```bash
uv lock
uv sync
```

Expected: `uv.lock` is generated and pytest is available through `uv run`.

- [ ] **Step 2: Write the failing solution-structure test**

Create `tests/test_solution_structure.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SOLUTION = ROOT / "solution" / "ARCollectionsDemo"


def test_solution_contains_one_flow_and_two_api_workflows():
    expected = {
        "ARCollectionsDisputeResolution": ".flow",
        "LookupPaymentApplication": "Workflow.json",
        "MockUpdateDispute": "Workflow.json",
    }
    for project, marker in expected.items():
        project_dir = SOLUTION / project
        assert project_dir.is_dir(), project
        if marker == ".flow":
            assert (project_dir / f"{project}.flow").is_file()
        else:
            assert (project_dir / marker).is_file()


def test_solution_manifest_registers_exactly_three_projects():
    manifest = json.loads((SOLUTION / "ARCollectionsDemo.uipx").read_text())
    projects = manifest["Projects"]
    assert len(projects) == 3
    serialized = json.dumps(projects)
    for name in (
        "ARCollectionsDisputeResolution",
        "LookupPaymentApplication",
        "MockUpdateDispute",
    ):
        assert name in serialized
```

- [ ] **Step 3: Run the structure test and observe the expected failure**

```bash
uv run pytest tests/test_solution_structure.py
```

Expected: FAIL because `solution/ARCollectionsDemo` does not exist.

- [ ] **Step 4: Confirm the live CLI target before scaffolding**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip --version
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip login status --output json
```

Expected: CLI `1.198.0` or a compatible later version, authenticated organization `uipathlabs`, tenant `Playground`. If either target differs, stop and ask the user before writing generated UiPath metadata.

- [ ] **Step 5: Scaffold the solution and its three projects with the CLI**

Run from the repository root:

```bash
mkdir -p solution
cd solution
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution init ARCollectionsDemo --output json
cd ARCollectionsDemo
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow init ARCollectionsDisputeResolution --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow init LookupPaymentApplication --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow init MockUpdateDispute --output json
```

Expected: each command reports success; the two API Workflows and one Flow are registered in `ARCollectionsDemo.uipx`. Preserve the generated metadata instead of recreating it manually.

- [ ] **Step 6: Re-run the structure test**

```bash
cd /Users/james.dickson/dev/playground/ar-collections-demo
uv run pytest tests/test_solution_structure.py
```

Expected: PASS.

- [ ] **Step 7: Commit the scaffold**

```bash
git add .gitignore pyproject.toml uv.lock tests/test_solution_structure.py solution/ARCollectionsDemo
git commit -m "build: scaffold AR collections UiPath solution"
```

---

## Task 2: Author and Test the Two Knowledge Articles

**Files:**

- Create: `knowledge/triage/ar-dispute-taxonomy-and-examples.txt`
- Create: `knowledge/payment/payment-misapplication-resolution-playbook.txt`
- Create: `tests/knowledge/test_knowledge_articles.py`

- [ ] **Step 1: Write failing content-contract tests**

Create `tests/knowledge/test_knowledge_articles.py`:

```python
from pathlib import Path

ROOT = Path(__file__).parents[2]
TRIAGE = ROOT / "knowledge/triage/ar-dispute-taxonomy-and-examples.txt"
PAYMENT = ROOT / "knowledge/payment/payment-misapplication-resolution-playbook.txt"


def normalized(path: Path) -> str:
    assert path.is_file()
    return path.read_text().lower()


def test_triage_article_covers_taxonomy_examples_and_manual_gate():
    text = normalized(TRIAGE)
    for required in (
        "po_mismatch",
        "missing_pod",
        "payment_misapplication",
        "unsupported",
        "positive signals",
        "exclusions",
        "example 1",
        "example 2",
        "0.75",
        "manual triage",
    ):
        assert required in text


def test_payment_article_covers_evidence_controls_and_demo_case():
    text = normalized(PAYMENT)
    for required in (
        "payment reference",
        "remittance",
        "target invoice",
        "control",
        "reallocation",
        "customer communication",
        "worked example 1",
        "worked example 2",
        "ar-pay-003",
        "pay-77821",
        "inv-30909",
        "inv-30915",
    ):
        assert required in text
```

- [ ] **Step 2: Run the knowledge tests and observe the expected failure**

```bash
uv run pytest tests/knowledge/test_knowledge_articles.py
```

Expected: FAIL because both text files are absent.

- [ ] **Step 3: Write the triage taxonomy article**

Use plain text and these exact sections for each of the three supported types: `Definition`, `Positive signals`, `Exclusions`, `Example 1`, and `Example 2`. Include these classification rules:

```text
Return po_mismatch only when invoice and purchase-order price, quantity, tax, or authorized amount conflict.
Return missing_pod only when payment is blocked because delivery evidence is requested or missing.
Return payment_misapplication only when the customer reports payment but the target invoice remains open because application is absent or incorrect.
Return unsupported when the evidence does not establish one supported category.
Return unsupported and request manual triage when confidence is below 0.75.
Never infer payment-system application details from a customer's statement alone.
```

The examples must include the three named demo patterns plus neutral examples that do not copy their wording. The ambiguous guidance must make `AR-AMB-004` unsupported.

- [ ] **Step 4: Write the payment-resolution article**

Use these exact headings: `Required evidence`, `Matching rules`, `Controls before reallocation`, `Resolution steps`, `Customer communication`, `Worked example 1`, and `Worked example 2`. State that reallocation may be recommended only when payment amount/reference/remittance match, the wrong applied invoice is identified, the intended target invoice is identified, and the source evidence reports `MISAPPLIED`. Include the `AR-PAY-003` values from the approved design and a second fictional worked example with different identifiers.

- [ ] **Step 5: Run the tests**

```bash
uv run pytest tests/knowledge/test_knowledge_articles.py
```

Expected: 2 passed.

- [ ] **Step 6: Commit the knowledge sources**

```bash
git add knowledge tests/knowledge
git commit -m "feat: add AR dispute grounding articles"
```

---

## Task 3: Implement and Verify Both Deterministic API Workflows

**Files:**

- Modify: `solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json`
- Modify: `solution/ARCollectionsDemo/LookupPaymentApplication/entry-points.json`
- Modify: `solution/ARCollectionsDemo/LookupPaymentApplication/project.uiproj`
- Modify: `solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json`
- Modify: `solution/ARCollectionsDemo/MockUpdateDispute/entry-points.json`
- Modify: `solution/ARCollectionsDemo/MockUpdateDispute/project.uiproj`
- Create: `tests/api_workflows/lookup-payment-input.json`
- Create: `tests/api_workflows/lookup-payment-expected.json`
- Create: `tests/api_workflows/mock-update-input.json`
- Create: `tests/api_workflows/mock-update-expected.json`
- Create: `tests/api_workflows/test_api_workflows.py`
- Create: `tests/api_workflows/verify_fixture_runs.py`

- [ ] **Step 1: Add the four input/output fixtures**

`lookup-payment-input.json`:

```json
{
  "caseId": "AR-PAY-003",
  "customerAccountId": "SUMMIT-4402",
  "invoiceNumber": "INV-30915",
  "paymentReference": "PAY-77821"
}
```

`lookup-payment-expected.json`:

```json
{
  "paymentReference": "PAY-77821",
  "paymentAmount": 36800,
  "paymentDate": "2026-07-02",
  "appliedInvoiceNumber": "INV-30909",
  "targetInvoiceNumber": "INV-30915",
  "applicationStatus": "MISAPPLIED",
  "matchedRemittance": true,
  "recommendedAction": "REALLOCATE_PAYMENT",
  "sourceSystem": "MockCashApplication"
}
```

`mock-update-input.json`:

```json
{
  "caseId": "AR-PAY-003",
  "disputeType": "payment_misapplication",
  "actionCode": "REALLOCATE_PAYMENT",
  "adjustmentAmount": 0,
  "approvedBy": "Demo Collector",
  "approvalComments": "Approved during demo verification."
}
```

`mock-update-expected.json`:

```json
{
  "updateId": "UPD-AR-PAY-003-REALLOCATE_PAYMENT",
  "status": "UPDATED",
  "updatedAt": "2026-08-06T12:00:00Z",
  "message": "Recorded REALLOCATE_PAYMENT for AR-PAY-003 in MockARDisputeSystem."
}
```

- [ ] **Step 2: Write failing static contract tests**

Create `tests/api_workflows/test_api_workflows.py` to load both `Workflow.json` files and assert:

```python
EXPECTED = {
    "LookupPaymentApplication": {
        "inputs": {"caseId", "customerAccountId", "invoiceNumber", "paymentReference"},
        "outputs": {
            "paymentReference", "paymentAmount", "paymentDate",
            "appliedInvoiceNumber", "targetInvoiceNumber", "applicationStatus",
            "matchedRemittance", "recommendedAction", "sourceSystem",
        },
    },
    "MockUpdateDispute": {
        "inputs": {
            "caseId", "disputeType", "actionCode", "adjustmentAmount",
            "approvedBy", "approvalComments",
        },
        "outputs": {"updateId", "status", "updatedAt", "message"},
    },
}
```

The test must recursively inspect the generated JSON rather than assume property order, verify both schemas contain the exact field sets, and verify the workflow contains a `Response` activity. It must also assert that neither workflow contains connector/resource bindings or network-call activities.

- [ ] **Step 3: Run the static test and observe the expected failure**

```bash
uv run pytest tests/api_workflows/test_api_workflows.py
```

Expected: FAIL because the scaffolds do not expose the required contracts.

- [ ] **Step 4: Implement `LookupPaymentApplication` from the generated API Workflow shape**

Keep the generated `Sequence` root. Add an input contract with the four input names, a deterministic JavaScript/Assign body, and a `Response` output. The core mapping must be equivalent to:

```javascript
const key = `${caseId}|${customerAccountId}|${invoiceNumber}|${paymentReference}`;
if (key !== "AR-PAY-003|SUMMIT-4402|INV-30915|PAY-77821") {
  throw new Error("LookupPaymentApplication supports only curated demo input AR-PAY-003.");
}
return {
  paymentReference: "PAY-77821",
  paymentAmount: 36800,
  paymentDate: "2026-07-02",
  appliedInvoiceNumber: "INV-30909",
  targetInvoiceNumber: "INV-30915",
  applicationStatus: "MISAPPLIED",
  matchedRemittance: true,
  recommendedAction: "REALLOCATE_PAYMENT",
  sourceSystem: "MockCashApplication"
};
```

This JavaScript lives inside `Workflow.json`; it is not a standalone `.js` file, so the workspace `npm test` rule is not triggered.

- [ ] **Step 5: Implement `MockUpdateDispute` from the same generated shape**

Validate `actionCode` against `ISSUE_CREDIT`, `PROVIDE_POD`, and `REALLOCATE_PAYMENT`. Return the deterministic receipt:

```javascript
return {
  updateId: `UPD-${caseId}-${actionCode}`,
  status: "UPDATED",
  updatedAt: "2026-08-06T12:00:00Z",
  message: `Recorded ${actionCode} for ${caseId} in MockARDisputeSystem.`
};
```

No external resource or connector is permitted in either workflow.

- [ ] **Step 6: Validate, build, and run each workflow directly**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow run solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --input-arguments '{"caseId":"AR-PAY-003","customerAccountId":"SUMMIT-4402","invoiceNumber":"INV-30915","paymentReference":"PAY-77821"}' --no-auth --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow build solution/ARCollectionsDemo/LookupPaymentApplication --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow run solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --input-arguments '{"caseId":"AR-PAY-003","disputeType":"payment_misapplication","actionCode":"REALLOCATE_PAYMENT","adjustmentAmount":0,"approvedBy":"Demo Collector","approvalComments":"Approved during demo verification."}' --no-auth --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow build solution/ARCollectionsDemo/MockUpdateDispute --output json
```

Expected: both validations and builds report success; each runtime result equals its expected fixture after unwrapping the CLI envelope.

- [ ] **Step 7: Automate fixture execution and run the API test suite**

Create `verify_fixture_runs.py` using `subprocess.run` with argument arrays, `check=True`, and `UIPATH_CLI_DISABLE_VERSION_SYNC=1`. It must invoke the two exact `uip api-workflow run ... --no-auth --output json` commands, normalize the CLI response envelope and PascalCase wrapper keys if present, and compare the business output to the expected JSON fixtures.

```bash
uv run pytest tests/api_workflows/test_api_workflows.py
uv run python tests/api_workflows/verify_fixture_runs.py
```

Expected: all static tests pass and the script prints `2 API Workflow fixtures passed`.

- [ ] **Step 8: Commit the API Workflows**

```bash
git add solution/ARCollectionsDemo/LookupPaymentApplication solution/ARCollectionsDemo/MockUpdateDispute tests/api_workflows
git commit -m "feat: add deterministic dispute API workflows"
```

---

## Task 4: Define and Provision the Context Grounding Resources

**Files:**

- Create: `config/platform-resources.json`
- Create: `tests/platform/test_platform_manifest.py`
- Create: `docs/build-evidence/context-grounding.md`

- [ ] **Step 1: Write the failing platform-manifest test**

Create `tests/platform/test_platform_manifest.py` to require this exact manifest shape:

```python
EXPECTED = {
    "folderPath": "JD_Demos/demos",
    "outlookConnection": "james.dickson@uipath.com",
    "resources": [
        {
            "source": "knowledge/triage/ar-dispute-taxonomy-and-examples.txt",
            "bucket": "ar-dispute-triage-kb",
            "index": "ar-dispute-triage-index",
        },
        {
            "source": "knowledge/payment/payment-misapplication-resolution-playbook.txt",
            "bucket": "ar-payment-resolution-kb",
            "index": "ar-payment-resolution-index",
        },
    ],
}
```

It must assert exact equality for these stable names while allowing additional discovered key/ID fields under each resource after provisioning.

- [ ] **Step 2: Run the platform test and observe the expected failure**

```bash
uv run pytest tests/platform/test_platform_manifest.py
```

Expected: FAIL because the manifest is absent.

- [ ] **Step 3: Create the stable manifest and pass the local test**

Create `config/platform-resources.json` with the exact stable fields above and empty `bucketKey`, `indexKey`, and `connectionKey` strings. These fields are populated only from live CLI output; never fabricate IDs.

```bash
uv run pytest tests/platform/test_platform_manifest.py
```

Expected: PASS.

- [ ] **Step 4: Reconfirm auth and inspect for collisions before mutating cloud state**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip login status --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or buckets list --folder-path "JD_Demos/demos" --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding list --folder-path "JD_Demos/demos" --format json
```

Expected: correct tenant/folder. If an exact bucket or index already exists, inspect it and reuse it only when its source/name matches this demo; otherwise stop rather than silently overwrite or duplicate it.

- [ ] **Step 5: Create and ingest the triage resource**

Use the exact resource names:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or buckets create "ar-dispute-triage-kb" --folder-path "JD_Demos/demos" --description "AR dispute taxonomy and examples for the Maestro demo" --output json
TRIAGE_BUCKET_KEY="$(UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or buckets list --folder-path "JD_Demos/demos" --output-filter "[?Name == 'ar-dispute-triage-kb'].Key | [0]" --output plain)"
test -n "$TRIAGE_BUCKET_KEY"
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or bucket-files upload "$TRIAGE_BUCKET_KEY" "ar-dispute-taxonomy-and-examples.txt" --folder-path "JD_Demos/demos" --file knowledge/triage/ar-dispute-taxonomy-and-examples.txt --content-type text/plain --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding create --index-name "ar-dispute-triage-index" --bucket-source "ar-dispute-triage-kb" --folder-path "JD_Demos/demos" --format json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding ingest --index-name "ar-dispute-triage-index" --folder-path "JD_Demos/demos" --format json
```

The assignment resolves the concrete bucket GUID and the non-empty check prevents an upload against an unresolved target. Poll with `uip context-grounding retrieve --index-name "ar-dispute-triage-index" --folder-path "JD_Demos/demos" --format json` until status is exactly `Successful`, then smoke-search:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding search --index-name "ar-dispute-triage-index" --folder-path "JD_Demos/demos" --query "How do PO mismatch, missing proof of delivery, and payment misapplication differ, and when is manual triage required?" --limit 5 --format json
```

Expected: results mention all three categories, the `0.75` rule, and manual triage.

- [ ] **Step 6: Create and ingest the payment resource**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or buckets create "ar-payment-resolution-kb" --folder-path "JD_Demos/demos" --description "Payment misapplication resolution playbook for the Maestro demo" --output json
PAYMENT_BUCKET_KEY="$(UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or buckets list --folder-path "JD_Demos/demos" --output-filter "[?Name == 'ar-payment-resolution-kb'].Key | [0]" --output plain)"
test -n "$PAYMENT_BUCKET_KEY"
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip or bucket-files upload "$PAYMENT_BUCKET_KEY" "payment-misapplication-resolution-playbook.txt" --folder-path "JD_Demos/demos" --file knowledge/payment/payment-misapplication-resolution-playbook.txt --content-type text/plain --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding create --index-name "ar-payment-resolution-index" --bucket-source "ar-payment-resolution-kb" --folder-path "JD_Demos/demos" --format json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding ingest --index-name "ar-payment-resolution-index" --folder-path "JD_Demos/demos" --format json
```

The assignment resolves the concrete bucket GUID and the non-empty check prevents an upload against an unresolved target. Poll with `uip context-grounding retrieve --index-name "ar-payment-resolution-index" --folder-path "JD_Demos/demos" --format json` until `Successful`, then run:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip context-grounding search --index-name "ar-payment-resolution-index" --folder-path "JD_Demos/demos" --query "What evidence and controls are required before reallocating PAY-77821 from INV-30909 to INV-30915?" --limit 5 --format json
```

Expected: the returned passages identify the payment, wrong invoice, target invoice, remittance match, `MISAPPLIED` status, and reallocation controls.

- [ ] **Step 7: Record live identities and evidence**

Update only the empty key fields in `config/platform-resources.json` with IDs returned by the CLI. Write `docs/build-evidence/context-grounding.md` with the date, tenant/folder, bucket/index names and keys, final ingestion statuses, exact smoke-search queries, and concise summaries of the returned passages. Do not paste authentication tokens or full CLI envelopes.

- [ ] **Step 8: Re-run the manifest test and commit**

```bash
uv run pytest tests/platform/test_platform_manifest.py
git add config/platform-resources.json tests/platform docs/build-evidence/context-grounding.md
git commit -m "build: provision dispute grounding resources"
```

---

## Task 5: Scaffold the Four Inline Agents and Enforce Their Contracts

**Files:**

- Create: `config/agent-projects.json`
- Create: four CLI-generated `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/<project-id>/agent.json` files
- Create: triage Context Grounding `resource.json`
- Create: payment Context Grounding `resource.json`
- Create: payment `LookupPaymentApplication` tool `resource.json`
- Create: `tests/agents/test_agent_contracts.py`
- Modify: Flow-project and agent-level `bindings_v2.json` files

- [ ] **Step 1: Write the failing agent-contract test**

Create `tests/agents/test_agent_contracts.py`. It must load `config/agent-projects.json`, resolve each generated directory, and require logical names `triage`, `poMismatch`, `missingPod`, and `paymentMisapplication`. Assert:

- every mapped directory and `agent.json` exists;
- each agent has a non-empty system prompt, user prompt, input schema, and output schema;
- triage output is exactly `disputeType`, `rationale`, `confidence`;
- each specialist output is exactly the common 12-field proposal contract;
- triage has exactly one enabled context resource for `ar-dispute-triage-index`;
- payment has exactly one enabled context resource for `ar-payment-resolution-index` and one enabled API tool for `LookupPaymentApplication`;
- PO and POD have no API tools and no Context Grounding resources;
- prompts require resource use where attached and forbid unsupported factual invention.

- [ ] **Step 2: Run the test and observe the expected failure**

```bash
uv run pytest tests/agents/test_agent_contracts.py
```

Expected: FAIL because the mapping and agents are absent.

- [ ] **Step 3: Discover an available model and scaffold four inline agents**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip agent model list --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip agent init solution/ARCollectionsDemo/ARCollectionsDisputeResolution --inline-in-flow --output json
```

Run the `agent init` command four times. Record each returned `ProjectId` immediately in `config/agent-projects.json` under, in order, `triage`, `poMismatch`, `missingPod`, and `paymentMisapplication`. Every value must be the concrete UUID returned by the CLI; make the contract test enforce the UUID format. Choose a currently supported general-purpose model suitable for structured tool use; prefer `gpt-5.6-terra` if it remains available in `uipathlabs/Playground`.

- [ ] **Step 4: Define the triage agent**

Set its input schema to one object field, `casePacket`, and exact output schema:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["disputeType", "rationale", "confidence"],
  "properties": {
    "disputeType": {"type": "string", "enum": ["po_mismatch", "missing_pod", "payment_misapplication", "unsupported"]},
    "rationale": {"type": "string"},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  }
}
```

The system prompt must say: search the attached taxonomy on every run; classify only from the packet and retrieved taxonomy; cite the taxonomy category/example in `rationale`; return `unsupported` when evidence is ambiguous, unsupported, or confidence is below `0.75`; never call tools or propose a resolution. The user prompt must include the serialized Flow case packet and explicitly ask for the three-field JSON contract.

- [ ] **Step 5: Define the common specialist schema and three specialist prompts**

Use this exact output field set for all specialists:

```text
caseId, disputeType, evidenceSummary, rootCause, recommendedAction,
actionCode, adjustmentAmount, confidence, approvalSummary,
emailSubject, emailBody, resourcesUsed
```

Make every field required and set `additionalProperties` to false. Use numeric schemas for `adjustmentAmount` and `confidence`; restrict `actionCode` to the three approved values. The common prompt rules are:

- use only the case packet and attached resource/tool results;
- preserve `caseId` and the routed `disputeType`;
- write a concise collector summary and plain-text customer email;
- address the customer by fictional company name but never select the recipient;
- describe sources in `resourcesUsed` without inventing resource calls;
- return only the structured contract.

Add specialist rules:

- PO mismatch: compare invoice amount `$48,750` with the PO-authorized amount `$47,250`; return `ISSUE_CREDIT`, `adjustmentAmount: 1500`, and request payment of `$47,250` after correction.
- Missing POD: use delivery date `2026-06-18`, signer `M. Chen`, and matching quantities; return `PROVIDE_POD` and `adjustmentAmount: 0`.
- Payment misapplication: call `LookupPaymentApplication` and search `ar-payment-resolution-index` before reasoning; require both resources to support the recommendation; return `REALLOCATE_PAYMENT`, `adjustmentAmount: 0`, and state that reallocation will clear `INV-30915`.

- [ ] **Step 6: Attach resources using generated resource directories**

Create the triage context resource with `type: context`, `contextType: index`, folder `JD_Demos/demos`, index `ar-dispute-triage-index`, semantic retrieval, result count `5`, and a description focused on classification.

Create two resources for payment:

1. Context resource for `ar-payment-resolution-index`, semantic retrieval, result count `5`.
2. API tool resource with `type: api`, `location: solution`, `processName: LookupPaymentApplication`, `folderPath: solution_folder`, the exact four-input/nine-output schema from Task 3, and a description that says it is a read-only lookup for cash-application evidence.

Use actual CLI-generated resource UUID directories and record their exact references in agent `bindings_v2.json`. Refresh solution resources first so the local API Workflow receives a real solution resource key:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution resources refresh --solution-folder solution/ARCollectionsDemo --output json
```

- [ ] **Step 7: Refresh and validate all four agents**

For each exact ID in `config/agent-projects.json`, run `uip agent refresh` on its concrete directory with `--inline-in-flow --bindings-target solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json --output json`, followed by `uip agent validate` on the same concrete directory with `--inline-in-flow --output json`. Use four explicit commands containing the UUIDs from the mapping; do not save a symbolic ID token in any artifact or script. Expected: four successful validations and bindings containing the three intended resource references.

- [ ] **Step 8: Run tests and commit**

```bash
uv run pytest tests/agents/test_agent_contracts.py
git add config/agent-projects.json tests/agents solution/ARCollectionsDemo/ARCollectionsDisputeResolution
git commit -m "feat: add grounded AR dispute agents"
```

---

## Task 6: Build Deterministic Case Loading, Grounded Triage, and Exclusive Routing

**Files:**

- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`
- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/project.uiproj`
- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json`
- Create: `tests/flow/test_flow_contract.py`

- [ ] **Step 1: Snapshot the installed Flow node definitions**

Before hand-editing the Flow, retrieve and use the installed definitions for:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry get core.logic.decision --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry get core.logic.switch --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry get uipath.agent.autonomous --output json
```

Also inspect the scaffolded Start, Script, and End nodes. Copy registry definitions verbatim; do not type their schema from memory. Every edge must declare the correct `targetPort`.

- [ ] **Step 2: Write failing Flow contract tests**

`tests/flow/test_flow_contract.py` must parse the `.flow` JSON and assert all of the following without depending on visual coordinates:

- required start inputs are exactly `caseId` and `recipientEmail`;
- a deterministic `Load Sample Case` script contains all four case IDs and the approved case values;
- the triage inline agent points to the mapped triage project ID;
- the decision expression enforces a supported type and `confidence >= 0.75`;
- the switch has exactly the three supported routes;
- exactly one specialist node is reachable per supported route;
- the negative branch reaches `needs_manual_triage` without reaching a specialist, API Workflow node, Quick Form, or connector node;
- all three specialist outputs expose the exact common proposal contract;
- all designed End outputs contain the result-contract fields from the spec.

- [ ] **Step 3: Run the Flow tests and observe the expected failure**

```bash
uv run pytest tests/flow/test_flow_contract.py
```

Expected: FAIL because the Flow is still a scaffold.

- [ ] **Step 4: Add the trigger contract and deterministic case loader**

The manual Start node must expose required string inputs `caseId` and `recipientEmail`. The loader script must reject unknown IDs and return this data shape for every fixture:

```json
{
  "caseId": "string",
  "customerName": "string",
  "customerAccountId": "string",
  "invoiceNumber": "string",
  "outstandingBalance": 0,
  "customerReason": "string",
  "openedDate": "YYYY-MM-DD",
  "evidence": {}
}
```

Use exact supported values from the spec, plus:

- `AR-PO-001`: `customerAccountId: NORTHSTAR-1701`, `openedDate: 2026-07-07`, invoice amount `48750`, PO authorized amount `47250`, difference `1500`.
- `AR-POD-002`: `customerAccountId: RIVERBEND-2904`, `openedDate: 2026-07-10`, delivered `2026-06-18`, signer `M. Chen`, quantities match.
- `AR-PAY-003`: `customerAccountId: SUMMIT-4402`, `openedDate: 2026-07-14`, reported payment `36800`, payment reference `PAY-77821`; omit application status and applied invoice.
- `AR-AMB-004`: fictional customer `Lakeshore Components`, invoice `INV-40102`, balance `12800`, reason `The balance does not look right; please investigate`, and no discriminating evidence.

- [ ] **Step 5: Add the triage agent and the single high-leverage decision**

Bind the triage input to the loader output. Define the success expression as the logical equivalent of:

```text
triage.confidence >= 0.75 AND triage.disputeType IN
  [po_mismatch, missing_pod, payment_misapplication]
```

False goes directly to an End node returning:

```json
{
  "status": "needs_manual_triage",
  "emailSent": false,
  "approvalDecision": null,
  "updateResult": null
}
```

Populate the remaining result fields from trigger/triage outputs and state in `auditSummary` that no specialist or side effect ran.

- [ ] **Step 6: Add the switch and three specialist branches**

Route the three exact dispute types to their corresponding mapped inline-agent project IDs. Bind each specialist to the same `casePacket` plus the triage result. Converge the mutually exclusive branches into one `Normalize Proposal` script; do not use the parallel `core.logic.merge` node. The script selects the one populated branch and verifies the exact 12-field contract before forwarding it.

- [ ] **Step 7: Format, validate, and run local static tests**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow format solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
uv run pytest tests/flow/test_flow_contract.py
```

Expected: formatting succeeds, validation has no warnings/errors, tests pass. Do not debug-run yet because later tasks add the only intended deployed bindings and side effects.

- [ ] **Step 8: Commit the core orchestration**

```bash
git add solution/ARCollectionsDemo/ARCollectionsDisputeResolution tests/flow
git commit -m "feat: route grounded disputes to specialists"
```

---

## Task 7: Add Collector Approval, Mock Update, Outlook, and Business Exits

**Files:**

- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`
- Modify: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/bindings_v2.json`
- Modify: `tests/flow/test_flow_contract.py`
- Modify: `config/platform-resources.json`

- [ ] **Step 1: Extend the tests before changing the Flow**

Add assertions that:

- exactly one `uipath.human-in-the-loop.quick-form` node exists after normalization;
- rejection reaches only `needs_rework` and cannot reach either side effect;
- approval reaches exactly one Flow-level `MockUpdateDispute` node, then exactly one Outlook Send Email node, then `resolved`;
- the update node receives all six approved inputs;
- Outlook To is bound only to Start `recipientEmail`, never case/customer data;
- Outlook subject/body are bound to normalized specialist output;
- `resolved` sets `emailSent: true` and includes the update receipt;
- `needs_rework` sets `emailSent: false`, `updateResult: null`, and preserves collector comments;
- no retry, catch, or technical-error branches are added.

Run:

```bash
uv run pytest tests/flow/test_flow_contract.py
```

Expected: FAIL on the new assertions.

- [ ] **Step 2: Retrieve the exact Quick Form definition and add the approval**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry get uipath.human-in-the-loop.quick-form --output json
```

Configure one form titled `Review AR dispute resolution`. Present customer, invoice, outstanding balance, triage type/rationale/confidence, specialist evidence/root cause/recommendation/action/adjustment/confidence, and complete subject/body preview. Capture `approvalDecision`, `approvedBy`, and `approvalComments`. The approved action continues; rejected returns `needs_rework` and performs no side effect.

- [ ] **Step 3: Add the solution-local `MockUpdateDispute` Flow node**

Refresh solution resources, locate the concrete resource key for `MockUpdateDispute`, then add the Flow-level node using the registry node type `uipath.core.api-workflow.<resource-key>`. Bind:

```text
caseId             <- normalizedProposal.caseId
disputeType        <- normalizedProposal.disputeType
actionCode         <- normalizedProposal.actionCode
adjustmentAmount   <- normalizedProposal.adjustmentAmount
approvedBy         <- quickForm.approvedBy
approvalComments   <- quickForm.approvalComments
```

Place it only on the approval path.

- [ ] **Step 4: Discover and verify the existing Outlook connection**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip is connections list uipath-microsoft-outlook365 --all-folders --output json
```

Select only the enabled connection named `james.dickson@uipath.com` in `JD_Demos/demos`, then ping it with the current CLI connection-ping command. Save its returned key to `config/platform-resources.json`. If the name, folder, enabled status, or ping differs from the approved design, stop and ask the user.

- [ ] **Step 5: Discover, add, and configure the CLI-owned Outlook activity**

Search the live registry broadly enough to locate the Microsoft Outlook 365 `SendEmailV2` activity:

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry search "Microsoft Outlook 365" --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow registry search "Send Email" --output json
```

Select the result whose connector is `uipath-microsoft-outlook365` and activity is `SendEmailV2`. Use `uip maestro flow node add` and `uip maestro flow node configure` with the discovered node type and verified connection key. Bind:

```text
To      <- Start.recipientEmail
Subject <- normalizedProposal.emailSubject
Body    <- normalizedProposal.emailBody
```

Leave CC, BCC, and attachments empty. Do not hand-write the connector definition or bind a sample-customer address.

- [ ] **Step 6: Add resolved and needs-rework result contracts**

The rejection End returns `needs_rework`, collector fields, no update, `emailSent: false`, resource usage, and a concise audit summary. The success End returns `resolved`, all triage/proposal/approval fields, the API receipt, `emailSent: true`, resource usage, and a concise audit summary. Maintain the exact result field list from the approved design for all three End nodes.

- [ ] **Step 7: Format, validate, and run all local tests**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution resources refresh --solution-folder solution/ARCollectionsDemo --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow format solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
uv run pytest
```

Expected: Flow validation reports no warnings/errors and the full test suite passes.

- [ ] **Step 8: Commit the complete Flow**

```bash
git add solution/ARCollectionsDemo/ARCollectionsDisputeResolution tests/flow config/platform-resources.json
git commit -m "feat: add approval and approved resolution effects"
```

---

## Task 8: Package, Link, Deploy, and Verify the Demo

**Files:**

- Create: `docs/build-evidence/deployment-and-smoke.md`
- Modify: solution-generated resource/binding files if packaging refreshes them

- [ ] **Step 1: Run the complete pre-deploy verification gate**

```bash
git status --short
uv run pytest
uv run python tests/api_workflows/verify_fixture_runs.py
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip api-workflow validate solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow format solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution pack solution/ARCollectionsDemo --dry-run --output json
```

Expected: clean worktree before generated refreshes, all tests pass, both API Workflows validate, Flow has no warnings/errors, and dry-run reports `Status: Valid`.

- [ ] **Step 2: Create a versioned package**

```bash
mkdir -p dist
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution pack solution/ARCollectionsDemo dist --name ARCollectionsDemo --version 1.0.0 --author "James Dickson" --description "Agentic AR collections dispute resolution demo" --output json
```

Expected: `dist/ARCollectionsDemo.1.0.0.zip` or the exact path reported by the installed CLI. `dist/` remains untracked.

- [ ] **Step 3: Publish and obtain the deployment configuration**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution publish dist/ARCollectionsDemo.1.0.0.zip --wait --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution deploy config get ARCollectionsDemo --package-version 1.0.0 -d .local/ar-collections-deployment.json --format json --output json
```

If the packer reports a different exact filename, use that reported path in the publish command. Expected: package is Ready and `.local/ar-collections-deployment.json` exists.

- [ ] **Step 4: Link deployment resources deliberately**

Inspect the generated configuration. Use `uip solution deploy config link`/`config set` help from the installed CLI to link:

- the Outlook connection resource to the verified `james.dickson@uipath.com` connection key;
- triage context to `ar-dispute-triage-index` in `JD_Demos/demos`;
- payment context to `ar-payment-resolution-index` in `JD_Demos/demos`.

Keep the two API Workflows solution-local. Validate that no new Outlook connection, storage bucket, or duplicate index will be created.

- [ ] **Step 5: Deploy and activate under the approved parent folder**

```bash
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution deploy run --name ARCollectionsDemo-1-0-0 --package-name ARCollectionsDemo --package-version 1.0.0 --folder-name ARCollectionsDemo --parent-folder-path "JD_Demos/demos" --config-file .local/ar-collections-deployment.json --output json
```

Expected: `DeploymentSucceeded` and `SuccessfulActivate`. If the platform indicates it would replace an unrelated existing deployment, stop rather than overwrite it.

- [ ] **Step 6: Verify the three proposal paths without approving side effects**

For `AR-PO-001`, `AR-POD-002`, and `AR-PAY-003`, run only far enough to inspect triage and the proposed Quick Form task. Confirm expected classification, specialist, action code, resource trace, and email preview. Reject or cancel these verification tasks so no mock update or email runs. For the payment case, confirm the trace contains both `LookupPaymentApplication` and `ar-payment-resolution-index`.

Run `AR-AMB-004` through completion and verify `needs_manual_triage`, no specialist call, no approval, no update, and no email.

- [ ] **Step 7: Pause for explicit live-smoke approval and recipient**

Report the deployed Flow identity, the four pre-side-effect results, and the verified Outlook connection. Ask the user for explicit authorization to send one real email and for the internal presenter-controlled destination. Do not infer that address from the Outlook connection or case data.

- [ ] **Step 8: Execute the single approved end-to-end payment smoke**

After approval, start `AR-PAY-003` with the supplied internal recipient, approve the Quick Form, and verify in order:

1. triage searched `ar-dispute-triage-index`;
2. payment specialist called `LookupPaymentApplication`;
3. payment specialist searched `ar-payment-resolution-index`;
4. proposal returned `REALLOCATE_PAYMENT` and incorporated both resources;
5. `MockUpdateDispute` returned `UPDATED`;
6. Outlook reported a successful send to the supplied address;
7. final result was `resolved` with `emailSent: true`.

Confirm receipt in the destination mailbox without sending a second message.

- [ ] **Step 9: Record concise, secret-free build evidence**

Create `docs/build-evidence/deployment-and-smoke.md` with CLI version, target tenant/folder, package/deployment versions, validation results, scenario outcomes, one approved email-send result, and the final audit status. Include run/trace IDs only when they are safe to retain; never include tokens, raw email content, or personal mailbox data beyond the approved recipient label.

- [ ] **Step 10: Commit generated bindings and evidence**

```bash
git add solution/ARCollectionsDemo docs/build-evidence/deployment-and-smoke.md
git commit -m "build: deploy and verify AR collections demo"
```

---

## Task 9: Create the Presenter Runbook and Final Acceptance Check

**Files:**

- Create: `docs/demo-runbook.md`

- [ ] **Step 1: Write the concise 10–12 minute runbook**

Use these sections and timing:

```text
0–2 minutes: Business stakes and the three supported disputes
2–4 minutes: Start AR-PAY-003 with the presenter's email
4–7 minutes: Show grounded triage, payment lookup, and playbook search
7–9 minutes: Review and approve the collector task
9–12 minutes: Show update receipt, received email, audit result, and reusable branches
```

Include exact start inputs, expected payment values, what to point out on the canvas, the approval action, and the expected final status. Add a `Demo safety` section: use only a presenter-controlled internal recipient; do not improvise case IDs; wait for the Quick Form before navigating away; do not demonstrate the negative fixture unless asked; if a technical node fails, use the platform incident view rather than adding or improvising a recovery branch.

- [ ] **Step 2: Run the final acceptance suite**

```bash
uv run pytest
uv run python tests/api_workflows/verify_fixture_runs.py
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip maestro flow validate solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
UIPATH_CLI_DISABLE_VERSION_SYNC=1 uip solution pack solution/ARCollectionsDemo --dry-run --output json
git status --short
```

Expected: all tests pass, both deterministic fixture runs pass, Flow validation has no warnings/errors, solution dry-run is valid, and only `docs/demo-runbook.md` is uncommitted.

- [ ] **Step 3: Perform explicit spec coverage review**

Check every acceptance criterion in the approved design against a concrete artifact or recorded runtime result. Specifically count one Flow, two API Workflows, four agents, two text articles, two buckets, two indexes, one Quick Form, one Outlook node, three supported cases, one hidden negative case, and three business statuses.

- [ ] **Step 4: Scan for incomplete markers and accidental secrets**

```bash
rg -n -i "TODO|TBD|FIXME|example\.com" . --glob '!docs/superpowers/plans/*'
rg -n -i "access[_-]?token|refresh[_-]?token|authorization: bearer|client_secret" . --glob '!uv.lock' --glob '!.git/*'
```

Expected: no incomplete implementation markers and no credentials. Intentional prose examples in knowledge articles must not use any forbidden marker.

- [ ] **Step 5: Commit the presenter handoff**

```bash
git add docs/demo-runbook.md
git commit -m "docs: add AR collections demo runbook"
```

- [ ] **Step 6: Confirm the final repository state**

```bash
git status --short
git log --oneline -10
```

Expected: clean working tree with task-level commits visible and no untracked package, token, or runtime-output files.

---

## Final Acceptance Mapping

| Approved requirement | Implementation evidence |
|---|---|
| One dispute per run | Start contract and deterministic loader in Task 6 |
| Three supported types | Taxonomy, fixtures, switch, and specialists in Tasks 2, 5, and 6 |
| Grounded triage on every run | Triage prompt/resource test plus runtime traces in Tasks 5 and 8 |
| Payment tool plus grounded playbook | API Workflow, payment resources, prompt, and trace checks in Tasks 3, 5, and 8 |
| One approval for every proposal | Single Quick Form after normalization in Task 7 |
| Rejection has no side effects | Graph reachability tests and `needs_rework` result in Task 7 |
| Approval updates before email | Graph order test and end-to-end trace in Tasks 7 and 8 |
| Real Outlook email to presenter input | Connection verification, direct trigger binding, and one consented smoke in Tasks 7 and 8 |
| Only one explicit error-handling moment | Manual-triage decision and absence-of-error-branch tests in Tasks 6 and 7 |
| Two buckets and two indexes | Stable manifest plus ingestion/search evidence in Task 4 |
| Demo-grade, mixed-audience story | Timed runbook and business-readable audit outputs in Task 9 |
