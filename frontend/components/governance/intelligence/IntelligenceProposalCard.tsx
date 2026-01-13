'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ChevronDown, ChevronUp, AlertCircle, Info } from 'lucide-react'
import { useState } from 'react'

interface Strategy {
  id: string
  name?: string
  description: string
  effort_estimate?: string
  prerequisites: string[]
  assumptions: string[]
  risks: string[]
}

interface AffectedFile {
  path: string
  line_range?: string
  severity?: string
}

interface IntelligenceProposalCardProps {
  proposal: {
    proposal_id: string
    analyzer_name: string
    bug_class: string
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
    confidence: number
    problem_statement: string
    root_cause_hypothesis: string
    risk_explanation: string
    affected_files: AffectedFile[] | string[]
    suggested_strategies: Strategy[]
    prerequisite_actions?: string[]
    conflicting_analysis_ids?: string[]
  }
  sequenceNumber: number
}

/**
 * Phase 11.4: Intelligence Proposal Card
 * 
 * READ-ONLY display of a single intelligence proposal.
 * Shows complete proposal data exactly as recorded in ledger.
 * No actions, no buttons, no mutations.
 */
export default function IntelligenceProposalCard({ 
  proposal, 
  sequenceNumber 
}: IntelligenceProposalCardProps) {
  const [expandedStrategies, setExpandedStrategies] = useState<string[]>([])
  const [showDetails, setShowDetails] = useState(false)

  const toggleStrategy = (strategyId: string) => {
    setExpandedStrategies(prev =>
      prev.includes(strategyId)
        ? prev.filter(id => id !== strategyId)
        : [...prev, strategyId]
    )
  }

  // Normalize affected files
  const affectedFiles = (proposal.affected_files || []).map(f =>
    typeof f === 'string' ? { path: f } : f
  )

  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-700 border-red-300',
    HIGH: 'bg-orange-100 text-orange-700 border-orange-300',
    MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    LOW: 'bg-blue-100 text-blue-700 border-blue-300',
  }

  const confidenceColor = proposal.confidence >= 0.8
    ? 'text-green-700'
    : proposal.confidence >= 0.6
    ? 'text-yellow-700'
    : 'text-orange-700'

  const bugClassLabel = proposal.bug_class.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').trim()

  return (
    <Card className="border-gray-200 bg-white">
      <CardContent className="p-4 space-y-4">
        {/* Header: Analyzer, Bug Class, Severity, Confidence */}
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="text-xs font-mono text-gray-500 mb-1">
                Analyzer: <span className="text-gray-700">{proposal.analyzer_name}</span>
              </div>
              <div className="text-sm font-semibold text-gray-900">
                {proposal.problem_statement}
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-gray-500 flex-shrink-0">
              seq #{sequenceNumber}
            </div>
          </div>

          {/* Tags: Bug Class, Severity, Confidence */}
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="text-xs">
              {bugClassLabel}
            </Badge>
            <Badge className={severityColors[proposal.severity]}>
              {proposal.severity}
            </Badge>
            <div className={`text-xs font-semibold ${confidenceColor}`}>
              {(proposal.confidence * 100).toFixed(0)}% confidence
            </div>
            {proposal.confidence < 0.6 && (
              <div className="flex items-center gap-1 text-orange-600 text-xs">
                <AlertCircle className="w-3 h-3" />
                <span>Low confidence - verify reasoning</span>
              </div>
            )}
          </div>
        </div>

        {/* Problem & Root Cause */}
        <div className="space-y-2 bg-gray-50 rounded p-3 border border-gray-200">
          <div>
            <div className="text-xs font-semibold text-gray-700 uppercase mb-1">Root Cause</div>
            <p className="text-sm text-gray-700">{proposal.root_cause_hypothesis}</p>
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-700 uppercase mb-1">Why This Is a Risk</div>
            <p className="text-sm text-gray-700">{proposal.risk_explanation}</p>
          </div>
        </div>

        {/* Affected Files */}
        {affectedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-700 uppercase">Affected Files</div>
            <div className="space-y-1">
              {affectedFiles.map((file, idx) => (
                <div
                  key={idx}
                  className="text-sm text-gray-700 bg-gray-50 rounded p-2 border border-gray-200 font-mono"
                >
                  {file.path}
                  {file.line_range && <span className="text-gray-500">:{file.line_range}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Strategies (Expandable) */}
        {proposal.suggested_strategies && proposal.suggested_strategies.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-gray-700 uppercase">
              Suggested Strategies ({proposal.suggested_strategies.length})
            </div>
            <div className="space-y-2">
              {proposal.suggested_strategies.map((strategy, idx) => (
                <div
                  key={strategy.id || idx}
                  className="border border-gray-200 rounded overflow-hidden"
                >
                  {/* Strategy Header */}
                  <button
                    onClick={() => toggleStrategy(strategy.id || idx.toString())}
                    className="w-full flex items-center justify-between p-2 bg-gray-50 hover:bg-gray-100 text-left"
                  >
                    <div className="flex-1">
                      <div className="text-sm font-semibold text-gray-900">
                        {strategy.name || `Strategy ${idx + 1}`}
                      </div>
                      <div className="text-xs text-gray-600 line-clamp-1">
                        {strategy.description}
                      </div>
                    </div>
                    {expandedStrategies.includes(strategy.id || idx.toString()) ? (
                      <ChevronUp className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    )}
                  </button>

                  {/* Strategy Details */}
                  {expandedStrategies.includes(strategy.id || idx.toString()) && (
                    <div className="p-3 border-t border-gray-200 space-y-3 bg-white">
                      <div>
                        <div className="text-xs font-semibold text-gray-700 uppercase mb-1">
                          Description
                        </div>
                        <p className="text-sm text-gray-700">{strategy.description}</p>
                      </div>

                      {strategy.effort_estimate && (
                        <div>
                          <div className="text-xs font-semibold text-gray-700 uppercase mb-1">
                            Effort Estimate
                          </div>
                          <Badge variant="outline" className="text-xs">
                            {strategy.effort_estimate}
                          </Badge>
                        </div>
                      )}

                      {strategy.prerequisites && strategy.prerequisites.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-gray-700 uppercase mb-1">
                            Prerequisites
                          </div>
                          <ul className="text-sm text-gray-700 space-y-1">
                            {strategy.prerequisites.map((req, idx) => (
                              <li key={idx} className="flex gap-2">
                                <span className="text-gray-500">•</span>
                                {req}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {strategy.assumptions && strategy.assumptions.length > 0 && (
                        <div className="bg-blue-50 border border-blue-200 rounded p-2">
                          <div className="text-xs font-semibold text-blue-900 uppercase mb-1">
                            Assumptions
                          </div>
                          <ul className="text-sm text-blue-900 space-y-1">
                            {strategy.assumptions.map((assumption, idx) => (
                              <li key={idx} className="flex gap-2">
                                <span className="text-blue-700">•</span>
                                {assumption}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {strategy.risks && strategy.risks.length > 0 && (
                        <div className="bg-orange-50 border border-orange-200 rounded p-2">
                          <div className="text-xs font-semibold text-orange-900 uppercase mb-1">
                            Risks & Tradeoffs
                          </div>
                          <ul className="text-sm text-orange-900 space-y-1">
                            {strategy.risks.map((risk, idx) => (
                              <li key={idx} className="flex gap-2">
                                <span className="text-orange-700">•</span>
                                {risk}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Conflicts (if present) */}
        {proposal.conflicting_analysis_ids && proposal.conflicting_analysis_ids.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded p-2">
            <div className="flex items-start gap-2">
              <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-xs text-amber-800">
                <strong>Note:</strong> This proposal conflicts with {proposal.conflicting_analysis_ids.length} other analysis result{proposal.conflicting_analysis_ids.length !== 1 ? 's' : ''}.
                Multiple analyzers detected overlapping issues.
              </div>
            </div>
          </div>
        )}

        {/* Read-Only Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded p-2">
          <p className="text-xs text-blue-900">
            <strong>Immutable & Replayable:</strong> This proposal was recorded by the ledger and cannot 
            be modified. It will be reconstructed identically on replay.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
