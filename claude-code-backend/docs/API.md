# Claude Code Agent — API 接口文档

## 启动服务

```bash
bun run serve [--port 3000] [--cwd /path/to/workdir]
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | `3000` | HTTP / WebSocket 监听端口 |
| `--cwd` | 当前工作目录 | Agent 操作的根目录 |

---

## HTTP 接口

### `GET /`

返回前端页面 (`public/index.html`)。

### `GET /health`

健康检查。

**Response** `200 OK`

```json
{
  "status": "ok",
  "sessions": 2
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | `string` | 固定值 `"ok"` |
| `sessions` | `number` | 当前活跃的 WebSocket 会话数 |

---

## WebSocket 接口

### 连接

```
ws://localhost:{port}/ws
```

连接成功后服务端自动推送一条 `result` 消息表示会话建立：

```json
{
  "type": "result",
  "message": {
    "type": "session_started",
    "sessionId": "uuid-string"
  }
}
```

---

## 客户端 → 服务端（Client → Server）

所有消息均为 JSON 字符串。

### 1. `user_message` — 发送用户消息

```json
{
  "type": "user_message",
  "content": "帮我写一个贪吃蛇游戏",
  "id": "optional-uuid"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | `"user_message"` | 是 | 消息类型 |
| `content` | `string` | 是 | 用户输入的文本 |
| `id` | `string` | 否 | 可选的消息 ID |

**约束**：同一会话同一时间只能处理一条消息。如果 Agent 正忙，会返回 `error`。

### 2. `abort` — 中断当前处理

```json
{
  "type": "abort"
}
```

发送后服务端会中止当前 Agent 处理，并返回：

```json
{
  "type": "result",
  "message": { "type": "aborted" }
}
```

---

## 服务端 → 客户端（Server → Client）

### 1. `assistant` — Agent 完整消息

Agent 处理过程中推送的完整 SDKMessage（assistant 文本、工具调用、工具结果等）。当一个 content block 完整生成后发送。

```json
{
  "type": "assistant",
  "message": { ... }
}
```

`message` 的内部结构取决于 SDKMessage 类型，常见的有：

#### a) 文本响应

```json
{
  "type": "assistant",
  "message": {
    "type": "assistant",
    "message": {
      "content": [
        { "type": "text", "text": "这是 Agent 的回复..." }
      ]
    }
  }
}
```

#### b) 工具调用

```json
{
  "type": "assistant",
  "message": {
    "type": "assistant",
    "message": {
      "content": [
        {
          "type": "tool_use",
          "id": "toolu_xxx",
          "name": "Write",
          "input": {
            "file_path": "/path/to/file.html",
            "content": "<html>...</html>"
          }
        }
      ]
    }
  }
}
```

#### c) 工具结果（在 user 类型消息中）

```json
{
  "type": "assistant",
  "message": {
    "type": "user",
    "message": {
      "content": [
        {
          "type": "tool_result",
          "tool_use_id": "toolu_xxx",
          "content": "File created successfully"
        }
      ]
    }
  }
}
```

#### d) 思考过程

```json
{
  "type": "assistant",
  "message": {
    "type": "assistant",
    "message": {
      "content": [
        { "type": "thinking", "thinking": "让我分析一下..." }
      ]
    }
  }
}
```

### 2. `stream` — 流式增量事件

实时推送 Anthropic API 的原始流事件，用于逐字渲染文本。前端应优先使用 `stream` 消息实现打字机效果，`assistant` 消息作为完整内容的补充。

```json
{
  "type": "stream",
  "event": { ... }
}
```

`event` 是 Anthropic Messages API 的原始 SSE 事件，常见类型：

#### a) `content_block_start` — 新内容块开始

```json
{
  "type": "stream",
  "event": {
    "type": "content_block_start",
    "index": 0,
    "content_block": { "type": "text", "text": "" }
  }
}
```

content_block 类型可以是 `text`、`tool_use` 或 `thinking`。

#### b) `content_block_delta` — 增量内容

文本增量：
```json
{
  "type": "stream",
  "event": {
    "type": "content_block_delta",
    "index": 0,
    "delta": { "type": "text_delta", "text": "你好" }
  }
}
```

思考增量：
```json
{
  "type": "stream",
  "event": {
    "type": "content_block_delta",
    "index": 0,
    "delta": { "type": "thinking_delta", "thinking": "让我想想..." }
  }
}
```

工具输入增量：
```json
{
  "type": "stream",
  "event": {
    "type": "content_block_delta",
    "index": 1,
    "delta": { "type": "input_json_delta", "partial_json": "{\"file_" }
  }
}
```

#### c) `content_block_stop` — 内容块结束

```json
{
  "type": "stream",
  "event": {
    "type": "content_block_stop",
    "index": 0
  }
}
```

#### d) `message_start` / `message_delta` / `message_stop` — 消息生命周期

这些事件标记整条消息的开始、元数据更新和结束，通常无需在 UI 中处理。

### 3. `result` — 回合结果

表示一个处理回合的生命周期事件。

```json
{
  "type": "result",
  "message": { "type": "session_started", "sessionId": "uuid" }
}
```

| `message.type` | 说明 |
|-----------------|------|
| `session_started` | 会话建立成功，包含 `sessionId` |
| `turn_complete` | 当前回合处理完成 |
| `aborted` | 用户主动中断 |

### 4. `error` — 错误消息

```json
{
  "type": "error",
  "error": "Session is busy processing a previous message. Send \"abort\" first."
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"error"` | 固定值 |
| `error` | `string` | 错误描述 |

常见错误：

| 错误信息 | 触发条件 |
|----------|----------|
| `Session not found` | WebSocket 连接未建立或已断开 |
| `Invalid message format` | 消息不是合法的 JSON 或缺少必要字段 |
| `Session is busy processing a previous message. Send "abort" first.` | Agent 正在处理上一条消息 |
| `Failed to initialize session: ...` | 会话初始化失败（连接后自动关闭） |

### 5. `preview` — 网页产物预览

当 Agent 使用 `develop-web-game` 等 skill 生成网页文件时，回合结束后自动推送预览地址。

```json
{
  "type": "preview",
  "previewType": "file",
  "url": "file:///D:/projects/game/index.html"
}
```

```json
{
  "type": "preview",
  "previewType": "dev_server",
  "url": "http://localhost:5173"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | `"preview"` | 固定值 |
| `previewType` | `"file"` \| `"dev_server"` | 产物类型 |
| `url` | `string` | 预览地址 |

**产物检测规则：**

| 场景 | `previewType` | `url` 格式 | 说明 |
|------|--------------|------------|------|
| Agent 生成单个 `.html` 文件 | `file` | `file:///absolute/path/to/file.html` | 直接使用文件路径 |
| Agent 生成含 `dev`/`start` 脚本的 npm 项目 | `dev_server` | `http://localhost:{port}` | 自动执行 `npm run dev` 并捕获端口 |

> 注意：`file://` URL 无法在 iframe 中加载，只能通过浏览器直接打开。`dev_server` 类型支持 iframe 内嵌预览。

---

## 消息时序

### 正常对话流程

```
Client                              Server
  |                                    |
  |--- ws://localhost:3000/ws -------->|
  |<-- result(session_started) --------|
  |                                    |
  |--- user_message ------------------>|
  |<-- stream(content_block_start) ----|
  |<-- stream(content_block_delta) ----|  ← 逐字推送
  |<-- stream(content_block_delta) ----|  ← 逐字推送
  |<-- stream(content_block_stop) -----|
  |<-- assistant (完整消息) -----------|
  |<-- stream(content_block_start) ----|  ← tool_use
  |<-- stream(content_block_stop) -----|
  |<-- assistant (工具调用) -----------|
  |<-- assistant (工具结果) -----------|
  |<-- preview (if web artifact) ------|
  |<-- result(turn_complete) ----------|
```

### 中断流程

```
Client                              Server
  |                                    |
  |--- user_message ------------------>|
  |<-- stream(content_block_delta) ----|
  |--- abort ------------------------->|
  |<-- result(aborted) ----------------|
```

### 并发消息（被拒绝）

```
Client                              Server
  |                                    |
  |--- user_message ------------------>|
  |<-- assistant (streaming...) -------|
  |--- user_message ------------------>|  (Agent 正忙)
  |<-- error("Session is busy...") ----|
```

---

## 完整示例（JavaScript）

```javascript
const ws = new WebSocket('ws://localhost:3000/ws')

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)

  switch (data.type) {
    case 'stream':
      // 流式增量事件 — 实现逐字渲染
      if (data.event.type === 'content_block_delta') {
        const delta = data.event.delta
        if (delta?.type === 'text_delta') {
          process.stdout.write(delta.text)  // 逐字输出
        } else if (delta?.type === 'thinking_delta') {
          process.stdout.write(`[思考] ${delta.thinking}`)
        }
      } else if (data.event.type === 'content_block_start') {
        const block = data.event.content_block
        if (block?.type === 'tool_use') {
          console.log(`[Tool Start] ${block.name}`)
        }
      }
      break

    case 'result':
      if (data.message.type === 'session_started') {
        console.log('Session:', data.message.sessionId)
      } else if (data.message.type === 'turn_complete') {
        console.log('\n--- Turn complete ---')
      }
      break

    case 'assistant':
      // 完整消息 — 可用于补充渲染或获取完整工具调用
      const msg = data.message?.message
      if (msg?.content) {
        for (const block of msg.content) {
          if (block.type === 'tool_use') {
            console.log(`[Tool] ${block.name}`, block.input)
          }
        }
      }
      break

    case 'preview':
      console.log(`Preview (${data.previewType}): ${data.url}`)
      // previewType === 'file' → window.open(data.url)
      // previewType === 'dev_server' → iframe.src = data.url
      break

    case 'error':
      console.error('Error:', data.error)
      break
  }
}

// 发送消息
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'user_message',
    content: '写一个贪吃蛇游戏'
  }))
}

// 中断
function abort() {
  ws.send(JSON.stringify({ type: 'abort' }))
}
```

---

## TypeScript 类型定义

完整类型定义见 [`src/server/protocol.ts`](../src/server/protocol.ts)。

```typescript
// Client → Server
type ClientMessage =
  | { type: 'user_message'; content: string; id?: string }
  | { type: 'abort' }

// Server → Client
type ServerMessage =
  | { type: 'assistant'; message: Record<string, unknown> }
  | { type: 'stream'; event: Record<string, unknown> }
  | { type: 'result'; message: Record<string, unknown>; usage?: Record<string, unknown> }
  | { type: 'error'; error: string }
  | { type: 'preview'; previewType: 'file' | 'dev_server'; url: string }
```
