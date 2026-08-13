import { describe, expect, it } from 'vitest'

import { ENTITY_ID, PROCESS_NAME, canDecide } from './config'

describe('AR collections configuration', () => {
  it('only enables decisions at the approved lifecycle stage', () => {
    expect(ENTITY_ID).toBe('bc0fc734-bf94-f111-9b32-000d3ab5d4c4')
    expect(PROCESS_NAME).toBe('ARCollectionsDisputeResolution')
    expect(canDecide('Awaiting approval')).toBe(true)
    expect(canDecide('Resolved')).toBe(false)
  })
})
