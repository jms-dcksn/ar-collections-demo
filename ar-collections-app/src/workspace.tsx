import { UiPath } from '@uipath/uipath-typescript/core'
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { DataFabricService } from './services/dataFabric'
import { liveDataFabricClient, loadLiveDisputes } from './services/liveWorkspace'
import { mockDisputeRows } from './lib/mockData'
import type { ApprovalDecision, DisputeRow } from './types'

interface WorkspaceContextValue {
  rows: DisputeRow[]
  authenticated: boolean
  loading: boolean
  notice?: string
  login: () => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
  submitDecision: (row: DisputeRow, decision: ApprovalDecision, comments: string) => Promise<void>
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const sdk = useMemo(() => new UiPath(), [])
  const [rows, setRows] = useState<DisputeRow[]>(mockDisputeRows)
  const [authenticated, setAuthenticated] = useState(false)
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState<string | undefined>('Showing fictional cases because no correlated Data Fabric records are currently available.')

  const refresh = useCallback(async () => {
    if (!sdk.isAuthenticated()) return
    setLoading(true)
    try {
      const liveRows = await loadLiveDisputes(sdk)
      if (liveRows.length) { setRows(liveRows); setNotice(undefined) }
      else { setRows(mockDisputeRows); setNotice('No active Flow instance has a correlated case ID. Showing fictional preview cases instead.') }
    } catch (error) {
      setRows(mockDisputeRows)
      setNotice(error instanceof Error ? `${error.message} Showing fictional preview cases instead.` : 'Live data could not be loaded. Showing fictional preview cases instead.')
    } finally { setLoading(false) }
  }, [sdk])

  useEffect(() => {
    if (sdk.isInOAuthCallback()) {
      void sdk.completeOAuth().then((signedIn) => { setAuthenticated(signedIn) })
    } else { setAuthenticated(sdk.isAuthenticated()) }
  }, [refresh, sdk])

  useEffect(() => { if (authenticated) void refresh() }, [authenticated, refresh])
  useEffect(() => () => sdk.destroy(), [sdk])

  const login = useCallback(async () => { await sdk.initialize(); setAuthenticated(sdk.isAuthenticated()) }, [sdk])
  const logout = useCallback(() => { sdk.logout(); setAuthenticated(false); setRows(mockDisputeRows); setNotice('You are signed out. Showing fictional preview cases.') }, [sdk])
  const submitDecision = useCallback(async (row: DisputeRow, decision: ApprovalDecision, comments: string) => {
    if (row.source === 'mock') return
    const updated = await new DataFabricService(liveDataFabricClient(sdk)).recordDecision(row.record, decision, comments)
    setRows((current) => current.map((candidate) => candidate.record.Id === row.record.Id ? { ...candidate, record: { ...candidate.record, ...updated } } : candidate))
  }, [sdk])

  return <WorkspaceContext.Provider value={{ rows, authenticated, loading, notice, login, logout, refresh, submitDecision }}>{children}</WorkspaceContext.Provider>
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext)
  if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider')
  return value
}
