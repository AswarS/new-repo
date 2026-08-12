/**
 * QueryEngine factory for the WebSocket API server.
 *
 * Creates a QueryEngine instance with auto-approve permissions,
 * reusing the project's existing tool/command/state infrastructure.
 */

import { randomUUID } from 'crypto'
import { getCommands } from '../commands.js'
import { QueryEngine, type QueryEngineConfig } from '../QueryEngine.js'
import { getDefaultAppState } from '../state/AppStateStore.js'
import { getEmptyToolPermissionContext } from '../Tool.js'
import type { ToolPermissionContext } from '../Tool.js'
import { getTools } from '../tools.js'
import type { CanUseToolFn } from '../hooks/useCanUseTool.js'
import { createAbortController } from '../utils/abortController.js'
import { cloneFileStateCache, type FileStateCache } from '../utils/fileStateCache.js'
import { getCwd } from '../utils/cwd.js'
import type { AppState } from '../state/AppStateStore.js'

/** Auto-approve all tool calls — no human confirmation needed. */
const autoApproveCanUseTool: CanUseToolFn = async () => ({
  behavior: 'allow' as const,
})

export type SessionEngine = {
  engine: QueryEngine
  getAppState: () => AppState
  setAppState: (f: (prev: AppState) => AppState) => void
  abortController: AbortController
}

/**
 * Create a fresh QueryEngine for a new session.
 * Each session gets its own state, abort controller, and file cache.
 *
 * @param cwd - Working directory for the session
 * @param allowedTools - Optional list of tool names to allow. If provided,
 *   only tools whose name matches an entry in this list will be available.
 */
export async function createSessionEngine(
  cwd?: string,
  allowedTools?: string[],
): Promise<SessionEngine> {
  const workingDir = cwd ?? getCwd()

  // Build permission context: bypassPermissions mode, no deny rules
  const permissionContext: ToolPermissionContext = {
    ...getEmptyToolPermissionContext(),
    mode: 'bypassPermissions',
    isBypassPermissionsModeAvailable: true,
  }

  let tools = getTools(permissionContext)

  // Filter tools if an allow-list is provided
  if (allowedTools && allowedTools.length > 0) {
    const allowed = new Set(allowedTools)
    tools = tools.filter(t => allowed.has(t.name))
  }

  const commands = await getCommands(workingDir)

  // Mutable app state per session
  let appState: AppState = {
    ...getDefaultAppState(),
    toolPermissionContext: permissionContext,
  }

  const getAppState = () => appState
  const setAppState = (f: (prev: AppState) => AppState) => {
    appState = f(appState)
  }

  const abortController = createAbortController()
  const readFileCache: FileStateCache = new Map()

  const config: QueryEngineConfig = {
    cwd: workingDir,
    tools,
    commands,
    mcpClients: [],
    agents: [],
    canUseTool: autoApproveCanUseTool,
    getAppState,
    setAppState,
    readFileCache,
    abortController,
    verbose: false,
    includePartialMessages: true,
  }

  const engine = new QueryEngine(config)

  return { engine, getAppState, setAppState, abortController }
}
