/**
 * Artifact detector for web game / web app outputs.
 *
 * Inspects the SDKMessage stream for file-write tool calls that produce
 * web artifacts (HTML files, npm projects). After a turn completes,
 * call `getDetectedArtifacts()` to retrieve preview URLs.
 *
 * Two artifact types:
 *   1. Single HTML file  → file:// URL pushed to frontend
 *   2. npm project       → spawn `npm run dev`, capture localhost URL
 */

import { spawn, type ChildProcess } from 'child_process'
import { existsSync } from 'fs'
import { readFile } from 'fs/promises'
import { dirname, resolve, basename } from 'path'

export type Artifact =
  | { type: 'file'; url: string; filePath: string }
  | { type: 'dev_server'; url: string; filePath: string; process: ChildProcess }

export type ArtifactTracker = {
  /** Feed each SDKMessage into the tracker to detect file writes. */
  inspect(sdkMessage: Record<string, unknown>): void
  /** After a turn completes, resolve all detected artifacts into preview info. */
  resolve(): Promise<Artifact[]>
  /** Kill any spawned dev server processes. */
  cleanup(): void
}

type PendingWrite = {
  toolName: string
  filePath: string
}

/**
 * Create a new artifact tracker for a session.
 */
export function createArtifactTracker(): ArtifactTracker {
  const pendingWrites: PendingWrite[] = []
  const devServers: ChildProcess[] = []

  function inspect(sdkMessage: Record<string, unknown>): void {
    // We look for assistant messages that contain tool_use blocks
    // with the Write tool targeting web-related files.
    if (sdkMessage.type !== 'assistant') return

    const message = sdkMessage.message as Record<string, unknown> | undefined
    if (!message) return

    const content = message.content
    if (!Array.isArray(content)) return

    for (const block of content) {
      if (
        block &&
        typeof block === 'object' &&
        block.type === 'tool_use' &&
        block.name === 'Write'
      ) {
        const input = block.input as Record<string, unknown> | undefined
        if (input && typeof input.file_path === 'string') {
          pendingWrites.push({
            toolName: 'Write',
            filePath: input.file_path,
          })
        }
      }
    }
  }

  async function resolveArtifacts(): Promise<Artifact[]> {
    const artifacts: Artifact[] = []
    const htmlFiles: string[] = []
    const projectDirs = new Set<string>()

    for (const write of pendingWrites) {
      const fp = write.filePath
      const lower = fp.toLowerCase()

      if (lower.endsWith('.html') || lower.endsWith('.htm')) {
        htmlFiles.push(fp)
        // Also check if this HTML file is in a project with package.json
        const dir = dirname(fp)
        if (existsSync(resolve(dir, 'package.json'))) {
          projectDirs.add(dir)
        }
      } else if (basename(fp).toLowerCase() === 'package.json') {
        projectDirs.add(dirname(fp))
      }
    }

    // Check npm projects first — if a project has a dev script, prefer dev_server
    const handledDirs = new Set<string>()

    for (const dir of projectDirs) {
      try {
        const pkgPath = resolve(dir, 'package.json')
        const pkgContent = await readFile(pkgPath, 'utf-8')
        const pkg = JSON.parse(pkgContent)

        if (pkg.scripts?.dev || pkg.scripts?.start) {
          const scriptName = pkg.scripts.dev ? 'dev' : 'start'
          const url = await startDevServer(dir, scriptName)
          if (url) {
            artifacts.push({
              type: 'dev_server',
              url,
              filePath: dir,
              process: devServers[devServers.length - 1]!,
            })
            handledDirs.add(dir)
          }
        }
      } catch {
        // package.json parse error or doesn't exist yet, skip
      }
    }

    // For HTML files NOT in a project dir that got a dev server, push file:// URL
    for (const htmlFile of htmlFiles) {
      const dir = dirname(htmlFile)
      if (!handledDirs.has(dir)) {
        if (existsSync(htmlFile)) {
          // Convert to file:// URL
          const fileUrl = pathToFileUrl(htmlFile)
          artifacts.push({ type: 'file', url: fileUrl, filePath: htmlFile })
        }
      }
    }

    // Clear pending writes after resolving
    pendingWrites.length = 0

    return artifacts
  }

  function cleanup(): void {
    for (const proc of devServers) {
      try {
        proc.kill()
      } catch {
        // already dead
      }
    }
    devServers.length = 0
  }

  /**
   * Spawn `npm run <script>` in the given directory and wait for a
   * localhost URL to appear in stdout.
   */
  function startDevServer(
    dir: string,
    scriptName: string,
  ): Promise<string | null> {
    return new Promise((resolvePromise) => {
      const isWindows = process.platform === 'win32'
      const child = spawn(
        isWindows ? 'npm.cmd' : 'npm',
        ['run', scriptName],
        {
          cwd: dir,
          stdio: ['ignore', 'pipe', 'pipe'],
          shell: false,
        },
      )

      devServers.push(child)

      let resolved = false
      const urlPattern = /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0):\d+/

      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true
          resolvePromise(null)
        }
      }, 30_000) // 30s timeout

      function checkOutput(data: Buffer) {
        if (resolved) return
        const text = data.toString()
        const match = text.match(urlPattern)
        if (match) {
          resolved = true
          clearTimeout(timeout)
          // Normalize 0.0.0.0 to localhost for browser access
          const url = match[0].replace('0.0.0.0', 'localhost')
          resolvePromise(url)
        }
      }

      child.stdout?.on('data', checkOutput)
      child.stderr?.on('data', checkOutput)

      child.on('error', () => {
        if (!resolved) {
          resolved = true
          clearTimeout(timeout)
          resolvePromise(null)
        }
      })

      child.on('exit', () => {
        if (!resolved) {
          resolved = true
          clearTimeout(timeout)
          resolvePromise(null)
        }
      })
    })
  }

  return {
    inspect,
    resolve: resolveArtifacts,
    cleanup,
  }
}

/** Convert a local file path to a file:// URL. */
function pathToFileUrl(filePath: string): string {
  // On Windows, paths like C:\foo\bar become file:///C:/foo/bar
  const normalized = filePath.replace(/\\/g, '/')
  if (/^[a-zA-Z]:/.test(normalized)) {
    return `file:///${normalized}`
  }
  return `file://${normalized}`
}
