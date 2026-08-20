import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApprovalCard } from './ApprovalCard'

describe('ApprovalCard', () => {
  afterEach(cleanup)

  it('keeps demo data read-only even when it awaits approval', () => {
    render(<ApprovalCard lifecycleState="awaiting_approval" isMock isSubmitting={false} onSubmit={vi.fn()} />)
    expect(screen.getByText(/Demo data cannot update a Flow/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Approve resolution' }).hasAttribute('disabled')).toBe(true)
  })

  it('submits a live approved decision with comments', () => {
    const onSubmit = vi.fn()
    render(<ApprovalCard lifecycleState="awaiting_approval" isMock={false} isSubmitting={false} onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText('Comments'), { target: { value: 'Evidence confirmed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Approve resolution' }))
    expect(onSubmit).toHaveBeenCalledWith('approved', 'Evidence confirmed')
  })
})
