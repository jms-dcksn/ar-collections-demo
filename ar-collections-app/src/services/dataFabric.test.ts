import { describe, expect, it, vi } from 'vitest'

import { ENTITY_ID, REQUIRED_ENTITY_FIELDS } from '../config'
import { DataFabricService, validateEntitySchema } from './dataFabric'

describe('DataFabricService', () => {
  it('rejects a schema that cannot safely accept approval comments', () => {
    expect(() => validateEntitySchema(REQUIRED_ENTITY_FIELDS.filter((field) => field !== 'approvalComments')))
      .toThrow('Data Fabric entity is missing required fields: approvalComments')
  })

  it('sends only the permitted decision payload through the event-triggering API', async () => {
    const updateRecordById = vi.fn().mockResolvedValue({ Id: 'record-1' })
    const service = new DataFabricService({ updateRecordById } as never)
    await service.recordDecision({ Id: 'record-1' }, 'Approved', ' Evidence confirmed ')
    expect(updateRecordById).toHaveBeenCalledWith(ENTITY_ID, 'record-1', {
      approvalDecision: 'Approved', approvalComments: 'Evidence confirmed', lifecycleState: 'Approved',
    })
  })
})
