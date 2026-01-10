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
      setPrSuccess(`✓ PR queued successfully! ${result.fix_count} fixes will be applied to branch "${result.branch_name}"`)
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
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><Loading /></main>
    </>
  )

  if (error) return (
    <>
      <Header />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center gap-3 mb-6">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
          <Link href="/runs" className="text-sm text-gray-600 hover:text-gray-900">Back to Runs</Link>
        </div>
        <ErrorAlert message={error} />
      </main>
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
                <FileCode className="w-6 h-6 text-gray-400" />
                <h1 className="text-3xl font-bold text-gray-900">{data?.repository_name || `Run #${data?.id}`}</h1>
              </div>
              <p className="text-gray-600">Run #{data?.id} • Detailed analysis results and metadata</p>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/runs">
                <Button variant="ghost" className="flex items-center gap-2"><ArrowLeft className="w-4 h-4" />Back</Button>
              </Link>
              <Button onClick={fetchDetail} disabled={refreshing} className="flex items-center gap-2">
                <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              {fixedCount > 0 && (
                <Button 
                  onClick={() => setShowPRModal(true)} 
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white"
                >
                  <GitPullRequest className="w-4 h-4" />
                  Create PR ({fixedCount} fixes)
                </Button>
              )}
            </div>
          </div>

          {/* Summary cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {prSuccess && (
              <div className="col-span-full bg-green-50 border border-green-200 rounded-lg p-4 text-green-800">
                {prSuccess}
              </div>
            )}
            <Card>
              <CardHeader><CardTitle>Status</CardTitle></CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <StatusBadge status={data!.status} />
                  <Badge className="bg-amber-100 text-amber-800">{data!.total_results} issues</Badge>
                </div>
                <div className="mt-4 space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-700 w-24">Created:</span>
                    <span className="text-gray-900">{parseDateUtc(data!.created_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
                  </div>
                  {data!.started_at && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700 w-24">Started:</span>
                      <span className="text-gray-900">{parseDateUtc(data!.started_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
                    </div>
                  )}
                  {data!.completed_at && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700 w-24">Completed:</span>
                      <span className="text-gray-900">{parseDateUtc(data!.completed_at)?.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) ?? '—'}</span>
                    </div>
                  )}
                  {data!.started_at && data!.completed_at && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-700 w-24">Duration:</span>
                      <span className="text-gray-900">{formatDuration(data!.started_at, data!.completed_at)}</span>
                    </div>
                  )}
                </div>
                {data!.error && (
                  <div className="mt-3 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">Error: {data!.error}</div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Auto-Fix Summary</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Fixed Issues</span>
                    <span className="text-lg font-bold text-green-600">{data!.results.filter(r => r.is_fixed).length}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Unfixed Issues</span>
                    <span className="text-lg font-bold text-amber-600">{data!.results.filter(r => !r.is_fixed).length}</span>
                  </div>
                  <div className="mt-3 w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-green-500 h-2 rounded-full"
                      style={{ width: `${data!.results.length > 0 ? (data!.results.filter(r => r.is_fixed).length / data!.results.length * 100) : 0}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-600 text-center mt-1">
                    {data!.results.length > 0 ? ((data!.results.filter(r => r.is_fixed).length / data!.results.length * 100).toFixed(0)) : 0}% Success Rate
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader><CardTitle>Repository</CardTitle></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="text-sm font-medium text-gray-900">{data!.repository_name || `Repository ID: ${data!.repository_id}`}</div>
                  <div className="flex items-center gap-2">
                    <Badge className="bg-blue-100 text-blue-800 text-xs">{data!.event}</Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Results table */}
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
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
                      <TableCell colSpan={7}>
                        <div className="py-8 text-center text-gray-600">No issues found</div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    data!.results.map((r) => (
                      <TableRow key={r.id} className={`hover:bg-gray-50 ${r.is_fixed ? 'bg-green-50' : ''}`}>
                        <TableCell>
                          <code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 border border-gray-200">{r.file_path}</code>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-700">{r.line_number}</span>
                        </TableCell>
                        <TableCell>
                          <Badge className="bg-gray-100 text-gray-800">{r.code}</Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-900">{r.name}</span>
                        </TableCell>
                        <TableCell>
                          <CategoryBadge category={r.category} />
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-gray-700">{r.message}</span>
                        </TableCell>
                        <TableCell>
                          {r.is_fixed ? (
                            <Badge className='bg-green-100 text-green-700 border border-green-300'>
                              ✓ Fixed
                            </Badge>
                          ) : (
                            <Badge className='bg-amber-100 text-amber-700 border border-amber-300'>
                              ⋯ Unfixed
                            </Badge>
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
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-lg max-w-md w-full p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <GitPullRequest className="w-5 h-5" />
                    Create Pull Request
                  </h3>
                  <button
                    onClick={() => setShowPRModal(false)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    ✕
                  </button>
                </div>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Branch Name (optional)
                    </label>
                    <input
                      type="text"
                      value={prBranch}
                      onChange={(e) => setPrBranch(e.target.value)}
                      placeholder={`agi-engineer-fixes-run-${runId}`}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Leave empty for auto-generated branch name</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      PR Title (optional)
                    </label>
                    <input
                      type="text"
                      value={prTitle}
                      onChange={(e) => setPrTitle(e.target.value)}
                      placeholder={`🤖 Auto-fix issues from run #${runId}`}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      PR Description (optional)
                    </label>
                    <textarea
                      value={prBody}
                      onChange={(e) => setPrBody(e.target.value)}
                      placeholder={`Automatically fixed ${fixedCount} issues`}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
                    <strong>Note:</strong> This will create a PR with {fixedCount} fixed issues. Make sure your GitHub token is configured.
                  </div>

                  {error && (
                    <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
                      {error}
                    </div>
                  )}

                  <div className="flex gap-3 pt-2">
                    <Button
                      onClick={handleCreatePR}
                      disabled={creatingPR}
                      className="flex-1 bg-green-600 hover:bg-green-700 text-white"
                    >
                      {creatingPR ? 'Creating...' : 'Create PR'}
                    </Button>
                    <Button
                      onClick={() => setShowPRModal(false)}
                      variant="ghost"
                      disabled={creatingPR}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
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
