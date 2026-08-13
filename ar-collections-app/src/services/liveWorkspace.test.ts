import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SOLUTION_FOLDER_KEY } from '../config'
import { liveDataFabricClient, loadLiveDisputes } from './liveWorkspace'

const sdk = vi.hoisted(() => ({
  entitiesGetAll: vi.fn(),
  entitiesGetById: vi.fn(),
  queryRecordsById: vi.fn(),
  updateRecordById: vi.fn(),
  insertRecordById: vi.fn(),
  processesGetAll: vi.fn(),
  instancesGetAll: vi.fn(),
  getVariables: vi.fn(),
}))

vi.mock('@uipath/uipath-typescript/entities', () => ({
  Entities: class {
    getAll = sdk.entitiesGetAll
    getById = sdk.entitiesGetById
    queryRecordsById = sdk.queryRecordsById
    updateRecordById = sdk.updateRecordById
    insertRecordById = sdk.insertRecordById
  },
}))

vi.mock('@uipath/uipath-typescript/maestro-processes', () => ({
  MaestroProcesses: class { getAll = sdk.processesGetAll },
  ProcessInstances: class {
    getAll = sdk.instancesGetAll
    getVariables = sdk.getVariables
  },
}))

describe('loadLiveDisputes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const entity = {
      id: 'bc0fc734-bf94-f111-9b32-000d3ab5d4c4',
      fields: [
        'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
        'customerReason', 'openedDate', 'evidence', 'recipientEmail', 'lifecycleState', 'disputeType',
        'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
        'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
        'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
        'emailSent', 'auditSummary',
      ].map((name) => ({ name })),
    }
    sdk.entitiesGetAll.mockResolvedValue([entity])
    sdk.entitiesGetById.mockResolvedValue(entity)
    sdk.processesGetAll.mockResolvedValue([{
      name: 'ARCollectionsDisputeResolution',
      processKey: 'flow-process-key',
      folderKey: SOLUTION_FOLDER_KEY,
    }])
    sdk.instancesGetAll
      .mockResolvedValueOnce({
        items: [{
          instanceId: 'flow-instance-1',
          instanceDisplayName: 'AR dispute',
          latestRunStatus: 'Running',
          startedTime: '2026-08-13T12:00:00.000Z',
          completedTime: null,
          folderKey: SOLUTION_FOLDER_KEY,
        }],
        hasNextPage: true,
        nextCursor: { value: 'next-page' },
      })
      .mockResolvedValueOnce({ items: [], hasNextPage: false })
    sdk.getVariables.mockResolvedValue({ globalVariables: { caseId: { value: 'CASE-001' } } })
    sdk.queryRecordsById.mockResolvedValue([{ Id: 'record-1', caseId: 'CASE-001' }])
  })

  it('queries every page of Flow instances for the discovered process', async () => {
    const rows = await loadLiveDisputes({})

    expect(sdk.instancesGetAll).toHaveBeenNthCalledWith(1, {
      processKey: 'flow-process-key',
      processType: 'Flow',
      pageSize: 200,
    })
    expect(sdk.instancesGetAll).toHaveBeenNthCalledWith(2, {
      processKey: 'flow-process-key',
      processType: 'Flow',
      pageSize: 200,
      cursor: { value: 'next-page' },
    })
    expect(rows).toHaveLength(1)
    expect(rows[0]?.record.caseId).toBe('CASE-001')
  })

  it('maps a newly inserted tenant-level record', async () => {
    sdk.insertRecordById.mockResolvedValue({ Id: 'record-2', caseId: 'CASE-002', outstandingBalance: 22400 })
    const payload = {
      caseId: 'CASE-002', customerName: 'Riverbend Retail', customerAccountId: 'RIVERBEND-2904', invoiceNumber: 'INV-20482',
      outstandingBalance: 22400, customerReason: 'Payment is on hold until proof of delivery is provided.', openedDate: '2026-07-10',
      evidence: '{"deliveryDate":"2026-06-18"}', recipientEmail: 'collector@example.com',
    }

    const record = await liveDataFabricClient({}).insertRecordById('entity-1', payload)

    expect(sdk.insertRecordById).toHaveBeenCalledWith('entity-1', payload)
    expect(record).toMatchObject({ Id: 'record-2', caseId: 'CASE-002', outstandingBalance: 22400 })
  })

  it('refuses insertion when the live entity schema cannot accept the recipient', async () => {
    sdk.entitiesGetById.mockResolvedValue({
      fields: [
        'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance', 'customerReason', 'openedDate', 'evidence',
        'lifecycleState', 'disputeType', 'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause', 'recommendedAction',
        'actionCode', 'adjustmentAmount', 'specialistConfidence', 'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult', 'emailSent', 'auditSummary',
      ].map((name) => ({ name })),
    })
    const payload = {
      caseId: 'CASE-003', customerName: 'Riverbend Retail', customerAccountId: 'RIVERBEND-2904', invoiceNumber: 'INV-20482',
      outstandingBalance: 22400, customerReason: 'Missing POD', openedDate: '2026-07-10', evidence: '{}', recipientEmail: 'collector@example.com',
    }

    await expect(liveDataFabricClient({}).insertRecordById('entity-1', payload))
      .rejects.toThrow('Data Fabric entity is missing required fields: recipientEmail')
    expect(sdk.insertRecordById).not.toHaveBeenCalled()
  })
})
