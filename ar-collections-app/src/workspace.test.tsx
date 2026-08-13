import { act, render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WorkspaceProvider, useWorkspace } from './workspace'

const mocks = vi.hoisted(() => ({
  authenticated: false,
  createDispute: vi.fn(),
  destroy: vi.fn(),
}))

vi.mock('@uipath/uipath-typescript/core', () => ({
  UiPath: class {
    isAuthenticated = () => mocks.authenticated
    isInOAuthCallback = () => false
    initialize = vi.fn()
    logout = vi.fn()
    destroy = mocks.destroy
  },
}))

vi.mock('./services/dataFabric', () => ({
  DataFabricService: class { createDispute = mocks.createDispute },
}))

vi.mock('./services/liveWorkspace', () => ({
  liveDataFabricClient: vi.fn(() => ({})),
  loadLiveDisputes: vi.fn().mockResolvedValue([]),
}))

let workspace: ReturnType<typeof useWorkspace>

function Capture({ children }: { children?: ReactNode }) {
  workspace = useWorkspace()
  return children
}

describe('WorkspaceProvider dispute creation', () => {
  beforeEach(() => {
    mocks.authenticated = false
    mocks.createDispute.mockReset()
  })

  it('rejects record creation when the SDK session is signed out', async () => {
    render(<WorkspaceProvider><Capture /></WorkspaceProvider>)

    await expect(workspace.createDispute({ scenarioId: 'po_mismatch', recipientEmail: 'collector@example.com' }))
      .rejects.toThrow('Sign in to create a dispute.')
    expect(mocks.createDispute).not.toHaveBeenCalled()
  })

  it('delegates record creation through the authenticated Data Fabric service', async () => {
    mocks.authenticated = true
    mocks.createDispute.mockResolvedValue({ Id: 'record-1', caseId: 'CASE-001' })
    render(<WorkspaceProvider><Capture /></WorkspaceProvider>)
    await waitFor(() => expect(workspace.authenticated).toBe(true))

    await act(async () => {
      await workspace.createDispute({ scenarioId: 'missing_pod', recipientEmail: 'collector@example.com' })
    })

    expect(mocks.createDispute).toHaveBeenCalledWith({ scenarioId: 'missing_pod', recipientEmail: 'collector@example.com' })
  })
})
