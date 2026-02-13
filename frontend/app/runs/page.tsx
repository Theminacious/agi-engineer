'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { listRuns, AnalysisRun } from '@/lib/api'
import { AppShell, Loading, ErrorAlert, StatusBadge } from '@/components/layout'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Search, Activity } from 'lucide-react'

export default function RunsPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchRuns = async (token: string) => {
    try {
      setIsRefreshing(true)
      const params = statusFilter !== 'all' ? { status: statusFilter, limit: 100 } : { limit: 100 }
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
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/auth')
      return
    }
    fetchRuns(token)
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

  const stats = {
    total: runs.length,
    completed: runs.filter(r => r.status === 'completed').length,
    failed: runs.filter(r => r.status === 'failed').length,
    inProgress: runs.filter(r => r.status === 'in_progress').length,
  }

  if (loading) {
    return (
      <AppShell>
        <Loading />
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Analysis Runs</h1>
          <p className="text-sm text-muted-foreground mt-1">History of all code analysis runs</p>
        </div>

        {error && <ErrorAlert message={error} />}

        {/* Stats */}
        <div className="flex items-center gap-6 text-xs text-muted-foreground">
          <span>Total <span className="font-mono text-foreground ml-1">{stats.total}</span></span>
          <span>Completed <span className="font-mono text-foreground ml-1">{stats.completed}</span></span>
          <span>Failed <span className="font-mono text-foreground ml-1">{stats.failed}</span></span>
          <span>In Progress <span className="font-mono text-foreground ml-1">{stats.inProgress}</span></span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search repository, branch, or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={statusFilter} onValueChange={(value: string) => setStatusFilter(value)}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="in_progress">In Progress</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Table */}
        <div className="border border-border rounded">
          {filteredRuns.length === 0 ? (
            <div className="p-12 text-center">
              <Activity className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-40" />
              <p className="text-sm text-muted-foreground">
                {searchQuery ? 'No runs match your search' : 'No runs found'}
              </p>
              {!searchQuery && (
                <p className="text-xs text-muted-foreground mt-1">Start an analysis from the Dashboard</p>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Repository</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>Event</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Issues</TableHead>
                  <TableHead className="text-right">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRuns.map((run) => (
                  <TableRow
                    key={run.id}
                    className="cursor-pointer hover:bg-muted/50 transition-colors"
                    onClick={() => router.push(`/runs/${run.id}`)}
                  >
                    <TableCell className="font-mono text-muted-foreground">#{run.id}</TableCell>
                    <TableCell className="font-medium">{run.repository_name}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">{run.branch}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">{run.event}</TableCell>
                    <TableCell><StatusBadge status={run.status} /></TableCell>
                    <TableCell className="text-right font-mono">{run.total_results}</TableCell>
                    <TableCell className="text-right text-sm text-muted-foreground">
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
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </AppShell>
  )
}
