export const ENTITY_ID = '81a5f874-d79b-f111-9b33-6045bdd6658d'
export const SOLUTION_FOLDER_KEY = 'ff31878b-35b2-438f-8051-4e1461534d91'
export const PROCESS_KEY = '33534c74-5c67-402d-a96f-0f9dc9e156c6'
export const PROCESS_PACKAGE_ID = 'AR.Collections.Dispute.Flow.flow.ARCollectionsDisputeResolution'
export const PROCESS_NAME = 'ARCollectionsDisputeResolution'

// The Flow owns these values and writes them in snake_case. Never invent display strings here.
export const LIFECYCLE = {
  triaging: 'triaging',
  awaitingApproval: 'awaiting_approval',
  approved: 'approved',
  rejected: 'rejected',
  updating: 'updating',
  resolved: 'resolved',
  needsManualTriage: 'needs_manual_triage',
} as const

export const REQUIRED_ENTITY_FIELDS = [
  'caseId', 'customerName', 'customerAccountId', 'invoiceNumber', 'outstandingBalance',
  'customerReason', 'openedDate', 'evidence', 'recipientEmail', 'lifecycleState', 'disputeType',
  'triageRationale', 'triageConfidence', 'evidenceSummary', 'rootCause',
  'recommendedAction', 'actionCode', 'adjustmentAmount', 'specialistConfidence',
  'approvalSummary', 'approvalDecision', 'approvalComments', 'updateResult',
  'emailSent', 'auditSummary',
] as const

// The Flow overwrites `caseId` with its own Maestro instance ID once the instance is running.
// Until that write lands, `caseId` still holds the business identifier the app inserted, so the
// GUID shape is the only signal that the value can be handed to ProcessInstances.
const INSTANCE_ID_SHAPE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

export function maestroInstanceIdOf(caseId?: string) {
  return caseId && INSTANCE_ID_SHAPE.test(caseId.trim()) ? caseId.trim() : undefined
}

// With the instance ID living on caseId, a GUID is an identifier and not a case label, so the
// invoice number carries the display name instead.
export function caseLabel(caseId?: string, invoiceNumber?: string) {
  const label = maestroInstanceIdOf(caseId) ? invoiceNumber : caseId
  return label || 'AR dispute'
}

export function canDecide(lifecycleState?: string) {
  return lifecycleState === LIFECYCLE.awaitingApproval
}

export function lifecycleLabel(value?: string) {
  if (!value) return '—'
  const words = value.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}
