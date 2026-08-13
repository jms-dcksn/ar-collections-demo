export type ScenarioId = 'po_mismatch' | 'missing_pod' | 'payment_misapplication'

export interface CreateDisputeInput {
  scenarioId: ScenarioId
  recipientEmail: string
}

export interface CreateDisputePayload {
  caseId: string
  customerName: string
  customerAccountId: string
  invoiceNumber: string
  outstandingBalance: number
  customerReason: string
  openedDate: string
  evidence: string
  recipientEmail: string
}

export interface DisputeScenario {
  id: ScenarioId
  label: string
  description: string
  evidenceSummary: string
  caseIdPrefix: string
  customerName: string
  customerAccountId: string
  invoiceNumber: string
  outstandingBalance: number
  customerReason: string
  openedDate: string
  evidence: Record<string, string | number>
}

export const DISPUTE_SCENARIOS: readonly DisputeScenario[] = [
  {
    id: 'po_mismatch', label: 'Purchase-order mismatch', description: 'Invoice amount exceeds the authorized purchase order.', evidenceSummary: 'Invoice $48,750 · PO authorized $47,250 · Difference $1,500', caseIdPrefix: 'AR-PO',
    customerName: 'Northstar Manufacturing', customerAccountId: 'NORTHSTAR-1701', invoiceNumber: 'INV-10471', outstandingBalance: 48750,
    customerReason: 'The invoice exceeds the purchase-order-authorized amount.', openedDate: '2026-07-07',
    evidence: { invoiceAmount: 48750, poAuthorizedAmount: 47250, difference: 1500 },
  },
  {
    id: 'missing_pod', label: 'Missing proof of delivery', description: 'Payment is held pending delivery documentation.', evidenceSummary: 'Delivered 2026-06-18 · Signed by M. Chen · 120 of 120 units', caseIdPrefix: 'AR-POD',
    customerName: 'Riverbend Retail', customerAccountId: 'RIVERBEND-2904', invoiceNumber: 'INV-20482', outstandingBalance: 22400,
    customerReason: 'Payment is on hold until proof of delivery is provided.', openedDate: '2026-07-10',
    evidence: { deliveryDate: '2026-06-18', signer: 'M. Chen', shipmentQuantity: 120, invoiceQuantity: 120 },
  },
  {
    id: 'payment_misapplication', label: 'Payment misapplication', description: 'A reported payment has not cleared the invoice balance.', evidenceSummary: 'Reported payment $36,800 · Reference PAY-77821', caseIdPrefix: 'AR-PAY',
    customerName: 'Summit Medical Distribution', customerAccountId: 'SUMMIT-4402', invoiceNumber: 'INV-30915', outstandingBalance: 36800,
    customerReason: 'We paid this invoice, but the balance is still open.', openedDate: '2026-07-14',
    evidence: { reportedPaymentAmount: 36800, paymentReference: 'PAY-77821' },
  },
] as const

export function isValidRecipientEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export function buildDisputePayload(
  input: CreateDisputeInput,
  now = new Date(),
  randomUUID: () => string = () => crypto.randomUUID(),
): CreateDisputePayload {
  const recipientEmail = input.recipientEmail.trim()
  if (!isValidRecipientEmail(recipientEmail)) throw new Error('Enter a valid recipient email.')
  const scenario = DISPUTE_SCENARIOS.find((candidate) => candidate.id === input.scenarioId)
  if (!scenario) throw new Error('Select a dispute scenario.')
  const date = now.toISOString().slice(0, 10).replaceAll('-', '')
  const suffix = randomUUID().replaceAll('-', '').slice(0, 8).toUpperCase()
  return {
    caseId: `${scenario.caseIdPrefix}-${date}-${suffix}`,
    customerName: scenario.customerName,
    customerAccountId: scenario.customerAccountId,
    invoiceNumber: scenario.invoiceNumber,
    outstandingBalance: scenario.outstandingBalance,
    customerReason: scenario.customerReason,
    openedDate: scenario.openedDate,
    evidence: JSON.stringify(scenario.evidence),
    recipientEmail,
  }
}
