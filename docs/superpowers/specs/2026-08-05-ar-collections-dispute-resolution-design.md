# AR Collections Dispute Resolution Demo

## Goal

Build a UiPath Maestro demo that resolves one accounts-receivable dispute per run. The demo must show Context Grounding-backed triage, specialist reasoning with tool use, a collector approval, a mocked back-office update through an API Workflow, and a real customer-style email through Microsoft Outlook 365.

The experience is optimized for a mixed business and technical audience and a 10–12 minute presentation.

## Scope

The demo supports three predefined dispute types:

1. Purchase-order mismatch
2. Missing proof of delivery
3. Payment misapplication

The presenter starts the Flow with a sample case ID and an email address. One reusable Flow classifies the dispute using a taxonomy knowledge index, routes it to the appropriate specialist agent, asks a collector to approve the proposed resolution, simulates the update, sends the approved response, and returns an audit result. The payment-misapplication specialist also calls a read-only API Workflow tool and searches a resolution-playbook index before producing its recommendation.

The implementation is demo-grade. It favors a clear canvas and reliable curated inputs over production exception handling.

## Audience and Story

For finance and AR leaders, the demo shows faster dispute resolution with human accountability. For technical builders, it shows how Maestro coordinates Context Grounding, a triage agent, specialist agents, an agent-callable API Workflow, human approval, a second Flow-level API Workflow, and an Integration Service activity through explicit contracts.

## Architecture

The solution contains these components:

1. **Manual trigger** — accepts `caseId` and `recipientEmail`.
2. **Load Sample Case script** — returns a predefined fictional dispute packet keyed by case ID.
3. **Triage taxonomy context** — exposes a Context Grounding index containing dispute definitions and examples.
4. **Triage agent** — searches the taxonomy context, classifies the packet, and explains its confidence.
5. **Maestro routing** — sends a supported, sufficiently confident classification to one specialist.
6. **PO mismatch specialist** — compares invoice and PO details and proposes a correction or credit.
7. **Proof-of-delivery specialist** — evaluates shipment evidence and proposes an evidence-based response.
8. **LookupPaymentApplication API Workflow tool** — returns predictable cash-application evidence to the payment specialist.
9. **Payment resolution context** — exposes a Context Grounding index containing a payment-resolution playbook and examples.
10. **Payment specialist** — calls the lookup tool, searches its resolution context, and proposes cash reallocation.
11. **Common proposal normalization** — exposes the same resolution contract from all three branches.
12. **Collector approval** — presents the evidence, recommendation, confidence, and email preview.
13. **MockUpdateDispute API Workflow** — returns a synthetic update receipt for an approved resolution.
14. **Microsoft Outlook 365 Send Email activity** — sends the approved response to the trigger's `recipientEmail` binding.
15. **End nodes** — return a compact business audit result.

Agents only propose decisions and content. Maestro owns routing, approval, side effects, and the final business outcome.

## Flow Behavior

### Happy path

1. The presenter enters a supported `caseId` and their own `recipientEmail`.
2. The script loads the associated sample packet.
3. The triage agent searches the dispute-taxonomy Context Grounding index.
4. The triage agent returns a supported dispute type with confidence of at least `0.75`.
5. Maestro routes the packet to the matching specialist agent.
6. The payment branch calls `LookupPaymentApplication` and searches the payment-resolution index; the other branches use their curated case evidence directly.
7. The selected specialist returns a structured proposed resolution and customer email.
8. A collector reviews and approves the proposal.
9. The Flow calls `MockUpdateDispute` and receives a synthetic update receipt.
10. The Flow sends the approved email through Outlook.
11. The Flow returns `resolved` with the classification, resource usage, approval, update, and email results.

The mocked update runs before the email so the customer-style message describes a resolution that has already been recorded by the simulated back-office system.

### Business alternatives

- If triage returns an unsupported type or confidence below `0.75`, the Flow ends as `needs_manual_triage` without invoking a specialist or performing side effects.
- If the collector rejects the proposal, the Flow ends as `needs_rework` with the collector comments and performs no side effects.

