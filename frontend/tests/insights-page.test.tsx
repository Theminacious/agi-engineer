// @vitest-environment jsdom
/**
 * Insights dashboard rendered end to end — PRODUCTION_READINESS_AUDIT.md P2 #6,
 * whose stated action was "Manual testing or automated E2E tests" against
 * frontend/app/insights/page.tsx.
 *
 * This renders the real page component. Only two things are substituted:
 * `next/navigation`'s useSearchParams (no router exists outside Next) and
 * global.fetch. Everything else — the effect, the loading/error/empty branches,
 * the period selector, the Retry button — is the shipping code.
 *
 * jsdom rather than a browser driver: no server or browser download is needed,
 * so this runs in CI as an ordinary unit test. Deterministic by construction —
 * every response is a resolved value, and no test depends on timing.
 *
 * tests/insights.test.ts covers the data layer's URLs and formatting; this file
 * covers what the user actually sees.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

const searchParams = new URLSearchParams()

vi.mock('next/navigation', () => ({
  useSearchParams: () => searchParams,
}))

import InsightsPage from '@/app/insights/page'
import { API_BASE } from '@/lib/api'

const INSIGHTS_PAYLOAD = {
  repository_id: 7,
  repository_name: 'acme/widgets',
  score: {
    reliability_score: 82.5,
    score_grade: 'B',
    score_change_7d: 1.25,
    score_change_30d: -3.5,
    last_score_update_at: '2026-08-01T00:00:00Z',
  },
  risk_breakdown: {
    critical_risks: 1,
    high_risks: 2,
    medium_risks: 3,
    low_risks: 4,
    total_risks: 10,
    risk_trend_7d: 'increasing',
    risk_trend_30d: 'stable',
  },
  risk_categories: {
    crash_risks: 1,
    resource_leaks: 2,
    reliability_antipatterns: 3,
    scalability_risks: 4,
    edge_case_vulnerabilities: 5,
  },
  fix_metrics: {
    total_fixes_proposed: 10,
    total_fixes_approved: 8,
    total_fixes_applied: 6,
    total_fixes_failed: 1,
    fix_adoption_rate: 0.8,
    fix_success_rate: 0.75,
  },
  pr_metrics: {
    total_prs_analyzed: 20,
    prs_with_critical_risks: 2,
    prs_with_high_risks: 5,
    prs_with_no_risks: 13,
  },
  last_analysis_at: '2026-08-01T00:00:00Z',
  last_fix_applied_at: null,
}

const TRENDS_PAYLOAD = {
  data_points: [
    { date: '2026-07-01', score: 80.0, critical_risks: 2, high_risks: 3, total_risks: 12 },
    { date: '2026-08-01', score: 82.5, critical_risks: 1, high_risks: 2, total_risks: 10 },
  ],
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, json: async () => body }
}

/**
 * Routes by URL rather than by call order.
 *
 * The page fires loadInsights and loadTrends from the same effect, so their
 * responses can settle in either order; a queue of sequential mock values would
 * make the tests order-dependent.
 */
function routeFetch(handlers: {
  insights?: () => unknown
  trends?: () => unknown
}) {
  global.fetch = vi.fn(async (url: string) => {
    if (url.includes('/trends')) {
      return (handlers.trends ?? (() => jsonResponse(TRENDS_PAYLOAD)))()
    }
    return (handlers.insights ?? (() => jsonResponse(INSIGHTS_PAYLOAD)))()
  }) as unknown as typeof fetch
}

function trendsRequests(): string[] {
  const mock = global.fetch as unknown as ReturnType<typeof vi.fn>
  return mock.mock.calls.map((call) => call[0] as string).filter((url) => url.includes('/trends'))
}

beforeEach(() => {
  vi.restoreAllMocks()
  // console.error is the page's own reporting for a failed load; silencing it
  // keeps the expected-failure tests from printing noise, and each test that
  // relies on the failure asserts on the rendered result instead.
  vi.spyOn(console, 'error').mockImplementation(() => {})
  searchParams.set('repo_id', '7')
  routeFetch({})
})

afterEach(cleanup)

