import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DashboardPage } from './DashboardPage'

const workspace = vi.hoisted(() => ({
  rows: [], authenticated: false, loading: false, notice: undefined,
  refresh: vi.fn(), createDispute: vi.fn(),
}))

vi.mock('../workspace', () => ({ useWorkspace: () => workspace }))

describe('DashboardPage dispute creation', () => {
  beforeEach(() => {
    workspace.authenticated = false
    workspace.refresh.mockReset().mockResolvedValue(undefined)
    workspace.createDispute.mockReset()
  })
  afterEach(cleanup)

  it('keeps the creation action disabled until the user signs in', () => {
    render(<DashboardPage />)
    expect((screen.getByRole('button', { name: 'Create dispute' }) as HTMLButtonElement).disabled).toBe(true)
  })

  it('opens the modal for an authenticated user', async () => {
    workspace.authenticated = true
    const user = userEvent.setup()
    render(<DashboardPage />)
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))
    expect(screen.getByRole('dialog')).toBeTruthy()
  })

  it('refreshes the workspace once after a record is created', async () => {
    workspace.authenticated = true
    workspace.createDispute.mockResolvedValue({ Id: 'record-1', caseId: 'AR-PO-20260813-ABCDEF12' })
    const user = userEvent.setup()
    render(<DashboardPage />)
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))
    await user.type(screen.getByLabelText('Recipient email'), 'collector@example.com')
    await user.click(screen.getAllByRole('button', { name: 'Create dispute' }).at(-1)!)

    await waitFor(() => expect(workspace.refresh).toHaveBeenCalledTimes(1))
    expect(screen.getByRole('status').textContent).toContain('AR-PO-20260813-ABCDEF12')
  })
})
