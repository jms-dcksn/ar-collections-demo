import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SOLUTION_FOLDER_KEY } from '../config'
import { loadLiveDisputes } from './liveWorkspace'

const sdk = vi.hoisted(() => ({
  entitiesGetAll: vi.fn(),
  queryRecordsById: vi.fn(),
  updateRecordById: vi.fn(),
  processesGetAll: vi.fn(),
  instancesGetAll: vi.fn(),
  getVariables: vi.fn(),
}))

vi.mock('@uipath/uipath-typescript/entities', () => ({
  Entities: class {
    getAll = sdk.entitiesGetAll
    queryRecordsById = sdk.queryRecordsById
    updateRecordById = sdk.updateRecordById
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
    sdk.entitiesGetAll.mockResolvedValue([{
      id: 'bc0fc734-bf94-f111-9b32-000d3ab5d4c4',
      fields: [
        'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
        'customerReason', 'openedDate', 'evidence', 'lifecycleState', 'disputeType',
        'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
        'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
        'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
        'emailSent', 'auditSummary',
      ].map((name) => ({ name })),
    }])
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
})
