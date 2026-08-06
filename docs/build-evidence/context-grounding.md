# Context Grounding build evidence

Date: 2026-08-06  
Organization / tenant: `uipathlabs / Playground`  
Folder: `JD_Demos/demos`

## Storage staged

| Resource | Bucket key | Source file | Upload |
|---|---|---|---|
| `ar-dispute-triage-kb` | `9ebe576c-c8b9-4e82-bd47-32be23a1cdc0` | `ar-dispute-taxonomy-and-examples.txt` | Successful, 4,545 bytes |
| `ar-payment-resolution-kb` | `8bdec5fc-9b40-4053-b879-a74ab933b9bc` | `payment-misapplication-resolution-playbook.txt` | Successful, 3,626 bytes |

Preflight confirmed there were no exact-name bucket or index collisions in the target folder.

## Indexes and ingestion

The first creation attempt encountered the tenant's 100-index quota. After the user removed two unused indexes, both planned indexes were created without changing any other resource:

| Index | Index key | Final ingestion status | Last ingested (UTC) |
|---|---|---|---|
| `ar-dispute-triage-index` | `9e46f4a3-6c15-4cab-9030-08def39d8059` | `Successful` | `2026-08-06T16:35:58.260657Z` |
| `ar-payment-resolution-index` | `469965c2-8382-4521-9031-08def39d8059` | `Successful` | `2026-08-06T16:36:00.114475Z` |

## Semantic smoke searches

Triage query:

```text
How do PO mismatch, missing proof of delivery, and payment misapplication differ, and when is manual triage required?
```

Hybrid retrieval returned two passages from `ar-dispute-taxonomy-and-examples.txt`. The top result scored `0.8246` and included all three category definitions, the classification exclusions, and the rule to return unsupported/manual triage below `0.75`. The second result included the `AR-AMB-004` example and the same manual-triage rule.

Payment query:

```text
What evidence and controls are required before reallocating PAY-77821 from INV-30909 to INV-30915?
```

Hybrid retrieval returned the payment playbook with score `0.8731`. The passage included the exact payment, wrong invoice, target invoice, `MISAPPLIED` status, matched remittance, `REALLOCATE_PAYMENT` action, collector approval, and post-update verification controls.
