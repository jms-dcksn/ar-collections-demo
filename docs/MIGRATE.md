# Migrating the solution to a new organization / tenant

This is the exact procedure used on 2026-08-19 to move the AR collections demo
from `cloud.uipath.com` to `https://staging.uipath.com` (`uipathlabs /
Playground`, folder `JD_Demos/demos/ARCollections`). It doubles as the runbook
for any future environment move.

The migration provisions platform resources and rewires the checked-in artifacts
to point at them. It deliberately stops short of publish and deploy.

A second move, on the same day, took the solution from `uipathlabs / Playground`
to `uipathstgSS_updated / UiPathDefault`, folder `JD/demos`. What differed is
recorded in "Second run" at the end.

## Scope

| In scope | Out of scope |
| --- | --- |
| Data Fabric entity (tenant-level) | `uip solution pack / publish / deploy / upload` |
| Storage buckets and knowledge uploads | `uip maestro flow debug` |
| Context Grounding indexes and ingestion | `ar-collections-app` (Coded App) |
| Flow connection, index, and folder rewiring | Deleting anything on the old environment |
| `config/platform-resources.json`, scripts, tests, docs | |

The Coded App is excluded on purpose. See `AGENTS.md`, "Coded App Migration
Pending".

## Environment variables used throughout

```bash
export UIPATH_CLI_DISABLE_VERSION_SYNC=1        # used on every uip call in this repo

FOLDER_KEY=0736cf9b-92af-45d8-bf09-075454d4d050   # JD_Demos/demos/ARCollections
FOLDER_PATH="JD_Demos/demos/ARCollections"
CONN_FOLDER_KEY=e072bd13-1c37-4125-a891-fde9bf3d7311   # JD_Demos (where connections live)
OUTLOOK_CONN=6ceaefdd-c68d-4753-a691-d115334f04a6
DF_CONN=07dd8820-fd9e-454d-a491-eb37ed81de6d
```

## Step 1 — Confirm the login target

The migration failure mode that started this work was a CLI authenticated to the
wrong environment. Verify before touching anything.

```bash
uip login status --output json
```

Expect `BaseUrl: https://staging.uipath.com`, `Organization: uipathlabs`,
`Tenant: Playground`. There is no `uip auth status` subcommand — `login status`
is the verification command. If the target is wrong, the user must run `uip
login` interactively; do not attempt it non-interactively.

## Step 2 — Survey the target before creating anything

Folder listing is paginated at 50 and the tenant has ~950 folders, so page
through rather than trusting one call.

```bash
for off in $(seq 0 50 900); do
  uip or folders list --output json --limit 50 --offset $off
done | jq -r '.Data[]? | [.Key,.Type,.Path] | @tsv' | sort -u -t$'\t' -k3 \
     | grep -iE "JD_Demos|ARCollection"
```

Then confirm the target folder is empty and the entity name is free:

```bash
uip or buckets list --folder-key "$FOLDER_KEY" --output json
uip context-grounding list --folder-key "$FOLDER_KEY" --output json
uip df entities list --include-folders --output json | jq -r '.Data[].Name' | grep -i collections
```

On 2026-08-19 the folder already existed and held no buckets and no indexes, and
no `JDARCollectionsEntity` existed, so nothing was overwritten.

## Step 3 — Verify the supplied connection IDs

`uip is connections` has no `get` verb. Look a connection up by ID with `list`,
and always pass `--all-folders` — a folder-scoped list returns a false negative.

```bash
uip is connections list --connection-id "$OUTLOOK_CONN" --all-folders --refresh --output json
uip is connections list --connection-id "$DF_CONN"     --all-folders --refresh --output json
```

Record `State` (must be `Enabled`) and `FolderKey`. Both connections resolved to
folder `JD_Demos` (`e072bd13-…`), one level above the resource folder. The
Flow's `connectionFolderKey` must name where the connection actually lives, so
it points at `JD_Demos`, not `ARCollections`.

## Step 4 — Create the Data Fabric entity

