import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DisputeDetailPage } from './DisputeDetailPage'
import type { DisputeRow } from '../types'

const INSTANCE_ID = '4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10'

const workspace = vi.hoisted(() => ({
  rows: [] as DisputeRow[], instanceVariables: vi.fn(), submitDecision: vi.fn(),
}))

vi.mock('../workspace', () => ({ useWorkspace: () => workspace }))

function row(overrides: Partial<DisputeRow['instance']>, caseId: string): DisputeRow {
  return {
    instance: {
      instanceId: INSTANCE_ID, instanceDisplayName: 'ARCollectionsDisputeResolution', latestRunStatus: 'Paused',
      startedTime: '2026-08-20T09:00:00Z', completedTime: null, folderKey: 'folder', instanceSource: 'maestro',
      packageVersion: '1.0.4', ...overrides,
    },
    record: {
      Id: 'record-1', caseId, customerName: 'Fabrikam Components', customerAccountId: 'CUS-9063',
      invoiceNumber: 'INV-18204', outstandingBalance: 7420, customerReason: 'Amount differs from the purchase order.',
      openedDate: '2026-08-13', evidence: '{}', lifecycleState: 'awaiting_approval',
    },
    source: 'live',
    correlation: 'matched',
  }
}

describe('DisputeDetailPage Flow monitor', () => {
  beforeEach(() => {
    workspace.instanceVariables.mockReset().mockResolvedValue([
      { id: 'v1', name: 'status', type: 'string', source: 'normalizeProposal', value: 'awaiting_approval' },
    ])
    workspace.submitDecision.mockReset()
  })
  afterEach(cleanup)

  it('reads Flow variables with the instance ID stored on caseId', async () => {
    workspace.rows = [row({}, INSTANCE_ID)]
    render(<DisputeDetailPage recordId="record-1" />)

    await waitFor(() => expect(workspace.instanceVariables).toHaveBeenCalledWith(INSTANCE_ID))
    expect(screen.getByText('Live Maestro instance')).toBeTruthy()
    expect(screen.getByText('Paused')).toBeTruthy()
    expect(screen.getByText('1.0.4')).toBeTruthy()
    expect(await screen.findByText('awaiting_approval')).toBeTruthy()
  })

  it('asks for nothing while the record carries only a business case ID', async () => {
    workspace.rows = [row({ instanceSource: 'derived', instanceId: 'record-1' }, 'AR-PO-20260813-ABCDEF12')]
    render(<DisputeDetailPage recordId="record-1" />)

    expect(workspace.instanceVariables).not.toHaveBeenCalled()
    expect(screen.getByText(/No Maestro instance ID is on this record yet/)).toBeTruthy()
  })

  it('reports a variables read that fails instead of blanking the page', async () => {
    workspace.rows = [row({}, INSTANCE_ID)]
    workspace.instanceVariables.mockRejectedValue(new Error('PIMS returned 403.'))
    render(<DisputeDetailPage recordId="record-1" />)

    expect(await screen.findByText('PIMS returned 403.')).toBeTruthy()
  })
})
