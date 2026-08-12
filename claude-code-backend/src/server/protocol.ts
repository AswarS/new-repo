/**
 * WebSocket API message protocol types.
 *
 * Client → Server: user_message, abort
 * Server → Client: assistant, result, error
 */

// ============================================================================
// Client → Server
// ============================================================================

export type ClientUserMessage = {
  type: 'user_message'
  content: string
  id?: string
}

export type ClientAbortMessage = {
  type: 'abort'
}

export type ClientMessage = ClientUserMessage | ClientAbortMessage

// ============================================================================
// Server → Client
// ============================================================================

export type ServerAssistantMessage = {
  type: 'assistant'
  message: Record<string, unknown>
}

export type ServerResultMessage = {
  type: 'result'
  message: Record<string, unknown>
  usage?: Record<string, unknown>
}

export type ServerErrorMessage = {
  type: 'error'
  error: string
}

export type ServerPreviewMessage = {
  type: 'preview'
  previewType: 'file' | 'dev_server'
  url: string
}

export type ServerStreamMessage = {
  type: 'stream'
  event: Record<string, unknown>
}

export type ServerMessage =
  | ServerAssistantMessage
  | ServerResultMessage
  | ServerErrorMessage
  | ServerPreviewMessage
  | ServerStreamMessage

// ============================================================================
// HTTP REST API types
// ============================================================================

export type HttpAgentRequest = {
  prompt: string
  cwd?: string
}

export type HttpAgentResponse = {
  messages: Record<string, unknown>[]
  result: { type: string }
}

export type HttpCreateSessionRequest = {
  cwd?: string
}

export type HttpCreateSessionResponse = {
  session_id: string
  status: string
}

export type HttpSessionMessageRequest = {
  content: string
}

export type HttpSessionListResponse = {
  sessions: Array<{
    id: string
    createdAt: number
    lastActiveAt: number
    busy: boolean
    cwd?: string
  }>
}

export type HttpErrorResponse = {
  error: string
}

// ============================================================================
// Helpers
// ============================================================================

export function parseClientMessage(raw: string): ClientMessage | null {
  try {
    const parsed = JSON.parse(raw)
    if (parsed?.type === 'user_message' && typeof parsed.content === 'string') {
      return parsed as ClientUserMessage
    }
    if (parsed?.type === 'abort') {
      return parsed as ClientAbortMessage
    }
    return null
  } catch {
    return null
  }
}
