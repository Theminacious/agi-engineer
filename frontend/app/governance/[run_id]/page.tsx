import { 
  readLedgerMetadata, 
  readLedgerEvents,
  readReplaySummary,
  checkInvariants
} from '@/lib/ledgerReader'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import PlanContextBlock from '@/components/governance/PlanContextBlock'
import Link from 'next/link'
import ReadOnlyBadge from '@/components/governance/ReadOnlyBadge'
import RunLedgerTimeline from '@/components/governance/RunLedgerTimeline'
import ReplaySummaryPanel from '@/components/governance/ReplaySummaryPanel'
import InvariantStatus from '@/components/governance/InvariantStatus'
import AuditTable from '@/components/governance/AuditTable'
import IntelligenceOverviewPanel from '@/components/governance/intelligence/IntelligenceOverviewPanel'
import IntelligenceProposalList from '@/components/governance/intelligence/IntelligenceProposalList'
import { 
  ArrowLeft,
  GitBranch,
  Calendar,
  Lock,
  Shield,
  Brain
} from 'lucide-react'

interface GovernanceRunDetailPageProps {
  params: {
    run_id: string
  }
}

export async function generateMetadata({ params }: GovernanceRunDetailPageProps) {
  return {
    title: `Run ${params.run_id} | Proof & Governance`,
    description: `Immutable ledger and deterministic replay for run ${params.run_id}`
  }
}

export default async function GovernanceRunDetailPage({ params }: GovernanceRunDetailPageProps) {
  const { run_id } = params

  // Fetch all data
  const metadata = await readLedgerMetadata(run_id)
  const events = await readLedgerEvents(run_id)
  const summary = await readReplaySummary(run_id)
  const invariants = await checkInvariants(events, metadata)

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }

  const stateColors: Record<string, string> = {
    COMPLETE: 'bg-green-100 text-green-700 border-green-300',
    INCOMPLETE: 'bg-amber-100 text-amber-700 border-amber-300',
    ABORTED: 'bg-red-100 text-red-700 border-red-300',
    REJECTED: 'bg-red-100 text-red-700 border-red-300'
  }

  // Convert invariants to InvariantCheck format
  const invariantChecks = [
    {
      name: 'Sequence Contiguous',
      passed: invariants.sequenceContiguous,
      description: 'Event sequence numbers are continuous without gaps (0, 1, 2, ... N)'
    },
    {
      name: 'Terminal Event Present',
      passed: invariants.terminalEventPresent,
      description: 'Ledger contains a terminal event (RUN_COMPLETED, RUN_ABORTED, or PLAN_REJECTED)'
    },
    {
      name: 'Approval Before Fix',
      passed: invariants.approvalBeforeFix,
      description: 'PLAN_APPROVED event must precede all FIX_APPLIED events'
    },
    {
      name: 'Safety Before Fix',
      passed: invariants.safetyBeforeFix,
      description: 'SAFETY_CHECK_PASSED event must precede all FIX_APPLIED events'
    },
    {
      name: 'Terminal State Match',
      passed: invariants.terminalMatches,
      description: 'Final state in metadata matches the terminal event type'
    }
  ]

  // Extract intelligence proposals from events (Phase 11.4)
  const intelligenceProposals = events
    .filter(event => event.event_type === 'INTELLIGENCE_PROPOSAL')
    .map(event => event.payload)
    .filter((payload): payload is Record<string, any> => Boolean(payload))

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Navigation */}
      <Link 
        href="/governance"
        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 hover:underline"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Governance Dashboard
      </Link>

      {/* Page Header with Metadata */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Lock className="w-6 h-6 text-blue-600" />
                <h1 className="text-2xl font-bold text-gray-900 font-mono">
                  {metadata.run_id}
                </h1>
                <Badge className={stateColors[metadata.final_state] || 'bg-gray-100'}>
                  {metadata.final_state}
                </Badge>
                <ReadOnlyBadge variant="archive" text="Frozen Ledger" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-4 h-4 text-gray-600" />
                  <span className="text-gray-600">Branch:</span>
                  <span className="font-mono text-gray-900">{metadata.branch}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-gray-600" />
                  <span className="text-gray-600">Started:</span>
                  <span className="text-gray-900">{formatTimestamp(metadata.started_at)}</span>
                </div>

                {metadata.ended_at && (
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-gray-600" />
                    <span className="text-gray-600">Ended:</span>
                    <span className="text-gray-900">{formatTimestamp(metadata.ended_at)}</span>
                  </div>
                )}

                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-gray-600" />
                  <span className="text-gray-600">Policy:</span>
                  <span className="font-mono text-gray-900">{metadata.policy}</span>
                </div>
              </div>

              <div className="mt-3 text-xs text-gray-600 font-mono bg-white p-2 rounded border">
                {metadata.repository_url}
              </div>
            </div>
          </div>

          {/* Read-Only Warning Banner */}
          <div className="bg-blue-100 border border-blue-300 rounded p-3">
            <p className="text-sm text-blue-900 flex items-center gap-2">
              <Lock className="w-4 h-4" />
              <strong>READ-ONLY:</strong> This page displays a frozen snapshot of the run. 
              No mutations are possible. To execute new runs, use the main Dashboard.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Plan Context Block (Phase 13.4) */}
      <PlanContextBlock plan="developer" timestamp={metadata.started_at} />

      {/* Intelligence Proposals Section (if any) */}
      {intelligenceProposals.length > 0 && (
        <Card className="border-purple-200 bg-purple-50">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <Brain className="w-5 h-5 text-purple-600" />
              <h2 className="text-lg font-semibold text-purple-900">
                🧠 Intelligence Proposals
              </h2>
              <Badge variant="outline" className="text-purple-700 border-purple-300">
                {intelligenceProposals.length} proposal{intelligenceProposals.length !== 1 ? 's' : ''}
              </Badge>
            </div>
            <p className="text-sm text-purple-800 mb-4">
              The analyzers detected potential issues and suggested strategies. 
              All data is immutable and replayable. No code has been modified.
            </p>
            <IntelligenceProposalList proposals={intelligenceProposals as any} />
          </CardContent>
        </Card>
      )}

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Timeline (2/3 width) */}
        <div className="lg:col-span-2 space-y-6">
          <RunLedgerTimeline events={events} />
          <AuditTable events={events} />
        </div>

        {/* Right Column: Summary & Invariants (1/3 width) */}
        <div className="space-y-6">
          <ReplaySummaryPanel summary={summary} />
          <InvariantStatus checks={invariantChecks} />
        </div>
      </div>

      {/* Footer Notice */}
      <Card className="bg-gray-50 border-gray-200">
        <CardContent className="p-4">
          <p className="text-xs text-gray-600">
            <strong>🔒 Cryptographic Proof:</strong> Each event in this ledger is cryptographically signed 
            and stored in an append-only log. The entire sequence can be deterministically replayed 
            to verify that the system behaved correctly. This proof is independent of trust in the AI.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
