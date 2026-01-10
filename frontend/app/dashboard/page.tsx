'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { listRuns, AnalysisRun } from '@/lib/api'
import { Header, Loading, ErrorAlert, StatusBadge, EmptyState } from '@/components/layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, Badge, Button } from '@/components/ui'
import Link from 'next/link'
import { TrendingUp, Code2, AlertCircle, CheckCircle2, Clock, ArrowRight, Plus, X, Loader } from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Repository {
  id: number
  name: string
  url: string
  branch: string
}

export default function DashboardPage() {
  const router = useRouter()
  const [runs, setRuns] = useState<AnalysisRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showImportModal, setShowImportModal] = useState(false)
  const [importingRepo, setImportingRepo] = useState(false)
  const [repoUrl, setRepoUrl] = useState('')
  const [repoBranch, setRepoBranch] = useState('main')
  const [enableAutoFix, setEnableAutoFix] = useState(true)

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

  const handleImportRepository = async () => {
    // Validate input
    const trimmedUrl = repoUrl.trim()
    if (!trimmedUrl) {
      setError('Repository URL is required')
      return
    }

    // Basic URL format validation
    const isValidUrl = /^(https:\/\/github\.com\/|git@github\.com:)[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+(\.git)?$/.test(trimmedUrl)
    if (!isValidUrl) {
      setError('Invalid GitHub URL. Expected format: https://github.com/owner/repo')
      return
    }

    // Validate branch name
    const trimmedBranch = repoBranch.trim()
    if (!trimmedBranch || !/^[a-zA-Z0-9._/-]+$/.test(trimmedBranch)) {
      setError('Invalid branch name. Use alphanumeric characters, hyphens, underscores, and slashes only.')
      return
    }

    try {
      setImportingRepo(true)
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
          repository_url: trimmedUrl,
          branch: trimmedBranch,
          event: 'manual',
          auto_fix: enableAutoFix,
        }),
      })

      const data = await response.json()
      
      if (!response.ok) {
        // Extract error message from response
        const errorMsg = typeof data === 'object' && data !== null && 'detail' in data
          ? data.detail
          : typeof data === 'string'
          ? data
          : `HTTP ${response.status}: Failed to import repository`
        throw new Error(errorMsg)
      }

      setShowImportModal(false)
      setRepoUrl('')
      setRepoBranch('main')
      setEnableAutoFix(true)
      setError(null)
      
      // Refresh runs immediately
      const t = localStorage.getItem('jwt_token')
      if (t) await fetchRuns(t)
    } catch (err) {
      const message = err instanceof Error 
        ? err.message 
        : typeof err === 'string'
        ? err
        : 'Failed to import repository'
      setError(message)
      console.error('Import error:', err)
    } finally {
      setImportingRepo(false)
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
      <main className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto px-6 py-8">
          {/* Page Header */}
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
              <p className="text-muted-foreground mt-1">Overview of your code analysis activity</p>
            </div>
            <button
              onClick={() => setShowImportModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded font-medium transition"
            >
              <Plus className="w-4 h-4" />
              Import Repository
            </button>
          </div>

          {error && <div className="mb-6"><ErrorAlert message={error} /></div>}

          {loading ? (
            <Loading />
          ) : (
            <>
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                {/* Total Runs */}
                <div className="bg-card border border-border rounded p-4 hover:border-primary transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Total Runs</p>
                      <h3 className="text-2xl font-bold text-foreground">{stats.total}</h3>
                    </div>
                    <Code2 className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">
                    <span className="text-foreground font-semibold">{stats.completed}</span> completed
                  </p>
                </div>

                {/* Completed */}
                <div className="bg-card border border-border rounded p-4 hover:border-primary transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Successful</p>
                      <h3 className="text-2xl font-bold text-foreground">{stats.completed}</h3>
                    </div>
                    <CheckCircle2 className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">
                    {stats.total > 0 ? ((stats.completed / stats.total) * 100).toFixed(1) : '0'}% success rate
                  </p>
                </div>

                {/* Issues */}
                <div className="bg-card border border-border rounded p-4 hover:border-primary transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Issues Found</p>
                      <h3 className="text-2xl font-bold text-foreground">{stats.totalIssues}</h3>
                    </div>
                    <AlertCircle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">
                    Across all analysis runs
                  </p>
                </div>

                {/* Pending */}
                <div className="bg-card border border-border rounded p-4 hover:border-primary transition">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">Pending</p>
                      <h3 className="text-2xl font-bold text-foreground">{stats.pending}</h3>
                    </div>
                    <Clock className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                  </div>
                  <p className="text-xs text-muted-foreground mt-3">
                    In progress
                  </p>
                </div>
              </div>

              {/* Recent Runs Card */}
              <div className="bg-card border border-border rounded">
                {/* Header */}
                <div className="p-4 border-b border-border flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <TrendingUp className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <h2 className="text-base font-semibold text-foreground">Recent Analysis</h2>
                      <p className="text-xs text-muted-foreground mt-0.5">Latest code analysis runs</p>
                    </div>
                  </div>
                  <Link
                    href="/runs"
                    className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-primary hover:text-primary/80 transition"
                  >
                    View All
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>

                {/* Content */}
                <div>
                  {runs.length === 0 ? (
                    <div className="p-8 text-center">
                      <div className="max-w-md mx-auto">
                        <Code2 className="w-6 h-6 text-muted-foreground mx-auto mb-3" />
                        <h3 className="text-base font-semibold text-foreground mb-2">No Analysis Runs Yet</h3>
                        <p className="text-muted-foreground text-sm mb-4">
                          Connect your GitHub repositories to start analyzing your code automatically.
                        </p>
                        <Link href="/runs">
                          <button className="inline-flex items-center gap-2 px-3 py-1.5 bg-primary hover:bg-primary/90 text-primary-foreground text-sm rounded font-medium transition">
                            View All Runs
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </Link>
                      </div>
                    </div>
                  ) : (
                    <div className="divide-y divide-border">
                      {runs.slice(0, 5).map((run) => (
                        <Link
                          key={run.id}
                          href={`/runs/${run.id}`}
                          className="block p-4 hover:bg-muted transition border-l-4 border-transparent hover:border-l-primary group"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-1">
                                <h3 className="font-semibold text-foreground text-sm">
                                  {run.repository_name}
                                </h3>
                                <span className="text-xs text-muted-foreground">Run #{run.id}</span>
                                <Badge variant="secondary" className="text-xs">
                                  {run.event}
                                </Badge>
                              </div>
                              <p className="text-xs text-muted-foreground mb-1">
                                Branch: <code className="bg-muted px-1.5 py-0.5 rounded text-xs text-muted-foreground font-mono">{run.branch}</code>
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {new Date(run.created_at).toLocaleString('en-US', { 
                                  month: 'short', 
                                  day: 'numeric', 
                                  year: 'numeric',
                                  hour: 'numeric', 
                                  minute: '2-digit',
                                  hour12: true 
                                })}
                              </p>
                            </div>

                            <div className="flex items-center gap-4 text-right ml-4">
                              <div>
                                <div className="text-lg font-bold text-foreground mb-0.5">
                                  {run.total_results}
                                </div>
                                <p className="text-xs text-muted-foreground">issues</p>
                              </div>
                              <StatusBadge status={run.status} />
                              <span className="text-muted-foreground text-base">
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

          {/* Import Repository Modal */}
          {showImportModal && (
            <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
              <div className="bg-card border border-border rounded max-w-md w-full">
                {/* Modal Header */}
                <div className="flex justify-between items-center p-4 border-b border-border">
                  <h2 className="text-base font-semibold text-foreground">Import Repository</h2>
                  <button
                    onClick={() => {
                      setShowImportModal(false)
                      setError(null)
                    }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Modal Body */}
                <div className="p-4 space-y-3">
                  {error && (
                    <div className="p-3 bg-destructive/10 border border-destructive rounded text-sm">
                      <p className="text-destructive">{error}</p>
                    </div>
                  )}

                  {/* Repository URL Input */}
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      Repository URL <span className="text-destructive">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="https://github.com/username/repo"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      disabled={importingRepo}
                      className="w-full px-2 py-1.5 text-sm border border-border rounded bg-muted text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Supports both HTTPS and SSH formats from GitHub
                    </p>
                  </div>

                  {/* Branch Input */}
                  <div>
                    <label className="block text-xs font-medium text-foreground mb-1">
                      Branch
                    </label>
                    <input
                      type="text"
                      placeholder="main"
                      value={repoBranch}
                      onChange={(e) => setRepoBranch(e.target.value)}
                      disabled={importingRepo}
                      className="w-full px-2 py-1.5 text-sm border border-border rounded bg-muted text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                    />
                    <p className="text-xs text-muted-foreground mt-0.5">
                      The branch to analyze (defaults to main if empty)
                    </p>
                  </div>

                  {/* Auto-Fix Checkbox */}
                  <div className="flex items-start gap-3 p-2 bg-primary/10 border border-primary rounded">
                    <input
                      type="checkbox"
                      id="auto-fix"
                      checked={enableAutoFix}
                      onChange={(e) => setEnableAutoFix(e.target.checked)}
                      disabled={importingRepo}
                      className="w-4 h-4 text-primary rounded focus:ring-1 focus:ring-primary mt-0.5 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <div className="flex-1">
                      <label htmlFor="auto-fix" className="text-xs font-medium text-foreground cursor-pointer block">
                        🤖 Auto-fix safe issues
                      </label>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Automatically fixes safe issues like unused imports, trailing whitespace, and other non-breaking problems
                      </p>
                    </div>
                  </div>
                </div>

                {/* Modal Footer */}
                <div className="flex gap-3 p-4 border-t border-border">
                  <button
                    onClick={() => {
                      setShowImportModal(false)
                      setError(null)
                    }}
                    disabled={importingRepo}
                    className="flex-1 px-3 py-1.5 text-muted-foreground bg-muted hover:bg-muted/80 rounded text-sm font-medium transition disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleImportRepository}
                    disabled={importingRepo || !repoUrl.trim()}
                    className="flex-1 px-3 py-1.5 bg-primary hover:bg-primary/90 disabled:opacity-50 text-primary-foreground text-sm rounded font-medium transition flex items-center justify-center gap-2"
                  >
                    {importingRepo && <Loader className="w-3 h-3 animate-spin" />}
                    {importingRepo ? 'Importing...' : 'Import'}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </>
  )
}
