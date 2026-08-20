import { useState } from 'react'

import { canDecide } from '../config'
import type { ApprovalDecision } from '../types'

export function ApprovalCard({ lifecycleState, isMock, isSubmitting, onSubmit }: { lifecycleState?: string; isMock: boolean; isSubmitting: boolean; onSubmit: (decision: ApprovalDecision, comments: string) => void }) {
  const [comments, setComments] = useState('')
  const isEligible = canDecide(lifecycleState)
  const disabled = !isEligible || isMock || isSubmitting
  return <section className="card section approval" aria-label="Collector decision">
    <p className="eyebrow">Collector checkpoint</p>
    <h2 className="approval-title">Resolution decision</h2>
    {isMock ? <p className="approval-copy">Demo data cannot update a Flow. Connect a correlated live record to submit a decision.</p> : isEligible ? <p className="approval-copy">A decision updates Data Fabric and advances the linked Flow event lifecycle.</p> : <p className="approval-copy">This case is not currently at an approval checkpoint.</p>}
    <label className="kv-key" htmlFor="comments">Comments</label>
    <textarea id="comments" className="textarea" value={comments} onChange={(event) => setComments(event.target.value)} placeholder="Optional decision rationale" disabled={disabled} />
    <div className="actions"><button className="button primary" disabled={disabled} onClick={() => onSubmit('approved', comments)}>Approve resolution</button><button className="button danger" disabled={disabled} onClick={() => onSubmit('rejected', comments)}>Reject</button></div>
  </section>
}