These are the only alternative branches on the canvas. Technical node faults use the platform run state and diagnostics rather than additional demo branches.

## Input Contract

The manual trigger exposes two required inputs:

| Field | Type | Meaning |
|---|---|---|
| `caseId` | string | One supported sample case identifier |
| `recipientEmail` | string | Presenter-controlled destination for the real Outlook message |

The sample dispute packet contains common customer, account, invoice, outstanding-balance, customer-reason, and opened-date fields plus evidence specific to its dispute type.

## Triage Contract

The triage agent returns:

| Field | Type | Rules |
|---|---|---|
| `disputeType` | string | `po_mismatch`, `missing_pod`, `payment_misapplication`, or `unsupported` |
| `rationale` | string | Concise explanation grounded in the packet |
| `confidence` | number | Value from `0.0` to `1.0` |

The triage agent must search the taxonomy index before classifying every case. Its rationale must name the taxonomy category or example that supports the result. If the retrieved guidance does not support one of the three types, the agent returns `unsupported`.

## Context Grounding Resources

The implementation creates two version-controlled plain-text knowledge sources and two bucket-backed Context Grounding indexes in `JD_Demos/demos`.

| Consumer | Local source file | Storage bucket | Context Grounding index |
|---|---|---|---|
| Triage agent | `knowledge/triage/ar-dispute-taxonomy-and-examples.txt` | `ar-dispute-triage-kb` | `ar-dispute-triage-index` |
| Payment specialist | `knowledge/payment/payment-misapplication-resolution-playbook.txt` | `ar-payment-resolution-kb` | `ar-payment-resolution-index` |

The taxonomy article contains:

- A definition, positive signals, and exclusions for each supported dispute type
- At least two short examples for each type
- Guidance for ambiguous or unsupported cases
- The `0.75` confidence rule and when to request manual triage

The payment-resolution article contains:

- Required evidence for a suspected payment misapplication
- Payment-to-remittance and remittance-to-invoice matching rules
- Controls required before recommending reallocation
- Resolution steps and customer-communication guidance
- At least two worked examples, including the `AR-PAY-003` pattern

Resource setup follows this sequence for each knowledge source:

1. Create an Orchestrator built-in storage bucket in `JD_Demos/demos`.
2. Upload the corresponding text file.
3. Create a bucket-backed Context Grounding index.
4. Trigger ingestion and poll until its status is `Successful`.
5. Run a semantic search that proves the expected guidance is retrievable.

The triage index is attached to the triage inline agent's context port. The payment-resolution index is attached to the payment specialist's context port. Both agents must search their attached resource at runtime before returning their structured output.

## Specialist Resolution Contract

Each specialist returns the same fields so all branches can join a common approval and execution path:

| Field | Type | Meaning |
|---|---|---|
| `caseId` | string | Original case identifier |
| `disputeType` | string | Selected supported type |
| `evidenceSummary` | string | Facts used to support the recommendation |
| `rootCause` | string | Concise cause of the payment blocker |
| `recommendedAction` | string | Proposed resolution |
| `actionCode` | string | `ISSUE_CREDIT`, `PROVIDE_POD`, or `REALLOCATE_PAYMENT` |
| `adjustmentAmount` | number | Financial adjustment, or `0` when none is needed |
| `confidence` | number | Specialist confidence from `0.0` to `1.0` |
| `approvalSummary` | string | Collector-facing summary |
| `emailSubject` | string | Proposed Outlook subject |
| `emailBody` | string | Proposed plain-text customer response |
| `resourcesUsed` | string | Business-readable list of case, API tool, and Context Grounding sources used |

The agent model is an implementation binding. Any supported model selected in the target tenant must satisfy these contracts.

## Sample Cases

### `AR-PO-001` — PO mismatch

- Customer: Northstar Manufacturing
- Invoice: `INV-10471`
- Outstanding balance: `$48,750`
- Evidence: the invoice exceeds its purchase order by `$1,500`
- Expected classification: `po_mismatch`
- Expected action code: `ISSUE_CREDIT`
- Expected proposal: issue a `$1,500` credit or correction and request payment of the corrected balance

