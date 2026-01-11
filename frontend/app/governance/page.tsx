import { listAvailableRuns } from '@/lib/ledgerReader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'
import GovernanceIntro from '@/components/governance/GovernanceIntro'
import ReadOnlyBadge from '@/components/governance/ReadOnlyBadge'
import { 
  GitBranch, 
  Calendar, 
  Clock, 
  CheckCircle2, 
  XCircle,
  Archive
} from 'lucide-react'

export const metadata = {
  title: 'Proof & Governance | AGI Engineer',
  description: 'Read-only governance dashboard with immutable run ledgers and deterministic replay'
}

export default async function GovernancePage() {
  const runs = await listAvailableRuns()

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

  const stateColors: Record<string, string> = {
    COMPLETE: 'bg-green-100 text-green-700 border-green-300',
    INCOMPLETE: 'bg-amber-100 text-amber-700 border-amber-300',
    ABORTED: 'bg-red-100 text-red-700 border-red-300',
    REJECTED: 'bg-red-100 text-red-700 border-red-300'
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Proof & Governance</h1>
          <p className="text-gray-600 mt-1">
            Immutable run ledgers and deterministic replay for compliance & trust
          </p>
        </div>
        <ReadOnlyBadge variant="lock" text="Immutable Dashboard" className="text-sm px-4 py-2" />
      </div>

      {/* Introduction Section */}
      <GovernanceIntro />

      {/* Available Runs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Archive className="w-5 h-5" />
            Available Frozen Runs
            <Badge variant="outline" className="ml-2">
              {runs.length} Run{runs.length !== 1 ? 's' : ''}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {runs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Archive className="w-12 h-12 mx-auto mb-2 text-gray-400" />
              <p>No frozen runs available yet.</p>
              <p className="text-sm mt-1">Complete a run with ledger enabled to see it here.</p>
            </div>
          ) : (
            runs.map((run) => (
              <Link 
                key={run.run_id}
                href={`/governance/${run.run_id}`}
                className="block"
              >
                <Card className="hover:shadow-md transition-shadow cursor-pointer border-2 hover:border-blue-300">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-lg font-semibold text-gray-900 font-mono">
                            {run.run_id}
                          </h3>
                          <Badge className={stateColors[run.final_state] || 'bg-gray-100'}>
                            {run.final_state}
                          </Badge>
                          <ReadOnlyBadge variant="archive" text="Frozen" />
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <GitBranch className="w-4 h-4" />
                            <span className="font-mono">{run.branch}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            <span>{formatTimestamp(run.started_at)}</span>
                          </div>
                          {run.ended_at && (
                            <div className="flex items-center gap-1">
                              <Clock className="w-4 h-4" />
                              <span>{formatDuration(run.started_at, run.ended_at)}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {run.final_state === 'COMPLETE' ? (
                          <CheckCircle2 className="w-6 h-6 text-green-600" />
                        ) : (
                          <XCircle className="w-6 h-6 text-red-600" />
                        )}
                      </div>
                    </div>

                    <div className="text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded">
                      {run.repository_url}
                    </div>

                    <div className="mt-2 text-xs text-gray-500">
                      Policy: <span className="font-mono text-gray-700">{run.policy}</span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))
          )}
        </CardContent>
      </Card>

      {/* Footer Notice */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <p className="text-sm text-blue-900">
            <strong>📌 Important:</strong> This dashboard is READ-ONLY by design. 
            You cannot trigger executions, approve plans, or modify any state from here. 
            To execute runs, use the main Dashboard → Runs section.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
