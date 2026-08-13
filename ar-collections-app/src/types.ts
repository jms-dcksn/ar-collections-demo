export type ApprovalDecision = 'Approved' | 'Rejected'
export type RecordSource = 'live' | 'mock'

export interface DisputeRecord {
  Id: string
  caseId: string
  customerName: string
  customerAccountId: string
  invoiceNumber: string
  outstandingBalance: number
  customerReason: string
  openedDate: string
  evidence: string
  lifecycleState?: string
  disputeType?: string
  triageRationale?: string
  triageConfidence?: number
  evidenceSummary?: string
  rootCause?: string
  recommendedAction?: string
  actionCode?: string
  adjustmentAmount?: number
  specialistConfidence?: number
  approvalSummary?: string
  approvalDecision?: string
  approvalComments?: string
  updateResult?: string
  emailSent?: boolean
  auditSummary?: string
}

export interface FlowInstance {
  instanceId: string
  instanceDisplayName: string
  latestRunStatus: string
  startedTime: string
  completedTime: string | null
  folderKey: string
}

export interface DisputeRow {
  instance: FlowInstance
  record: DisputeRecord
  source: RecordSource
  correlation: 'matched' | 'mock-preview'
}