### `AR-POD-002` — Missing proof of delivery

- Customer: Riverbend Retail
- Invoice: `INV-20482`
- Outstanding balance: `$22,400`
- Evidence: delivered June 18, 2026, signed by M. Chen, with shipment and invoice quantities matching
- Expected classification: `missing_pod`
- Expected action code: `PROVIDE_POD`
- Expected proposal: provide the delivery facts and request release of the invoice for payment with no financial adjustment

The email body includes the synthetic proof-of-delivery details. A binary file attachment is out of scope.

### `AR-PAY-003` — Payment misapplication

- Customer: Summit Medical Distribution
- Invoice: `INV-30915`
- Outstanding balance: `$36,800`
- Case evidence: the customer reports a `$36,800` payment with reference `PAY-77821`; system application details are intentionally absent from the packet
- Tool evidence: `LookupPaymentApplication` returns that the payment was applied to another invoice
- Expected classification: `payment_misapplication`
- Expected action code: `REALLOCATE_PAYMENT`
- Expected proposal: reallocate the payment and confirm a zero balance

### Hidden negative fixture

`AR-AMB-004` contains an ambiguous customer reason and insufficient evidence. It exists only to verify the `needs_manual_triage` branch and is not presented as a fourth supported dispute type.

## Collector Approval

The approval presents:

- Customer, invoice, and outstanding balance
- Triage classification, rationale, and confidence
- Specialist evidence summary, root cause, recommendation, adjustment, and confidence
- Complete Outlook subject and body preview
- Approve and reject actions with collector comments

Approval continues to the mocked update and email. Rejection returns `needs_rework`.

## API Workflow Contracts

### `LookupPaymentApplication`

This read-only API Workflow is packaged in the same UiPath solution and attached to the payment specialist as an API Workflow tool. The payment specialist must call it before recommending a resolution.

It accepts:

- `caseId`
- `customerAccountId`
- `invoiceNumber`
- `paymentReference`

For `AR-PAY-003`, it returns a predictable payload:

- `paymentReference` with value `PAY-77821`
- `paymentAmount` with value `36800`
- `paymentDate` with value `2026-07-02`
- `appliedInvoiceNumber` with value `INV-30909`
- `targetInvoiceNumber` with value `INV-30915`
- `applicationStatus` with value `MISAPPLIED`
- `matchedRemittance` with value `true`
- `recommendedAction` with value `REALLOCATE_PAYMENT`
- `sourceSystem` with value `MockCashApplication`

The API Workflow performs no external read or write. Its purpose is to demonstrate an agent invoking a deterministic UiPath tool and incorporating the returned evidence into its resolution.

### `MockUpdateDispute`

`MockUpdateDispute` accepts:

- `caseId`
- `disputeType`
- `actionCode`
- `adjustmentAmount`
- `approvedBy`
- `approvalComments`

It performs no external write and returns:

- `updateId`
- `status` with value `UPDATED`
- `updatedAt`
- `message`

The response must be predictable and business-readable so the presenter can show it as evidence of the simulated system update.

## Outlook Integration

The solution targets the `uipathlabs / Playground` tenant and the `JD_Demos/demos` folder. It binds the Microsoft Outlook 365 **Send Email** activity to the existing **james.dickson@uipath.com** connection in that folder. The connection was listed as enabled and passed a live connection ping during design discovery.

The activity bindings are:

- To: trigger `recipientEmail`
- Subject: specialist `emailSubject`
- Body: specialist `emailBody`

The demo does not derive a recipient from customer data, add CC or BCC recipients, or attach files.

## Result Contract

Designed business exits return:

| Field | Meaning |
|---|---|
| `status` | `resolved`, `needs_rework`, or `needs_manual_triage` |
| `caseId` | Original case identifier |
| `disputeType` | Triage result |
| `triageRationale` | Triage explanation |
| `triageConfidence` | Triage confidence |
| `recommendedAction` | Specialist recommendation when available |
| `approvalDecision` | Collector outcome when available |
| `approvalComments` | Collector comments when available |
| `updateResult` | Mock API receipt when approved |
| `emailSent` | Whether the Outlook step completed |
| `resourcesUsed` | Runtime knowledge and API resources used by the agents |
| `auditSummary` | Concise business-readable outcome |

