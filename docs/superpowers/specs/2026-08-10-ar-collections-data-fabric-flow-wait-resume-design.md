# AR Collections Data Fabric Flow Wait/Resume

## Purpose

Replace the manual AR dispute Flow trigger and Action Center quick form with a Data Fabric-driven lifecycle. A tenant-scoped `JDARCollectionsEntity` record starts the Flow. The Flow persists triage, proposal, approval, API, email, and terminal state back to that same record. A later Process App update resumes the waiting instance.

## Scope

- Data Fabric entity: `JDARCollectionsEntity` (`JD AR Collections Entity`), tenant-scoped.
- Flow: `solution/ARCollectionsDemo/ARCollectionsDisputeResolution/ARCollectionsDisputeResolution.flow`.
- Data Fabric connector: the enabled connection scoped to `JD_Demos/demos/ARCollectionsDemo`.
- The existing Data Fabric event records supply the case packet. The Flow no longer loads a hard-coded sample case or accepts a manual `recipientEmail` input.
- The current API Workflow and Outlook email remain in the approved path only.

## Entity contract

The tenant-scoped entity keeps the existing required case-packet fields: `caseId`, `customerName`, `customerAccountId`, `invoiceNumber`, `outstandingBalance`, `customerReason`, `openedDate`, and JSON-text `evidence`.

The following fields extend the entity for the Flow lifecycle:

| Field | Data Fabric type | Required | Written by |
| --- | --- | --- | --- |
| `recipientEmail` | `STRING` | Yes | Process App before record creation |
| `lifecycleState` | `STRING` | No | Flow |
| `disputeType` | `STRING` | No | Flow |
| `triageRationale` | `MULTILINE_TEXT` | No | Flow |
| `triageConfidence` | `DECIMAL`, precision 4 | No | Flow |
| `evidenceSummary` | `MULTILINE_TEXT` | No | Flow |
| `rootCause` | `MULTILINE_TEXT` | No | Flow |
| `recommendedAction` | `MULTILINE_TEXT` | No | Flow |
| `actionCode` | `STRING` | No | Flow |
| `adjustmentAmount` | `DECIMAL`, precision 2 | No | Flow |
| `specialistConfidence` | `DECIMAL`, precision 4 | No | Flow |
| `approvalSummary` | `MULTILINE_TEXT` | No | Flow |
| `emailSubject` | `STRING` | No | Flow |
| `emailBody` | `MULTILINE_TEXT` | No | Flow |
| `resourcesUsed` | `MULTILINE_TEXT` | No | Flow |
| `approvalDecision` | `STRING` | No | Process App |
| `approvedBy` | `STRING` | No | Process App |
| `approvalComments` | `MULTILINE_TEXT` | No | Process App |
| `updateResult` | `MULTILINE_TEXT` | No | Flow |
| `emailSent` | `BOOLEAN` | No | Flow |
| `auditSummary` | `MULTILINE_TEXT` | No | Flow |

`approvalDecision` accepts `approved` or `rejected`. The Process App writes it together with `approvedBy` and `approvalComments` to the existing record.

## Flow lifecycle

1. **Record created** — `Record Created` starts the Flow for `JDARCollectionsEntity`. Its `Id` is retained as the record key for every later Data Fabric update.
2. **Triage and specialist proposal** — The Flow maps the trigger record directly into the agents, then writes `triaging` data followed by `awaiting_approval` and the normalized proposal.
3. **Wait and correlate** — `Record Updated` waits mid-Flow. Because the connector does not support an expression-based event filter, a decision checks the update event's `Id` against the original created-record `Id`. An update for another record loops back to the wait. A matching update without an `approvalDecision` also waits again. Only a matching `approved` or `rejected` decision continues.
4. **Rejection** — The Flow writes `rejected`, returns the terminal result, and never invokes the API Workflow or Outlook connector.
5. **Approval** — The Flow writes `approved`, invokes `MockUpdateDispute`, sends the approved email to `recipientEmail`, then writes `resolved`, `updateResult`, `emailSent`, and `auditSummary`.
6. **Manual triage** — An unsupported or low-confidence classification writes `needs_manual_triage`, returns its terminal result, and never invokes the API Workflow or Outlook connector.

The terminal state set is `needs_manual_triage`, `rejected`, and `resolved`; intermediate states are `triaging`, `awaiting_approval`, `approved`, and `updating`.

## Safety and correlation

Every Flow-owned Data Fabric update uses the event record's `Id`, never `caseId`, so a duplicate or malformed business key cannot update or resume a different dispute. The wait loop ignores updates for other records and incomplete matching updates. Approval, update, and email side effects remain reachable only from the matching `approved` path.

## Validation

- Extend the checked-in platform manifest with the tenant-scoped entity ID and all field constraints.
- Replace quick-form and manual-trigger contract tests with tests covering the record-created trigger, record-ID wait loop, Data Fabric updates, and side-effect isolation.
- Run focused Flow and platform tests, the full `uv run pytest -q` suite, `uip maestro flow validate`, and the repository test command.
- Add a concise demo runbook covering record creation, Process App approval/rejection updates, wait/resume behavior, and terminal-state verification.

## Out of scope

- A Process App implementation.
- Data Fabric record retention, RBAC design, or schema normalization beyond the fields required for issue #2.
- Publishing or deploying the solution, and executing a live Flow debug run.