The entity is tenant-scoped: pass no `--folder-key`. Generate the request body
from the checked-in contract so the schema cannot drift by hand-transcription.

```bash
python3 - <<'PY' > /tmp/ar-entity-body.json
import json
m = json.load(open('config/platform-resources.json'))
e = m['dataFabricEntities'][0]
fields = []
for f in e['fields']:
    d = {"fieldName": f['name'], "type": f['type']}
    if f.get('required'):
        d["isRequired"] = True
    if f.get('unique'):
        d["isUnique"] = True
    if 'decimalPrecision' in f:
        d["decimalPrecision"] = f['decimalPrecision']
    fields.append(d)
print(json.dumps({
    "displayName": e['displayName'],
    "description": "AR collections dispute resolution case packet and lifecycle state.",
    "fields": fields,
}, indent=2))
PY

uip df entities create "JDARCollectionsEntity" --file /tmp/ar-entity-body.json --output json
```

Returns `Data.Id` — the new entity ID. Verify it round-trips against the
contract rather than eyeballing it:

```bash
uip df entities get <NEW_ENTITY_ID> --output json > /tmp/ar-entity-live.json
```

Compare live non-system fields (excluding `Id`, `CreatedBy`, `CreateTime`,
`UpdatedBy`, `UpdateTime` and anything with `IsSystemField`) against the
manifest on name, type, `IsRequired`, `IsUnique`, and `DecimalPrecision`. The
2026-08-19 run matched 29/29 with `FolderId` all-zeros, confirming tenant scope.

Note the live field shape: the type is at `Fields[].FieldDataType.Name` and the
precision at `Fields[].FieldDataType.DecimalPrecision`, not on the field object
itself.

## Step 5 — Create the storage buckets and upload the knowledge

```bash
uip or buckets create "ar-dispute-triage-kb" --folder-key "$FOLDER_KEY" \
  -d "Triage taxonomy knowledge for the AR collections triage agent." --output json

uip or buckets create "ar-payment-resolution-kb" --folder-key "$FOLDER_KEY" \
  -d "Payment misapplication resolution playbook for the payment specialist agent." --output json
```

Each returns both an `Identifier` (GUID) and a numeric `Id`. **Upload takes the
GUID, and both the bucket key and the destination path are positional** — there
is no `--path` flag, and passing the numeric `Id` fails.

```bash
uip or bucket-files upload <TRIAGE_BUCKET_GUID> "ar-dispute-taxonomy-and-examples.txt" \
  --folder-key "$FOLDER_KEY" --file knowledge/triage/ar-dispute-taxonomy-and-examples.txt --output json

uip or bucket-files upload <PAYMENT_BUCKET_GUID> "payment-misapplication-resolution-playbook.txt" \
  --folder-key "$FOLDER_KEY" --file knowledge/payment/payment-misapplication-resolution-playbook.txt --output json
```

Check the reported byte counts against the previous environment's evidence
(4,545 and 3,626) to prove the sources carried over unchanged.

## Step 6 — Create the Context Grounding indexes and ingest

**`context-grounding create` requires `--folder-path`.** Passing only
`--folder-key` fails with `400 A required property (folderName) is missing`.
Creation does not ingest; ingestion is a separate async call.

```bash
uip context-grounding create --index-name "ar-dispute-triage-index" \
  --bucket-source "ar-dispute-triage-kb" --folder-path "$FOLDER_PATH" \
  --description "AR dispute triage taxonomy and worked examples." --output json

uip context-grounding create --index-name "ar-payment-resolution-index" \
  --bucket-source "ar-payment-resolution-kb" --folder-path "$FOLDER_PATH" \
  --description "Payment misapplication resolution playbook." --output json

uip context-grounding ingest --index-name "ar-dispute-triage-index"     --folder-path "$FOLDER_PATH" --output json
uip context-grounding ingest --index-name "ar-payment-resolution-index" --folder-path "$FOLDER_PATH" --output json
```

Poll until terminal. `retrieve` returns the index object; read
`last_ingestion_status` (`Successful` / `Failed` / anything else means still
running).

