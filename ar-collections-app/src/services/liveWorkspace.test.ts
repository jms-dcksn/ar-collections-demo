import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ENTITY_ID, SOLUTION_FOLDER_KEY } from '../config'
import { liveDataFabricClient, loadInstanceVariables, loadLiveDisputes } from './liveWorkspace'

const sdk = vi.hoisted(() => ({
  entitiesGetAll: vi.fn(),
  entitiesGetById: vi.fn(),
  queryRecordsById: vi.fn(),
  updateRecordById: vi.fn(),
  insertRecordById: vi.fn(),
  processesGetAll: vi.fn(),
  instancesGetAll: vi.fn(),
  instancesGetById: vi.fn(),
  getVariables: vi.fn(),
}))

const INSTANCE_ID = '4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10'

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
    getById = sdk.instancesGetById
    getVariables = sdk.getVariables
  },
}))

describe('loadLiveDisputes', () => {
  const entity = {
    id: ENTITY_ID,
    fields: [
      'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
      'customerReason', 'openedDate', 'evidence', 'recipientEmail', 'lifecycleState', 'disputeType',
      'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
      'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
      'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
      'emailSent', 'auditSummary',
    ].map((name) => ({ name })),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    sdk.entitiesGetAll.mockResolvedValue([entity])
    sdk.entitiesGetById.mockResolvedValue(entity)
    sdk.queryRecordsById.mockResolvedValue({
      items: [
        { Id: 'record-awaiting', caseId: 'CASE-001', lifecycleState: 'awaiting_approval', CreateTime: '2026-08-19T21:16:29Z' },
        { Id: 'record-triaging', caseId: 'CASE-002', lifecycleState: 'triaging' },
        { Id: 'record-resolved', caseId: 'CASE-003', lifecycleState: 'resolved' },
        { Id: 'record-rejected', caseId: 'CASE-004', lifecycleState: 'rejected' },
        { Id: 'record-manual', caseId: 'CASE-005', lifecycleState: 'needs_manual_triage' },
      ],
      hasNextPage: false,
    })
  })

  it('resolves the entity with getById and never the page-capped getAll', async () => {
    await loadLiveDisputes({})

    expect(sdk.entitiesGetById).toHaveBeenCalledWith(ENTITY_ID)
    expect(sdk.entitiesGetAll).not.toHaveBeenCalled()
  })

  it('never consults the Maestro listing endpoints', async () => {
    // ProcessInstances.getAll cannot see this Flow's instances (no folder-key header), so rows
    // still come from Data Fabric alone. Reintroducing these calls reintroduces the bug.
    await loadLiveDisputes({})

    expect(sdk.processesGetAll).not.toHaveBeenCalled()
    expect(sdk.instancesGetAll).not.toHaveBeenCalled()
  })

  it('skips getById while caseId still holds a business identifier', async () => {
    await loadLiveDisputes({})

    expect(sdk.instancesGetById).not.toHaveBeenCalled()
  })

  it('resolves the live instance from the ID the Flow stored on caseId', async () => {
    sdk.queryRecordsById.mockResolvedValue({
      items: [{ Id: 'record-stamped', caseId: INSTANCE_ID, lifecycleState: 'awaiting_approval' }],
      hasNextPage: false,
    })
    sdk.instancesGetById.mockResolvedValue({
      instanceId: INSTANCE_ID, instanceDisplayName: 'ARCollectionsDisputeResolution',
      latestRunStatus: 'Paused', startedTime: '2026-08-20T09:00:00Z', completedTime: null,
      folderKey: SOLUTION_FOLDER_KEY, packageVersion: '1.0.4', startedByUser: 'flow-trigger',
      latestRunId: 'run-7',
    })

    const [row] = await loadLiveDisputes({})

    expect(sdk.instancesGetById).toHaveBeenCalledWith(INSTANCE_ID, SOLUTION_FOLDER_KEY)
    expect(row?.instance).toMatchObject({
      instanceId: INSTANCE_ID,
      instanceDisplayName: 'ARCollectionsDisputeResolution',
      latestRunStatus: 'Paused',
      startedTime: '2026-08-20T09:00:00Z',
      completedTime: null,
      packageVersion: '1.0.4',
      startedByUser: 'flow-trigger',
      latestRunId: 'run-7',
      instanceSource: 'maestro',
    })
  })

  it('degrades one row to the derived instance when PIMS refuses the instance', async () => {
    sdk.queryRecordsById.mockResolvedValue({
      items: [{ Id: 'record-stamped', caseId: INSTANCE_ID, lifecycleState: 'triaging', CreateTime: '2026-08-20T09:00:00Z' }],
      hasNextPage: false,
    })
    sdk.instancesGetById.mockRejectedValue(new Error('404'))

    const [row] = await loadLiveDisputes({})

    expect(row?.instance).toMatchObject({
      instanceId: 'record-stamped', latestRunStatus: 'Running', instanceSource: 'derived',
    })
  })

  it('shows only work still in flight and drops terminal lifecycle states', async () => {
    const rows = await loadLiveDisputes({})

    expect(rows.map((row) => row.record.Id)).toEqual(['record-awaiting', 'record-triaging'])
    expect(rows.every((row) => row.source === 'live')).toBe(true)
  })

  it('derives a display-only Flow instance from the record', async () => {
    const [awaiting] = await loadLiveDisputes({})

    expect(awaiting?.instance).toMatchObject({
      instanceId: 'record-awaiting',
      instanceDisplayName: 'CASE-001',
      latestRunStatus: 'Waiting',
      startedTime: '2026-08-19T21:16:29Z',
      completedTime: null,
      folderKey: SOLUTION_FOLDER_KEY,
      instanceSource: 'derived',
    })
  })

  it('pages through every record page instead of trusting one response', async () => {
    sdk.queryRecordsById.mockReset()
      .mockResolvedValueOnce({ items: [{ Id: 'record-a', caseId: 'CASE-A', lifecycleState: 'triaging' }], hasNextPage: true, nextCursor: { value: 'page-2' } })
      .mockResolvedValueOnce({ items: [{ Id: 'record-b', caseId: 'CASE-B', lifecycleState: 'updating' }], hasNextPage: false })

    const rows = await loadLiveDisputes({})

    expect(sdk.queryRecordsById).toHaveBeenNthCalledWith(1, ENTITY_ID, { pageSize: 100 })
    expect(sdk.queryRecordsById).toHaveBeenNthCalledWith(2, ENTITY_ID, { pageSize: 100, cursor: { value: 'page-2' } })
    expect(rows.map((row) => row.record.Id)).toEqual(['record-a', 'record-b'])
  })

  it('reads Data Fabric fields regardless of payload key casing', async () => {
    sdk.queryRecordsById.mockResolvedValue({
      items: [{ Id: 'record-9', CaseId: 'CASE-001', LifecycleState: 'awaiting_approval', OutstandingBalance: 36800 }],
      hasNextPage: false,
    })

    const rows = await loadLiveDisputes({})

    expect(rows).toHaveLength(1)
    expect(rows[0]?.record).toMatchObject({
      Id: 'record-9', caseId: 'CASE-001', lifecycleState: 'awaiting_approval', outstandingBalance: 36800,
    })
  })

  it('surfaces a clear error when the entity cannot be read', async () => {
    sdk.entitiesGetById.mockRejectedValue(new Error('403'))

    await expect(loadLiveDisputes({}))
      .rejects.toThrow('The configured AR Collections entity is not available to this user.')
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

  it('reads Flow globals for one instance and formats every value for display', async () => {
    sdk.getVariables.mockResolvedValue({
      instanceId: INSTANCE_ID,
      parentElementId: null,
      elements: [],
      globalVariables: [
        { id: 'v1', name: 'status', type: 'string', source: 'normalizeProposal', elementId: 'e1', value: 'awaiting_approval' },
        { id: 'v2', name: 'emailSent', type: 'boolean', source: 'persistResolved1', elementId: 'e2', value: false },
        { id: 'v3', name: 'resourcesUsed', type: 'any', source: 'normalizeProposal', elementId: 'e3', value: { tools: ['lookupPaymentTool'] } },
      ],
    })

    const variables = await loadInstanceVariables({}, INSTANCE_ID)

    expect(sdk.getVariables).toHaveBeenCalledWith(INSTANCE_ID, SOLUTION_FOLDER_KEY)
    expect(variables).toEqual([
      { id: 'v1', name: 'status', type: 'string', source: 'normalizeProposal', value: 'awaiting_approval' },
      { id: 'v2', name: 'emailSent', type: 'boolean', source: 'persistResolved1', value: 'false' },
      { id: 'v3', name: 'resourcesUsed', type: 'any', source: 'normalizeProposal', value: JSON.stringify({ tools: ['lookupPaymentTool'] }, null, 2) },
    ])
  })
})
