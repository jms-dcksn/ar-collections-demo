# AR Collections Data Fabric Entity

## Purpose

Create the initial Data Fabric schema for the AR collections demo. It persists the same case packet returned by the `Load Sample Case` Flow node, without adding lifecycle, approval, routing, recommendation, update-result, or audit fields.

## Scope

- Data Fabric folder: `JD_Demos/demos/ARCollectionsDemo` (`bbe64c10-b957-4adf-a535-77109c673e5a`).
- Entity display name: `JD AR Collections Entity`.
- Entity system name: `JDARCollectionsEntity`. Data Fabric system names cannot contain spaces.
- All fields below are required because every sample case supplies them. `caseId` is unique.
- The Flow remains responsible for its sample cases; it serializes `evidence` with `JSON.stringify` before any persistence integration is introduced.

| Field | Data Fabric type | Constraints | Source case property |
| --- | --- | --- | --- |
| `caseId` | `STRING` | Required, unique | `caseId` |
| `customerName` | `STRING` | Required | `customerName` |
| `customerAccountId` | `STRING` | Required | `customerAccountId` |
| `invoiceNumber` | `STRING` | Required | `invoiceNumber` |
| `outstandingBalance` | `DECIMAL` | Required, precision 2 | `outstandingBalance` |
| `customerReason` | `MULTILINE_TEXT` | Required | `customerReason` |
| `openedDate` | `DATE` | Required | `openedDate` |
| `evidence` | `MULTILINE_TEXT` | Required; JSON text | `JSON.stringify(evidence)` |

## Evidence representation

Data Fabric does not provide a suitable object field for the variable evidence payloads in this demo. `evidence` is therefore stored as JSON text. Consumers must parse this field as JSON when they need individual evidence attributes. This is a demo-oriented interoperability choice, not a normalized production design.

## Deferred issue requirements

GitHub issue #1 also asks for lifecycle statuses, retention, role ownership, and Flow/entity mappings. This change deliberately limits the entity to the case-packet schema requested for the first Flow node. Those broader design decisions remain open and must be resolved before a Data Fabric-triggered Flow or dispute-management app is implemented.
