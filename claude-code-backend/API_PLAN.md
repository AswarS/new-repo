# HTTP REST API for Agent Invocation — Implementation Plan

## Goal

Add HTTP REST API endpoints to `claude-code-backend` so users can invoke the agent via simple HTTP calls (POST/SSE) without needing a WebSocket connection.

## Current Architecture

The project already has:
- `src/server/apiServer.ts` — Bun.serve HTTP + WebSocket server (`bun run serve`)
- `src/server/sessionManager.ts` — WebSocket-based session management
- `src/server/engineFactory.ts` — Creates QueryEngine with auto-approve permissions
- `src/server/protocol.ts` — Message types

## New API Design

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent` | One-shot: send prompt, get full response (blocking) |
| POST | `/api/agent/stream` | Send prompt, get SSE stream of agent events |
| POST | `/api/sessions` | Create a persistent session |
| POST | `/api/sessions/:id/message` | Send message to existing session |
| GET  | `/api/sessions/:id/message/stream` | SSE stream for an existing session's response |
| DELETE | `/api/sessions/:id` | Destroy a session |
| GET  | `/api/sessions` | List active sessions |

### Request/Response Schemas

**POST /api/agent** (one-shot)
```json
// Request
{
  "prompt": "create a hello world file",
  "cwd": "/path/to/workdir",       // optional
  "permissions": "auto"             // optional: "auto" | "ask"
}

// Response
{
  "session_id": "uuid",
  "messages": [...],                // all SDK messages from the turn
  "result": { "type": "turn_complete" }
}
```

**POST /api/agent/stream** (SSE)
```json
// Request (same as /api/agent)
{
  "prompt": "explain this code",
  "cwd": "/path/to/workdir"
}
```
SSE response: each event is `data: {json}\n\n` with types: `assistant`, `stream`, `result`, `error`

**POST /api/sessions** (create session)
```json
// Request
{ "cwd": "/path/to/workdir" }

// Response
{ "session_id": "uuid", "status": "running" }
```

**POST /api/sessions/:id/message**
```json
// Request
{ "content": "now add tests" }

// Response (same shape as /api/agent response)
{ "messages": [...], "result": {...} }
```

## Implementation Plan

### 1. `src/server/httpSessionStore.ts` (new)
- In-memory Map of HTTP sessions (id → SessionEngine + message history)
- Idle timeout cleanup (configurable, default 30min)
- Methods: create, get, destroy, list

### 2. `src/server/apiRoutes.ts` (new)
- All REST route handlers
- Auth middleware (Bearer token from `--auth-token` flag)
- SSE helper for streaming responses
- Shared logic for running a prompt through a SessionEngine

### 3. Update `src/server/apiServer.ts`
- Import and mount REST routes in the `fetch` handler
- Parse new CLI flags: `--auth-token`, `--idle-timeout`

### 4. Update `src/server/protocol.ts`
- Add HTTP request/response type definitions

## Key Design Decisions

1. **Reuse `engineFactory.ts`** — same QueryEngine infrastructure as WebSocket sessions
2. **Bearer token auth** — simple token passed via `--auth-token` CLI flag; reject requests without valid token (disabled if no token specified = local dev mode)
3. **SSE for streaming** — standard `text/event-stream` for streaming responses, compatible with any HTTP client (curl, fetch, etc.)
4. **Session persistence is in-memory** — sessions live as long as the server runs; no DB needed for this scope
5. **Auto-approve permissions by default** — same as existing WebSocket server; suitable for local/trusted environments
