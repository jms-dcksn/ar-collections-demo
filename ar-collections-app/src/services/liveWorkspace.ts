import { Entities } from '@uipath/uipath-typescript/entities'
import { ProcessInstances } from '@uipath/uipath-typescript/maestro-processes'

import { ENTITY_ID, LIFECYCLE, SOLUTION_FOLDER_KEY, maestroInstanceIdOf } from '../config'
import type { CreateDisputePayload } from '../lib/disputeScenarios'
import { validateEntitySchema } from './dataFabric'
import type { DisputeRecord, DisputeRow, FlowInstance, FlowVariable } from '../types'

type Raw = Record<string, unknown>

function string(value: unknown) { return typeof value === 'string' ? value : '' }
function number(value: unknown) { return typeof value === 'number' ? value : Number(value ?? 0) }
function bool(value: unknown) { return value === true || value === 'true' }

// Data Fabric and PIMS payload key casing is not guaranteed to match the entity schema —
// the uip CLI renders these same fields PascalCase — so read every field case-insensitively.
function reader(raw: object) {
  const lower: Raw = {}
  for (const [key, value] of Object.entries(raw)) lower[key.toLowerCase()] = value
  return (...names: string[]) => names.map((name) => lower[name.toLowerCase()]).find((value) => value !== undefined && value !== null)
}

function mapRecord(raw: object): DisputeRecord {
  const at = reader(raw)
  return {
    Id: string(at('Id')), caseId: string(at('caseId')), customerName: string(at('customerName')),
    customerAccountId: string(at('customerAccountId')), invoiceNumber: string(at('invoiceNumber')),
    outstandingBalance: number(at('outstandingBalance')), customerReason: string(at('customerReason')),
    openedDate: string(at('openedDate')), evidence: string(at('evidence')), lifecycleState: string(at('lifecycleState')),
    disputeType: string(at('disputeType')), triageRationale: string(at('triageRationale')),
    triageConfidence: number(at('triageConfidence')), evidenceSummary: string(at('evidenceSummary')),
    rootCause: string(at('rootCause')), recommendedAction: string(at('recommendedAction')), actionCode: string(at('actionCode')),
    adjustmentAmount: number(at('adjustmentAmount')), specialistConfidence: number(at('specialistConfidence')),
    approvalSummary: string(at('approvalSummary')), approvalDecision: string(at('approvalDecision')),
    approvalComments: string(at('approvalComments')), updateResult: string(at('updateResult')), emailSent: bool(at('emailSent')), auditSummary: string(at('auditSummary')),
    createdTime: string(at('CreateTime')),
  }
}

// queryRecordsById NEVER resolves to a bare array. Passing pageSize makes it a
// PaginatedResponse, and even without pagination options it is a NonPaginatedResponse — both
// wrap the rows in `items`. Calling .map() on the result throws at runtime.
async function getAllRecords(entities: Entities) {
  const records: DisputeRecord[] = []
  let cursor: { value: string } | undefined

  while (true) {
    const page = await entities.queryRecordsById(ENTITY_ID, {
      pageSize: 100,
      ...(cursor ? { cursor } : {}),
    })
    records.push(...page.items.map(mapRecord))
    if (!page.hasNextPage || !page.nextCursor) return records
    cursor = page.nextCursor
  }
}

function fieldNames(entity: object) {
  const raw = reader(entity)('fields')
  return (Array.isArray(raw) ? raw : []).map((field) => string(reader(field as object)('name'))).filter(Boolean)
}

// ProcessInstances.getAll() still cannot see this Flow's instances. PIMS scopes instance listing
// by the x-uipath-folderkey header, which getAll never sends and offers no way to supply; every
// server-side filter it does accept (processKey, packageId) returns zero, and exhausting the
// unfiltered list (527 instances, 3 pages) contains none of ours. Verified in-browser against
// the real SDK on 2026-08-19. getById(instanceId, folderKey) and getVariables(instanceId,
// folderKey) DO send that header and do work, so the Flow now writes its own instance ID onto
// the record's caseId field and that value — not a listing — is what gives the app an ID. Rows
// still come from Data Fabric, the system of record; the instance supplies live run detail.
const ACTIVE_LIFECYCLE = new Set<string>([
  LIFECYCLE.triaging, LIFECYCLE.awaitingApproval, LIFECYCLE.approved, LIFECYCLE.updating,
])

