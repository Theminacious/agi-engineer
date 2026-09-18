'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'

/**
 * API client for backend communication
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Absolute URL for a backend path.
 *
 * The backend is a separate origin (Next.js on :3000, FastAPI on :8000 — see
 * docker-compose.yml), and this app defines no route handlers under app/api and
 * no `rewrites` in next.config.js. A relative `fetch('/api/...')` therefore hits
 * the Next.js server, which has nothing mounted there, and 404s. Every backend
 * call must go through this helper.
 *
 * Guarded by frontend/tests/api-urls.test.ts.
 *
 * @param path Backend path including the `/api` prefix, e.g. `/api/insights/repo/1`.
 */
export function apiUrl(path: string): string {
  const base = API_BASE.replace(/\/+$/, '')
  const suffix = path.startsWith('/') ? path : `/${path}`
  return `${base}${suffix}`
}

// Create axios instance
export const apiClient = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface AnalysisRun {
  id: number
  repository_id: number
  repository_name: string
  event: string
  branch: string
  commit_sha: string
  pr_number: number | null
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  total_results: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export type FileClass =
  | 'application'
  | 'type_stub'
  | 'generated'
  | 'vendored'
  | 'test'
  | 'test_fixture'
  | 'documentation'
  | 'build_config'

export type Relevance = 'actionable' | 'review' | 'informational' | 'unknown'

export type FindingRecommendation = 'fix' | 'review' | 'acknowledge' | 'suppress_candidate'

export interface FindingContext {
  finding_ref: string
  file_path: string
  line_number: number
  rule_code: string
  file_class: FileClass
  classification_reasons: string[]
  secondary_file_classes: FileClass[]
  symbol: string | null
  symbol_node_id: string | null
  caller_count: number | null
  downstream_count: number | null
  production_reachable: boolean | null
  reachability_reason: string
  change_relation: string | null
  relevance: Relevance
  relevance_reasons: string[]
  confidence: number
  confidence_reasons: string[]
  severity: string
  recommendation: FindingRecommendation
  correlation_id: string | null
  correlated_count: number
  context_version: number
}

export interface AnalysisResult {
  id: number
  file_path: string
  line_number: number
  code: string
  name: string
  category: 'safe' | 'review' | 'suggestion'
  severity: string | null
  message: string
  is_fixed: number
  file_class: FileClass | null
  relevance: Relevance | null
  confidence: number | null
  recommendation: FindingRecommendation | null
  context: FindingContext | null
}

export interface RelevanceSummary {
  by_relevance: Record<Relevance, number>
  by_recommendation: Record<FindingRecommendation, number>
  by_file_class: Record<string, number>
  actionable_count: number
  informational_count: number
  unclassified_count: number
}

export interface AnalysisRunDetail extends AnalysisRun {
  results: AnalysisResult[]
  relevance_summary: RelevanceSummary | null
  executed_analyzers: string[]
}

export interface RepositoryHealth {
  repository_id: number
  repository_name: string
  is_enabled: boolean
  total_runs: number
  completed_runs: number
  failed_runs: number
  success_rate: number
  average_analysis_time_seconds: number
  recent_issues: Array<{
    file: string
    line: number
    code: string
    message: string
  }>
}

// OAuth
export async function getOAuthUrl(): Promise<{ authorization_url: string; state: string }> {
  const res = await fetch(apiUrl('/oauth/authorize'))
  if (!res.ok) throw new Error('Failed to get OAuth URL')
  return res.json()
}

export async function oauthCallback(code: string, state: string): Promise<{ token: string; user: string; installation_id: number }> {
  const res = await fetch(apiUrl(`/oauth/callback?code=${code}&state=${state}`))
  if (!res.ok) throw new Error('OAuth callback failed')
  return res.json()
}

// Analysis Runs
export async function getRunDetail(runId: number, token?: string): Promise<AnalysisRunDetail> {
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { headers })
  if (!res.ok) throw new Error('Failed to get run details')
  const data = await res.json()
  return data
}

export async function listRuns(
  params?: {
    repository_id?: number
    status?: string
    limit?: number
  },
  token?: string
): Promise<AnalysisRun[]> {
  const searchParams = new URLSearchParams()
  if (params?.repository_id) searchParams.append('repository_id', params.repository_id.toString())
  if (params?.status) searchParams.append('status', params.status)
  if (params?.limit) searchParams.append('limit', params.limit.toString())

  const query = searchParams.toString()
  const url = query ? `${API_BASE}/api/runs?${query}` : `${API_BASE}/api/runs`
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}

  const res = await fetch(url, { headers })
  if (!res.ok) throw new Error('Failed to list runs')
  return res.json()
}

// Repository Health
export async function getRepositoryHealth(repoId: number, token?: string): Promise<RepositoryHealth> {
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE}/api/repositories/${repoId}/health`, { headers })
  if (!res.ok) throw new Error('Failed to get repository health')
  return res.json()
}

// Health Check
export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(apiUrl('/health'))
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

/**
 * Hook for polling run details
 */
export function useRunDetail(runId: number, token?: string, pollInterval = 5000) {
  const [data, setData] = useState<AnalysisRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true)
        const result = await getRunDetail(runId, token)
        setData(result)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch')
      } finally {
        setLoading(false)
      }
    }

    fetch()
    const interval = setInterval(fetch, pollInterval)
    return () => clearInterval(interval)
  }, [runId, token, pollInterval])

  return { data, loading, error }
}

/**
 * Hook for listing runs
 */
export function useRuns(
  params?: {
    repository_id?: number
    status?: string
    limit?: number
  },
  token?: string,
) {
  const [data, setData] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true)
        const result = await listRuns(params, token)
        setData(result)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch')
      } finally {
        setLoading(false)
      }
    }

    fetch()
  }, [params, token])

  const refresh = async () => {
    try {
      const result = await listRuns(params, token)
      setData(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh')
    }
  }

  return { data, loading, error, refresh }
}