```bash
uip context-grounding retrieve --index-name "ar-dispute-triage-index" --folder-path "$FOLDER_PATH" --output json
```

Then smoke-test retrieval with the two queries recorded in
`docs/build-evidence/context-grounding.md` so scores are comparable across
environments. Results arrive under `semantic_results.values[]`, each with
`score`, `content`, and `metadata.source`.

```bash
uip context-grounding search --index-name "ar-dispute-triage-index" \
  --query "How do PO mismatch, missing proof of delivery, and payment misapplication differ, and when is manual triage required?" \
  --folder-path "$FOLDER_PATH" --limit 2 --output json
```

A prior tenant hit a 100-index quota at this step. If creation fails on quota,
stop and have the user remove unused indexes; do not delete anything to make
room.

## Step 7 — Rewire the Flow

Build the substitution map first. The one trap: a single old folder key served
two different roles and must be split, so a blanket find-and-replace is wrong.

| Old value | New value | Sites |
| --- | --- | --- |
| Outlook connection `c61c5442-…` | `6ceaefdd-…` | 4 |
| Data Fabric connection `6cd4c047-…` | `07dd8820-…` | 25 |
| `bbe64c10-…` as `connectionFolderKey` | `e072bd13-…` (`JD_Demos`) | 10 |
| `bbe64c10-…` as connection-binding `default` | `e072bd13-…` (`JD_Demos`) | 1 |
| `bbe64c10-…` as index / process `folderKey` | `0736cf9b-…` (`ARCollections`) | 4 |
| `67fc19c3-…` as `connectionFolderKey` | `e072bd13-…` | 1 |
| Triage index `39da4378-…` | `659822b4-…` | 4 |
| Payment index `9c3d6d90-…` | `8bd172f0-…` | 4 |
| `JD_Demos/demos/ARCollectionsDemo` | `JD_Demos/demos/ARCollections` | 12 |

Take a per-key census before editing so you know what each occurrence is:

```bash
F=solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow
for g in <OLD_GUIDS>; do
  echo "### $g total=$(grep -o "$g" $F | wc -l)"
  grep -o "\"[A-Za-z_]*\": \"$g\"" $F | sort | uniq -c
done
```

### Why in-place edits, not `node configure`

`uip maestro flow node configure` owns `inputs.detail` on connector nodes, but it
has no targeted "rebind the connection" mode — it requires the full detail
payload (method, endpoint, object name, body parameters). Re-running it across
the 12 connector nodes would mean re-authoring every field mapping, which is
exactly the surface behind the binding-drop and lossy-save defects filed as
UV-15989 / UV-15990. `uip maestro flow binding` only offers `add` / `list` /
`remove`, with no update. So the identifier swap is done as in-place value edits,
which preserve node IDs, `$vars`, and every existing mapping.

### Edit order

Order matters, because the narrow case shares text with the broad ones.

1. **First**, the one connection `FolderKey` binding (`id: bz4c8Jueg`) whose
   `default` must become `JD_Demos` while its siblings become `ARCollections`.
   Anchor on the `resourceKey` + `default` pair so the match is unique, and
   change both lines in one edit — before the global connection-GUID replace
   rewrites the anchor.
2. `"connectionFolderKey": "bbe64c10-…"` → `e072bd13-…` (all occurrences).
3. `"connectionFolderKey": "67fc19c3-…"` → `e072bd13-…`.
4. Remaining bare `bbe64c10-…` → `0736cf9b-…`. By now every survivor is an
   index or process `folderKey`.
5. `6cd4c047-…` → `07dd8820-…`, then `c61c5442-…` → `6ceaefdd-…`.
6. Both index GUIDs. These appear in `nodes[].type`,
   `definitions[].nodeType`, `definitions[].inputDefaults.indexId`, and inside
   `edges[].id`, so a substring replace covers all four sites per index.
7. `JD_Demos/demos/ARCollectionsDemo` → `JD_Demos/demos/ARCollections`. The
   shorter string is a prefix of
   `…ARCollectionsDemo.LookupPaymentApplication`, so one replace handles both
   forms.

