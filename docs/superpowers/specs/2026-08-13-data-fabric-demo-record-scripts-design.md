# Data Fabric Demo Record Scripts

## Goal

Provide three simple, standalone commands that each create one fresh demo record
in the existing tenant-level `JDARCollectionsEntity`
(`bc0fc734-bf94-f111-9b32-000d3ab5d4c4`). The scripts do not create or alter
Data Fabric schemas.

## Scripts and scenarios

- `scripts/create-payment-misapplication-record.sh` seeds the supported payment
  misapplication path.
- `scripts/create-missing-pod-record.sh` seeds the supported missing proof of
  delivery path.
- `scripts/create-po-mismatch-record.sh` seeds the supported purchase-order
  mismatch path.

Each script accepts one mandatory positional argument: the recipient email.
All other business data is a fixed, fictional fixture for that scenario. Each
invocation generates a fresh scenario-shaped `caseId` consisting of the scenario
prefix, current UTC date, and a unique suffix.

## Data Fabric interaction

Each script invokes the supported `uip df records insert` command exactly once,
at tenant scope, and prints its JSON response. It sets
`UIPATH_CLI_DISABLE_VERSION_SYNC=1` so record creation is not obscured by CLI
update checks. A missing recipient argument or failed CLI operation terminates
the script with a nonzero exit code.

The scripts never update, reuse, or delete records. Creating a record may start
the deployed record-created Flow. The currently checked-out Flow includes an
`Update Case ID on record` node that can replace the initially seeded `caseId`
with the Maestro instance ID after insertion.

## Verification and documentation

Pytest coverage executes each script against a temporary fake `uip` executable
and verifies that it issues exactly one insert for the expected entity and
scenario payload. Tests also verify that recipient email is mandatory and that
the generated case ID uses the correct scenario prefix.

The Data Fabric lifecycle runbook will document these copy-paste commands:

```bash
./scripts/create-payment-misapplication-record.sh james.dickson@uipath.com
./scripts/create-missing-pod-record.sh james.dickson@uipath.com
./scripts/create-po-mismatch-record.sh james.dickson@uipath.com
```
