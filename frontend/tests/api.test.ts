import { describe, it, expect, beforeEach, vi } from 'vitest'

// Ensure env base URL
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000'

import * as api from '@/lib/api'

describe('frontend lib/api', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    global.fetch = vi.fn()
  })

  it('getOAuthUrl returns URL and state', async () => {
    const mockJson = { authorization_url: 'https://github.com/login/oauth/authorize?client_id=123', state: 'abc123' }
    ;(global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockJson })

    const res = await api.getOAuthUrl()
    expect(res).toEqual(mockJson)
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/oauth/authorize')
  })

  it('oauthCallback passes query and returns token payload', async () => {
    const mockJson = { token: 'jwt-token', user: 'octocat', installation_id: 42 }
    ;(global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockJson })

    const res = await api.oauthCallback('CODE123', 'STATE456')
    expect(res).toEqual(mockJson)
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/oauth/callback?code=CODE123&state=STATE456')
  })

  it('listRuns sends params and auth header', async () => {
    const mockRuns = [
      { id: 1, repository_id: 9, event: 'push', branch: 'main', commit_sha: 'abc', pr_number: null, status: 'completed', total_results: 2, created_at: new Date().toISOString(), started_at: null, completed_at: new Date().toISOString(), error: null },
    ]
    ;(global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockRuns })

    const res = await api.listRuns({ status: 'completed', limit: 10 }, 'JWT')
    expect(res).toEqual(mockRuns)
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/runs?status=completed&limit=10', { headers: { Authorization: 'Bearer JWT' } })
  })

  it('getRunDetail sends auth header when provided', async () => {
    const mockDetail = {
      id: 1,
      repository_id: 9,
      event: 'push',
      branch: 'main',
      commit_sha: 'abc',
      pr_number: null,
      status: 'completed',
      total_results: 2,
      created_at: new Date().toISOString(),
      started_at: null,
      completed_at: new Date().toISOString(),
      error: null,
      results: [],
    }
    ;(global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockDetail })

    const res = await api.getRunDetail(1, 'JWT')
    expect(res).toEqual(mockDetail)
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/api/runs/1', { headers: { Authorization: 'Bearer JWT' } })
  })

  it('healthCheck returns status', async () => {
    const mockJson = { status: 'healthy' }
    ;(global.fetch as any).mockResolvedValue({ ok: true, json: async () => mockJson })

    const res = await api.healthCheck()
    expect(res).toEqual(mockJson)
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:8000/health')
  })

  it('throws on non-ok responses', async () => {
    ;(global.fetch as any).mockResolvedValue({ ok: false, status: 500, json: async () => ({}) })

    await expect(api.getOAuthUrl()).rejects.toThrow('Failed to get OAuth URL')
    await expect(api.oauthCallback('a', 'b')).rejects.toThrow('OAuth callback failed')
    await expect(api.listRuns()).rejects.toThrow('Failed to list runs')
    await expect(api.getRunDetail(1)).rejects.toThrow('Failed to get run details')
    await expect(api.healthCheck()).rejects.toThrow('Health check failed')
  })
})