Then confirm zero old identifiers remain, re-run the census against the new
GUIDs to check the 11/4 folder-key split landed, and confirm the file still
parses as JSON.

### The other files carrying the same identifiers

Plain JSON — safe to `sed`. Find them by content rather than by hard-coded
path, because the editor renames and re-keys several of these (see "Editor churn"
below):

```bash
grep -rIl "<OLD_GUID_OR_FOLDER_PATH>" solution/ARCollectionsDemo --include='*.json'
```

On 2026-08-19 that resolved to:

- `ARCollectionsDisputeResolution/bindings_v2.json`
- the Outlook connection resource under
  `resources/solution_folder/connection/uipath-microsoft-outlook365/`
- the Data Fabric connection resource under
  `resources/solution_folder/connection/uipath-uipath-dataservice/`
- `resources/solution_folder/process/flow/ARCollectionsDisputeResolution.json`
- three inline-agent attachments, each carrying a `folderPath` and no GUIDs —
  the triage context index (under the `f7d7d1a5-…` agent), and the payment
  context index plus the `LookupPaymentApplication` tool (both under the
  `1c6b5289-…` agent)

The Flow references the entity by system name (`JDARCollectionsEntity`, 45
occurrences), never by GUID, so keeping the entity name identical means no
entity rewiring inside the Flow at all.

## Step 8 — Update the checked-in contract, scripts, tests, and docs

`config/platform-resources.json` is the canonical record. The 2026-08-19 run
also added four keys that were previously implicit: `folderKey`,
`connectionFolderPath`, `connectionFolderKey`, `dataFabricConnection`, and
`dataFabricConnectionKey`. Adding keys requires extending
`ALLOWED_MANIFEST_KEYS` in `tests/platform/test_platform_manifest.py`.

Then update:

- `scripts/create-{po-mismatch,missing-pod,payment-misapplication}-record.sh` — the entity ID
- `tests/platform/test_demo_record_scripts.py` — `ENTITY_ID`
- `tests/platform/test_platform_manifest.py` — `EXPECTED`, `ALLOWED_MANIFEST_KEYS`, `entityKey`
- `tests/flow/test_flow_contract.py` — connection GUIDs, index node types, folder paths, process folder key
- `tests/agents/test_{triage,payment}_agent.py` — index `folderPath`
- `AGENTS.md`, `CLAUDE.md`, `docs/context/data-fabric-record-creation.md` — identifiers plus the base URL
- `docs/build-evidence/context-grounding.md` — new provisioning evidence, with the retired keys kept in a closing section
- `docs/build-evidence/deployment-and-smoke.md` — a retired-environment banner, since its identifiers all belong to the old org

Record the base URL explicitly. `uipathlabs / Playground` alone is ambiguous —
the same org and tenant names exist on both `cloud.uipath.com` and
`staging.uipath.com`, which is what made the original environment mix-up hard to
see.

## Step 9 — Verify

```bash
UV_CACHE_DIR=/private/tmp/ar-collections-uv-cache uv run pytest -q

uip maestro flow validate \
  solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow --output json
uip api-workflow validate solution/ARCollectionsDemo/LookupPaymentApplication/Workflow.json --output json
uip api-workflow validate solution/ARCollectionsDemo/MockUpdateDispute/Workflow.json --output json

git diff --check
```

Result on 2026-08-19, immediately after the rewiring and before any editor
session: 51 passed with 2 xfail (the pre-existing lossy-save xfails), Flow
`Valid`, both API workflows `Success`, no whitespace errors. Run this gate
*before* opening the solution in VS Code so you can tell migration defects apart
from editor churn.

The Flow emits one warning — one Data Fabric connection shared across the ten
persist nodes. That is the intended architecture, not a migration regression;
the same warning applied before the move.

Finally, re-list every provisioned resource and confirm the Flow's references
resolve: buckets present with the right file sizes, both indexes `Successful`,
both connections `Enabled` in `JD_Demos`.

