/**
 * HTTP REST API route handlers for Claude Code Agent.
 *
 * Provides endpoints for:
 * - One-shot prompt execution (blocking and SSE streaming)
 * - Persistent session management (create/message/destroy/list)
 */

import { createSessionEngine } from './engineFactory.js'
import { HttpSessionStore, type HttpSession } from './httpSessionStore.js'

export type ApiRoutesConfig = {
  /** Bearer token for auth. If undefined, auth is disabled (local dev mode). */
  authToken?: string
  /** Default working directory for sessions. */
  cwd?: string
  /** Idle timeout for sessions in ms. */
  idleTimeoutMs?: number
  /** Maximum concurrent sessions. */
  maxSessions?: number
  /** Maximum concurrent one-shot requests in flight. Default 20. */
  maxConcurrentRequests?: number
}

const DEFAULT_MAX_CONCURRENT = 20

export class ApiRoutes {
  private store: HttpSessionStore
  private authToken: string | undefined
  private defaultCwd: string | undefined
  private maxConcurrent: number
  private activeConcurrent = 0

  constructor(config: ApiRoutesConfig) {
    this.authToken = config.authToken
    this.defaultCwd = config.cwd
    this.maxConcurrent = config.maxConcurrentRequests ?? DEFAULT_MAX_CONCURRENT
    this.store = new HttpSessionStore({
      idleTimeoutMs: config.idleTimeoutMs,
      maxSessions: config.maxSessions,
    })
  }

  /**
   * Main request dispatcher. Returns a Response if the route matches,
   * or null if it should fall through to other handlers.
   */
  async handle(req: Request): Promise<Response | null> {
    const url = new URL(req.url)
    const path = url.pathname

    // Auth check
    if (this.authToken) {
      const authHeader = req.headers.get('authorization')
      const token = authHeader?.startsWith('Bearer ')
        ? authHeader.slice(7)
        : null
      if (token !== this.authToken) {
        return json({ error: 'Unauthorized' }, 401)
      }
    }

    // Route dispatch
    if (req.method === 'POST' && path === '/api/agent') {
      return this.handleOneShot(req)
    }
    if (req.method === 'POST' && path === '/api/agent/stream') {
      return this.handleOneShotStream(req)
    }
    if (req.method === 'POST' && path === '/api/sessions') {
      return this.handleCreateSession(req)
    }
    if (req.method === 'GET' && path === '/api/sessions') {
      return this.handleListSessions()
    }

    // Session-specific routes: /api/sessions/:id/...
    const sessionMatch = path.match(/^\/api\/sessions\/([^/]+)/)
    if (sessionMatch) {
      const sessionId = sessionMatch[1]!
      const subPath = path.slice(`/api/sessions/${sessionId}`.length)

      if (req.method === 'DELETE' && subPath === '') {
        return this.handleDeleteSession(sessionId)
      }
      if (req.method === 'POST' && subPath === '/message') {
        return this.handleSessionMessage(req, sessionId)
      }
      if (req.method === 'POST' && subPath === '/message/stream') {
        return this.handleSessionMessageStream(req, sessionId)
      }
    }

    return null // no match
  }

  // ===========================================================================
  // One-shot endpoints
  // ===========================================================================

  private async handleOneShot(req: Request): Promise<Response> {
    if (this.activeConcurrent >= this.maxConcurrent) {
      return json({ error: 'Too many concurrent requests. Try again later.' }, 429)
    }

    const body = await parseBody(req)
    if (!body?.prompt || typeof body.prompt !== 'string') {
      return json({ error: 'Missing required field: prompt' }, 400)
    }

    this.activeConcurrent++
    const cwd = (body.cwd as string) || this.defaultCwd
    const allowedTools = parseAllowedTools(body.allowedTools)
    let engine
    try {
      engine = await createSessionEngine(cwd, allowedTools)
    } catch (err) {
      this.activeConcurrent--
      return json({ error: `Failed to create engine: ${errMsg(err)}` }, 500)
    }

    const messages: Record<string, unknown>[] = []
    try {
      const generator = engine.engine.submitMessage(body.prompt)
      for await (const sdkMessage of generator) {
        messages.push(sdkMessage as Record<string, unknown>)
      }
      return json({
        messages,
        result: { type: 'turn_complete' },
      })
    } catch (err) {
      return json({ error: errMsg(err), messages }, 500)
    } finally {
      this.activeConcurrent--
      engine.abortController.abort()
    }
  }