describe('opening the dashboard for a repository', () => {
  it('shows a spinner, then the repository and its score', async () => {
    render(<InsightsPage />)

    expect(screen.getByText('Loading insights...')).toBeDefined()

    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())
    // getAllByText: 82.5 is both the current score and the latest trend point.
    expect(screen.getAllByText('82.5').length).toBeGreaterThan(0)
    expect(screen.getByText('B')).toBeDefined()
    expect(screen.queryByText('Loading insights...')).toBeNull()
  })

  it('requests both endpoints on the backend origin', async () => {
    render(<InsightsPage />)
    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())

    const mock = global.fetch as unknown as ReturnType<typeof vi.fn>
    const urls = mock.mock.calls.map((call) => call[0] as string)
    expect(urls).toContain(`${API_BASE}/api/insights/repo/7`)
    expect(urls).toContain(`${API_BASE}/api/insights/repo/7/trends?days=30`)
  })

  it('renders the trend history returned by the backend', async () => {
    render(<InsightsPage />)

    // 80.0 belongs to the older data point only, so finding it proves the list
    // rendered rather than just the score card. Dates are not asserted: they go
    // through toLocaleDateString and would vary with the CI machine's locale.
    await waitFor(() => expect(screen.getByText('80.0')).toBeDefined())
    expect(screen.getByText('12 risks (2C / 3H)')).toBeDefined()
    expect(screen.queryByText(/No trend data available/i)).toBeNull()
  })

  it('shows the trend empty state when the backend has no history yet', async () => {
    routeFetch({ trends: () => jsonResponse({ data_points: [] }) })

    render(<InsightsPage />)

    await waitFor(() => expect(screen.getByText(/No trend data available/i)).toBeDefined())
  })

  it('still renders the score card when only the trends call fails', async () => {
    // Trends are supplementary. Treating their failure as a page error would
    // hide a score the backend returned successfully.
    routeFetch({ trends: () => jsonResponse({}, false, 500) })

    render(<InsightsPage />)

    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())
    expect(screen.queryByText('Error Loading Insights')).toBeNull()
  })
})

describe('arriving with no repository selected', () => {
  it('shows the empty state instead of spinning for ever', async () => {
    // Regression test. The effect returned early when repo_id was absent without
    // clearing `loading`, which is initialised to true — so /insights with no
    // query parameter rendered the spinner permanently and the "No repository
    // selected" branch below was unreachable.
    searchParams.delete('repo_id')

    render(<InsightsPage />)

    await waitFor(() => expect(screen.getByText('No repository selected')).toBeDefined())
    expect(screen.queryByText('Loading insights...')).toBeNull()
    expect(global.fetch).not.toHaveBeenCalled()
  })
})

describe('when the backend rejects the request', () => {
  it('shows the error message and a Retry button', async () => {
    routeFetch({ insights: () => jsonResponse({ detail: 'no such repo' }, false, 404) })

    render(<InsightsPage />)

    await waitFor(() => expect(screen.getByText('Error Loading Insights')).toBeDefined())
    expect(screen.getByText('Failed to load insights')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeDefined()
  })

  it('Retry re-requests and recovers', async () => {
    let succeed = false
    routeFetch({
      insights: () => (succeed ? jsonResponse(INSIGHTS_PAYLOAD) : jsonResponse({}, false, 503)),
    })

    render(<InsightsPage />)
    await waitFor(() => expect(screen.getByText('Error Loading Insights')).toBeDefined())

    succeed = true
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))

    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())
    expect(screen.queryByText('Error Loading Insights')).toBeNull()
  })

  it('surfaces a connection failure rather than an empty dashboard', async () => {
    routeFetch({ insights: () => Promise.reject(new Error('ECONNREFUSED')) })

    render(<InsightsPage />)

    await waitFor(() => expect(screen.getByText('ECONNREFUSED')).toBeDefined())
  })
})

describe('changing the trend period', () => {
  it('refetches trends for the selected number of days', async () => {
    render(<InsightsPage />)
    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())
    expect(trendsRequests()).toEqual([`${API_BASE}/api/insights/repo/7/trends?days=30`])

    fireEvent.click(screen.getByRole('button', { name: '90 days' }))

    await waitFor(() =>
      expect(trendsRequests()).toContain(`${API_BASE}/api/insights/repo/7/trends?days=90`)
    )
  })

  it('marks the selected period as active', async () => {
    render(<InsightsPage />)
    await waitFor(() => expect(screen.getByText('acme/widgets')).toBeDefined())

    // 30 is the default.
    expect(screen.getByRole('button', { name: '30 days' }).className).toContain('bg-blue-600')
    expect(screen.getByRole('button', { name: '7 days' }).className).not.toContain('bg-blue-600')

    fireEvent.click(screen.getByRole('button', { name: '7 days' }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: '7 days' }).className).toContain('bg-blue-600')
    )
    expect(screen.getByRole('button', { name: '30 days' }).className).not.toContain('bg-blue-600')
  })
})