## Editor churn to expect on the first VS Code debug

Opening the migrated solution in VS Code and running a debug against the new
tenant rewrites parts of the solution on disk. Observed immediately after the
2026-08-19 migration, before any publish:

- A new `userProfile/<user-id>/` directory appears for the new environment's
  user (the old `userProfile/<id>/debug_overwrites.json` is left in place, keyed
  by the old tenant).
- Both connection resource files are **renamed** to match the real connection
  names on the new tenant — `james.dickson@uipath.com.json` became
  `james.dickson@uipath.com_demo_connection.json`, and
  `james.dickson@uipath.com_1.json` became `Data_Fabric_#4.json`.
- New `resources/solution_folder/Bucket/OrchestratorBucket/ar-*-kb.json`
  resources are added — the buckets become solution resources for the first
  time.
- Duplicate index resources appear alongside the originals
  (`ar-dispute-triage-index_1.json`, `ar-payment-resolution-index_1.json`).
  This is the resource re-add churn tied to the deploy-resources checkbox.
- The triage agent's context-index attachment is re-created under a **new
  resource ID**, so its `resources/<id>/resource.json` directory changes name
  and the `source` value in the Flow's index node changes with it.
- All four `agent.json` files are re-saved.

The migration's own rewiring survives this: after the churn, the `.flow` still
carried zero old identifiers and the full set of new ones.

**One regression did not survive.** The editor re-pointed the Outlook node's
subject and body expressions:

| Input | Committed contract | After editor save |
| --- | --- | --- |
| `message.subject` | `=js:($vars.normalizeProposal.output.emailSubject)` | `=js:($vars.waitForApprovalUpdate.output.emailSubject)` |
| `message.body.content` | `=js:($vars.normalizeProposal.output.emailBody)` | `=js:($vars.waitForApprovalUpdate.output.emailBody)` |

This is the binding-rebind defect class tracked as UV-15989 / UV-15990, not a
migration side effect — the migration touched only GUIDs and folder-path strings
and never any `=js:` expression. `tests/flow/test_flow_contract.py` catches it.
After any editor session, re-run the suite and diff the Flow's expressions
against `HEAD` before trusting the file:

```bash
git diff solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow \
  | grep -E '^[+-].*=js:'
```

## Step 10 — Hand back without publishing

Stop here. Publish, deploy, `solution upload`, and `flow debug` are the user's
to run; they exercise the VS Code / Studio Web path deliberately.

Two carry-overs worth stating in the handoff:

- `solution/ARCollectionsDemo/userProfile/<id>/debug_overwrites.json` was left
  untouched. Its entries are keyed by the **old** tenant, so VS Code should add a
  fresh block for the new tenant rather than reuse them. If the first debug run
  shows stale resource bindings, look there first.
- The record-created trigger consumes its event, so each debug run needs a fresh
  record (otherwise error 102016). `scripts/create-*-record.sh <recipient-email>`
  now insert into the new entity. These are live actions that can end in real
  email — use a monitored demo mailbox only.

---

# Second run — `uipathlabs / Playground` → `uipathstgSS_updated / UiPathDefault`

Same day, same base URL (`https://staging.uipath.com`), different organization
and tenant. Target folder `JD/demos` (`e716bfc7-4c75-4921-ab5b-e5a3bc0d4c2c`).
All ten steps above applied; only the differences are recorded here.

## What was easier

**The folder-key split trap disappeared.** Both supplied connections resolved to
`JD/demos` itself — the same folder as the resources — rather than one level
above. So `connectionFolderKey` and the index / process `folderKey` collapse to a
single value, and a blanket replace of both old keys to that one new key is safe.
No anchored first edit, no ordering constraint. The census afterwards shows 17
occurrences of the one key, split 11 `connectionFolderKey` / 4 `default` / 2
`folderKey`.

**The entity name was free again**, so the Flow's 45 name-based
`JDARCollectionsEntity` references needed no rewiring, exactly as before.

## Substitution map