function runStatusFor(lifecycleState?: string) {
  if (lifecycleState === LIFECYCLE.awaitingApproval) return 'Waiting'
  if (lifecycleState === LIFECYCLE.resolved) return 'Completed'
  if (lifecycleState === LIFECYCLE.rejected || lifecycleState === LIFECYCLE.needsManualTriage) return 'Ended'
  return 'Running'
}

// Fallback for a record the Flow has not stamped yet, or an instance PIMS will not return.
function displayInstanceFor(record: DisputeRecord): FlowInstance {
  return {
    instanceId: record.Id,
    instanceDisplayName: record.caseId || 'AR Collections resolution',
    latestRunStatus: runStatusFor(record.lifecycleState),
    startedTime: record.createdTime || record.openedDate,
    completedTime: null,
    folderKey: SOLUTION_FOLDER_KEY,
    instanceSource: 'derived',
  }
}

function mapInstance(raw: object, record: DisputeRecord): FlowInstance {
  const at = reader(raw)
  const completed = string(at('completedTime'))
  return {
    instanceId: string(at('instanceId')) || record.caseId,
    instanceDisplayName: string(at('instanceDisplayName')) || record.caseId,
    latestRunStatus: string(at('latestRunStatus')) || runStatusFor(record.lifecycleState),
    startedTime: string(at('startedTime')) || record.createdTime || record.openedDate,
    completedTime: completed || null,
    folderKey: string(at('folderKey')) || SOLUTION_FOLDER_KEY,
    instanceSource: 'maestro',
    packageVersion: string(at('packageVersion')),
    startedByUser: string(at('startedByUser')),
    latestRunId: string(at('latestRunId')),
  }
}

// One getById per in-flight record. The demo shows a handful of active disputes, so the cost is
// a few parallel calls; a failure degrades that row to the derived instance instead of the page.
async function instanceFor(instances: ProcessInstances, record: DisputeRecord): Promise<FlowInstance> {
  const instanceId = maestroInstanceIdOf(record.caseId)
  if (!instanceId) return displayInstanceFor(record)
  const raw = await instances.getById(instanceId, SOLUTION_FOLDER_KEY).catch(() => undefined)
  return raw ? mapInstance(raw, record) : displayInstanceFor(record)
}

export async function loadLiveDisputes(sdk: unknown): Promise<DisputeRow[]> {
  // getById, not getAll().find(): Entities.getAll() sends no page size, so the server caps the
  // list and our entity is not guaranteed to be in it. getById fetches this entity directly.
  const entities = new Entities(sdk)
  const entity = await entities.getById(ENTITY_ID).catch(() => undefined)
  if (!entity) throw new Error('The configured AR Collections entity is not available to this user.')
  validateEntitySchema(fieldNames(entity))

  // Rows come from Data Fabric, not from a Maestro instance listing — see the note above
  // ACTIVE_LIFECYCLE. Terminal states are excluded so the desk shows work still in flight.
  const records = await getAllRecords(entities)
  const instances = new ProcessInstances(sdk)

  return Promise.all(records
    .filter((record) => record.Id && ACTIVE_LIFECYCLE.has(record.lifecycleState ?? ''))
    .map(async (record) => ({
      instance: await instanceFor(instances, record),
      record,
      source: 'live' as const,
      correlation: 'matched' as const,
    })))
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value)
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}

// Global variables for one instance. getVariables needs the folder key for the same reason
// getById does, and the ID must be the Flow-written instance ID, never the record ID.
export async function loadInstanceVariables(sdk: unknown, instanceId: string): Promise<FlowVariable[]> {
  const response = await new ProcessInstances(sdk).getVariables(instanceId, SOLUTION_FOLDER_KEY)
  return (response.globalVariables ?? []).map((variable) => ({
    id: variable.id, name: variable.name, type: variable.type, source: variable.source,
    value: displayValue(variable.value),
  }))
}

export function liveDataFabricClient(sdk: unknown) {
  const entities = new Entities(sdk)
  return {
    updateRecordById: async (entityId: string, recordId: string, data: Record<string, unknown>) => mapRecord(await entities.updateRecordById(entityId, recordId, data)),
    insertRecordById: async (entityId: string, data: CreateDisputePayload) => {
      const entity = await entities.getById(entityId)
      validateEntitySchema(fieldNames(entity))
      return mapRecord(await entities.insertRecordById(entityId, data))
    },
  }
}
