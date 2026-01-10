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
      <main className="min-h-screen bg-background">
        <div className="px-6 py-6">
          {/* Header */}
          <div className="mb-4">
            <h1 className="text-lg font-medium text-muted-foreground">Analysis Runs</h1>
          </div>

          {error && <div className="mb-4"><ErrorAlert message={error} /></div>}

          {/* Controls */}
          <div className="mb-4 space-y-3">
            <div className="flex items-center gap-3">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-2.5 top-2 w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search repository, branch, ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-muted border border-border rounded text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary transition-colors"
                />
              </div>

              {/* Status filter */}
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-1.5 bg-muted border border-border rounded text-sm text-foreground focus:outline-none focus:border-primary transition-colors"
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
                className="px-3 py-1.5 bg-muted hover:bg-card border border-border text-foreground rounded text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-6 text-[11px] text-muted-foreground">
              <span>Total <span className="font-mono text-foreground ml-1">{runs.length}</span></span>
              <span>Completed <span className="font-mono text-foreground ml-1">{runs.filter(r => r.status === 'completed').length}</span></span>
              <span>Failed <span className="font-mono text-foreground ml-1">{runs.filter(r => r.status === 'failed').length}</span></span>
            </div>
          </div>

          {loading ? (
            <Loading />
          ) : filteredRuns.length === 0 ? (
            <div className="bg-card border border-border rounded p-8">
              <EmptyState message={searchQuery ? "No runs match your search" : "No runs found"} />
            </div>
          ) : (
            <div className="bg-card border border-border overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">id</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">repository</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">event</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">branch</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">status</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">issues</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground">created</th>
                      <th className="px-4 py-2 text-left text-[11px] font-medium text-muted-foreground"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {filteredRuns.map((run) => (
                      <tr
                        key={run.id}
                        onClick={() => router.push(`/runs/${run.id}`)}
                        className="border-l-2 border-transparent hover:border-primary hover:bg-muted/30 transition-colors cursor-pointer"
                      >
                        <td className="px-4 py-2 text-xs font-mono text-muted-foreground">#{run.id}</td>
                        <td className="px-4 py-2 text-sm font-medium text-foreground">{run.repository_name}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">{run.event}</td>
                        <td className="px-4 py-2 text-xs font-mono text-muted-foreground">{run.branch}</td>
                        <td className="px-4 py-2 text-xs">
                          <StatusBadge status={run.status} />
                        </td>
                        <td className="px-4 py-2 text-xs font-mono text-foreground">{run.total_results}</td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          {(() => {
                            const diff = Date.now() - new Date(run.created_at).getTime()
                            const minutes = Math.floor(diff / 60000)
                            const hours = Math.floor(minutes / 60)
                            const days = Math.floor(hours / 24)
                            if (days > 0) return `${days}d ago`
                            if (hours > 0) return `${hours}h ago`
                            if (minutes > 0) return `${minutes}m ago`
                            return 'just now'
                          })()}
                        </td>
                        <td className="px-4 py-2 text-xs text-muted-foreground">
                          →
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