| Old value | New value | Sites in `.flow` |
| --- | --- | --- |
| Data Fabric connection `07dd8820-…` | `b2a02899-3708-4bb6-810a-02321afb77f6` | 25 |
| Outlook connection `6ceaefdd-…` | `8643408a-62b4-4d36-ba1e-bc9b68d4fce9` | 5 |
| `e072bd13-…` (`JD_Demos`) | `e716bfc7-…` (`JD/demos`) | 13 |
| `0736cf9b-…` (`ARCollections`) | `e716bfc7-…` (`JD/demos`) | 4 |
| Triage index `659822b4-…` | `a1b7fb4e-cfb3-43a8-b29e-08defd736a4b` | 4 |
| Payment index `8bd172f0-…` | `9745fa62-cff9-45d4-b29f-08defd736a4b` | 4 |
| Triage bucket `0a30973a-…` | `6a30bffd-5a68-4348-b66d-fea899e8a7af` | resources only |
| Payment bucket `32007736-…` | `306dcb5e-6cf3-4c03-bcff-64633cd9c174` | resources only |
| Entity `d22e70b2-…` | `81a5f874-d79b-f111-9b33-6045bdd6658d` | scripts / tests / docs |
| `JD_Demos/demos/ARCollections` | `JD/demos` | 9 |

The Outlook connection count rose from 4 to 5 because the editor had populated a
`FolderKey` binding that was previously empty (see below).

## Connection names changed too, not just keys

Both connections on the new tenant are named `james.dickson@uipath.com`. The
checked-in resources still carried the previous tenant's names — `Data Fabric #4`
and `james.dickson@uipath.com demo connection` — in places a GUID-only replace
does not reach:

- `resource.name` and `resource.spec.name` in both connection resource files
- the resource **filenames** themselves
- `outlookConnection` / `dataFabricConnection` in `config/platform-resources.json`,
  the `EXPECTED` copy in `tests/platform/test_platform_manifest.py`, and the
  Platform Contracts list in `AGENTS.md`

## The blanket path replace needs a guard

`JD_Demos` → `JD/demos` as a bare string is **not** safe across `docs/`. It
corrupts historical references to the retired folders: `JD_Demos/demos` became
`JD/demos/demos`, and `JD_Demos/demos/ARCollectionsDemo` became `JD/demosDemo`,
in `docs/build-evidence/context-grounding.md` and
`docs/build-evidence/deployment-and-smoke.md`. Exclude `docs/superpowers/`
entirely — approved specs and plans are historical records, not live config —
and re-check the survivors afterwards:

```bash
grep -rIn "JD/demos/demos\|JD/demosDemo" docs/
```

## Three baseline test failures had to be resolved first

The working tree already carried the first migration plus its editor churn, with
two failing tests — not the documented xfails. They needed opposite fixes:

| Failure | Which side was wrong |
| --- | --- |
| Outlook `saveAsDraft` was `true`, `includeMessageDetails` `false` | **The artifact.** `HEAD` had `false` / `true`; the editor reverted both to the connector's `defaultValue`. Left alone, the demo saves a draft instead of sending. Fixed in the `.flow`. |
| Triage context-index `source` expected `1148f840-…`, artifact had `b77b72f2-…` | **The test.** Documented resource re-creation churn; the artifact is correct. Updated the expectation. |
| Outlook `FolderKey` binding `resourceKey` expected `""` | **The test.** The editor populated a binding `HEAD` left empty, making both connections symmetric. Updated the expectation. |

The `saveAsDraft` revert is the same lossy-save defect class as UV-15989 /
UV-15990 and deserves separate mention: it is silent, behavioural rather than
structural, and only the contract test catches it. Check it explicitly after any
editor session.

## Verification result

51 passed, 2 xfail. Flow `Valid` with the one expected shared-connection
warning. Both API workflows `Success`. `git diff --check` clean. Retrieval smoke
scores `0.8247` (triage) and `0.8730` (payment) — matching the previous
environment to four decimal places, since the knowledge sources and their byte
counts (4,545 / 3,626) carried over identically.
