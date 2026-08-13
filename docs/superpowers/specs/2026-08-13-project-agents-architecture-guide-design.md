# Project AGENTS Architecture Guide

## Purpose

Expand the repository-root `AGENTS.md` into a concise, durable operating guide
for agents working on the AR collections demo. The guide should let a new agent
understand the solution boundaries, authoritative platform resources, data flow,
technology stack, and validation expectations without repeating the generated
solution-lifecycle reference under `solution/ARCollectionsDemo/AGENTS.md`.

## Scope

Update only the repository-root `AGENTS.md`. Preserve the existing GitHub issue
label guidance. Do not modify UiPath artifacts, application code, resource
manifests, tests, or the nested solution `AGENTS.md`.

The guide will contain:

- A short business-purpose summary.
- A directory and component map for the UiPath solution, Coded App, configuration,
  knowledge content, tests, and runbooks.
- The event-driven lifecycle from Data Fabric record creation through Flow triage,
  specialist resolution, approval wait/resume, mocked system update, Outlook email,
  and terminal record state.
- Ownership and correlation rules, especially the distinction between Data Fabric
  record `Id` and business `caseId`.
- Stable platform bindings: `uipathlabs / Playground`, deployment folder
  `JD_Demos/demos`, tenant-level entity `JDARCollectionsEntity`, entity UUID
  `bc0fc734-bf94-f111-9b32-000d3ab5d4c4`, and the configured Outlook connection.
- The verified sample record created on 2026-08-13, including its record and case
  identifiers, as a test fixture reference rather than a reusable constant.
- The current technology stack: UiPath Solution, Maestro Flow, inline low-code
  agents, API Workflows, Data Fabric, Context Grounding, Integration Service,
  Outlook, React, TypeScript, Vite, UiPath Apollo, Tailwind, the UiPath TypeScript
  SDK, Vitest, and Python/pytest repository contract tests managed with `uv`.
- The relevant validation commands and repository working agreements.

## Architecture Summary

The system is an event-driven UiPath demo. Creating a tenant-level Data Fabric
record starts `ARCollectionsDisputeResolution`. The Flow retains the Data Fabric
record UUID as the lifecycle correlation key, classifies the dispute with an
inline triage agent, routes supported cases to one specialist agent, normalizes
the proposal, persists it, and waits for an update to the same record. The Coded
App correlates Maestro instances to records by the Flow's `caseId` global variable
for display, but performs updates by Data Fabric record UUID. Rejection and manual
triage end without external side effects. Approval invokes the deterministic mock
update API Workflow, sends the approved Outlook email, and persists the terminal
result and audit fields.

## Content Boundaries

- Keep the root guide concise and stable; link to design documents and runbooks for
  detailed contracts.
- Do not copy the nested solution `AGENTS.md`; state that it governs all work below
  `solution/ARCollectionsDemo`.
- Do not include transient quality findings, deployment status, live run status,
  or recommendations that will quickly become stale.
- Clearly label the created sample row as current test data that may later be
  updated by a Flow run.
- Do not present the Data Fabric `caseId` as the record update key.
- Do not imply that creating a test row is side-effect free: the entity's record-
  created event can start the deployed Flow.

## Verification

- Confirm only the root `AGENTS.md` changes during implementation.
- Check every stated path, project type, resource identifier, and command against
  the repository manifests and current CLI behavior.
- Run `git diff --check`.
- No JavaScript or Python source is modified, so `npm test` and pytest are not
  required solely for this documentation change.
