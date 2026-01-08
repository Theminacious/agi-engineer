'use client'

import { useEffect, useState } from 'react'

/**
 * API client for backend communication
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface AnalysisRun {
  id: number
  repository_id: number
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

export interface AnalysisResult {
  id: number
  file_path: string
  line_number: number
  code: string
  name: string
  category: 'safe' | 'review' | 'suggestion'
  message: string
  is_fixed: number
}

export interface AnalysisRunDetail extends AnalysisRun {
  results: AnalysisResult[]
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
  const res = await fetch(`${API_BASE}/oauth/authorize`)
  if (!res.ok) throw new Error('Failed to get OAuth URL')
  return res.json()
}

export async function oauthCallback(code: string, state: string): Promise<{ token: string; user: string; installation_id: number }> {
  const res = await fetch(`${API_BASE}/oauth/callback?code=${code}&state=${state}`)
  if (!res.ok) throw new Error('OAuth callback failed')
  return res.json()
}

// Analysis Runs
export async function getRunDetail(runId: number, token?: string): Promise<AnalysisRunDetail> {
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { headers })
  if (!res.ok) throw new Error('Failed to get run details')
  return res.json()
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
  const headers = token ? { Authorization: `Bearer ${token}` } : {}

  const res = await fetch(url, { headers })
  if (!res.ok) throw new Error('Failed to list runs')
  return res.json()
}

// Repository Health
export async function getRepositoryHealth(repoId: number, token?: string): Promise<RepositoryHealth> {
  const headers = token ? { Authorization: `Bearer ${token}` } : {}
  const res = await fetch(`${API_BASE}/api/repositories/${repoId}/health`, { headers })
  if (!res.ok) throw new Error('Failed to get repository health')
  return res.json()
}

// Health Check
export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`)
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
