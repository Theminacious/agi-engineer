'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Header, Loading, ErrorAlert } from '@/components/layout'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import {
  TrendingUp,
  BarChart3,
  Filter,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertCircle,
  Percent,
} from 'lucide-react'

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AnalyticsPage() {
  const router = useRouter()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [issuesSummary, setIssuesSummary] = useState<any>(null)
  const [issuesByRepo, setIssuesByRepo] = useState<any>(null)
  const [trendingIssues, setTrendingIssues] = useState<any>(null)
  const [refreshing, setRefreshing] = useState(false)

  const token =
    typeof window !== 'undefined'
      ? localStorage.getItem('jwt_token')
      : null

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (token) headers['Authorization'] = `Bearer ${token}`

    return headers
  }

  const fetchAnalytics = async () => {
    try {
      setRefreshing(true)

      const headers = getHeaders()

      const [summaryRes, repoRes, trendingRes] = await Promise.all([
        fetch(`${API_BASE}/api/issues/summary?limit=100`, { headers }),
        fetch(`${API_BASE}/api/issues/by-repository?limit=50`, { headers }),
        fetch(
          `${API_BASE}/api/trending-issues?days=7&limit=15`,
          { headers }
        ),
      ])

      if (!summaryRes.ok || !repoRes.ok || !trendingRes.ok) {
        throw new Error('Failed to fetch analytics')
      }

      const [summary, byRepo, trending] = await Promise.all([
        summaryRes.json(),
        repoRes.json(),
        trendingRes.json(),
      ])

      setIssuesSummary(summary)
      setIssuesByRepo(byRepo)
      setTrendingIssues(trending)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Failed to fetch analytics'
      )
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!token) {
      router.push('/auth')
      return
    }

    fetchAnalytics()
  }, [token, router])

  if (loading) {
    return (
      <div className="bg-[#050505] min-h-screen text-white">
        <Header />
        <main className="flex h-[calc(100vh-64px)] items-center justify-center bg-[#050505]">
          <Loading />
        </main>
      </div>
    )
  }

  return (
    <div className="bg-[#050505] min-h-screen text-white font-sans selection:bg-blue-500/30">
      <Header />

      <main className="p-6 sm:p-8">
        <div className="mx-auto max-w-7xl space-y-8">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <h1 className="text-2xl font-bold tracking-tight text-white">
                Analytics
              </h1>
              <p className="text-sm text-gray-400">
                Overview of system health and issue resolution metrics.
              </p>
            </div>

            <button
              onClick={fetchAnalytics}
              disabled={refreshing}
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-white/10 bg-[#121214] text-gray-400 shadow-sm transition-colors hover:bg-white/5 hover:text-white disabled:opacity-50"
            >
              <RefreshCw
                className={`h-4 w-4 ${
                  refreshing ? 'animate-spin' : ''
                }`}
              />
            </button>
          </div>

          {error && <ErrorAlert message={error} />}

          {/* Key Metrics */}
          {issuesSummary && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                title="Total Issues"
                value={issuesSummary.total_issues}
                icon={Activity}
                description="Detected across repositories"
              />
              <MetricCard
                title="Fixed"
                value={issuesSummary.fixed_count}
                icon={CheckCircle2}
                description="Resolved automatically"
              />
              <MetricCard
                title="Unfixed"
                value={issuesSummary.unfixed_count}
                icon={AlertCircle}
                description="Pending resolution"
              />
              <MetricCard
                title="Fix Rate"
                value={`${issuesSummary.fix_rate.toFixed(1)}%`}
                icon={Percent}
                description="Overall efficiency"
              />
            </div>
          )}

          {/* Lower Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {/* Top Issue Types */}
            {issuesSummary && (
              <Card className="bg-[#121214] border-white/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-white">
                    <Filter className="h-4 w-4 text-gray-400" />
                    Top Issue Types
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {issuesSummary.issues_by_code
                    ?.slice(0, 8)
                    .map((issue: any) => (
                      <div
                        key={issue.code}
                        className="flex items-center justify-between text-sm"
                      >
                        <div className="min-w-0 pr-4">
                          <div className="font-mono text-xs font-medium text-gray-200">
                            {issue.code}
                          </div>
                          <div className="truncate text-[11px] text-gray-500">
                            {issue.name}
                          </div>
                        </div>
                        <span className="font-mono text-xs text-gray-400">
                          {issue.count}
                        </span>
                      </div>
                    ))}
                </CardContent>
              </Card>
            )}

            {/* Trending */}
            {trendingIssues && (
              <Card className="bg-[#121214] border-white/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-white">
                    <TrendingUp className="h-4 w-4 text-gray-400" />
                    Trending (7 Days)
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {trendingIssues.trending_issues
                    ?.slice(0, 8)
                    .map((issue: any) => (
                      <div
                        key={issue.code}
                        className="flex items-center justify-between text-sm"
                      >
                        <div className="min-w-0 pr-4">
                          <div className="font-mono text-xs font-medium text-gray-200">
                            {issue.code}
                          </div>
                          <div className="text-[11px] text-gray-500">
                            {issue.name}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-mono text-xs text-gray-200">
                            {issue.occurrences}
                          </div>
                          <div className="text-[10px] text-gray-500">
                            {issue.fixed} fixed
                          </div>
                        </div>
                      </div>
                    ))}
                </CardContent>
              </Card>
            )}

            {/* Distribution */}
            {issuesSummary && (
              <Card className="bg-[#121214] border-white/10">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base text-white">
                    <BarChart3 className="h-4 w-4 text-gray-400" />
                    Distribution
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">
                      Unique Issue Codes
                    </span>
                    <span className="font-mono font-medium text-white">
                      {
                        issuesSummary.issues_by_code?.filter(
                          (i: any) => i.code
                        ).length
                      }
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon: Icon,
  description,
}: {
  title: string
  value: string | number
  icon: any
  description: string
}) {
  return (
    <Card className="bg-[#121214] border-white/10">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-white">{title}</CardTitle>
        <Icon className="h-4 w-4 text-gray-400" />
      </CardHeader>
      <CardContent>
        <div className="font-mono text-2xl font-bold text-white">{value}</div>
        <p className="mt-1 text-xs text-gray-500">
          {description}
        </p>
      </CardContent>
    </Card>
  )
}