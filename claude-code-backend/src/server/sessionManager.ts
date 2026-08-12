/**
 * Session manager for the WebSocket API server.
 *
 * Each WebSocket connection maps to one Session with its own QueryEngine.
 * Supports multi-turn conversations and concurrent sessions.
 */

import { randomUUID } from 'crypto'
import type { ServerWebSocket } from 'bun'
import { createSessionEngine, type SessionEngine } from './engineFactory.js'
import { parseClientMessage, type ServerMessage } from './protocol.js'
import { createArtifactTracker, type ArtifactTracker } from './artifactDetector.js'

export type Session = {
  id: string
  engine: SessionEngine
  /** True while the engine is processing a prompt. */
  busy: boolean
  /** Tracks web artifact file writes for preview URL detection. */
  artifactTracker: ArtifactTracker
}

const sessions = new Map<ServerWebSocket<{ sessionId: string }>, Session>()

function send(ws: ServerWebSocket<{ sessionId: string }>, msg: ServerMessage) {
  try {
    ws.send(JSON.stringify(msg))
  } catch {
    // connection already closed
  }
}

export async function handleOpen(
  ws: ServerWebSocket<{ sessionId: string }>,
  cwd?: string,
) {
  const id = ws.data.sessionId
  try {
    const engine = await createSessionEngine(cwd)
    const artifactTracker = createArtifactTracker()
    sessions.set(ws, { id, engine, busy: false, artifactTracker })
    send(ws, {
      type: 'result',
      message: { type: 'session_started', sessionId: id },
    })
  } catch (err) {
    send(ws, {
      type: 'error',
      error: `Failed to initialize session: ${err instanceof Error ? err.message : String(err)}`,
    })
    ws.close()
  }
}

export async function handleMessage(
  ws: ServerWebSocket<{ sessionId: string }>,
  raw: string,
) {
  const session = sessions.get(ws)
  if (!session) {
    send(ws, { type: 'error', error: 'Session not found' })
    return
  }

  const msg = parseClientMessage(raw)
  if (!msg) {
    send(ws, { type: 'error', error: 'Invalid message format' })
    return
  }

  if (msg.type === 'abort') {
    session.engine.abortController.abort()
    send(ws, { type: 'result', message: { type: 'aborted' } })
    return
  }

  // user_message
  if (session.busy) {
    send(ws, {
      type: 'error',
      error: 'Session is busy processing a previous message. Send "abort" first.',
    })
    return
  }

  session.busy = true
  console.log(`\n[WS IN] session=${session.id} content=${msg.content.slice(0, 200)}...`)
  try {
    const generator = session.engine.engine.submitMessage(msg.content)
    let msgCount = 0
    for await (const sdkMessage of generator) {
      const msgRecord = sdkMessage as Record<string, unknown>
      msgCount++
      // Log first 5 messages and any non-stream messages
      if (msgCount <= 5 || msgRecord.type !== 'stream_event') {
        console.log(`[WS OUT] session=${session.id} msg#${msgCount} type=${msgRecord.type} keys=${Object.keys(msgRecord).join(',')} preview=${JSON.stringify(msgRecord).slice(0, 500)}`)
      }
      if (msgRecord.type === 'result') {
        console.log(`[WS RESULT FULL] session=${session.id}`, JSON.stringify(msgRecord, null, 2).slice(0, 2000))
      }
      // Feed each message into the artifact tracker
      session.artifactTracker.inspect(msgRecord)

      // Forward stream events as a dedicated 'stream' message type
      // so the frontend can render text deltas in real time.
      if (msgRecord.type === 'stream_event') {
        send(ws, { type: 'stream', event: msgRecord.event as Record<string, unknown> })
      } else {
        send(ws, { type: 'assistant', message: msgRecord })
      }
    }
    console.log(`[WS DONE] session=${session.id} total_messages=${msgCount}`)

    // After the turn completes, check for web artifacts (HTML files, npm projects)
    try {
      const artifacts = await session.artifactTracker.resolve()
      for (const artifact of artifacts) {
        send(ws, {
          type: 'preview',
          previewType: artifact.type === 'file' ? 'file' : 'dev_server',
          url: artifact.url,
        })
      }
    } catch {
      // Artifact detection is best-effort, don't fail the turn
    }

    send(ws, { type: 'result', message: { type: 'turn_complete' } })
  } catch (err) {
    console.log(`[WS ERROR] session=${session.id} error=${err instanceof Error ? err.message : String(err)}`)
    send(ws, {
      type: 'error',
      error: err instanceof Error ? err.message : String(err),
    })
  } finally {
    session.busy = false
  }
}

export function handleClose(ws: ServerWebSocket<{ sessionId: string }>) {
  const session = sessions.get(ws)
  if (session) {
    session.engine.abortController.abort()
    session.artifactTracker.cleanup()
    sessions.delete(ws)
  }
}

export function getSessionCount(): number {
  return sessions.size
}