## Verification

1. Format and validate the Maestro Flow without warnings.
2. Validate and directly run both API Workflows with representative inputs.
3. Confirm both knowledge text files contain the required taxonomy, rules, and examples.
4. Create both storage buckets, upload their text files, create both indexes, and verify each ingestion status is `Successful`.
5. Search `ar-dispute-triage-index` for the differences among the three dispute types and verify relevant taxonomy content is returned.
6. Search `ar-payment-resolution-index` for the evidence and controls required before payment reallocation and verify relevant playbook content is returned.
7. Run `AR-PO-001`, `AR-POD-002`, and `AR-PAY-003` far enough to verify expected triage searches, routing, specialist selection, and proposal contracts.
8. Verify the payment specialist calls `LookupPaymentApplication`, searches `ar-payment-resolution-index`, and incorporates both results into its recommendation.
9. Run `AR-AMB-004` and verify `needs_manual_triage` without specialist execution.
10. Package and deploy the solution to `JD_Demos/demos` with the existing Outlook connection and both Context Grounding resources bound.
11. Run one end-to-end smoke test using `AR-PAY-003` and a presenter-supplied internal email address.
12. Approve the task and confirm both agent resource calls, the mock update receipt, the received Outlook email, and the final `resolved` audit result.

The PO and proof-of-delivery scenarios do not need additional live email sends during verification because they use the same approved execution path.

## Demo Storyboard

### Minutes 0–2: Set the stakes

Introduce three overdue invoices blocked by three different dispute types. Explain that the goal is faster resolution using enterprise knowledge, system evidence, and human accountability.

### Minutes 2–4: Start the payment case

Enter `AR-PAY-003` and the presenter's email. Show the triage agent search the taxonomy index, classify the case, and route it to the payment specialist.

### Minutes 4–7: Inspect the recommendation

Show the payment specialist call `LookupPaymentApplication`, search the resolution playbook, and combine those results into its evidence, root cause, proposed action, confidence, and email preview.

### Minutes 7–9: Exercise human control

Approve the resolution. Show the synthetic back-office update receipt and the real Outlook message.

### Minutes 9–12: Reveal reuse

Return to the canvas and point out the PO mismatch and proof-of-delivery specialists, both Context Grounding resources, the payment API tool, the shared approval and execution path, the audit result, and the single manual-triage exception.

## Out of Scope

- Real ERP, logistics, cash-application, or customer-master integrations
- Real financial or invoice updates
- Batch processing or multiple disputes per run
- Attachments in the Outlook message
- Production-grade retries, compensating transactions, or technical error branches
- Automatically addressing real customers
- Production security, scale, monitoring, and operational hardening beyond what the demo requires

## Acceptance Criteria

- A new standalone UiPath solution implements one Maestro Flow and two mocked API Workflows.
- The Flow accepts only a sample case ID and presenter-controlled recipient email.
- Two version-controlled text knowledge articles are uploaded to two separate storage buckets in `JD_Demos/demos` and ingested into two separate Context Grounding indexes.
- The triage agent searches `ar-dispute-triage-index` before routing each supported case to its corresponding specialist agent.
- The payment specialist calls `LookupPaymentApplication` and searches `ar-payment-resolution-index` before returning its proposal.
- All specialists return one common proposal contract and feed one collector approval.
- Unsupported or low-confidence triage is the only explicit exception branch.
- Collector rejection performs no side effects.
- Collector approval calls the mocked update before sending a real Outlook email.
- The Outlook activity is bound to the verified connection in `JD_Demos/demos` and uses the trigger email variable as its recipient.
- The Flow returns a business-readable audit result for every designed business exit.
- Local validation passes, both indexes ingest and search successfully, the solution deploys to the target folder, and the payment smoke test completes end to end.
