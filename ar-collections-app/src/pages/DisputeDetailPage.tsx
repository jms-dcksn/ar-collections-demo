import { ArrowLeft, CheckCircle2, CircleDot, FileSearch } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { caseLabel, lifecycleLabel, maestroInstanceIdOf } from '../config'
import { mockDisputeRows } from '../lib/mockData'
import { ApprovalCard } from '../components/ApprovalCard'
import { useWorkspace } from '../workspace'
import type { ApprovalDecision, FlowVariable } from '../types'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 })
function Field({ label, value }: { label: string; value?: string | number | boolean }) { return <div className="kv-item"><span className="kv-key">{label}</span><span className="kv-value">{value === undefined || value === '' ? '—' : String(value)}</span></div> }
function Section({ title, children }: { title: string; children: ReactNode }) { return <section className="card section"><h2>{title}</h2><div className="kv">{children}</div></section> }

// Flow globals come back as name/type/source/value metadata, so they render as a table rather
// than a JSON dump. Values that are objects arrive pre-formatted from loadInstanceVariables.
function FlowData({ instanceId, variables, loading, error }: { instanceId?: string; variables: FlowVariable[]; loading: boolean; error?: string }) {
  return <section className="card section"><h2>Flow data</h2>{
    !instanceId ? <p className="subtle">No Maestro instance ID is on this record yet. The Flow writes its instance ID to the case ID field once the instance is running.</p>
      : loading ? <p className="subtle">Reading Flow variables…</p>
      : error ? <p className="subtle">{error}</p>
      : variables.length === 0 ? <p className="subtle">This instance exposes no global variables yet.</p>
      : <div className="table-wrap"><table><thead><tr><th>Variable</th><th>Value</th><th>Type</th><th>Set by</th></tr></thead><tbody>{variables.map((variable) => <tr key={variable.id}><td>{variable.name}</td><td className="kv-value" style={{ maxWidth: 420 }}>{variable.value || '—'}</td><td><span className="badge neutral">{variable.type}</span></td><td>{variable.source}</td></tr>)}</tbody></table></div>
  }</section>
}

