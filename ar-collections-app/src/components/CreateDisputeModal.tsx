import { useEffect, useMemo, useRef, useState } from 'react'

import { DISPUTE_SCENARIOS, isValidRecipientEmail } from '../lib/disputeScenarios'
import type { ScenarioId } from '../lib/disputeScenarios'
import { useWorkspace } from '../workspace'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export function CreateDisputeModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (caseId: string) => void }) {
  const { createDispute } = useWorkspace()
  const [scenarioId, setScenarioId] = useState<ScenarioId>('po_mismatch')
  const [recipientEmail, setRecipientEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [createdCaseId, setCreatedCaseId] = useState('')
  const submittingRef = useRef(false)
  const dialogRef = useRef<HTMLDivElement>(null)
  const emailRef = useRef<HTMLInputElement>(null)
  const returnFocusRef = useRef<HTMLElement | null>(null)
  const scenario = useMemo(() => DISPUTE_SCENARIOS.find((item) => item.id === scenarioId)!, [scenarioId])

  useEffect(() => {
    if (!open) return
    returnFocusRef.current = document.activeElement as HTMLElement | null
    setScenarioId('po_mismatch')
    setRecipientEmail('')
    setSubmitting(false)
    submittingRef.current = false
    setError('')
    setCreatedCaseId('')
    requestAnimationFrame(() => emailRef.current?.focus())
    return () => returnFocusRef.current?.focus()
  }, [open])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !submittingRef.current) onClose()
      if (event.key !== 'Tab') return
      const focusable = [...(dialogRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled)') ?? [])]
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable.at(-1)!
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose, open])

  if (!open) return null

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (submittingRef.current) return
    if (!isValidRecipientEmail(recipientEmail)) { setError('Enter a valid recipient email.'); return }
    submittingRef.current = true
    setSubmitting(true)
    setError('')
    try {
      const record = await createDispute({ scenarioId, recipientEmail })
      setCreatedCaseId(record.caseId)
      onCreated(record.caseId)
    } catch {
      setError('The dispute could not be created. Check your access and try again.')
    } finally {
      submittingRef.current = false
      setSubmitting(false)
    }
  }

  return <div className="modal-overlay">
    <div ref={dialogRef} className="modal" role="dialog" aria-modal="true" aria-labelledby="create-dispute-title" aria-describedby="create-dispute-description">
      <div className="modal-head"><div><div className="eyebrow">New Flow trigger</div><h2 id="create-dispute-title">Create dispute</h2><p id="create-dispute-description" className="subtle">Create a fictional Data Fabric case to start the AR resolution Flow.</p></div></div>
      {createdCaseId ? <div className="modal-success" role="status"><strong>Dispute record created</strong><span>Case {createdCaseId} was submitted. The Flow will appear after the record-created trigger is processed.</span></div> : <form noValidate onSubmit={(event) => void submit(event)}>
        <label className="field-label" htmlFor="scenario">Scenario</label>
        <select id="scenario" className="field-control" required value={scenarioId} disabled={submitting} onChange={(event) => setScenarioId(event.target.value as ScenarioId)}>{DISPUTE_SCENARIOS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select>
        <p className="field-help">{scenario.description}</p>
        <label className="field-label" htmlFor="recipient-email">Recipient email</label>
        <input ref={emailRef} id="recipient-email" className="field-control" type="email" required autoComplete="email" placeholder="collector@example.com" value={recipientEmail} disabled={submitting} aria-invalid={error ? true : undefined} aria-describedby={`recipient-email-help${error ? ' recipient-email-error' : ''}`} onChange={(event) => setRecipientEmail(event.target.value)} />
        <p id="recipient-email-help" className="field-help">The approved Flow path prepares its message for this address.</p>
        <section className="scenario-preview" aria-label="Scenario preview"><h3>Record preview</h3><div className="preview-grid"><Preview label="Customer" value={scenario.customerName} /><Preview label="Account" value={scenario.customerAccountId} /><Preview label="Invoice" value={scenario.invoiceNumber} /><Preview label="Balance" value={money.format(scenario.outstandingBalance)} /><Preview label="Opened" value={scenario.openedDate} /><Preview label="Reason" value={scenario.customerReason} /><Preview label="Evidence" value={scenario.evidenceSummary} /></div></section>
        {error && <div id="recipient-email-error" className="modal-error" role="alert">{error}</div>}
        <div className="modal-actions"><button type="button" className="button" disabled={submitting} onClick={onClose}>Cancel</button><button type="submit" className="button primary" disabled={submitting}>{submitting ? 'Creating dispute' : 'Create dispute'}</button></div>
      </form>}
      {createdCaseId && <div className="modal-actions"><button type="button" className="button primary" onClick={onClose}>Close</button></div>}
    </div>
  </div>
}

function Preview({ label, value }: { label: string; value: string }) {
  return <div className="preview-item"><span>{label}</span><strong>{value}</strong></div>
}
