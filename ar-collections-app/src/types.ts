export type ApprovalDecision = 'approved' | 'rejected'
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
  /** Data Fabric system field, used for the display-only Flow instance start time. */
  createdTime?: string
}

export interface FlowInstance {
  instanceId: string
  instanceDisplayName: string
  latestRunStatus: string
  startedTime: string
  completedTime: string | null
  folderKey: string
  /**
   * 'maestro' when PIMS returned the instance for the ID the Flow stored on `caseId`;
   * 'derived' when no instance ID was available and the values come from the record.
   */
  instanceSource: 'maestro' | 'derived'
  packageVersion?: string
  startedByUser?: string
  latestRunId?: string
}

/** One Flow global variable, value already rendered for display. */
export interface FlowVariable {
  id: string
  name: string
  type: string
  source: string
  value: string
}

export interface DisputeRow {
  instance: FlowInstance
  record: DisputeRecord
  source: RecordSource
  correlation: 'matched' | 'mock-preview'
}
