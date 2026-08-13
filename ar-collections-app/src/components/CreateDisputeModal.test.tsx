import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CreateDisputeModal } from './CreateDisputeModal'

const createDispute = vi.fn()

vi.mock('../workspace', () => ({
  useWorkspace: () => ({ createDispute }),
}))

describe('CreateDisputeModal', () => {
  beforeEach(() => createDispute.mockReset())
  afterEach(cleanup)

  it('shows the selected scenario preview and closes while idle', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<CreateDisputeModal open onClose={onClose} onCreated={vi.fn()} />)

    expect(screen.getByRole('dialog').getAttribute('aria-labelledby')).toBe('create-dispute-title')
    expect(screen.getByText('Northstar Manufacturing')).toBeTruthy()
    await user.selectOptions(screen.getByLabelText('Scenario'), 'missing_pod')
    expect(screen.getByText('Riverbend Retail')).toBeTruthy()
    expect(screen.getByText('Delivered 2026-06-18 · Signed by M. Chen · 120 of 120 units')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('validates the recipient before calling Data Fabric', async () => {
    const user = userEvent.setup()
    render(<CreateDisputeModal open onClose={vi.fn()} onCreated={vi.fn()} />)

    await user.type(screen.getByLabelText('Recipient email'), 'invalid')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))

    expect(screen.getByRole('alert').textContent).toContain('Enter a valid recipient email.')
    expect(createDispute).not.toHaveBeenCalled()
  })

  it('blocks duplicate submission and confirms the created case ID', async () => {
    const user = userEvent.setup()
    let resolve!: (value: { Id: string; caseId: string }) => void
    createDispute.mockReturnValue(new Promise((done) => { resolve = done }))
    const onCreated = vi.fn()
    render(<CreateDisputeModal open onClose={vi.fn()} onCreated={onCreated} />)
    await user.type(screen.getByLabelText('Recipient email'), ' collector@example.com ')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))

    expect((screen.getByRole('button', { name: 'Creating dispute' }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: 'Cancel' }) as HTMLButtonElement).disabled).toBe(true)
    expect(createDispute).toHaveBeenCalledTimes(1)

    resolve({ Id: 'record-1', caseId: 'AR-PO-20260813-ABCDEF12' })
    await waitFor(() => expect(screen.getByRole('status').textContent).toContain('AR-PO-20260813-ABCDEF12'))
    expect(onCreated).toHaveBeenCalledWith('AR-PO-20260813-ABCDEF12')
  })

  it('retains input after failure and allows retry', async () => {
    const user = userEvent.setup()
    createDispute.mockRejectedValueOnce(new Error('Data Fabric is unavailable.')).mockResolvedValueOnce({ Id: 'record-2', caseId: 'AR-PAY-20260813-12345678' })
    render(<CreateDisputeModal open onClose={vi.fn()} onCreated={vi.fn()} />)
    await user.selectOptions(screen.getByLabelText('Scenario'), 'payment_misapplication')
    await user.type(screen.getByLabelText('Recipient email'), 'collector@example.com')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))

    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('The dispute could not be created. Check your access and try again.'))
    expect(screen.getByRole('alert').textContent).not.toContain('Data Fabric is unavailable.')
    expect((screen.getByLabelText('Recipient email') as HTMLInputElement).value).toBe('collector@example.com')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))
    await waitFor(() => expect(createDispute).toHaveBeenCalledTimes(2))
  })

  it('closes with Escape only while idle', () => {
    const onClose = vi.fn()
    render(<CreateDisputeModal open onClose={onClose} onCreated={vi.fn()} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('links validation to the recipient field and restores focus after close', async () => {
    const user = userEvent.setup()
    const launcher = document.createElement('button')
    launcher.textContent = 'Launcher'
    document.body.append(launcher)
    launcher.focus()
    const { rerender } = render(<CreateDisputeModal open onClose={vi.fn()} onCreated={vi.fn()} />)
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Recipient email')))
    await user.type(screen.getByLabelText('Recipient email'), 'invalid')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))
    const field = screen.getByLabelText('Recipient email')
    expect(field.getAttribute('aria-invalid')).toBe('true')
    expect(field.getAttribute('aria-describedby')).toContain('recipient-email-error')
    rerender(<CreateDisputeModal open={false} onClose={vi.fn()} onCreated={vi.fn()} />)
    expect(document.activeElement).toBe(launcher)
    launcher.remove()
  })

  it('traps keyboard focus and ignores Escape while creation is pending', async () => {
    const user = userEvent.setup()
    createDispute.mockReturnValue(new Promise(() => undefined))
    const onClose = vi.fn()
    render(<CreateDisputeModal open onClose={onClose} onCreated={vi.fn()} />)
    await user.type(screen.getByLabelText('Recipient email'), 'collector@example.com')
    await user.click(screen.getByRole('button', { name: 'Create dispute' }))
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).not.toHaveBeenCalled()

    cleanup()
    createDispute.mockReset()
    render(<CreateDisputeModal open onClose={onClose} onCreated={vi.fn()} />)
    const first = screen.getByLabelText('Scenario')
    const last = screen.getByRole('button', { name: 'Create dispute' })
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText('Recipient email')))
    last.focus()
    await user.tab()
    expect(document.activeElement).toBe(first)
    await user.tab({ shift: true })
    expect(document.activeElement).toBe(last)
  })
})
