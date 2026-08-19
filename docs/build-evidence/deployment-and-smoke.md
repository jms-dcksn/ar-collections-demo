# Deployment and smoke evidence

Date: 2026-08-07

> **Retired environment.** This record describes the `cloud.uipath.com`
> deployment. The solution moved twice on 2026-08-19 — first to
> `https://staging.uipath.com` (`uipathlabs / Playground`, folder
> `JD_Demos/demos/ARCollections`), then to `https://staging.uipath.com`
> (`uipathstgSS_updated / UiPathDefault`, folder `JD/demos`) — and has not been
> published or deployed in either. Every identifier below belongs to the retired
> `cloud.uipath.com` environment; the current contract is
> `config/platform-resources.json`.

## Deployment

- UiPath CLI: `1.198.0`
- Target: `uipathlabs / Playground`
- Parent folder: `JD_Demos/demos`
- Package: `ARCollectionsDemo 1.0.0`
- Deployment: `ARCollectionsDemo-1-0-0`
- Deployment folder: `JD_Demos/demos/ARCollectionsDemo`
- Pipeline deployment: `3f75317f-d9e6-4b69-8864-08def47454ac`
- Result: `DeploymentSucceeded`
- Activation: `SuccessfulActivate`

## Linked existing resources

- Outlook connection `james.dickson@uipath.com`: enabled and active
- Storage buckets `ar-dispute-triage-kb` and `ar-payment-resolution-kb`
- Context Grounding indexes `ar-dispute-triage-index` and `ar-payment-resolution-index`: ingestion successful

The deployment configuration links all five shared resources in `JD_Demos/demos`. It creates only the solution-local Lookup Payment, Mock Update, and Flow processes.

## Verification

- Repository tests: 34 passed
- `LookupPaymentApplication` fixture: passed
- `MockUpdateDispute` fixture: passed
- Both API Workflow validations: valid
- Maestro Flow validation: valid
- Solution dry-run package: valid
- Versioned package build and publish: successful
- Packaged BPMN audit: `MockUpdateDispute` uses `approvalCommentsInput` and resolves its name and `solution_folder` bindings
- Independent targeted review: no blocking or important findings

## Runtime smoke status

Runtime proposal checks and the live email smoke are pending explicit execution approval. No Flow debug run, approval task, mock update, or email send was initiated during deployment.
