/**
 * HTTP + WebSocket + REST API server for Claude Code Agent.
 *
 * Usage: bun run serve [--port 3000] [--cwd /path/to/workdir] [--auth-token TOKEN] [--add-dir /path/to/skills]
 *
 * Endpoints:
 *   GET  /health             — health check
 *   WS   /ws                 — WebSocket agent session
 *   POST /api/agent          — one-shot prompt (blocking response)
 *   POST /api/agent/stream   — one-shot prompt (SSE streaming)
 *   POST /api/sessions       — create persistent session
 *   GET  /api/sessions       — list active sessions
 *   POST /api/sessions/:id/message        — send message (blocking)
 *   POST /api/sessions/:id/message/stream — send message (SSE streaming)
 *   DELETE /api/sessions/:id — destroy session
 */

import { randomUUID } from 'crypto'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'
import {
  handleOpen,
  handleMessage,
  handleClose,
  getSessionCount,
} from './sessionManager.js'
import { ApiRoutes } from './apiRoutes.js'
import { setAdditionalDirectoriesForClaudeMd } from '../bootstrap/state.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const PUBLIC_DIR = resolve(__dirname, '../../public')

function parseArgs(args: string[]): {
  port: number
  cwd?: string
  authToken?: string
  idleTimeout?: number
  maxSessions?: number
  addDirs: string[]
} {
  let port = 3000
  let cwd: string | undefined
  let authToken: string | undefined
  let idleTimeout: number | undefined
  let maxSessions: number | undefined
  const addDirs: string[] = []

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--port' && args[i + 1]) {
      port = parseInt(args[i + 1]!, 10)
      i++
    } else if (args[i] === '--cwd' && args[i + 1]) {
      cwd = args[i + 1]
      i++
    } else if (args[i] === '--auth-token' && args[i + 1]) {
      authToken = args[i + 1]
      i++
    } else if (args[i] === '--idle-timeout' && args[i + 1]) {
      idleTimeout = parseInt(args[i + 1]!, 10) * 1000 // seconds to ms
      i++
    } else if (args[i] === '--max-sessions' && args[i + 1]) {
      maxSessions = parseInt(args[i + 1]!, 10)
      i++
    } else if (args[i] === '--add-dir' && args[i + 1]) {
      addDirs.push(resolve(args[i + 1]!))
      i++
    }
  }

  return { port, cwd, authToken, idleTimeout, maxSessions, addDirs }
}

export async function startApiServer(args: string[]): Promise<void> {
  const { port, cwd, authToken, idleTimeout, maxSessions, addDirs } = parseArgs(args)

  // Global init (configs, telemetry, etc.)
  const { init } = await import('../entrypoints/init.js')
  await init()

  // Register additional directories for skill/CLAUDE.md discovery
  if (addDirs.length > 0) {
    setAdditionalDirectoriesForClaudeMd(addDirs)
  }

  // Create REST API route handler
  const apiRoutes = new ApiRoutes({
    authToken,
    cwd,
    idleTimeoutMs: idleTimeout,
    maxSessions,
  })

  const server = Bun.serve<{ sessionId: string }>({
    port,
    idleTimeout: 255, // max value (seconds) — prevents SSE stream disconnects during long tool runs
    async fetch(req, server) {
      const url = new URL(req.url)

      // Serve frontend
      if (url.pathname === '/' || url.pathname === '/index.html') {
        return new Response(Bun.file(resolve(PUBLIC_DIR, 'index.html')))
      }

      // Health check
      if (url.pathname === '/health') {
        return new Response(
          JSON.stringify({
            status: 'ok',
            sessions: getSessionCount(),
          }),
          { headers: { 'Content-Type': 'application/json' } },
        )
      }

      // WebSocket upgrade
      if (url.pathname === '/ws') {
        const upgraded = server.upgrade(req, {
          data: { sessionId: randomUUID() },
        })
        if (upgraded) return undefined
        return new Response('WebSocket upgrade failed', { status: 400 })
      }

      // REST API routes
      if (url.pathname.startsWith('/api/')) {
        const response = await apiRoutes.handle(req)
        if (response) return response
      }

      return new Response('Not Found', { status: 404 })
    },
    websocket: {
      async open(ws) {
        await handleOpen(ws, cwd)
      },
      async message(ws, message) {
        const raw = typeof message === 'string' ? message : message.toString()
        await handleMessage(ws, raw)
      },
      close(ws) {
        handleClose(ws)
      },
    },
  })

  console.log(`Claude Code API server listening on http://localhost:${server.port}`)
  console.log('')
  console.log('Endpoints:')
  console.log(`  WebSocket:    ws://localhost:${server.port}/ws`)
  console.log(`  Health:       http://localhost:${server.port}/health`)
  console.log(`  REST API:     http://localhost:${server.port}/api/agent`)
  console.log(`  Sessions:     http://localhost:${server.port}/api/sessions`)
  if (addDirs.length > 0) {
    console.log('')
    console.log('Skill directories:')
    for (const dir of addDirs) {
      console.log(`  ${dir}/.claude/skills/`)
    }
  }
  if (authToken) {
    console.log('')
    console.log('Auth: Bearer token required for /api/* endpoints')
  } else {
    console.log('')
    console.log('Auth: disabled (no --auth-token specified)')
  }
}
