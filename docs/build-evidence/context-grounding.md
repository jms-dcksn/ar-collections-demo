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

## Index quota blocker

Creation of `ar-dispute-triage-index` was rejected by the Context Grounding service with HTTP 429:

```text
The number of indexes created for this tenant has reached rate limits. Allowed 100, used 100.
```

The payment index was not attempted after the same tenant-wide limit was confirmed. No existing index was deleted, overwritten, or repurposed. The CLI inventory exposes 68 indexes to the current identity, including one failed index and one stale in-progress index outside the demo folder, but the current user has not authorized removing either.

The two `indexKey` fields in `config/platform-resources.json` intentionally remain empty until two tenant index slots are available. Ingestion and semantic smoke-search evidence are pending that capacity decision.
