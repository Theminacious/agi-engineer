'use client'

import IntelligenceProposalCard from './IntelligenceProposalCard'
import ProposalReadOnlyBanner from './ProposalReadOnlyBanner'
import { useMemo } from 'react'

interface IntelligenceProposal {
  proposal_id: string
  analyzer_name: string
  bug_class: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  confidence: number
  problem_statement: string
  root_cause_hypothesis: string
  risk_explanation: string
  affected_files: any[]
  suggested_strategies: any[]
  prerequisite_actions?: string[]
  conflicting_analysis_ids?: string[]
}

interface IntelligenceProposalListProps {
  proposals: IntelligenceProposal[]
}

/**
 * Phase 11.4: Intelligence Proposal List
 * 
 * Displays all intelligence proposals in ledger sequence order (immutable).
 * Grouped visually by severity for readability, but sequence order is preserved.
 * 
 * CRITICAL CONSTRAINT: Proposals are ordered strictly by ledger sequence.
 * They are NOT ranked, scored, or sorted. Visual grouping is for UX only.
 */
export default function IntelligenceProposalList({ proposals }: IntelligenceProposalListProps) {
  // Group by severity for visual organization, but track original ledger index
  const groupedProposals = useMemo(() => {
    const groups = {
      CRITICAL: [] as Array<{ proposal: IntelligenceProposal; ledgerIndex: number }>,
      HIGH: [] as Array<{ proposal: IntelligenceProposal; ledgerIndex: number }>,
      MEDIUM: [] as Array<{ proposal: IntelligenceProposal; ledgerIndex: number }>,
      LOW: [] as Array<{ proposal: IntelligenceProposal; ledgerIndex: number }>,
    }

    proposals.forEach((proposal, index) => {
      groups[proposal.severity].push({ proposal, ledgerIndex: index })
    })

    return groups
  }, [proposals])

  const totalProposals = proposals.length
  const severityOrder = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] as const

  return (
    <div className="space-y-4">
      {/* Banner */}
      <ProposalReadOnlyBanner />

      {/* Empty State */}
      {totalProposals === 0 && (
        <div className="text-center py-8 text-gray-500 border border-dashed border-gray-300 rounded">
          <p className="text-sm">No intelligence proposals for this run.</p>
        </div>
      )}

      {/* Grouped Proposals */}
      {totalProposals > 0 && (
        <div className="space-y-6">
          {severityOrder.map(severity => {
            const severityGroup = groupedProposals[severity]
            if (severityGroup.length === 0) return null

            const severityColors: Record<string, string> = {
              CRITICAL: 'bg-red-50 border-red-200',
              HIGH: 'bg-orange-50 border-orange-200',
              MEDIUM: 'bg-yellow-50 border-yellow-200',
              LOW: 'bg-blue-50 border-blue-200',
            }

            const severityTextColors: Record<string, string> = {
              CRITICAL: 'text-red-900',
              HIGH: 'text-orange-900',
              MEDIUM: 'text-yellow-900',
              LOW: 'text-blue-900',
            }

            return (
              <div key={severity} className={`border rounded-lg p-4 ${severityColors[severity]}`}>
                <div className={`text-sm font-semibold ${severityTextColors[severity]} mb-4`}>
                  {severity} Severity ({severityGroup.length})
                </div>
                <div className="space-y-3">
                  {severityGroup.map(({ proposal, ledgerIndex }) => (
                    <IntelligenceProposalCard
                      key={proposal.proposal_id}
                      proposal={proposal}
                      sequenceNumber={ledgerIndex + 1}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Footer Info */}
      {totalProposals > 0 && (
        <div className="text-xs text-gray-500 text-center pt-4 border-t border-gray-200">
          Showing {totalProposals} proposal{totalProposals !== 1 ? 's' : ''} in ledger sequence order.
          Proposals are grouped by severity for readability only.
        </div>
      )}
    </div>
  )
}
