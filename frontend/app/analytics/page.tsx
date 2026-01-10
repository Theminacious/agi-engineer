'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Header, Loading, ErrorAlert } from '@/components/layout'
import { Badge, Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { TrendingUp, BarChart3, Filter, RefreshCw } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AnalyticsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [issuesSummary, setIssuesSummary] = useState<any>(null)
  const [issuesByRepo, setIssuesByRepo] = useState<any>(null)
  const [trendingIssues, setTrendingIssues] = useState<any>(null)
  const [refreshing, setRefreshing] = useState(false)

  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    return headers
  }

  const fetchAnalytics = async () => {
    try {
      setRefreshing(true)
      const headers = getHeaders()

      // Fetch all analytics in parallel
      const [summaryRes, repoRes, trendingRes] = await Promise.all([
        fetch(`${API_BASE}/api/issues/summary?limit=100`, { headers }),
        fetch(`${API_BASE}/api/issues/by-repository?limit=50`, { headers }),
        fetch(`${API_BASE}/api/trending-issues?days=7&limit=15`, { headers }),
      ])

      if (!summaryRes.ok || !repoRes.ok || !trendingRes.ok) throw new Error('Failed to fetch analytics')

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
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics')
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

  if (loading) return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><Loading /></main>
    </>
  )

  return (
    <>
      <Header />
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <BarChart3 className="w-6 h-6 text-gray-400" />
                <h1 className="text-3xl font-bold text-gray-900">Issue Analytics</h1>
              </div>
              <p className="text-gray-600">Comprehensive overview of all code issues across your repositories</p>
            </div>
            <button
              onClick={fetchAnalytics}
              disabled={refreshing}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {error && <div className="mb-6"><ErrorAlert message={error} /></div>}

          {/* Summary Stats */}
          {issuesSummary && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <Card>
                <CardHeader><CardTitle className="text-sm">Total Issues</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-gray-900">{issuesSummary.total_issues}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">Fixed Issues</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-green-600">{issuesSummary.fixed_count}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">Unfixed Issues</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-amber-600">{issuesSummary.unfixed_count}</div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader><CardTitle className="text-sm">Fix Rate</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold text-blue-600">{issuesSummary.fix_rate.toFixed(1)}%</div>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top Issues by Type */}
            {issuesSummary && (
              <Card>
                <CardHeader><CardTitle>Top Issue Types</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {issuesSummary.issues_by_code?.slice(0, 10).map((issue: any) => (
                      <div key={issue.code} className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-sm text-gray-900">{issue.code}</div>
                          <div className="text-xs text-gray-600 truncate">{issue.name}</div>
                        </div>
                        <Badge className="bg-blue-100 text-blue-800">{issue.count}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Trending Issues */}
            {trendingIssues && (
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-orange-500" />
                    <CardTitle>Trending Issues (7 days)</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {trendingIssues.trending_issues?.slice(0, 10).map((issue: any) => (
                      <div key={issue.code} className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-sm text-gray-900">{issue.code}</div>
                          <div className="text-xs text-gray-600">{issue.name}</div>
                        </div>
                        <div className="text-right">
                          <div className="font-semibold text-sm">{issue.occurrences}</div>
                          <div className="text-xs text-green-600">{issue.fixed} fixed</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Category Distribution */}
            {issuesSummary && (
              <Card>
                <CardHeader><CardTitle>Categories</CardTitle></CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700">Suggestions</span>
                        <Badge className="bg-blue-100 text-blue-800">{issuesSummary.issues_by_code?.filter((i: any) => i.code).length || 0}</Badge>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div className="bg-blue-500 h-2 rounded-full" style={{ width: '100%' }} />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Issues by Repository */}
          {issuesByRepo && issuesByRepo.repositories?.length > 0 && (
            <div className="mt-8">
              <Card>
                <CardHeader><CardTitle>Issues by Repository</CardTitle></CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-200 bg-gray-50">
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Repository</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Total</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Fixed</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Unfixed</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase">Fix Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200">
                        {issuesByRepo.repositories?.map((repo: any) => (
                          <tr key={repo.repository_id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 text-sm font-medium text-gray-900">{repo.repository_name}</td>
                            <td className="px-6 py-4 text-sm text-gray-600">{repo.total_issues}</td>
                            <td className="px-6 py-4 text-sm text-green-600 font-semibold">{repo.fixed_issues}</td>
                            <td className="px-6 py-4 text-sm text-amber-600">{repo.unfixed_issues}</td>
                            <td className="px-6 py-4 text-sm">
                              <Badge className={repo.fix_rate > 50 ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}>
                                {repo.fix_rate.toFixed(1)}%
                              </Badge>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
