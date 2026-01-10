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
      <main className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          {/* Page Header */}
          <div className="flex justify-between items-start mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
              <p className="text-gray-600 mt-2">Overview of your code analysis activity</p>
            </div>
            <button
              onClick={() => setShowImportModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
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
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                {/* Total Runs */}
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-blue-300 hover:shadow-lg transition-all duration-200">
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
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-green-300 hover:shadow-lg transition-all duration-200">
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
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-amber-300 hover:shadow-lg transition-all duration-200">
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
                <div className="bg-white rounded-lg border border-gray-200 p-6 hover:border-gray-300 hover:shadow-lg transition-all duration-200">
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
                      <div className="max-w-md mx-auto">
                        <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-4">
                          <Code2 className="w-8 h-8 text-blue-600" />
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">No Analysis Runs Yet</h3>
                        <p className="text-gray-600 mb-6">
                          Connect your GitHub repositories to start analyzing your code automatically.
                        </p>
                        <Link href="/runs">
                          <button className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition">
                            View All Runs
                            <ArrowRight className="w-4 h-4" />
                          </button>
                        </Link>
                      </div>
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-200">
                      {runs.slice(0, 5).map((run) => (
                        <Link
                          key={run.id}
                          href={`/runs/${run.id}`}
                          className="block p-6 hover:bg-blue-50 transition-all duration-200 border-l-4 border-transparent hover:border-l-blue-600 group"
                        >
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2">
                                <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition">
                                  {run.repository_name}
                                </h3>
                                <span className="text-sm text-gray-500">Run #{run.id}</span>
                                <Badge variant="secondary" className="text-xs">
                                  {run.event}
                                </Badge>
                              </div>
                              <p className="text-sm text-gray-600 mb-2">
                                Branch: <code className="bg-gray-100 px-2 py-1 rounded text-xs text-gray-700 font-mono">{run.branch}</code>
                              </p>
                              <p className="text-xs text-gray-500">
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

                            <div className="flex items-center gap-6 text-right ml-4">
                              <div>
                                <div className="text-2xl font-bold text-amber-600 mb-1">
                                  {run.total_results}
                                </div>
                                <p className="text-xs text-gray-600">issues</p>
                              </div>
                              <StatusBadge status={run.status} />
                              <span className="text-gray-400 group-hover:text-blue-600 transition text-lg">
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
            <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
              <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                {/* Modal Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-900">Import Repository</h2>
                  <button
                    onClick={() => {
                      setShowImportModal(false)
                      setError(null)
                    }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 space-y-4">
                  {error && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  )}

                  {/* Repository URL Input */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Repository URL <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      placeholder="https://github.com/username/repo"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      disabled={importingRepo}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Supports both HTTPS and SSH formats from GitHub
                    </p>
                  </div>

                  {/* Branch Input */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Branch
                    </label>
                    <input
                      type="text"
                      placeholder="main"
                      value={repoBranch}
                      onChange={(e) => setRepoBranch(e.target.value)}
                      disabled={importingRepo}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      The branch to analyze (defaults to main if empty)
                    </p>
                  </div>

                  {/* Auto-Fix Checkbox */}
                  <div className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                    <input
                      type="checkbox"
                      id="auto-fix"
                      checked={enableAutoFix}
                      onChange={(e) => setEnableAutoFix(e.target.checked)}
                      disabled={importingRepo}
                      className="w-4 h-4 text-green-600 rounded focus:ring-2 focus:ring-green-500 mt-0.5 cursor-pointer disabled:cursor-not-allowed"
                    />
                    <div className="flex-1">
                      <label htmlFor="auto-fix" className="text-sm font-medium text-gray-700 cursor-pointer block">
                        🤖 Auto-fix safe issues
                      </label>
                      <p className="text-xs text-gray-600 mt-1">
                        Automatically fixes safe issues like unused imports, trailing whitespace, and other non-breaking problems
                      </p>
                    </div>
                  </div>
                </div>

                {/* Modal Footer */}
                <div className="flex gap-3 p-6 border-t border-gray-200">
                  <button
                    onClick={() => {
                      setShowImportModal(false)
                      setError(null)
                    }}
                    disabled={importingRepo}
                    className="flex-1 px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium transition disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleImportRepository}
                    disabled={importingRepo || !repoUrl.trim()}
                    className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg font-medium transition flex items-center justify-center gap-2"
                  >
                    {importingRepo && <Loader className="w-4 h-4 animate-spin" />}
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
