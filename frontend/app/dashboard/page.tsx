'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import { listRuns, AnalysisRun } from '@/lib/api'
import { Header, Loading, ErrorAlert, StatusBadge } from '@/components/layout'
import { Badge } from '@/components/ui'
import Link from 'next/link'
import { 
  TrendingUp, 
  Code2, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  ArrowRight, 
  Plus, 
  X, 
  Loader, 
  GitBranch, 
  Calendar,
  Activity,
  ShieldCheck,
  Search,
  Command
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ----------------------------------------------------------------------
// Types & Interfaces
// ----------------------------------------------------------------------

interface Repository {
  id: number
  name: string
  url: string
  branch: string
}

export default function DashboardPage() {
  // ----------------------------------------------------------------------
  // Core Logic & State (Strictly Preserved)
  // ----------------------------------------------------------------------
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
    const trimmedUrl = repoUrl.trim()
    if (!trimmedUrl) {
      setError('Repository URL is required')
      return
    }

    const isValidUrl = /^(https:\/\/github\.com\/|git@github\.com:)[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]+(\.git)?$/.test(trimmedUrl)
    if (!isValidUrl) {
      setError('Invalid GitHub URL. Expected format: https://github.com/owner/repo')
      return
    }

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

  const stats = {
    total: runs.length,
    completed: runs.filter((r) => r.status === 'completed').length,
    failed: runs.filter((r) => r.status === 'failed').length,
    pending: runs.filter((r) => r.status === 'pending').length,
    totalIssues: runs.reduce((sum, r) => sum + r.total_results, 0),
  }

  // ----------------------------------------------------------------------
  // Local UI Components (Themed)
  // ----------------------------------------------------------------------

  const MetricCard = ({ label, value, subtext, icon: Icon, color }: { label: string, value: string | number, subtext: string, icon: any, color: string }) => (
    <div className="group relative overflow-hidden rounded-2xl border border-white/5 bg-[#121214] p-5 transition-all hover:border-white/10 hover:shadow-lg hover:shadow-black/40">
      {/* Glow Effect */}
      <div className={`absolute -right-6 -top-6 h-24 w-24 rounded-full opacity-10 blur-3xl transition-opacity group-hover:opacity-20 ${color}`} />
      
      <div className="relative z-10 flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-gray-500">{label}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <h3 className="text-3xl font-light tracking-tight text-white">{value}</h3>
          </div>
        </div>
        <div className="rounded-lg bg-white/5 p-2 text-gray-400 backdrop-blur-sm transition-colors group-hover:bg-white/10 group-hover:text-white">
          <Icon className="h-5 w-5" />
        </div>
      </div>
      <div className="relative z-10 mt-4 flex items-center gap-2">
        <span className="text-[11px] font-medium text-gray-500">{subtext}</span>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#09090b] text-white selection:bg-blue-500/30">
      <Header />
      
      {/* Background Texture */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.02]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")` }} />

      <main className="relative z-10 mx-auto max-w-[1400px] px-6 py-10">
          
        {/* Dashboard Header */}
        <div className="mb-12 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight text-white">Dashboard</h1>
            <p className="text-sm text-gray-400 max-w-lg leading-relaxed">
              Real-time oversight of your repositories. Monitor analysis runs, review auto-fixes, and track code health.
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-gray-400 sm:flex">
                <Search className="h-3.5 w-3.5" />
                <span>Search runs...</span>
                <span className="ml-2 rounded bg-white/10 px-1.5 py-0.5 text-[10px] font-medium text-gray-300">⌘K</span>
            </div>
            <button
              onClick={() => setShowImportModal(true)}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-bold text-black shadow-[0_0_20px_rgba(255,255,255,0.1)] transition-all hover:scale-105 hover:bg-gray-200 active:scale-95"
            >
              <Plus className="h-4 w-4" />
              Import Repository
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-8 animate-in fade-in slide-in-from-top-2">
            <ErrorAlert message={error} />
          </div>
        )}

        {loading ? (
          <div className="flex h-96 items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/5">
            <div className="flex flex-col items-center gap-3">
                <Loader className="h-6 w-6 animate-spin text-gray-500" />
                <p className="text-xs text-gray-500 font-mono">loading_workspace_data...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
            
            {/* Metrics Grid */}
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard 
                label="Total Analysis Runs" 
                value={stats.total} 
                subtext={`${stats.completed} successful completions`}
                icon={Activity}
                color="bg-blue-500"
              />
              <MetricCard 
                label="Success Rate" 
                value={stats.total > 0 ? `${((stats.completed / stats.total) * 100).toFixed(1)}%` : 'N/A'} 
                subtext="System reliability score"
                icon={CheckCircle2} 
                color="bg-green-500"
              />
              <MetricCard 
                label="Issues Detected" 
                value={stats.totalIssues} 
                subtext="Across all tracked repos"
                icon={AlertCircle} 
                color="bg-red-500"
              />
              <MetricCard 
                label="Pending Jobs" 
                value={stats.pending} 
                subtext="Currently processing"
                icon={Clock} 
                color="bg-yellow-500"
              />
            </div>

            {/* Recent Activity Panel */}
            <div className="rounded-2xl border border-white/10 bg-[#121214]/50 backdrop-blur-sm shadow-xl">
              
              <div className="flex items-center justify-between border-b border-white/5 px-6 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 border border-white/5">
                    <TrendingUp className="h-4 w-4 text-gray-400" />
                  </div>
                  <div>
                    <h2 className="text-sm font-semibold text-white">Recent Activity</h2>
                    <p className="text-[11px] text-gray-500">Latest automated checks</p>
                  </div>
                </div>
                <Link 
                  href="/runs" 
                  className="group flex items-center gap-1.5 rounded-full border border-white/5 bg-white/5 px-4 py-1.5 text-xs font-medium text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                >
                  Full History
                  <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                </Link>
              </div>

              <div className="divide-y divide-white/5">
                {runs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-24 text-center">
                    <div className="mb-6 rounded-full bg-white/5 p-6 ring-1 ring-white/10">
                      <Code2 className="h-8 w-8 text-gray-500" />
                    </div>
                    <h3 className="text-base font-semibold text-white">No analysis runs recorded</h3>
                    <p className="mt-2 max-w-sm text-sm text-gray-500 leading-relaxed">
                      Your workspace is empty. Import a GitHub repository to trigger the AGI Engine.
                    </p>
                    <button 
                      onClick={() => setShowImportModal(true)}
                      className="mt-8 text-xs font-bold text-blue-400 hover:text-blue-300 uppercase tracking-wider"
                    >
                      + Start First Run
                    </button>
                  </div>
                ) : (
                  runs.slice(0, 5).map((run) => (
                    <Link
                      key={run.id}
                      href={`/runs/${run.id}`}
                      className="group flex flex-col gap-4 p-5 transition-all hover:bg-white/[0.02] sm:flex-row sm:items-center sm:justify-between sm:px-6"
                    >
                      <div className="flex flex-1 items-start gap-5">
                        {/* Status Icon Indicator */}
                        <div className={`mt-1 hidden h-2 w-2 rounded-full sm:block ${
                            run.status === 'completed' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' :
                            run.status === 'failed' ? 'bg-red-500' : 'bg-yellow-500 animate-pulse'
                        }`} />
                        
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-3">
                            <h3 className="font-medium text-gray-200 group-hover:text-white transition-colors">
                              {run.repository_name}
                            </h3>
                            <div className="hidden sm:block">
                                <StatusBadge status={run.status} />
                            </div>
                          </div>
                          
                          <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 font-mono">
                            <span className="flex items-center gap-1.5">
                              <GitBranch className="h-3 w-3" />
                              <span>{run.branch}</span>
                            </span>
                            <span className="hidden text-white/10 sm:inline">|</span>
                            <span className="flex items-center gap-1.5">
                              <Calendar className="h-3 w-3" />
                              {new Date(run.created_at).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                hour: 'numeric',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-8 sm:justify-end">
                        {/* Mobile Status Badge */}
                        <div className="sm:hidden">
                            <StatusBadge status={run.status} />
                        </div>

                        <div className="text-right min-w-[80px]">
                           <div className="text-sm font-bold text-white tabular-nums">
                             {run.total_results}
                           </div>
                           <div className="text-[10px] font-medium uppercase tracking-wider text-gray-600">
                             Issues
                           </div>
                        </div>

                        <div className="h-8 w-8 rounded-full border border-white/5 bg-white/5 flex items-center justify-center opacity-0 transition-all group-hover:opacity-100 -translate-x-2 group-hover:translate-x-0">
                             <ArrowRight className="h-4 w-4 text-white" />
                        </div>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Import Modal - Dark Glass Theme */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-md transition-all duration-200 animate-in fade-in">
          <div 
            className="w-full max-w-[500px] scale-100 rounded-2xl border border-white/10 bg-[#121214] p-0 shadow-2xl ring-1 ring-white/5"
            role="dialog"
            aria-modal="true"
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-white/5 px-6 py-5">
              <div>
                <h2 className="text-lg font-bold text-white">Import Repository</h2>
                <p className="text-xs text-gray-400 mt-1">Configure a new source for the analysis engine.</p>
              </div>
              <button
                onClick={() => {
                  setShowImportModal(false)
                  setError(null)
                }}
                className="rounded-full p-2 text-gray-500 hover:bg-white/10 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {error && !importingRepo && (
                <div className="rounded-lg bg-red-500/10 p-3 text-xs text-red-300 border border-red-500/20 flex gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              <div className="space-y-5">
                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Repository URL <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      placeholder="https://github.com/owner/repo"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      disabled={importingRepo}
                      className="flex h-11 w-full rounded-xl border border-white/10 bg-black/20 px-4 py-2 text-sm text-white placeholder:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:border-transparent disabled:cursor-not-allowed disabled:opacity-50 font-mono transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                    Target Branch
                  </label>
                  <div className="relative">
                     <GitBranch className="absolute left-4 top-3.5 h-4 w-4 text-gray-500" />
                    <input
                      type="text"
                      placeholder="main"
                      value={repoBranch}
                      onChange={(e) => setRepoBranch(e.target.value)}
                      disabled={importingRepo}
                      className="flex h-11 w-full rounded-xl border border-white/10 bg-black/20 pl-10 pr-4 py-2 text-sm text-white placeholder:text-gray-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:border-transparent disabled:cursor-not-allowed disabled:opacity-50 font-mono transition-all"
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-4 transition-colors hover:bg-blue-500/10">
                  <div className="flex items-start gap-3">
                    <div className="flex h-5 items-center">
                      <input
                        type="checkbox"
                        id="auto-fix"
                        checked={enableAutoFix}
                        onChange={(e) => setEnableAutoFix(e.target.checked)}
                        disabled={importingRepo}
                        className="h-4 w-4 rounded border-gray-600 bg-black/40 text-blue-500 focus:ring-blue-500/40 disabled:opacity-50"
                      />
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="auto-fix" className="text-sm font-semibold text-gray-200 cursor-pointer flex items-center gap-2">
                        <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
                        Enable AI Auto-Fix
                      </label>
                      <p className="text-xs text-gray-400 leading-relaxed">
                        The engine will automatically resolve safe issues (unused imports, formatting) and create a PR.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end gap-3 border-t border-white/5 bg-white/[0.02] px-6 py-5">
              <button
                onClick={() => {
                  setShowImportModal(false)
                  setError(null)
                }}
                disabled={importingRepo}
                className="inline-flex h-10 items-center justify-center rounded-lg px-4 text-sm font-medium text-gray-400 hover:bg-white/5 hover:text-white transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImportRepository}
                disabled={importingRepo || !repoUrl.trim()}
                className="inline-flex h-10 min-w-[120px] items-center justify-center rounded-lg bg-white px-5 text-sm font-bold text-black shadow-lg shadow-white/10 transition-all hover:bg-gray-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/20 disabled:pointer-events-none disabled:opacity-50"
              >
                {importingRepo ? (
                  <>
                    <Loader className="mr-2 h-4 w-4 animate-spin" />
                    Initializing...
                  </>
                ) : (
                  'Start Analysis'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}