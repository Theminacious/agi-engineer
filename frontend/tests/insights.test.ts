/**
 * Insights dashboard flows — PRODUCTION_READINESS_AUDIT.md P2 #6.
 *
 * The audit named frontend/app/insights/page.tsx for end-to-end testing. These
 * tests drive the page's real data layer (lib/insights.ts, which the page now
 * imports) rather than a reimplementation of it, in the same idiom as
 * tests/api.test.ts: mock global.fetch, assert the exact URL requested and the
 * value handed back to the component.
 *
 * The flow that mattered most was broken: the page fetched a relative
 * `/api/insights/...`, which resolves against the Next.js origin (:3000). There
 * are no route handlers under app/api and no `rewrites` in next.config.js, so
 * every request 404'd and the dashboard could only ever render its error state.
 * `test_requests_the_backend_origin` below is that regression test.
 *
 * environment is 'node' (vitest.config.ts) and no DOM/browser library is
 * installed, so nothing here renders React. The page keeps only JSX; every
 * decision it makes is exercised here.
 *
 * URL expectations are built from the imported API_BASE rather than from a
 * literal: lib/api.ts reads process.env.NEXT_PUBLIC_API_URL at module load, and
 * ESM hoists imports above any assignment written earlier in this file, so
 * setting the variable here cannot influence it.
 */

import { describe, expect, it, beforeEach, vi } from 'vitest'

import { API_BASE } from '@/lib/api'
import {
  fetchRepoInsights,
  fetchRepoTrends,
  repoInsightsUrl,
  repoTrendsUrl,
  riskTrendClassName,
  scoreBackgroundColor,
  scoreColor,
  trendIndicator,
} from '@/lib/insights'

/** Shape of GET /api/insights/repo/{id} — backend/app/routers/insights.py. */
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

/** The single URL passed to fetch during the call under test. */
function requestedUrl(): string {
  const mock = global.fetch as unknown as ReturnType<typeof vi.fn>
  expect(mock).toHaveBeenCalledTimes(1)
  return mock.mock.calls[0][0] as string
}

beforeEach(() => {
  vi.restoreAllMocks()
  global.fetch = vi.fn()
})

