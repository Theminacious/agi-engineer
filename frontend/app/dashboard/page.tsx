'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { listRuns, AnalysisRun } from '@/lib/api'
import { AppShell, Loading, ErrorAlert, StatusBadge } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { 
  Activity,
  CheckCircle2, 
  AlertCircle, 
  Clock,
  Plus,
  ExternalLink
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function DashboardPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showImportModal, setShowImportModal] = useState(false)
  const [importing, setImporting] = useState(false)
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')

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
      setError((err as Error).message || 'Failed to fetch runs')
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    if (!repoUrl.trim()) {
      setError('Repository URL is required')
      return
    }

    try {
      setImporting(true)
      setError(null)
      
      const token = localStorage.getItem('jwt_token')
      if (!token) throw new Error('Not authenticated')

      const response = await fetch(`${API_BASE}/api/analysis/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          repository_url: repoUrl.trim(),
          branch: branch.trim(),
          event: 'manual',
          auto_fix: false,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to import repository')
      }

      setShowImportModal(false)
      setRepoUrl('')
      setBranch('main')
      await fetchRuns(token)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1">Mission control for code analysis</p>
          </div>
          <Button onClick={() => setShowImportModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            New Analysis
          </Button>
        </div>

        {error && <ErrorAlert message={error} />}

        {/* Metrics */}
        <div className="grid grid-cols-4 gap-6">
          <div className="border border-border rounded p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Activity className="w-4 h-4" />
              <span>Total Runs</span>
            </div>
            <div className="text-3xl font-semibold tracking-tight tabular-nums">{stats.total}</div>
          </div>
          <div className="border border-border rounded p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>Completed</span>
            </div>
            <div className="text-3xl font-semibold tracking-tight tabular-nums">{stats.completed}</div>
          </div>
          <div className="border border-border rounded p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <AlertCircle className="w-4 h-4" />
              <span>Failed</span>
            </div>
            <div className="text-3xl font-semibold tracking-tight tabular-nums">{stats.failed}</div>
          </div>
          <div className="border border-border rounded p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
              <Clock className="w-4 h-4" />
              <span>In Progress</span>
            </div>
            <div className="text-3xl font-semibold tracking-tight tabular-nums">{stats.inProgress}</div>
          </div>
        </div>

        {/* Recent Runs Table */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent Runs</h2>
            <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
              View all
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          
          <div className="border border-border rounded">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Repository</TableHead>
                  <TableHead>Branch</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Issues</TableHead>
                  <TableHead className="text-right">Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-32 text-center text-sm text-muted-foreground">
                      No analysis runs yet. Click &quot;New Analysis&quot; to get started.
                    </TableCell>
                  </TableRow>
                ) : (
                  runs.map(run => (
                    <TableRow key={run.id} className="cursor-pointer hover:bg-muted/50 transition-colors" onClick={() => router.push(`/runs/${run.id}`)}>
                      <TableCell className="font-medium">{run.repository_name}</TableCell>
                      <TableCell className="text-muted-foreground text-sm font-mono">{run.branch}</TableCell>
                      <TableCell><StatusBadge status={run.status} /></TableCell>
                      <TableCell className="text-right font-mono text-sm">{run.total_results}</TableCell>
                      <TableCell className="text-right text-sm text-muted-foreground">
                        {new Date(run.created_at).toLocaleDateString('en-US', { 
                          month: 'short', 
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>

      {/* Import Dialog */}
      <Dialog open={showImportModal} onOpenChange={setShowImportModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start New Analysis</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {error && <ErrorAlert message={error} />}
            <div className="space-y-2">
              <Label htmlFor="repo-url">Repository URL</Label>
              <Input
                id="repo-url"
                placeholder="https://github.com/owner/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                disabled={importing}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="branch">Branch</Label>
              <Input
                id="branch"
                placeholder="main"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={importing}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowImportModal(false)} disabled={importing}>
              Cancel
            </Button>
            <Button onClick={handleImport} disabled={importing || !repoUrl.trim()}>
              {importing ? 'Starting...' : 'Start Analysis'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}