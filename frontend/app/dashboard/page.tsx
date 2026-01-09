'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { listRuns, AnalysisRun } from '@/lib/api'
import { Header, Loading, ErrorAlert, StatusBadge, EmptyState } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Badge } from '@/components/ui'
import Link from 'next/link'
import { TrendingUp, Code2, AlertCircle, CheckCircle2, Clock, ArrowRight } from 'lucide-react'

export default function DashboardPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/auth')
      return
    }

    fetchRuns(token)
  }, [router])

  const fetchRuns = async (token: string) => {
    try {
      setLoading(true)
      const data = await listRuns({ limit: 10 }, token)
      setRuns(data)
      setError(null)
    } catch (err) {
      const message = (err as Error).message || 'Failed to fetch runs'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  // Calculate stats
  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === 'completed').length,
    failed: runs.filter((r) => r.status === 'failed').length,
    pending: runs.filter((r) => r.status === 'pending').length,
    totalIssues: runs.reduce((sum, r) => sum + r.total_results, 0),
  }

  const successRate = stats.total > 0 ? ((stats.completed / stats.total) * 100).toFixed(1) : 'N/A'

  return (
    <>
      <Header />
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Page Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <p className="text-gray-600 mt-2">Overview of your code analysis activity</p>
          </div>

          {error && <div className="mb-6"><ErrorAlert message={error} /></div>}

          {loading ? (
            <Loading />
          ) : (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                {/* Total Runs */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-300 transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Total Runs</p>
                      <h3 className="text-3xl font-bold text-gray-900">{stats.total}</h3>
                    </div>
                    <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                      <Code2 className="w-5 h-5 text-blue-600" />
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-4">
                    <span className="text-green-600 font-semibold">{stats.completed}</span> completed
                  </p>
                </div>

                {/* Completed */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-300 transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Successful</p>
                      <h3 className="text-3xl font-bold text-green-600">{stats.completed}</h3>
                    </div>
                    <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center">
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-4">
                    {stats.total > 0 ? ((stats.completed / stats.total) * 100).toFixed(1) : '0'}% success rate
                  </p>
                </div>

                {/* Issues */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-300 transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Issues Found</p>
                      <h3 className="text-3xl font-bold text-amber-600">{stats.totalIssues}</h3>
                    </div>
                    <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center">
                      <AlertCircle className="w-5 h-5 text-amber-600" />
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-4">
                    Across all analysis runs
                  </p>
                </div>

                {/* Pending */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-300 transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600 mb-1">Pending</p>
                      <h3 className="text-3xl font-bold text-gray-600">{stats.pending}</h3>
                    </div>
                    <div className="w-10 h-10 bg-gray-50 rounded-lg flex items-center justify-center">
                      <Clock className="w-5 h-5 text-gray-400" />
                    </div>
                  </div>
                  <p className="text-xs text-gray-600 mt-4">
                    In progress
                  </p>
                </div>
              </div>

              {/* Recent Runs Card */}
              <div className="bg-white rounded-lg border border-gray-200">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="w-5 h-5 text-gray-400" />
                    <div>
                      <h2 className="text-lg font-semibold text-gray-900">Recent Analysis</h2>
                      <p className="text-sm text-gray-600 mt-1">Latest code analysis runs</p>
                    </div>
                  </div>
                  <Link
                    href="/runs"
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition"
                  >
                    View All
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>

                {/* Content */}
                <div>
                  {runs.length === 0 ? (
                    <div className="p-12 text-center">
                      <EmptyState message="No analysis runs yet. Start analyzing your repositories!" icon="📊" />
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-200">
                      {runs.slice(0, 5).map((run) => (
                        <Link
                          key={run.id}
                          href={`/runs/${run.id}`}
                          className="block p-6 hover:bg-gray-50 transition border-l-4 border-transparent hover:border-l-blue-600"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h3 className="font-semibold text-gray-900">
                                  Run #{run.id}
                                </h3>
                                <Badge variant="secondary" className="text-xs">
                                  {run.event}
                                </Badge>
                              </div>
                              <p className="text-sm text-gray-600 mb-2">
                                Branch: <code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700">{run.branch}</code>
                              </p>
                              <p className="text-xs text-gray-500">
                                {new Date(run.created_at).toLocaleString()}
                              </p>
                            </div>

                            <div className="flex items-center gap-6 text-right ml-4">
                              <div>
                                <div className="text-2xl font-bold text-amber-600 mb-1">
                                  {run.total_results}
                                </div>
                                <p className="text-xs text-gray-600">issues</p>
                              </div>
                              <StatusBadge status={run.status} />
                              <span className="text-gray-400 text-lg">
                                →
                              </span>
                            </div>
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  )
}
