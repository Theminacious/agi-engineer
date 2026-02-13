'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell, Loading, ErrorAlert } from '@/components/layout'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  TrendingUp,
  RefreshCw,
  Activity,
  CheckCircle2,
  AlertCircle,
  Percent,
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface IssueByCode {
  code: string
  name: string
  count: number
}

interface TrendingIssue {
  code: string
  name: string
  occurrences: number
  fixed: number
}

interface IssuesSummary {
  total_issues: number
  fixed_count: number
  unfixed_count: number
  fix_rate: number
  issues_by_code: IssueByCode[]
}

interface TrendingData {
  trending_issues: TrendingIssue[]
}

export default function AnalyticsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [issuesSummary, setIssuesSummary] = useState<IssuesSummary | null>(null)
  const [trendingIssues, setTrendingIssues] = useState<TrendingData | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const token = typeof window !== 'undefined' ? localStorage.getItem('jwt_token') : null

  const getHeaders = (): Record<string, string> => {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (token) headers['Authorization'] = `Bearer ${token}`
    return headers
  }

  const fetchAnalytics = async () => {
    try {
      setRefreshing(true)
      const headers = getHeaders()

      const [summaryRes, trendingRes] = await Promise.all([
        fetch(`${API_BASE}/api/issues/summary?limit=100`, { headers }),
        fetch(`${API_BASE}/api/trending-issues?days=7&limit=15`, { headers }),
      ])

      if (!summaryRes.ok || !trendingRes.ok) {
        throw new Error('Failed to fetch analytics')
      }

      const [summary, trending] = await Promise.all([
        summaryRes.json(),
        trendingRes.json(),
      ])

      setIssuesSummary(summary)
      setTrendingIssues(trending)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics')
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
    fetchAnalytics()
  }, [token, router])

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
            <h1 className="text-2xl font-semibold tracking-tight">Analytics</h1>
            <p className="text-sm text-muted-foreground mt-1">System health and resolution metrics</p>
          </div>
          <Button variant="outline" size="icon" onClick={fetchAnalytics} disabled={refreshing}>
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {error && <ErrorAlert message={error} />}

        {/* Key Metrics */}
        {issuesSummary && (
          <div className="grid grid-cols-4 gap-6">
            <div className="border border-border rounded p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <Activity className="w-4 h-4" />
                <span>Total Issues</span>
              </div>
              <div className="text-3xl font-semibold tracking-tight tabular-nums">{issuesSummary.total_issues}</div>
              <p className="text-xs text-muted-foreground mt-1">Detected across repositories</p>
            </div>

            <div className="border border-border rounded p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <CheckCircle2 className="w-4 h-4" />
                <span>Fixed</span>
              </div>
              <div className="text-3xl font-semibold tracking-tight tabular-nums">{issuesSummary.fixed_count}</div>
              <p className="text-xs text-muted-foreground mt-1">Resolved automatically</p>
            </div>

            <div className="border border-border rounded p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <AlertCircle className="w-4 h-4" />
                <span>Unfixed</span>
              </div>
              <div className="text-3xl font-semibold tracking-tight tabular-nums">{issuesSummary.unfixed_count}</div>
              <p className="text-xs text-muted-foreground mt-1">Pending resolution</p>
            </div>

            <div className="border border-border rounded p-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-2">
                <Percent className="w-4 h-4" />
                <span>Fix Rate</span>
              </div>
              <div className="text-3xl font-semibold tracking-tight tabular-nums">{issuesSummary.fix_rate.toFixed(1)}%</div>
              <p className="text-xs text-muted-foreground mt-1">Overall efficiency</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-6">
          {/* Top Issue Types */}
          {issuesSummary && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold">Top Issue Types</h2>
              <div className="border border-border rounded">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead className="text-right">Count</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {issuesSummary.issues_by_code?.slice(0, 8).map((issue) => (
                      <TableRow key={issue.code}>
                        <TableCell className="font-mono text-sm">{issue.code}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{issue.name}</TableCell>
                        <TableCell className="text-right font-mono">{issue.count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Trending Issues */}
          {trendingIssues && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold">Trending Issues</h2>
                <span className="text-xs text-muted-foreground">(7 days)</span>
              </div>
              <div className="border border-border rounded">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Code</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Fixed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trendingIssues.trending_issues?.slice(0, 8).map((issue) => (
                      <TableRow key={issue.code}>
                        <TableCell className="font-mono text-sm">{issue.code}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{issue.name}</TableCell>
                        <TableCell className="text-right font-mono">{issue.occurrences}</TableCell>
                        <TableCell className="text-right font-mono text-muted-foreground">{issue.fixed}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}