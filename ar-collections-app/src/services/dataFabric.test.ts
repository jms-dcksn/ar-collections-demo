import { describe, expect, it, vi } from 'vitest'

import { ENTITY_ID, REQUIRED_ENTITY_FIELDS } from '../config'
import { DataFabricService, validateEntitySchema } from './dataFabric'

describe('DataFabricService', () => {
  it('rejects a schema that cannot safely accept approval comments', () => {
    expect(() => validateEntitySchema(REQUIRED_ENTITY_FIELDS.filter((field) => field !== 'approvalComments')))
      .toThrow('Data Fabric entity is missing required fields: approvalComments')
  })

  it('rejects a schema that cannot accept a creation recipient', () => {
    expect(() => validateEntitySchema(REQUIRED_ENTITY_FIELDS.filter((field) => field !== 'recipientEmail')))
      .toThrow('Data Fabric entity is missing required fields: recipientEmail')
  })

  it('sends only the permitted decision payload through the event-triggering API', async () => {
    const updateRecordById = vi.fn().mockResolvedValue({ Id: 'record-1' })
    const service = new DataFabricService({ updateRecordById } as never)
    await service.recordDecision({ Id: 'record-1' }, 'approved', ' Evidence confirmed ')
    expect(updateRecordById).toHaveBeenCalledWith(ENTITY_ID, 'record-1', {
      approvalDecision: 'approved', approvalComments: 'Evidence confirmed', lifecycleState: 'approved',
    })
  })

  it('inserts a script-equivalent payload into the configured tenant entity', async () => {
    const insertRecordById = vi.fn().mockResolvedValue({ Id: 'record-2', caseId: 'AR-PAY-20260813-ABCDEF12' })
    const service = new DataFabricService({ insertRecordById } as never)
    await service.createDispute(
      { scenarioId: 'payment_misapplication', recipientEmail: ' collector@example.com ' },
      new Date('2026-08-13T01:00:00.000Z'),
      () => 'abcdef12-3456-7890-abcd-ef1234567890',
    )
    expect(insertRecordById).toHaveBeenCalledWith(ENTITY_ID, {
      caseId: 'AR-PAY-20260813-ABCDEF12', customerName: 'Summit Medical Distribution', customerAccountId: 'SUMMIT-4402',
      invoiceNumber: 'INV-30915', outstandingBalance: 36800,
      customerReason: 'We paid this invoice, but the balance is still open.', openedDate: '2026-07-14',
      evidence: '{"reportedPaymentAmount":36800,"paymentReference":"PAY-77821"}', recipientEmail: 'collector@example.com',
    })
  })
})
