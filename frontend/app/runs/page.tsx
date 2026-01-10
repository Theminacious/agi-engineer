'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { listRuns, AnalysisRun } from '@/lib/api'
import { Header, Loading, ErrorAlert, EmptyState, StatusBadge } from '@/components/layout'
import { Badge } from '@/components/ui'
import Link from 'next/link'
import { RefreshCw, Search, TrendingUp } from 'lucide-react'

export default function RunsPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchRuns = async (token: string) => {
    try {
      setIsRefreshing(true)
      const params = statusFilter ? { status: statusFilter, limit: 100 } : { limit: 100 }
      const data = await listRuns(params, token)
      setRuns(data)
      setError(null)
    } catch (err) {
      const message = (err as Error).message || 'Failed to fetch runs'
      setError(message)
    } finally {
      setIsRefreshing(false)
      setLoading(false)
    }
  }

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/auth')
      return
    }

    fetchRuns(token)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, router])

  const handleRefresh = () => {
    const token = localStorage.getItem('jwt_token')
    if (token) fetchRuns(token)
  }

  const filteredRuns = runs.filter((run) =>
    run.branch.toLowerCase().includes(searchQuery.toLowerCase()) ||
    run.id.toString().includes(searchQuery) ||
    run.repository_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <>
      <Header />
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-6 h-6 text-gray-400" />
              <h1 className="text-3xl font-bold text-gray-900">All Analysis Runs</h1>
            </div>
            <p className="text-gray-600">Complete history of your code analysis</p>
          </div>

          {error && <div className="mb-6"><ErrorAlert message={error} /></div>}

          {/* Controls */}
          <div className="mb-8 space-y-4">
            {/* Search and filter bar */}
            <div className="flex flex-col md:flex-row gap-3">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by repository, branch, or run ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                />
              </div>

              {/* Status filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-4 py-2.5 bg-white border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
              >
                <option value="">All Status</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>

              {/* Refresh button */}
              <button
                onClick={handleRefresh}
                disabled={isRefreshing}
                className="px-4 py-2.5 bg-white hover:bg-gray-50 border border-gray-300 text-gray-700 rounded-lg font-medium transition-all flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>

            {/* Stats */}
            <div className="flex gap-6 text-sm text-gray-600">
              <span>Total: <span className="text-gray-900 font-semibold">{runs.length}</span></span>
              <span>Completed: <span className="text-green-600 font-semibold">{runs.filter(r => r.status === 'completed').length}</span></span>
              <span>Failed: <span className="text-red-600 font-semibold">{runs.filter(r => r.status === 'failed').length}</span></span>
            </div>
          </div>

          {loading ? (
            <Loading />
          ) : filteredRuns.length === 0 ? (
            <div className="bg-white rounded-lg border border-gray-200 p-12">
              <EmptyState message={searchQuery ? "No runs match your search" : "No runs found"} icon="📊" />
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 bg-gray-50">
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">ID</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Repository</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Event</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Branch</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Issues</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Created</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wide">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filteredRuns.map((run) => (
                      <tr
                        key={run.id}
                        className="hover:bg-gray-50 transition-colors"
                      >
                        <td className="px-6 py-4 text-sm font-semibold text-blue-600">#{run.id}</td>
                        <td className="px-6 py-4 text-sm font-medium text-gray-900">{run.repository_name}</td>
                        <td className="px-6 py-4 text-sm text-gray-900">{run.event}</td>
                        <td className="px-6 py-4 text-sm">
                          <code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 border border-gray-200">{run.branch}</code>
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <StatusBadge status={run.status} />
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <span className="text-amber-600 font-semibold">{run.total_results}</span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {new Date(run.created_at).toLocaleString('en-US', { 
                            month: 'short', 
                            day: 'numeric', 
                            year: 'numeric',
                            hour: 'numeric', 
                            minute: '2-digit',
                            hour12: true 
                          })}
                        </td>
                        <td className="px-6 py-4 text-sm">
                          <Link
                            href={`/runs/${run.id}`}
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-600 text-xs font-semibold transition-all"
                          >
                            View
                            <span>→</span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
