# Context Grounding build evidence

Date: 2026-08-19 (second org/tenant move of the day; supersedes both the
`uipathlabs / Playground` run and the 2026-08-06 record below)
Base URL: `https://staging.uipath.com`
Organization / tenant: `uipathstgSS_updated / UiPathDefault`
Folder: `JD/demos` (`e716bfc7-4c75-4921-ab5b-e5a3bc0d4c2c`)

The folder already existed and held one unrelated bucket and index
(`supplier-qualification-knowledge`). No name collisions, nothing overwritten,
and no index-quota failure. Both Integration Service connections live in this
same folder, so the resource folder key and the connection folder key are one
value.

## Storage staged

| Resource | Bucket key | Source file | Upload |
|---|---|---|---|
| `ar-dispute-triage-kb` | `6a30bffd-5a68-4348-b66d-fea899e8a7af` | `ar-dispute-taxonomy-and-examples.txt` | Successful, 4,545 bytes |
| `ar-payment-resolution-kb` | `306dcb5e-6cf3-4c03-bcff-64633cd9c174` | `payment-misapplication-resolution-playbook.txt` | Successful, 3,626 bytes |

Both byte counts match every earlier upload exactly, confirming the knowledge
sources were carried over unchanged across both moves.

## Indexes and ingestion

Both indexes are bucket-backed with the default `LLMV4` extraction strategy and
embeddings enabled.

| Index | Index key | Final ingestion status | Last ingested (UTC) |
|---|---|---|---|
| `ar-dispute-triage-index` | `a1b7fb4e-cfb3-43a8-b29e-08defd736a4b` | `Successful` | `2026-08-19T14:09:56.508361Z` |
| `ar-payment-resolution-index` | `9745fa62-cff9-45d4-b29f-08defd736a4b` | `Successful` | `2026-08-19T14:09:58.256168Z` |

`uip context-grounding create` requires `--folder-path`; passing only
`--folder-key` fails with `400 A required property (folderName) is missing`.

## Semantic smoke searches

The two queries from the 2026-08-06 run were replayed verbatim so the scores stay
directly comparable across all three environments.

Triage query:

```text
How do PO mismatch, missing proof of delivery, and payment misapplication differ, and when is manual triage required?
```

Top result from `ar-dispute-taxonomy-and-examples.txt` scored `0.8247` (was
`0.8246`) and contained all three category definitions, the classification
exclusions, and the rule to return unsupported/manual triage below `0.75`. The
second result at `0.6646` contained the payment-reference worked example.

Payment query:

```text
What evidence and controls are required before reallocating PAY-77821 from INV-30909 to INV-30915?
```

Top result from `payment-misapplication-resolution-playbook.txt` scored `0.8730`
(was `0.8731`) and contained the required-evidence section: payment reference,
amount, date, customer account, and remittance.

## Retired environment (interim, `uipathlabs / Playground`)

The first 2026-08-19 move provisioned these in `JD_Demos/demos/ARCollections`
(`0736cf9b-92af-45d8-bf09-075454d4d050`). They were superseded the same day and
are no longer referenced by any checked-in artifact:

| Resource | Retired key |
|---|---|
| `ar-dispute-triage-kb` | `0a30973a-325d-49cd-9108-552ec42bed9c` |
| `ar-payment-resolution-kb` | `32007736-59a5-4a24-ab79-33a580c95b2c` |
| `ar-dispute-triage-index` | `659822b4-4c13-4fed-b304-08defd7674b3` |
| `ar-payment-resolution-index` | `8bd172f0-18ed-47fb-b296-08defd736a4b` |
| `JDARCollectionsEntity` | `d22e70b2-cc9b-f111-9b32-000d3a69a13b` |

## Retired environment (2026-08-06)

The original resources were provisioned on `cloud.uipath.com` in folder
`JD_Demos/demos` and are no longer referenced by any checked-in artifact:

| Resource | Retired key |
|---|---|
| `ar-dispute-triage-kb` | `9ebe576c-c8b9-4e82-bd47-32be23a1cdc0` |
| `ar-payment-resolution-kb` | `8bdec5fc-9b40-4053-b879-a74ab933b9bc` |
| `ar-dispute-triage-index` | `9e46f4a3-6c15-4cab-9030-08def39d8059` |
| `ar-payment-resolution-index` | `469965c2-8382-4521-9031-08def39d8059` |

Those resources were left in place on their respective environments; neither
migration deleted anything.
