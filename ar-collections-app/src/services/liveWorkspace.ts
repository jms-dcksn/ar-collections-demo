import { Entities } from '@uipath/uipath-typescript/entities'
import { MaestroProcesses, ProcessInstances } from '@uipath/uipath-typescript/maestro-processes'

import { ENTITY_ID, PROCESS_NAME } from '../config'
import { validateEntitySchema } from './dataFabric'
import type { DisputeRecord, DisputeRow, FlowInstance } from '../types'

type Raw = Record<string, unknown>

function string(value: unknown) { return typeof value === 'string' ? value : '' }
function number(value: unknown) { return typeof value === 'number' ? value : Number(value ?? 0) }
function bool(value: unknown) { return value === true || value === 'true' }

function mapRecord(raw: Raw): DisputeRecord {
  return {
    Id: string(raw.Id ?? raw.id), caseId: string(raw.caseId), customerName: string(raw.customerName),
    customerAccountId: string(raw.customerAccountId), invoiceNumber: string(raw.invoiceNumber),
    outstandingBalance: number(raw.outstandingBalance), customerReason: string(raw.customerReason),
    openedDate: string(raw.openedDate), evidence: string(raw.evidence), lifecycleState: string(raw.lifecycleState),
    disputeType: string(raw.disputeType), triageRationale: string(raw.triageRationale),
    triageConfidence: number(raw.triageConfidence), evidenceSummary: string(raw.evidenceSummary),
    rootCause: string(raw.rootCause), recommendedAction: string(raw.recommendedAction), actionCode: string(raw.actionCode),
    adjustmentAmount: number(raw.adjustmentAmount), specialistConfidence: number(raw.specialistConfidence),
    approvalSummary: string(raw.approvalSummary), approvalDecision: string(raw.approvalDecision),
    approvalComments: string(raw.approvalComments), updateResult: string(raw.updateResult), emailSent: bool(raw.emailSent), auditSummary: string(raw.auditSummary),
  }
}

function mapInstance(raw: Raw): FlowInstance {
  return {
    instanceId: string(raw.instanceId ?? raw.id), instanceDisplayName: string(raw.instanceDisplayName ?? raw.displayName ?? raw.processName) || 'AR Collections resolution',
    latestRunStatus: string(raw.latestRunStatus ?? raw.status) || 'Running', startedTime: string(raw.startedTime ?? raw.startedTimeUtc),
    completedTime: raw.completedTime ? string(raw.completedTime) : null, folderKey: string(raw.folderKey),
  }
}

async function caseIdFor(instance: FlowInstance, instances: ProcessInstances) {
  if (!instance.instanceId || !instance.folderKey) return ''
  const variables = await instances.getVariables(instance.instanceId, instance.folderKey)
  const caseId = variables.globalVariables?.caseId
  return typeof caseId === 'object' && caseId !== null ? string((caseId as Raw).value) : string(caseId)
}

export async function loadLiveDisputes(sdk: unknown): Promise<DisputeRow[]> {
  const entities = new Entities(sdk)
  const entity = (await entities.getAll()).find((candidate) => candidate.id === ENTITY_ID)
  if (!entity) throw new Error('The configured AR Collections entity is not available to this user.')
  validateEntitySchema((entity.fields ?? []).map((field) => field.name))

  const processes = new MaestroProcesses(sdk)
  const process = (await processes.getAll()).find((candidate) => [candidate.name, candidate.packageId, candidate.displayName].includes(PROCESS_NAME))
  if (!process) return []

  const instances = new ProcessInstances(sdk)
  const active = (await instances.getAll({ processKey: process.processKey })).map(mapInstance).filter((instance) => !instance.completedTime)
  const matches = await Promise.all(active.map(async (instance) => ({ instance, caseId: await caseIdFor(instance, instances) })))
  const caseIds = new Set(matches.map((match) => match.caseId).filter(Boolean))
  if (!caseIds.size) return []

  const records = (await entities.queryRecordsById(ENTITY_ID, { pageSize: 100 })).map(mapRecord)
  const byCaseId = new Map(records.filter((record) => record.caseId).map((record) => [record.caseId, record]))
  return matches.flatMap(({ instance, caseId }) => {
    const record = byCaseId.get(caseId)
    return record ? [{ instance, record, source: 'live' as const, correlation: 'matched' as const }] : []
  })
}

export function liveDataFabricClient(sdk: unknown) {
  const entities = new Entities(sdk)
  return {
    updateRecordById: async (entityId: string, recordId: string, data: Record<string, unknown>) => mapRecord(await entities.updateRecordById(entityId, recordId, data)),
  }
}
