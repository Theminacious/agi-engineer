export const dynamic = 'force-dynamic';

'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { listAvailableRuns, LedgerMetadata } from '@/lib/ledgerReader'
import { AppShell, Loading, ErrorAlert } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { 
  Archive, 
  GitBranch, 
  Clock,
  AlertCircle,
  ShieldCheck
} from 'lucide-react'

export default function GovernancePage() {
  const router = useRouter()
  const [runs, setRuns] = useState<LedgerMetadata[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('jwt_token')
    if (!token) {
      router.push('/auth')
      return
    }
    fetchRuns()
  }, [router])

  const fetchRuns = async () => {
    try {
      setLoading(true)
      const data = await listAvailableRuns()
      setRuns(data)
      setError(null)
    } catch (err) {
      setError((err as Error).message || 'Failed to fetch governance data')
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    })
  }

  const formatDuration = (start: string, end: string) => {
    const startDate = new Date(start)
    const endDate = new Date(end)
    const seconds = Math.floor((endDate.getTime() - startDate.getTime()) / 1000)
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  const getStateColor = (state: string): string => {
    switch (state) {
      case 'COMPLETE': return 'text-green-400'
      case 'INCOMPLETE': return 'text-amber-400'
      case 'ABORTED':
      case 'REJECTED': return 'text-red-400'
      default: return 'text-muted-foreground'
    }
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
          <div className="flex items-center gap-2 mb-2">
            <h1 className="text-2xl font-semibold tracking-tight">Proof & Governance</h1>
            <Badge variant="outline" className="text-xs">
              <Archive className="w-3 h-3 mr-1" />
              Read-only
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">Immutable run ledgers for compliance and audit</p>
        </div>

        {error && <ErrorAlert message={error} />}

        {/* Introduction */}
        <div className="border border-border rounded p-6 space-y-4">
          <div className="flex items-start gap-4">
            <div className="p-2 border border-border rounded">
              <ShieldCheck className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 space-y-2">
              <h2 className="text-lg font-semibold">Deterministic Replay & Audit Trail</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                This dashboard provides read-only access to frozen run ledgers. Each ledger captures the complete execution history, 
                enabling deterministic replay and compliance verification. You cannot trigger executions or modify state from here.
              </p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <AlertCircle className="w-4 h-4" />
                <span>To execute runs, use the <span className="text-foreground">Dashboard → Runs</span> section</span>
              </div>
            </div>
          </div>
        </div>

        {/* Runs Table */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Frozen Runs</h2>
            <span className="text-xs text-muted-foreground">{runs.length} total</span>
          </div>

          {runs.length === 0 ? (
            <div className="border border-border rounded p-12 text-center">
              <Archive className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
              <p className="text-sm text-muted-foreground">No frozen runs available yet</p>
              <p className="text-xs text-muted-foreground mt-1">Complete a run with ledger enabled to see it here</p>
            </div>
          ) : (
            <div className="border border-border rounded">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Branch</TableHead>
                    <TableHead>State</TableHead>
                    <TableHead>Policy</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead className="text-right">Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow 
                      key={run.run_id}
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => router.push(`/governance/${run.run_id}`)}
                    >
                      <TableCell className="font-mono font-medium">{run.run_id}</TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        <div className="flex items-center gap-2">
                          <GitBranch className="w-3 h-3" />
                          {run.branch}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={`text-sm font-medium ${getStateColor(run.final_state)}`}>
                          {run.final_state}
                        </span>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">{run.policy}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatTimestamp(run.started_at)}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm text-muted-foreground">
                        {run.ended_at ? (
                          <div className="flex items-center justify-end gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDuration(run.started_at, run.ended_at)}
                          </div>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}