// The route carries the Data Fabric record Id — the only stable correlation key. The Maestro
// instance ID arrives later on caseId and would change the URL mid-flight.
export function DisputeDetailPage({ recordId }: { recordId?: string }) {
  const { rows, instanceVariables, submitDecision } = useWorkspace()
  const [submitting, setSubmitting] = useState(false)
  const [decisionMessage, setDecisionMessage] = useState<string | undefined>()
  const row = rows.find((candidate) => candidate.record.Id === recordId) ?? rows[0] ?? mockDisputeRows[0]
  const { record, instance } = row
  const maestroInstanceId = row.source === 'live' && instance.instanceSource === 'maestro' ? maestroInstanceIdOf(record.caseId) : undefined
  const [variables, setVariables] = useState<FlowVariable[]>([])
  const [variablesLoading, setVariablesLoading] = useState(false)
  const [variablesError, setVariablesError] = useState<string | undefined>()
  useEffect(() => {
    if (!maestroInstanceId) { setVariables([]); setVariablesError(undefined); return }
    let current = true
    setVariablesLoading(true); setVariablesError(undefined)
    instanceVariables(maestroInstanceId)
      .then((next) => { if (current) setVariables(next) })
      .catch((error) => { if (current) setVariablesError(error instanceof Error ? error.message : 'Flow variables could not be read.') })
      .finally(() => { if (current) setVariablesLoading(false) })
    return () => { current = false }
  }, [instanceVariables, maestroInstanceId])
  let evidence: Record<string, unknown> = {}
  try { evidence = JSON.parse(record.evidence) as Record<string, unknown> } catch { evidence = {} }
  const isMock = row.source === 'mock'
  const submit = async (decision: ApprovalDecision, comments: string) => {
    setSubmitting(true); setDecisionMessage(undefined)
    try { await submitDecision(row, decision, comments); setDecisionMessage(`${lifecycleLabel(decision)} decision saved to Data Fabric.`) }
    catch (error) { setDecisionMessage(error instanceof Error ? error.message : 'The decision could not be saved. Please try again.') }
    finally { setSubmitting(false) }
  }
  return <div className="page"><a href="#/disputes" className="case-link"><ArrowLeft size={15} style={{ verticalAlign: '-2px' }} /> Back to disputes</a><div className="hero" style={{ marginTop: 18 }}><div><div className="eyebrow">{isMock ? 'Demo data preview' : 'Correlated live record'}</div><h1 className="page-title">{caseLabel(record.caseId, record.invoiceNumber)} · {record.customerName}</h1><p className="subtle">{record.invoiceNumber} · {money.format(record.outstandingBalance)} disputed balance</p></div><span className="badge awaiting">{lifecycleLabel(record.lifecycleState)}</span></div>{isMock && <div className="notice"><FileSearch size={19} /><span><strong>Read-only visual preview</strong><br />This fictional record demonstrates the live review experience. Approval actions activate only for a correlated Data Fabric record.</span></div>}<div className="detail-grid"><div className="stack"><Section title="Case summary"><Field label="Customer account" value={record.customerAccountId} /><Field label="Opened" value={record.openedDate} /><Field label="Customer reason" value={record.customerReason} /><Field label="Dispute type" value={record.disputeType?.replaceAll('_', ' ')} /></Section><Section title="Resolution context"><Field label="Triage rationale" value={record.triageRationale} /><Field label="Evidence summary" value={record.evidenceSummary} /><Field label="Root cause" value={record.rootCause} /><Field label="Recommendation" value={record.recommendedAction} /><Field label="Action code" value={record.actionCode} /><Field label="Adjustment amount" value={money.format(record.adjustmentAmount ?? 0)} /></Section><Section title="Evidence"><Field label="Triage confidence" value={`${Math.round((record.triageConfidence ?? 0) * 100)}%`} />{Object.entries(evidence).map(([key, value]) => <Field key={key} label={key.replaceAll(/([A-Z])/g, ' $1')} value={typeof value === 'string' || typeof value === 'number' ? value : 'Available'} />)}</Section><Section title="Flow monitor"><Field label="Instance ID" value={maestroInstanceId} /><Field label="Instance" value={instance.instanceDisplayName} /><Field label="Run status" value={instance.latestRunStatus} /><Field label="Started" value={instance.startedTime ? new Date(instance.startedTime).toLocaleString() : undefined} /><Field label="Completed" value={instance.completedTime ? new Date(instance.completedTime).toLocaleString() : 'Still running'} /><Field label="Package version" value={instance.packageVersion} /><Field label="Started by" value={instance.startedByUser} /><Field label="Instance data" value={instance.instanceSource === 'maestro' ? 'Live Maestro instance' : 'Derived from the Data Fabric record'} /><Field label="Correlation" value={isMock ? 'Demo fixture — no live record mutation' : 'Data Fabric record is the system of record'} /></Section><Section title="Audit"><Field label="Update result" value={record.updateResult} /><Field label="Email sent" value={record.emailSent ? 'Yes' : 'No'} /><Field label="Audit summary" value={record.auditSummary} /></Section><FlowData instanceId={maestroInstanceId} variables={variables} loading={variablesLoading} error={variablesError} /></div><div className="stack"><ApprovalCard lifecycleState={record.lifecycleState} isMock={isMock} isSubmitting={submitting} onSubmit={(decision, comments) => void submit(decision, comments)} />{decisionMessage && <p className="decision-message" role="status">{decisionMessage}</p>}<section className="card section"><h2>Decision path</h2><p className="subtle"><CircleDot size={16} style={{ verticalAlign: '-3px', color: '#4f46e5' }} /> Recommendation prepared</p><p className="subtle"><CheckCircle2 size={16} style={{ verticalAlign: '-3px', color: '#c28a00' }} /> Collector approval pending</p><p className="subtle">Data Fabric becomes the decision record and triggers the next Flow event.</p></section></div></div></div>
}
