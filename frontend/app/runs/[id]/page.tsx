'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getRunDetail, AnalysisRunDetail, API_BASE } from '@/lib/api'
import { AppShell, Loading, ErrorAlert, StatusBadge } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import ExecutionCoverage from '@/components/runs/ExecutionCoverage'
import { usePlanSelection } from '@/hooks/usePlanSelection'
import { ArrowLeft, RefreshCw, FileCode, GitBranch, GitPullRequest, Wrench, ExternalLink, CheckCircle2 } from 'lucide-react'

export default function RunDetailPage() {
  const params = useParams()
  const router = useRouter()
  const runId = Number(params?.id)
  const { plan } = usePlanSelection()

  const [data, setData] = useState<AnalysisRunDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [showPRModal, setShowPRModal] = useState(false)
  const [prBranch, setPrBranch] = useState('')
  const [prTitle, setPrTitle] = useState('')
  const [prBody, setPrBody] = useState('')
  const [creatingPR, setCreatingPR] = useState(false)
  const [prSuccess, setPrSuccess] = useState<string | null>(null)
  const [fixSummary, setFixSummary] = useState<{proposed: number, approved: number, applied: number, failed: number} | null>(null)

  const token = useMemo(() => (typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null), [])

  const parseDateUtc = (value?: string | null) => {
    if (!value) return null
    const normalized = value.endsWith('Z') ? value : `${value}Z`
    const dt = new Date(normalized)
    return Number.isNaN(dt.getTime()) ? null : dt
  }

  const fetchDetail = async () => {
    try {
      setRefreshing(true)
      const result = await getRunDetail(runId, token ?? undefined)
      setData(result)
      setError(null)
      
      try {
        const fixResponse = await fetch(`${API_BASE}/api/fixes/run/${runId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        if (fixResponse.ok) {
          const fixData = await fixResponse.json()
          setFixSummary(fixData.status_counts || null)
        }
      } catch (fixErr) {
        console.error('Failed to fetch fix summary:', fixErr)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch run')
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
    fetchDetail()
  }, [runId])

  const fixedCount = data?.results.filter(r => r.is_fixed).length || 0

  const formatDuration = (start?: string | null, end?: string | null) => {
    if (!start || !end) return '—'
    const startMs = new Date(start).getTime()
    const endMs = new Date(end).getTime()
    if (Number.isNaN(startMs) || Number.isNaN(endMs)) return '—'
    const totalSeconds = Math.max(0, Math.round((endMs - startMs) / 1000))
    const minutes = Math.floor(totalSeconds / 60)
    const seconds = totalSeconds % 60
    if (minutes > 0) return `${minutes}m ${seconds}s (${totalSeconds}s)`
    return `${seconds}s`
  }

  const handleCreatePR = async () => {
    if (!token) return
    
    try {
      setCreatingPR(true)
      setError(null)
      setPrSuccess(null)
      
      const response = await fetch(`${API_BASE}/api/runs/${runId}/create-pr`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          branch_name: prBranch || undefined,
          pr_title: prTitle || undefined,
          pr_body: prBody || undefined
        })
      })
      
      if (!response.ok) {
        const contentType = response.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          const errorData = await response.json()
          throw new Error(typeof errorData === 'object' && errorData.detail ? errorData.detail : 'Failed to create PR')
        }
        const text = await response.text()
        throw new Error(text || 'Failed to create PR')
      }
      
      const result = await response.json()
      setPrSuccess(`PR queued successfully! ${result.fix_count} fixes will be applied to branch "${result.branch_name}"`)
      setShowPRModal(false)
      setPrBranch('')
      setPrTitle('')
      setPrBody('')
      
      setTimeout(() => {
        fetchDetail()
      }, 2000)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create PR')
    } finally {
      setCreatingPR(false)
    }
  }

  if (loading) {
    return (
      <AppShell>
        <Loading />
      </AppShell>
    )
  }

  if (error) {
    return (
      <AppShell>
        <div className="max-w-7xl mx-auto px-6 py-8 space-y-4">
          <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Runs
          </Link>
          <ErrorAlert message={error} />
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
                <ArrowLeft className="w-3.5 h-3.5" />
              </Link>
              <div>
                <h1 className="text-lg font-semibold text-foreground">{data?.repository_name || `Run #${data?.id}`}</h1>
                <p className="text-xs text-muted-foreground">Run #{data?.id} • {data?.event}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="icon" onClick={fetchDetail} disabled={refreshing}>
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
              {fixedCount > 0 && (
                <Button onClick={() => setShowPRModal(true)}>
                  <GitPullRequest className="w-4 h-4 mr-2" />
                  Create PR ({fixedCount})
                </Button>
              )}
            </div>
          </div>

        {/* Success message */}
        {prSuccess && (
          <div className="border border-green-500/20 bg-green-500/10 rounded p-4 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
            <p className="text-sm text-foreground">{prSuccess}</p>
          </div>
        )}

        {/* Execution Coverage */}
        <ExecutionCoverage 
              plan={plan}
              executedAnalyzers={[
                'architectural',
                'abstraction',
                'api_contracts',
                'god_objects',
                'performance',
                'concurrency',
                'security',
                'test_coverage',
                'broken_invariants',
                'configuration',
                'dependencies'
              ]}
              skippedAnalyzers={[]}
            />

        {/* Fix Summary */}
        {fixSummary && (fixSummary.proposed > 0 || fixSummary.approved > 0 || fixSummary.applied > 0 || fixSummary.failed > 0) && (
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Wrench className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-semibold">Fix Summary</h3>
                </div>
                <Link 
                  href={`/governance/run-${runId}`}
                  className="text-xs text-muted-foreground hover:text-foreground font-medium flex items-center gap-1"
                >
                  Review in Governance
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
              <div className="grid grid-cols-4 gap-3">
                <div className="border border-border rounded p-3">
                  <div className="text-lg font-semibold">{fixSummary.proposed}</div>
                  <div className="text-xs text-muted-foreground">Proposed</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-lg font-semibold">{fixSummary.approved}</div>
                  <div className="text-xs text-muted-foreground">Approved</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-lg font-semibold">{fixSummary.applied}</div>
                  <div className="text-xs text-muted-foreground">Applied</div>
                </div>
                <div className="border border-border rounded p-3">
                  <div className="text-lg font-semibold">{fixSummary.failed}</div>
                  <div className="text-xs text-muted-foreground">Failed</div>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                All fix actions (approve, reject, apply) must be performed in Governance for audit compliance.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Summary */}
        <div className="border border-border border-l-2 border-l-primary rounded p-4">
            <div className="grid grid-cols-3 gap-6 text-xs">
              <div>
                <div className="text-muted-foreground mb-1">Status</div>
                <StatusBadge status={data!.status} />
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Total Issues</div>
                <div className="font-mono text-sm text-foreground">{data!.total_results}</div>
              </div>
              <div>
                <div className="text-muted-foreground mb-1">Fixed</div>
                <div className="font-mono text-sm text-foreground">{data!.results.filter(r => r.is_fixed).length}</div>
              </div>
            </div>
            
            <div className="mt-4 pt-4 border-t border-border space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Success Rate</span>
                <span className="font-mono text-foreground">
                  {data!.results.length > 0 ? ((data!.results.filter(r => r.is_fixed).length / data!.results.length * 100).toFixed(0)) : 0}%
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Created</span>
                <span className="text-foreground">{parseDateUtc(data!.created_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
              </div>
              {data!.started_at && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Started</span>
                  <span className="text-foreground">{parseDateUtc(data!.started_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
                </div>
              )}
              {data!.completed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Completed</span>
                  <span className="text-foreground">{parseDateUtc(data!.completed_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
                </div>
              )}
              {data!.started_at && data!.completed_at && (
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Duration</span>
                  <span className="font-mono text-foreground">{formatDuration(data!.started_at, data!.completed_at)}</span>
                </div>
              )}
            </div>
            
            {data!.error && (
              <div className="mt-3 pt-3 border-t border-border text-xs text-destructive">
                Error: {data!.error}
              </div>
            )}
        </div>

        {/* Results table */}
        <div className="border border-border rounded">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File</TableHead>
                <TableHead>Line</TableHead>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Fixed</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data!.results.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="h-32 text-center">
                    <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-green-400 opacity-40" />
                    <p className="text-sm text-muted-foreground">No issues found</p>
                    <p className="text-xs text-muted-foreground mt-1">This codebase looks great!</p>
                  </TableCell>
                </TableRow>
              ) : (
                data!.results.map((r) => (
                  <TableRow key={r.id} className="cursor-pointer hover:bg-muted/50 transition-colors">
                    <TableCell className="font-mono text-sm max-w-xs truncate">{r.file_path}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">{r.line_number}</TableCell>
                    <TableCell className="font-mono text-sm text-muted-foreground">{r.code}</TableCell>
                    <TableCell className="text-sm">{r.name}</TableCell>
                    <TableCell><Badge variant="secondary" className="capitalize">{r.category}</Badge></TableCell>
                    <TableCell className="text-sm text-muted-foreground max-w-lg">{r.message}</TableCell>
                    <TableCell>
                      {r.is_fixed ? (
                        <Badge variant="default">Fixed</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* PR Creation Modal */}
        <Dialog open={showPRModal} onOpenChange={setShowPRModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <GitPullRequest className="w-4 h-4" />
                Create Pull Request
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="pr-branch">Branch Name (optional)</Label>
                <Input
                  id="pr-branch"
                  value={prBranch}
                  onChange={(e) => setPrBranch(e.target.value)}
                  placeholder={`agi-engineer-fixes-run-${runId}`}
                  disabled={creatingPR}
                />
                <p className="text-xs text-muted-foreground">Leave empty for auto-generated name</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="pr-title">PR Title (optional)</Label>
                <Input
                  id="pr-title"
                  value={prTitle}
                  onChange={(e) => setPrTitle(e.target.value)}
                  placeholder={`Auto-fix issues from run #${runId}`}
                  disabled={creatingPR}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="pr-body">PR Description (optional)</Label>
                <Textarea
                  id="pr-body"
                  value={prBody}
                  onChange={(e) => setPrBody(e.target.value)}
                  placeholder={`Automatically fixed ${fixedCount} issues`}
                  rows={3}
                  disabled={creatingPR}
                />
              </div>

              <div className="border border-border rounded p-3 text-sm">
                This will create a PR with {fixedCount} fixed issues
              </div>

              {error && (
                <div className="border border-destructive rounded p-3 text-sm text-destructive">
                  {error}
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowPRModal(false)} disabled={creatingPR}>
                Cancel
              </Button>
              <Button onClick={handleCreatePR} disabled={creatingPR}>
                {creatingPR ? 'Creating...' : 'Create PR'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </AppShell>
  )
}
