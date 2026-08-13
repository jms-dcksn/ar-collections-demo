export const ENTITY_ID = 'bc0fc734-bf94-f111-9b32-000d3ab5d4c4'
export const PROCESS_NAME = 'ARCollectionsDisputeResolution'

export const REQUIRED_ENTITY_FIELDS = [
  'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
  'customerReason', 'openedDate', 'evidence', 'lifecycleState', 'disputeType',
  'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
  'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
  'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
  'emailSent', 'auditSummary',
] as const

export function canDecide(lifecycleState?: string) {
  return lifecycleState === 'Awaiting approval'
}