  private async handleOneShotStream(req: Request): Promise<Response> {
    if (this.activeConcurrent >= this.maxConcurrent) {
      return json({ error: 'Too many concurrent requests. Try again later.' }, 429)
    }

    const body = await parseBody(req)
    if (!body?.prompt || typeof body.prompt !== 'string') {
      return json({ error: 'Missing required field: prompt' }, 400)
    }

    const cwd = (body.cwd as string) || this.defaultCwd
    const allowedTools = parseAllowedTools(body.allowedTools)
    this.activeConcurrent++
    let engine
    try {
      engine = await createSessionEngine(cwd, allowedTools)
    } catch (err) {
      this.activeConcurrent--
      return json({ error: `Failed to create engine: ${errMsg(err)}` }, 500)
    }

    const prompt = body.prompt
    const self = this
    return createSSEResponse(async function* () {
      try {
        const generator = engine.engine.submitMessage(prompt)
        for await (const sdkMessage of generator) {
          const msg = sdkMessage as Record<string, unknown>
          if (msg.type === 'stream_event') {
            yield { type: 'stream', event: msg.event }
          } else {
            yield { type: 'assistant', message: msg }
          }
        }
        yield { type: 'result', message: { type: 'turn_complete' } }
      } catch (err) {
        yield { type: 'error', error: errMsg(err) }
      } finally {
        self.activeConcurrent--
        engine.abortController.abort()
      }
    })
  }

  // ===========================================================================
  // Session management endpoints
  // ===========================================================================

  private async handleCreateSession(req: Request): Promise<Response> {
    const body = await parseBody(req)
    const cwd = (body?.cwd as string) || this.defaultCwd
    const allowedTools = parseAllowedTools(body?.allowedTools)

    try {
      const session = await this.store.create(cwd, allowedTools)
      return json({ session_id: session.id, status: 'running' }, 201)
    } catch (err) {
      return json({ error: errMsg(err) }, 503)
    }
  }

  private handleListSessions(): Response {
    return json({ sessions: this.store.list() })
  }

  private handleDeleteSession(sessionId: string): Response {
    const destroyed = this.store.destroy(sessionId)
    if (!destroyed) {
      return json({ error: 'Session not found' }, 404)
    }
    return json({ status: 'destroyed' })
  }

  private async handleSessionMessage(req: Request, sessionId: string): Promise<Response> {
    const body = await parseBody(req)
    if (!body?.content || typeof body.content !== 'string') {
      return json({ error: 'Missing required field: content' }, 400)
    }

    const session = this.store.get(sessionId)
    if (!session) {
      return json({ error: 'Session not found' }, 404)
    }
    if (session.busy) {
      return json({ error: 'Session is busy. Wait for the current turn to complete or abort.' }, 409)
    }

    session.busy = true
    const messages: Record<string, unknown>[] = []
    try {
      const generator = session.engine.engine.submitMessage(body.content)
      for await (const sdkMessage of generator) {
        messages.push(sdkMessage as Record<string, unknown>)
      }
      return json({ messages, result: { type: 'turn_complete' } })
    } catch (err) {
      return json({ error: errMsg(err), messages }, 500)
    } finally {
      session.busy = false
    }
  }

  private async handleSessionMessageStream(req: Request, sessionId: string): Promise<Response> {
    const body = await parseBody(req)
    if (!body?.content || typeof body.content !== 'string') {
      return json({ error: 'Missing required field: content' }, 400)
    }

    const session = this.store.get(sessionId)
    if (!session) {
      return json({ error: 'Session not found' }, 404)
    }
    if (session.busy) {
      return json({ error: 'Session is busy. Wait for the current turn to complete or abort.' }, 409)
    }

    session.busy = true
    const content = body.content

    return createSSEResponse(async function* () {
      try {
        const generator = session.engine.engine.submitMessage(content)
        for await (const sdkMessage of generator) {
          const msg = sdkMessage as Record<string, unknown>
          if (msg.type === 'stream_event') {
            yield { type: 'stream', event: msg.event }
          } else {
            yield { type: 'assistant', message: msg }
          }
        }
        yield { type: 'result', message: { type: 'turn_complete' } }
      } catch (err) {
        yield { type: 'error', error: errMsg(err) }
      } finally {
        session.busy = false
      }
    })
  }

  shutdown(): void {
    this.store.shutdown()
  }
}

// =============================================================================
// Helpers
// =============================================================================

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

async function parseBody(req: Request): Promise<Record<string, unknown> | null> {
  try {
    return (await req.json()) as Record<string, unknown>
  } catch {
    return null
  }
}

function errMsg(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

/**
 * Parse allowedTools from request body.
 * Accepts a comma-separated string or an array of strings.
 * Returns undefined if not provided (meaning all tools are available).
 */
function parseAllowedTools(raw: unknown): string[] | undefined {
  if (!raw) return undefined
  if (Array.isArray(raw)) return raw.filter((t): t is string => typeof t === 'string')
  if (typeof raw === 'string') return raw.split(',').map(s => s.trim()).filter(Boolean)
  return undefined
}

/**
 * Create an SSE (text/event-stream) Response from an async generator of events.
 */
function createSSEResponse(
  generator: () => AsyncGenerator<Record<string, unknown>>,
): Response {
  const stream = new ReadableStream({
    async start(controller) {
      const encoder = new TextEncoder()
      try {
        for await (const event of generator()) {
          const data = `data: ${JSON.stringify(event)}\n\n`
          controller.enqueue(encoder.encode(data))
        }
      } catch (err) {
        const errorEvent = `data: ${JSON.stringify({ type: 'error', error: errMsg(err) })}\n\n`
        controller.enqueue(encoder.encode(errorEvent))
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
