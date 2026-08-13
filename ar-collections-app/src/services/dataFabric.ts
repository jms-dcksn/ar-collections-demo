import { ENTITY_ID, REQUIRED_ENTITY_FIELDS } from '../config'
import type { ApprovalDecision, DisputeRecord } from '../types'

export interface DataFabricClient {
  updateRecordById(entityId: string, recordId: string, data: Record<string, unknown>): Promise<DisputeRecord>
}

export function validateEntitySchema(fieldNames: readonly string[]) {
  const available = new Set(fieldNames)
  const missing = REQUIRED_ENTITY_FIELDS.filter((field) => !available.has(field))
  if (missing.length) {
    throw new Error(`Data Fabric entity is missing required fields: ${missing.join(', ')}`)
  }
}

export class DataFabricService {
  private readonly client: DataFabricClient

  constructor(client: DataFabricClient) {
    this.client = client
  }

  recordDecision(record: Pick<DisputeRecord, 'Id'>, decision: ApprovalDecision, comments: string) {
    return this.client.updateRecordById(ENTITY_ID, record.Id, {
      approvalDecision: decision,
      approvalComments: comments.trim(),
      lifecycleState: decision,
    })
  }
}
