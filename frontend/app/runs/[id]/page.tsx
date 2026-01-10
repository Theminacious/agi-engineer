'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getRunDetail, AnalysisRunDetail, API_BASE } from '@/lib/api'
import { Header, Loading, ErrorAlert, StatusBadge, CategoryBadge } from '@/components/layout'
import { Button, Badge, Table, TableHeader, TableRow, TableHead, TableBody, TableCell, Card, CardHeader, CardTitle, CardContent } from '@/components/ui'
import { ArrowLeft, RefreshCw, FileCode, GitBranch, GitPullRequest } from 'lucide-react'

export default function RunDetailPage() {
  const params = useParams()
  const router = useRouter()
  const runId = Number(params?.id)

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

  const token = useMemo(() => (typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null), [])

  const parseDateUtc = (value?: string | null) => {
    if (!value) return null
    // If the backend sent a naive timestamp, treat it as UTC
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        // Gracefully handle non-JSON error responses (e.g., HTML error pages)
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
      
      // Refresh data after a delay
      setTimeout(() => {
        fetchDetail()
      }, 2000)
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create PR')
    } finally {
      setCreatingPR(false)
    }
  }

  if (loading) return (
    <>
      <Header />
      <main className="px-6 py-6"><Loading /></main>
    </>
  )

  if (error) return (
    <>
      <Header />
      <main className="px-6 py-6">
        <div className="mb-4">
          <Link href="/runs" className="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Runs
          </Link>
        </div>
        <ErrorAlert message={error} />
      </main>
    </>
  )

  return (
    <>
      <Header />
      <main className="min-h-screen bg-background">
        <div className="px-6 py-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
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
              <button
                onClick={fetchDetail}
                disabled={refreshing}
                className="px-3 py-1.5 bg-muted hover:bg-card border border-border text-foreground rounded text-sm transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              </button>
              {fixedCount > 0 && (
                <button
                  onClick={() => setShowPRModal(true)}
                  className="px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded text-sm transition-colors flex items-center gap-2"
                >
                  <GitPullRequest className="w-3.5 h-3.5" />
                  Create PR ({fixedCount})
                </button>
              )}
            </div>
          </div>

          {/* Summary info */}
          {prSuccess && (
            <div className="mb-4 bg-card border border-primary rounded p-3 text-sm text-foreground">
              {prSuccess}
            </div>
          )}
          
          <div className="mb-4 bg-card border border-border border-l-2 border-l-primary rounded p-4">
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
          <div className="bg-card border border-border overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="sticky top-0 z-10 bg-card border-b border-border">
                  <TableRow>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">file</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">line</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">code</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">name</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">category</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">message</TableHead>
                    <TableHead className="text-[11px] font-medium text-muted-foreground bg-card">fixed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data!.results.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7}>
                        <div className="py-8 text-center text-muted-foreground text-sm">No issues found</div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data!.results.map((r) => (
                      <TableRow key={r.id} className="border-l-2 border-transparent hover:border-primary hover:bg-muted/20 transition-colors">
                        <TableCell className="font-mono text-sm text-foreground max-w-xs truncate">{r.file_path}</TableCell>
                        <TableCell className="font-mono text-xs bg-muted px-2 py-1 text-muted-foreground">{r.line_number}</TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">{r.code}</TableCell>
                        <TableCell className="text-xs text-foreground">{r.name}</TableCell>
                        <TableCell className="text-xs"><CategoryBadge category={r.category} /></TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-lg">{r.message}</TableCell>
                        <TableCell className="text-xs">
                          {r.is_fixed ? (
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted border border-border text-foreground">
                              Fixed
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-muted border border-border text-muted-foreground">
                              —
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* PR Creation Modal */}
          {showPRModal && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
              <div className="bg-card border border-border rounded max-w-md w-full p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-medium flex items-center gap-2 text-foreground">
                    <GitPullRequest className="w-4 h-4" />
                    Create Pull Request
                  </h3>
                  <button
                    onClick={() => setShowPRModal(false)}
                    className="text-muted-foreground hover:text-foreground text-sm"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      Branch Name (optional)
                    </label>
                    <input
                      type="text"
                      value={prBranch}
                      onChange={(e) => setPrBranch(e.target.value)}
                      placeholder={`agi-engineer-fixes-run-${runId}`}
                      className="w-full px-3 py-1.5 bg-muted border border-border rounded text-sm text-foreground focus:outline-none focus:border-primary"
                    />
                    <p className="text-[11px] text-muted-foreground mt-1">Leave empty for auto-generated name</p>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      PR Title (optional)
                    </label>
                    <input
                      type="text"
                      value={prTitle}
                      onChange={(e) => setPrTitle(e.target.value)}
                      placeholder={`Auto-fix issues from run #${runId}`}
                      className="w-full px-3 py-1.5 bg-muted border border-border rounded text-sm text-foreground focus:outline-none focus:border-primary"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">
                      PR Description (optional)
                    </label>
                    <textarea
                      value={prBody}
                      onChange={(e) => setPrBody(e.target.value)}
                      placeholder={`Automatically fixed ${fixedCount} issues`}
                      rows={3}
                      className="w-full px-3 py-1.5 bg-muted border border-border rounded text-sm text-foreground focus:outline-none focus:border-primary"
                    />
                  </div>

                  <div className="bg-card border border-primary rounded p-3 text-xs text-foreground">
                    This will create a PR with {fixedCount} fixed issues
                  </div>

                  {error && (
                    <div className="bg-card border border-destructive rounded p-3 text-xs text-destructive">
                      {error}
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleCreatePR}
                      disabled={creatingPR}
                      className="flex-1 px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded text-sm transition-colors disabled:opacity-50"
                    >
                      {creatingPR ? 'Creating...' : 'Create PR'}
                    </button>
                    <button
                      onClick={() => setShowPRModal(false)}
                      disabled={creatingPR}
                      className="flex-1 px-3 py-1.5 bg-muted hover:bg-card border border-border text-foreground rounded text-sm transition-colors disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
