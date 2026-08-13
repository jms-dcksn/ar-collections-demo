import { describe, expect, it } from 'vitest'

import { buildDisputePayload, isValidRecipientEmail } from './disputeScenarios'

const now = new Date('2026-08-13T23:59:59.000Z')
const uuid = () => 'abcdef12-3456-7890-abcd-ef1234567890'

describe('buildDisputePayload', () => {
  it.each([
    ['po_mismatch', {
      caseId: 'AR-PO-20260813-ABCDEF12', customerName: 'Northstar Manufacturing', customerAccountId: 'NORTHSTAR-1701',
      invoiceNumber: 'INV-10471', outstandingBalance: 48750,
      customerReason: 'The invoice exceeds the purchase-order-authorized amount.', openedDate: '2026-07-07',
      evidence: '{"invoiceAmount":48750,"poAuthorizedAmount":47250,"difference":1500}', recipientEmail: 'collector@example.com',
    }],
    ['missing_pod', {
      caseId: 'AR-POD-20260813-ABCDEF12', customerName: 'Riverbend Retail', customerAccountId: 'RIVERBEND-2904',
      invoiceNumber: 'INV-20482', outstandingBalance: 22400,
      customerReason: 'Payment is on hold until proof of delivery is provided.', openedDate: '2026-07-10',
      evidence: '{"deliveryDate":"2026-06-18","signer":"M. Chen","shipmentQuantity":120,"invoiceQuantity":120}', recipientEmail: 'collector@example.com',
    }],
    ['payment_misapplication', {
      caseId: 'AR-PAY-20260813-ABCDEF12', customerName: 'Summit Medical Distribution', customerAccountId: 'SUMMIT-4402',
      invoiceNumber: 'INV-30915', outstandingBalance: 36800,
      customerReason: 'We paid this invoice, but the balance is still open.', openedDate: '2026-07-14',
      evidence: '{"reportedPaymentAmount":36800,"paymentReference":"PAY-77821"}', recipientEmail: 'collector@example.com',
    }],
  ] as const)('reproduces the %s shell-script payload', (scenarioId, expected) => {
    expect(buildDisputePayload({ scenarioId, recipientEmail: ' collector@example.com ' }, now, uuid)).toEqual(expected)
  })

  it('generates a fresh case ID for each attempt', () => {
    const values = ['11111111-aaaa-bbbb-cccc-dddddddddddd', '22222222-aaaa-bbbb-cccc-dddddddddddd']
    const randomUUID = () => values.shift()!

    expect(buildDisputePayload({ scenarioId: 'po_mismatch', recipientEmail: 'a@b.co' }, now, randomUUID).caseId)
      .toBe('AR-PO-20260813-11111111')
    expect(buildDisputePayload({ scenarioId: 'po_mismatch', recipientEmail: 'a@b.co' }, now, randomUUID).caseId)
      .toBe('AR-PO-20260813-22222222')
  })

  it.each(['', 'not-an-email', 'missing@domain', '@example.com'])('rejects invalid recipient email %j', (recipientEmail) => {
    expect(() => buildDisputePayload({ scenarioId: 'po_mismatch', recipientEmail }, now, uuid))
      .toThrow('Enter a valid recipient email.')
  })
})

describe('isValidRecipientEmail', () => {
  it('accepts a trimmed conventional address', () => {
    expect(isValidRecipientEmail(' collector+demo@example.com ')).toBe(true)
  })
})
