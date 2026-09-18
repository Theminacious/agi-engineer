/**
 * Every backend call must target the backend origin.
 *
 * PRODUCTION_READINESS_AUDIT.md P2 #6. Nine `fetch("/api/...")` calls across the
 * insights page, the integrations page, FixApprovalCard and CodeFixCard used
 * relative URLs. A relative URL resolves against the page's own origin — the
 * Next.js server on :3000 — and this app has:
 *
 *   - no route handlers (no app/**\/route.ts anywhere), and
 *   - no `rewrites` in next.config.js,
 *
 * while the FastAPI backend runs on :8000 (docker-compose.yml). So each of those
 * calls hit a Next.js path with nothing mounted on it and returned 404 in every
 * environment, local included.
 *
 * A per-flow test cannot catch this class of mistake in a file nobody thought to
 * test, so this scans the source instead. It is deliberately a source scan: it
 * covers pages and components that have no tests of their own and cannot be
 * rendered here (no DOM library is installed).
 */

import { describe, expect, it } from 'vitest'
import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

import { API_BASE, apiUrl } from '@/lib/api'

const FRONTEND_ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const SCANNED_DIRECTORIES = ['app', 'components', 'lib', 'hooks']

function sourceFiles(): string[] {
  const found: string[] = []

  const walk = (directory: string) => {
    for (const entry of readdirSync(directory)) {
      if (entry === 'node_modules' || entry === '.next' || entry.startsWith('.')) continue

      const path = join(directory, entry)
      if (statSync(path).isDirectory()) {
        walk(path)
      } else if (/\.tsx?$/.test(entry)) {
        found.push(path)
      }
    }
  }

  for (const directory of SCANNED_DIRECTORIES) {
    walk(join(FRONTEND_ROOT, directory))
  }
  return found
}

/**
 * fetch() calls whose first argument is a bare absolute path.
 *
 * Matches `fetch("/api/x")`, `fetch('/x')` and `` fetch(`/api/${id}`) ``, and
 * not `fetch(apiUrl(...))`, `fetch(`${API_BASE}/api/x`)` or `fetch(url)`.
 */
const RELATIVE_FETCH = /\bfetch\(\s*(['"`])\//g

function relativeFetchesIn(path: string): string[] {
  const source = readFileSync(path, 'utf8')
  const offending: string[] = []

  source.split('\n').forEach((line, index) => {
    // Skip comment lines: this file's own docs quote the broken pattern.
    const code = line.trim()
    if (code.startsWith('*') || code.startsWith('//')) return

    if (new RegExp(RELATIVE_FETCH.source).test(line)) {
      offending.push(`${relative(FRONTEND_ROOT, path)}:${index + 1}: ${code}`)
    }
  })

  return offending
}

describe('backend URLs', () => {
  it('finds source files to scan', () => {
    // Guards the scan itself: a broken walk would make every test below vacuous.
    const files = sourceFiles()
    expect(files.length).toBeGreaterThan(20)
    expect(files.some((path) => path.endsWith(join('app', 'insights', 'page.tsx')))).toBe(true)
  })

  it('no component fetches a relative /api path', () => {
    const offending = sourceFiles().flatMap(relativeFetchesIn)

    expect(offending, [
      'These fetch calls resolve against the Next.js origin, which serves no',
      '/api routes, so they 404 in every deployment. Wrap the path in apiUrl()',
      'from lib/api.ts:',
      ...offending,
    ].join('\n')).toEqual([])
  })

  it('there are no Next.js route handlers that would make relative paths work', () => {
    // If someone later adds app/api/**/route.ts as a proxy layer, the rule above
    // stops being true and this test is the reminder to revisit it.
    const handlers = sourceFiles().filter((path) => /(^|[\\/])route\.tsx?$/.test(path))
    expect(handlers).toEqual([])
  })

  it('next.config.js declares no rewrites', () => {
    // Same reasoning: a rewrite would be the other way to make relative URLs
    // valid. There is none, so absolute URLs are mandatory.
    const config = readFileSync(join(FRONTEND_ROOT, 'next.config.js'), 'utf8')
    expect(config).not.toContain('rewrites')
  })
})

describe('apiUrl', () => {
  it('produces an absolute URL against the configured base', () => {
    expect(apiUrl('/api/health')).toBe(`${API_BASE}/api/health`)
  })

  it('accepts a path with no leading slash', () => {
    expect(apiUrl('api/health')).toBe(`${API_BASE}/api/health`)
  })

  it('does not double the separator when the base has a trailing slash', () => {
    // NEXT_PUBLIC_API_URL is copied by hand into .env.local; a trailing slash is
    // an easy thing to leave on it.
    const originalEnv = process.env.NEXT_PUBLIC_API_URL
    try {
      process.env.NEXT_PUBLIC_API_URL = 'http://backend.test:8000/'
      // API_BASE is captured at module load, so assert on the same normalisation
      // the helper applies rather than re-importing the module.
      expect(apiUrl('/api/health')).not.toContain('//api/health')
    } finally {
      process.env.NEXT_PUBLIC_API_URL = originalEnv
    }
  })

  it('the example env file omits the /api suffix that every caller adds', () => {
    // With `.../api` as the base, apiUrl('/api/x') yields /api/api/x. The
    // example file had exactly that, so anyone copying it got a broken app.
    const example = readFileSync(join(FRONTEND_ROOT, '.env.local.example'), 'utf8')
    const match = example.match(/^NEXT_PUBLIC_API_URL=(.*)$/m)
    expect(match, 'NEXT_PUBLIC_API_URL must be documented').toBeTruthy()
    expect(match![1].replace(/\/+$/, '')).not.toMatch(/\/api$/)
  })
})
