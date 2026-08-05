# AR Collections Dispute Resolution Demo

## Goal

Build a UiPath Maestro demo that resolves one accounts-receivable dispute per run. The demo must show agentic triage, specialist reasoning, a collector approval, a mocked back-office update through an API Workflow, and a real customer-style email through Microsoft Outlook 365.

The experience is optimized for a mixed business and technical audience and a 10–12 minute presentation.

## Scope

The demo supports three predefined dispute types:

1. Purchase-order mismatch
2. Missing proof of delivery
3. Payment misapplication

The presenter starts the Flow with a sample case ID and an email address. One reusable Flow classifies the dispute, routes it to the appropriate specialist agent, asks a collector to approve the proposed resolution, simulates the update, sends the approved response, and returns an audit result.

The implementation is demo-grade. It favors a clear canvas and reliable curated inputs over production exception handling.

## Audience and Story

For finance and AR leaders, the demo shows faster dispute resolution with human accountability. For technical builders, it shows how Maestro coordinates a triage agent, specialist agents, human approval, an API Workflow, and an Integration Service activity through explicit contracts.

## Architecture

The solution contains these components:

1. **Manual trigger** — accepts `caseId` and `recipientEmail`.
2. **Load Sample Case script** — returns a predefined fictional dispute packet keyed by case ID.
3. **Triage agent** — classifies the packet and explains its confidence.
4. **Maestro routing** — sends a supported, sufficiently confident classification to one specialist.
5. **PO mismatch specialist** — compares invoice and PO details and proposes a correction or credit.
6. **Proof-of-delivery specialist** — evaluates shipment evidence and proposes an evidence-based response.
7. **Payment specialist** — matches payment and remittance details and proposes cash reallocation.
8. **Common proposal normalization** — exposes the same resolution contract from all three branches.
9. **Collector approval** — presents the evidence, recommendation, confidence, and email preview.
10. **MockUpdateDispute API Workflow** — returns a synthetic update receipt for an approved resolution.
11. **Microsoft Outlook 365 Send Email activity** — sends the approved response to the trigger's `recipientEmail` binding.
12. **End nodes** — return a compact business audit result.

Agents only propose decisions and content. Maestro owns routing, approval, side effects, and the final business outcome.

## Flow Behavior

### Happy path

1. The presenter enters a supported `caseId` and their own `recipientEmail`.
2. The script loads the associated sample packet.
3. The triage agent returns a supported dispute type with confidence of at least `0.75`.
4. Maestro routes the packet to the matching specialist agent.
5. The specialist returns a structured proposed resolution and customer email.
6. A collector reviews and approves the proposal.
7. The Flow calls `MockUpdateDispute` and receives a synthetic update receipt.
8. The Flow sends the approved email through Outlook.
9. The Flow returns `resolved` with the classification, approval, update, and email results.

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
- Evidence: a `$36,800` payment was received but applied to another invoice
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

## Mock API Workflow Contract

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
| `auditSummary` | Concise business-readable outcome |

## Verification

1. Format and validate the Maestro Flow without warnings.
2. Validate and directly run the API Workflow with a representative approved action.
3. Run `AR-PO-001`, `AR-POD-002`, and `AR-PAY-003` far enough to verify expected triage, routing, specialist selection, and proposal contracts.
4. Run `AR-AMB-004` and verify `needs_manual_triage` without specialist execution.
5. Package and deploy the solution to `JD_Demos/demos` with the existing Outlook connection bound.
6. Run one end-to-end smoke test using `AR-POD-002` and a presenter-supplied internal email address.
7. Approve the task and confirm the mock update receipt, received Outlook email, and final `resolved` audit result.

The PO and payment scenarios do not need additional live email sends during verification because they use the same approved execution path.

## Demo Storyboard

### Minutes 0–2: Set the stakes

Introduce three overdue invoices blocked by three different dispute types. Explain that the goal is faster resolution with human accountability.

### Minutes 2–4: Start the POD case

Enter `AR-POD-002` and the presenter's email. Show the triage agent classify the case and Maestro route it to the proof-of-delivery specialist.

### Minutes 4–7: Inspect the recommendation

Show the evidence, root cause, confidence, proposed action, and complete email preview.

### Minutes 7–9: Exercise human control

Approve the resolution. Show the synthetic back-office update receipt and the real Outlook message.

### Minutes 9–12: Reveal reuse

Return to the canvas and point out the PO mismatch and payment misapplication specialists, shared approval and execution path, final audit result, and single manual-triage exception.

## Out of Scope

- Real ERP, logistics, cash-application, or customer-master integrations
- Real financial or invoice updates
- Batch processing or multiple disputes per run
- Attachments in the Outlook message
- Production-grade retries, compensating transactions, or technical error branches
- Automatically addressing real customers
- Production security, scale, monitoring, and operational hardening beyond what the demo requires

## Acceptance Criteria

- A new standalone UiPath solution implements one Maestro Flow and one mocked API Workflow.
- The Flow accepts only a sample case ID and presenter-controlled recipient email.
- A triage agent routes each of the three supported cases to its corresponding specialist agent.
- All specialists return one common proposal contract and feed one collector approval.
- Unsupported or low-confidence triage is the only explicit exception branch.
- Collector rejection performs no side effects.
- Collector approval calls the mocked update before sending a real Outlook email.
- The Outlook activity is bound to the verified connection in `JD_Demos/demos` and uses the trigger email variable as its recipient.
- The Flow returns a business-readable audit result for every designed business exit.
- Local validation passes, the solution deploys to the target folder, and the POD smoke test completes end to end.
