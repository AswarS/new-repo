/**
 * In-memory session store for HTTP REST API.
 *
 * Manages persistent sessions that can be used across multiple HTTP requests.
 * Each session wraps a SessionEngine from engineFactory.ts.
 */

import { randomUUID } from 'crypto'
import { createSessionEngine, type SessionEngine } from './engineFactory.js'

export type HttpSession = {
  id: string
  engine: SessionEngine
  createdAt: number
  lastActiveAt: number
  busy: boolean
  cwd?: string
}

export type HttpSessionStoreConfig = {
  /** Idle timeout in ms. Sessions inactive longer than this are cleaned up. 0 = never. Default 30min. */
  idleTimeoutMs?: number
  /** Max concurrent sessions. Default 10. */
  maxSessions?: number
}

const DEFAULT_IDLE_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes
const DEFAULT_MAX_SESSIONS = 10
const CLEANUP_INTERVAL_MS = 60_000 // check every minute

export class HttpSessionStore {
  private sessions = new Map<string, HttpSession>()
  private idleTimeoutMs: number
  private maxSessions: number
  private cleanupTimer: ReturnType<typeof setInterval> | null = null

  constructor(config?: HttpSessionStoreConfig) {
    this.idleTimeoutMs = config?.idleTimeoutMs ?? DEFAULT_IDLE_TIMEOUT_MS
    this.maxSessions = config?.maxSessions ?? DEFAULT_MAX_SESSIONS

    if (this.idleTimeoutMs > 0) {
      this.cleanupTimer = setInterval(() => this.cleanupExpired(), CLEANUP_INTERVAL_MS)
    }
  }

  async create(cwd?: string, allowedTools?: string[]): Promise<HttpSession> {
    if (this.sessions.size >= this.maxSessions) {
      throw new Error(`Maximum session limit reached (${this.maxSessions})`)
    }

    const id = randomUUID()
    const engine = await createSessionEngine(cwd, allowedTools)
    const now = Date.now()

    const session: HttpSession = {
      id,
      engine,
      createdAt: now,
      lastActiveAt: now,
      busy: false,
      cwd,
    }

    this.sessions.set(id, session)
    return session
  }

  get(id: string): HttpSession | undefined {
    const session = this.sessions.get(id)
    if (session) {
      session.lastActiveAt = Date.now()
    }
    return session
  }

  destroy(id: string): boolean {
    const session = this.sessions.get(id)
    if (!session) return false
    session.engine.abortController.abort()
    this.sessions.delete(id)
    return true
  }

  list(): Array<{ id: string; createdAt: number; lastActiveAt: number; busy: boolean; cwd?: string }> {
    return Array.from(this.sessions.values()).map(s => ({
      id: s.id,
      createdAt: s.createdAt,
      lastActiveAt: s.lastActiveAt,
      busy: s.busy,
      cwd: s.cwd,
    }))
  }

  get size(): number {
    return this.sessions.size
  }

  private cleanupExpired(): void {
    if (this.idleTimeoutMs <= 0) return
    const now = Date.now()
    for (const [id, session] of this.sessions) {
      if (!session.busy && now - session.lastActiveAt > this.idleTimeoutMs) {
        session.engine.abortController.abort()
        this.sessions.delete(id)
      }
    }
  }

  shutdown(): void {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
      this.cleanupTimer = null
    }
    for (const [, session] of this.sessions) {
      session.engine.abortController.abort()
    }
    this.sessions.clear()
  }
}
