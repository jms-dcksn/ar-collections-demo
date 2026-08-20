import { describe, expect, it } from 'vitest'

import { ENTITY_ID, PROCESS_KEY, PROCESS_NAME, PROCESS_PACKAGE_ID, SOLUTION_FOLDER_KEY, canDecide, caseLabel, lifecycleLabel, maestroInstanceIdOf } from './config'

describe('AR collections configuration', () => {
  it('pins the deployed platform resources', () => {
    expect(ENTITY_ID).toBe('81a5f874-d79b-f111-9b33-6045bdd6658d')
    expect(SOLUTION_FOLDER_KEY).toBe('ff31878b-35b2-438f-8051-4e1461534d91')
    expect(PROCESS_KEY).toBe('33534c74-5c67-402d-a96f-0f9dc9e156c6')
    expect(PROCESS_PACKAGE_ID).toBe('AR.Collections.Dispute.Flow.flow.ARCollectionsDisputeResolution')
    expect(PROCESS_NAME).toBe('ARCollectionsDisputeResolution')
  })

  it('only enables decisions on the lifecycle value the Flow writes', () => {
    expect(canDecide('awaiting_approval')).toBe(true)
    expect(canDecide('Awaiting approval')).toBe(false)
    expect(canDecide('resolved')).toBe(false)
  })

  it('treats only a GUID on caseId as the Flow-written instance ID', () => {
    expect(maestroInstanceIdOf('4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10')).toBe('4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10')
    expect(maestroInstanceIdOf('AR-PO-20260813-ABCDEF12')).toBeUndefined()
    expect(maestroInstanceIdOf('')).toBeUndefined()
    expect(maestroInstanceIdOf(undefined)).toBeUndefined()
  })

  it('falls back to the invoice number once caseId holds an instance ID', () => {
    expect(caseLabel('AR-PO-20260813-ABCDEF12', 'INV-18204')).toBe('AR-PO-20260813-ABCDEF12')
    expect(caseLabel('4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10', 'INV-18204')).toBe('INV-18204')
    expect(caseLabel('4441ec7a-9f2c-4d1b-8a37-6b5c4d3e2f10', '')).toBe('AR dispute')
  })

  it('renders a stored lifecycle value as prose', () => {
    expect(lifecycleLabel('needs_manual_triage')).toBe('Needs manual triage')
    expect(lifecycleLabel(undefined)).toBe('\u2014')
  })
})
