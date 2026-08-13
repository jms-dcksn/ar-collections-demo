import { ArrowLeft, CheckCircle2, CircleDot, FileSearch } from 'lucide-react'
import { useState } from 'react'
import type { ReactNode } from 'react'

import { mockDisputeRows } from '../lib/mockData'
import { ApprovalCard } from '../components/ApprovalCard'
import { useWorkspace } from '../workspace'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
function Field({ label, value }: { label: string; value?: string | number | boolean }) { return <div className="kv-item"><span className="kv-key">{label}</span><span className="kv-value">{value === undefined || value === '' ? '—' : String(value)}</span></div> }
function Section({ title, children }: { title: string; children: ReactNode }) { return <section className="card section"><h2>{title}</h2><div className="kv">{children}</div></section> }

export function DisputeDetailPage({ instanceId }: { instanceId?: string }) {
  const { rows, submitDecision } = useWorkspace()
  const [submitting, setSubmitting] = useState(false)
  const [decisionMessage, setDecisionMessage] = useState<string | undefined>()
  const row = rows.find((candidate) => candidate.instance.instanceId === instanceId) ?? rows[0] ?? mockDisputeRows[0]
  const { record, instance } = row
  let evidence: Record<string, unknown> = {}
  try { evidence = JSON.parse(record.evidence) as Record<string, unknown> } catch { evidence = {} }
  const isMock = row.source === 'mock'
  const submit = async (decision: 'Approved' | 'Rejected', comments: string) => {
    setSubmitting(true); setDecisionMessage(undefined)
    try { await submitDecision(row, decision, comments); setDecisionMessage(`${decision} decision saved to Data Fabric.`) }
    catch (error) { setDecisionMessage(error instanceof Error ? error.message : 'The decision could not be saved. Please try again.') }
    finally { setSubmitting(false) }
  }
  return <div className="page"><a href="#/disputes" className="case-link"><ArrowLeft size={15} style={{ verticalAlign: '-2px' }} /> Back to disputes</a><div className="hero" style={{ marginTop: 18 }}><div><div className="eyebrow">{isMock ? 'Demo data preview' : 'Correlated live record'}</div><h1 className="page-title">{record.caseId} · {record.customerName}</h1><p className="subtle">{record.invoiceNumber} · {money.format(record.outstandingBalance)} disputed balance</p></div><span className="badge awaiting">{record.lifecycleState}</span></div>{isMock && <div className="notice"><FileSearch size={19} /><span><strong>Read-only visual preview</strong><br />This fictional record demonstrates the live review experience. Approval actions activate only for a correlated Data Fabric record.</span></div>}<div className="detail-grid"><div className="stack"><Section title="Case summary"><Field label="Customer account" value={record.customerAccountId} /><Field label="Opened" value={record.openedDate} /><Field label="Customer reason" value={record.customerReason} /><Field label="Dispute type" value={record.disputeType?.replaceAll('_', ' ')} /></Section><Section title="Resolution context"><Field label="Triage rationale" value={record.triageRationale} /><Field label="Evidence summary" value={record.evidenceSummary} /><Field label="Root cause" value={record.rootCause} /><Field label="Recommendation" value={record.recommendedAction} /><Field label="Action code" value={record.actionCode} /><Field label="Adjustment amount" value={money.format(record.adjustmentAmount ?? 0)} /></Section><Section title="Evidence"><Field label="Triage confidence" value={`${Math.round((record.triageConfidence ?? 0) * 100)}%`} />{Object.entries(evidence).map(([key, value]) => <Field key={key} label={key.replaceAll(/([A-Z])/g, ' $1')} value={typeof value === 'string' || typeof value === 'number' ? value : 'Available'} />)}</Section><Section title="Flow monitor"><Field label="Instance" value={instance.instanceDisplayName} /><Field label="Run status" value={instance.latestRunStatus} /><Field label="Started" value={new Date(instance.startedTime).toLocaleString()} /><Field label="Correlation" value={isMock ? 'Demo fixture — no live record mutation' : 'caseId matched to Data Fabric'} /></Section><Section title="Audit"><Field label="Update result" value={record.updateResult} /><Field label="Email sent" value={record.emailSent ? 'Yes' : 'No'} /><Field label="Audit summary" value={record.auditSummary} /></Section></div><div className="stack"><ApprovalCard lifecycleState={record.lifecycleState} isMock={isMock} isSubmitting={submitting} onSubmit={(decision, comments) => void submit(decision, comments)} />{decisionMessage && <p className="decision-message" role="status">{decisionMessage}</p>}<section className="card section"><h2>Decision path</h2><p className="subtle"><CircleDot size={16} style={{ verticalAlign: '-3px', color: '#4f46e5' }} /> Recommendation prepared</p><p className="subtle"><CheckCircle2 size={16} style={{ verticalAlign: '-3px', color: '#c28a00' }} /> Collector approval pending</p><p className="subtle">Data Fabric becomes the decision record and triggers the next Flow event.</p></section></div></div></div>
}
