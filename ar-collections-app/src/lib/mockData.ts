import type { DisputeRow } from '../types'

const minutesAgo = (minutes: number) => new Date(Date.now() - minutes * 60_000).toISOString()

export const mockDisputeRows: DisputeRow[] = [
  {
    source: 'mock', correlation: 'mock-preview',
    instance: { instanceId: 'demo-payment-reallocation', instanceDisplayName: 'Payment reallocation review', latestRunStatus: 'Waiting', startedTime: minutesAgo(142), completedTime: null, folderKey: 'demo' },
    record: { Id: 'demo-payment-003', caseId: 'AR-PAY-003', customerName: 'Contoso Supply Co.', customerAccountId: 'CUS-2048', invoiceNumber: 'INV-30915', outstandingBalance: 18420, customerReason: 'A remittance was received but the payment was posted to an unrelated invoice.', openedDate: '2026-08-11', lifecycleState: 'Awaiting approval', disputeType: 'payment_misapplication', triageRationale: 'Payment reference and remittance details match the open balance.', triageConfidence: 0.96, evidenceSummary: 'Payment of $18,420 is available for reallocation to INV-30915.', rootCause: 'The payment was applied to the wrong customer invoice.', recommendedAction: 'Reallocate the received payment to clear the disputed invoice.', actionCode: 'REALLOCATE_PAYMENT', adjustmentAmount: 0, specialistConfidence: 0.94, approvalSummary: 'Approve payment reallocation with no financial adjustment.', evidence: '{"paymentReference":"PMT-88271","remittanceDate":"2026-08-09","matchedAmount":18420}', auditSummary: 'Waiting for a collector decision.', emailSent: false },
  },
  {
    source: 'mock', correlation: 'mock-preview',
    instance: { instanceId: 'demo-pod-002', instanceDisplayName: 'Proof of delivery review', latestRunStatus: 'Running', startedTime: minutesAgo(57), completedTime: null, folderKey: 'demo' },
    record: { Id: 'demo-pod-002', caseId: 'AR-POD-002', customerName: 'Northstar Health Systems', customerAccountId: 'CUS-1189', invoiceNumber: 'INV-20841', outstandingBalance: 12650, customerReason: 'Customer requested proof of delivery before releasing the invoice.', openedDate: '2026-08-12', lifecycleState: 'In review', disputeType: 'missing_pod', triageRationale: 'The case requests delivery evidence and includes a shipment reference.', triageConfidence: 0.91, evidenceSummary: 'Signed delivery record is available for the full shipment quantity.', rootCause: 'Delivery evidence was not attached to the original invoice communication.', recommendedAction: 'Provide the signed proof of delivery and request release for payment.', actionCode: 'PROVIDE_POD', adjustmentAmount: 0, specialistConfidence: 0.89, approvalSummary: 'No approval required until the specialist completes its review.', evidence: '{"deliveryDate":"2026-06-18","signer":"M. Chen","shipment":"SHP-40192"}', auditSummary: 'Specialist evidence review is in progress.', emailSent: false },
  },
  {
    source: 'mock', correlation: 'mock-preview',
    instance: { instanceId: 'demo-po-001', instanceDisplayName: 'PO mismatch review', latestRunStatus: 'Running', startedTime: minutesAgo(23), completedTime: null, folderKey: 'demo' },
    record: { Id: 'demo-po-001', caseId: 'AR-PO-001', customerName: 'Fabrikam Components', customerAccountId: 'CUS-9063', invoiceNumber: 'INV-18204', outstandingBalance: 7420, customerReason: 'The invoice amount differs from the purchase order total.', openedDate: '2026-08-13', lifecycleState: 'New', disputeType: 'po_mismatch', triageRationale: 'The order and invoice references indicate a quantity variance.', triageConfidence: 0.87, evidenceSummary: 'Ordered quantity and shipped quantity require validation.', rootCause: 'The purchase order amendment was not reflected in billing.', recommendedAction: 'Validate the variance and issue a credit only if the amendment is confirmed.', actionCode: 'ISSUE_CREDIT', adjustmentAmount: 420, specialistConfidence: 0.82, approvalSummary: 'Await specialist recommendation before a collector decision.', evidence: '{"poNumber":"PO-77819","orderedQuantity":120,"invoicedQuantity":126}', auditSummary: 'New dispute awaiting triage completion.', emailSent: false },
  },
]
