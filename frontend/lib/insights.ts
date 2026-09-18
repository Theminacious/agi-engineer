/**
 * Data layer and view formatting for the Reliability Insights dashboard.
 *
 * Extracted from app/insights/page.tsx so the page's user-critical behaviour —
 * which URL is requested, what happens on a non-ok response, how a score or
 * trend is rendered — is reachable from a test without a browser. The page keeps
 * the JSX; everything decidable lives here.
 *
 * Covered by frontend/tests/insights.test.ts.
 */

import { apiUrl } from './api'

export interface ReliabilityScore {
  reliability_score: number
  score_grade: string
  score_change_7d: number | null
  score_change_30d: number | null
  last_score_update_at: string | null
}

export interface RiskBreakdown {
  critical_risks: number
  high_risks: number
  medium_risks: number
  low_risks: number
  total_risks: number
  risk_trend_7d: string | null
  risk_trend_30d: string | null
}

export interface RiskCategories {
  crash_risks: number
  resource_leaks: number
  reliability_antipatterns: number
  scalability_risks: number
  edge_case_vulnerabilities: number
}

export interface FixMetrics {
  total_fixes_proposed: number
  total_fixes_approved: number
  total_fixes_applied: number
  total_fixes_failed: number
  fix_adoption_rate: number
  fix_success_rate: number
}

export interface PRMetrics {
  total_prs_analyzed: number
  prs_with_critical_risks: number
  prs_with_high_risks: number
  prs_with_no_risks: number
}

export interface RepoInsights {
  repository_id: number
  repository_name: string
  score: ReliabilityScore
  risk_breakdown: RiskBreakdown
  risk_categories: RiskCategories
  fix_metrics: FixMetrics
  pr_metrics: PRMetrics
  last_analysis_at: string | null
  last_fix_applied_at: string | null
}

export interface TrendDataPoint {
  date: string
  score: number
  critical_risks: number
  high_risks: number
  total_risks: number
}

/** Matches backend/app/routers/insights.py: GET /api/insights/repo/{repo_id} */
export function repoInsightsUrl(repoId: string): string {
  return apiUrl(`/api/insights/repo/${repoId}`)
}

/** Matches backend/app/routers/insights.py: GET /api/insights/repo/{repo_id}/trends */
export function repoTrendsUrl(repoId: string, days: number): string {
  return apiUrl(`/api/insights/repo/${repoId}/trends?days=${days}`)
}

export async function fetchRepoInsights(repoId: string): Promise<RepoInsights> {
  const response = await fetch(repoInsightsUrl(repoId))

  if (!response.ok) {
    throw new Error('Failed to load insights')
  }

  return response.json()
}

export async function fetchRepoTrends(
  repoId: string,
  days: number
): Promise<TrendDataPoint[]> {
  const response = await fetch(repoTrendsUrl(repoId, days))

  if (!response.ok) {
    throw new Error('Failed to load trends')
  }

  const data = await response.json()
  // The endpoint returns {data_points: [...]}. Defaulting to [] rather than
  // passing undefined through: the page maps over this value, and a response
  // missing the key would otherwise crash the chart instead of drawing nothing.
  return data.data_points ?? []
}

export function scoreColor(score: number): string {
  if (score >= 90) return 'text-green-600'
  if (score >= 80) return 'text-blue-600'
  if (score >= 70) return 'text-yellow-600'
  if (score >= 60) return 'text-orange-600'
  return 'text-red-600'
}

export function scoreBackgroundColor(score: number): string {
  if (score >= 90) return 'bg-green-50 border-green-200'
  if (score >= 80) return 'bg-blue-50 border-blue-200'
  if (score >= 70) return 'bg-yellow-50 border-yellow-200'
  if (score >= 60) return 'bg-orange-50 border-orange-200'
  return 'bg-red-50 border-red-200'
}

export interface TrendIndicator {
  label: string
  className: string
}

/** Arrow, magnitude and colour for a score delta. null means "no comparison yet". */
export function trendIndicator(change: number | null): TrendIndicator {
  if (change === null) return { label: '—', className: 'text-gray-400' }
  if (change > 0) return { label: `↑ ${change.toFixed(1)}`, className: 'text-green-600' }
  if (change < 0) {
    return { label: `↓ ${Math.abs(change).toFixed(1)}`, className: 'text-red-600' }
  }
  return { label: '— 0.0', className: 'text-gray-600' }
}

const RISK_TREND_CLASSES: Record<string, string> = {
  increasing: 'bg-red-100 text-red-700',
  stable: 'bg-blue-100 text-blue-700',
  decreasing: 'bg-green-100 text-green-700',
}

/**
 * Badge colour for a risk-trend string.
 *
 * Falls back to a neutral grey for anything the backend adds later. The previous
 * inline version indexed an object literal directly, so an unrecognised value
 * put the string "undefined" into the class list and the badge lost its
 * background entirely.
 */
export function riskTrendClassName(trend: string): string {
  return RISK_TREND_CLASSES[trend] ?? 'bg-gray-100 text-gray-700'
}
