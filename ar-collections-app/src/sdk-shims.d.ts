declare module '@uipath/uipath-typescript/entities' {
  export class Entities {
    constructor(sdk: unknown)
    getAll(options?: Record<string, unknown>): Promise<Array<{ id: string; fields?: Array<{ name: string }> }>>
    queryRecordsById(entityId: string, options?: Record<string, unknown>): Promise<Array<Record<string, unknown>>>
    updateRecordById(entityId: string, recordId: string, data: Record<string, unknown>): Promise<Record<string, unknown>>
  }
}

declare module '@uipath/uipath-typescript/maestro-processes' {
  export class MaestroProcesses {
    constructor(sdk: unknown)
    getAll(options?: Record<string, unknown>): Promise<Array<Record<string, unknown>>>
  }

  export class ProcessInstances {
    constructor(sdk: unknown)
    getAll(options?: Record<string, unknown>): Promise<{
      items: Array<Record<string, unknown>>
      hasNextPage: boolean
      nextCursor?: { value: string }
    }>
    getVariables(instanceId: string, folderKey: string): Promise<{ globalVariables?: Record<string, unknown> }>
  }
}