describe('loading a repository dashboard', () => {
  it('requests the backend origin, not the Next.js origin', async () => {
    // The regression this file exists for. A relative URL here reaches the
    // Next.js server, which serves no /api routes, so the page 404s in every
    // deployment — frontend :3000 and backend :8000 are separate origins.
    ;(global.fetch as any).mockResolvedValue(jsonResponse(INSIGHTS_PAYLOAD))

    await fetchRepoInsights('7')

    const url = requestedUrl()
    expect(url).toMatch(/^https?:\/\//)
    expect(url).toBe(`${API_BASE}/api/insights/repo/7`)
    expect(url.startsWith('/api')).toBe(false)
  })

  it('returns the payload the score card renders', async () => {
    ;(global.fetch as any).mockResolvedValue(jsonResponse(INSIGHTS_PAYLOAD))

    const insights = await fetchRepoInsights('7')

    expect(insights.repository_name).toBe('acme/widgets')
    expect(insights.score.reliability_score).toBe(82.5)
    expect(insights.risk_breakdown.total_risks).toBe(10)
  })

  it('raises the message the error branch displays when the backend rejects', async () => {
    ;(global.fetch as any).mockResolvedValue(jsonResponse({ detail: 'nope' }, false, 404))

    await expect(fetchRepoInsights('7')).rejects.toThrow('Failed to load insights')
  })

  it('propagates a network failure rather than resolving empty', async () => {
    // The page's catch sets its error state from this; swallowing it here would
    // leave the dashboard showing zeroes as though they were real measurements.
    ;(global.fetch as any).mockRejectedValue(new Error('ECONNREFUSED'))

    await expect(fetchRepoInsights('7')).rejects.toThrow('ECONNREFUSED')
  })
})

describe('loading trend history', () => {
  it('requests the backend origin with the selected period', async () => {
    ;(global.fetch as any).mockResolvedValue(jsonResponse(TRENDS_PAYLOAD))

    await fetchRepoTrends('7', 90)

    expect(requestedUrl()).toBe(
      `${API_BASE}/api/insights/repo/7/trends?days=90`
    )
  })

  it('unwraps data_points', async () => {
    ;(global.fetch as any).mockResolvedValue(jsonResponse(TRENDS_PAYLOAD))

    const points = await fetchRepoTrends('7', 30)

    expect(points).toHaveLength(2)
    expect(points[1].score).toBe(82.5)
  })

  it('returns an empty list when the response omits data_points', async () => {
    // The page maps over the result; undefined would throw during render.
    ;(global.fetch as any).mockResolvedValue(jsonResponse({}))

    expect(await fetchRepoTrends('7', 30)).toEqual([])
  })

  it('raises on a rejected response so the page can log it', async () => {
    ;(global.fetch as any).mockResolvedValue(jsonResponse({}, false, 500))

    await expect(fetchRepoTrends('7', 30)).rejects.toThrow('Failed to load trends')
  })

  it('changing the period changes the request', async () => {
    // The period selector re-runs the effect via its selectedPeriod dependency;
    // a URL that ignored the period would silently show stale history.
    expect(repoTrendsUrl('7', 7)).toContain('days=7')
    expect(repoTrendsUrl('7', 30)).toContain('days=30')
    expect(repoTrendsUrl('7', 90)).toContain('days=90')
  })
})

describe('url construction', () => {
  it('the base is an absolute origin', () => {
    // Everything below inherits its absoluteness from this.
    expect(API_BASE).toMatch(/^https?:\/\/[^/]+$/)
  })

  it('both endpoints are absolute', () => {
    for (const url of [repoInsightsUrl('7'), repoTrendsUrl('7', 30)]) {
      expect(url).toMatch(/^https?:\/\//)
    }
  })

  it('matches the paths the backend router mounts', () => {
    // backend/app/routers/insights.py: prefix="/api/insights", then
    // "/repo/{repo_id}" and "/repo/{repo_id}/trends".
    expect(repoInsightsUrl('42')).toBe(`${API_BASE}/api/insights/repo/42`)
    expect(repoTrendsUrl('42', 30)).toBe(
      `${API_BASE}/api/insights/repo/42/trends?days=30`
    )
  })
})

describe('score presentation', () => {
  it.each([
    [100, 'text-green-600'],
    [90, 'text-green-600'],
    [89.9, 'text-blue-600'],
    [80, 'text-blue-600'],
    [79.9, 'text-yellow-600'],
    [70, 'text-yellow-600'],
    [69.9, 'text-orange-600'],
    [60, 'text-orange-600'],
    [59.9, 'text-red-600'],
    [0, 'text-red-600'],
  ])('a score of %s is coloured %s', (score, expected) => {
    expect(scoreColor(score as number)).toBe(expected)
  })

  it('the card background uses the same grade boundaries as the number', () => {
    // A mismatch would show, say, a red number on a green card.
    for (const score of [95, 85, 75, 65, 55]) {
      const hue = scoreColor(score).replace('text-', '').replace('-600', '')
      expect(scoreBackgroundColor(score)).toContain(`bg-${hue}-50`)
    }
  })
})

describe('trend indicators', () => {
  it('shows a dash when there is no comparison period yet', () => {
    expect(trendIndicator(null)).toEqual({ label: '—', className: 'text-gray-400' })
  })

  it('an improvement is an up arrow in green', () => {
    expect(trendIndicator(1.25)).toEqual({ label: '↑ 1.3', className: 'text-green-600' })
  })

  it('a regression is a down arrow in red, with the sign dropped', () => {
    // The arrow carries the direction; a "↓ -3.5" would read as a double negative.
    expect(trendIndicator(-3.5)).toEqual({ label: '↓ 3.5', className: 'text-red-600' })
  })

  it('exactly zero is flat, not an improvement', () => {
    expect(trendIndicator(0)).toEqual({ label: '— 0.0', className: 'text-gray-600' })
  })
})

describe('risk trend badges', () => {
  it.each([
    ['increasing', 'bg-red-100 text-red-700'],
    ['stable', 'bg-blue-100 text-blue-700'],
    ['decreasing', 'bg-green-100 text-green-700'],
  ])('%s renders as %s', (trend, expected) => {
    expect(riskTrendClassName(trend)).toBe(expected)
  })

  it('an unrecognised trend still gets a real background', () => {
    // The previous inline lookup interpolated `undefined` into the class list,
    // so a value the backend added later rendered an unstyled badge.
    const className = riskTrendClassName('volatile')
    expect(className).not.toContain('undefined')
    expect(className).toContain('bg-')
  })
})
