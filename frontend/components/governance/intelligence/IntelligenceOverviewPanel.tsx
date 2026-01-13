'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Brain, AlertTriangle } from 'lucide-react'

interface IntelligenceProposal {
  proposal_id: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  confidence: number
  analyzer_name: string
}

interface IntelligenceOverviewPanelProps {
  proposals: IntelligenceProposal[]
}

/**
 * Phase 11.4: Intelligence Overview Panel
 * 
 * READ-ONLY summary of intelligence proposals.
 * Shows aggregate statistics without any mutation capabilities.
 */
export default function IntelligenceOverviewPanel({ proposals }: IntelligenceOverviewPanelProps) {
  // Calculate statistics
  const totalProposals = proposals.length
  const severityCounts = {
    CRITICAL: proposals.filter(p => p.severity === 'CRITICAL').length,
    HIGH: proposals.filter(p => p.severity === 'HIGH').length,
    MEDIUM: proposals.filter(p => p.severity === 'MEDIUM').length,
    LOW: proposals.filter(p => p.severity === 'LOW').length,
  }
  
  const avgConfidence = totalProposals > 0
    ? (proposals.reduce((sum, p) => sum + p.confidence, 0) / totalProposals * 100).toFixed(1)
    : '—'
  
  const lowConfidenceCount = proposals.filter(p => p.confidence < 0.6).length

  const severityColors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-700 border-red-300',
    HIGH: 'bg-orange-100 text-orange-700 border-orange-300',
    MEDIUM: 'bg-yellow-100 text-yellow-700 border-yellow-300',
    LOW: 'bg-blue-100 text-blue-700 border-blue-300',
  }

  return (
    <Card className="border-blue-200 bg-blue-50">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-blue-600" />
          <CardTitle className="text-lg">Intelligence Analysis</CardTitle>
          <Badge className="bg-blue-600 text-white ml-auto">Proposals Only</Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Total Proposals */}
        <div className="bg-white rounded-lg p-3 border border-blue-200">
          <div className="text-xs text-gray-600 mb-1">Total Proposals</div>
          <div className="text-3xl font-bold text-gray-900">{totalProposals}</div>
          <p className="text-xs text-gray-500 mt-1">
            Detected by analyzers (immutable, replayable)
          </p>
        </div>

        {/* Severity Breakdown */}
        <div className="space-y-2">
          <div className="text-xs font-semibold text-gray-700 uppercase">By Severity</div>
          <div className="space-y-2">
            {Object.entries(severityCounts).map(([severity, count]) => (
              <div key={severity} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className={severityColors[severity]}>
                    {severity}
                  </Badge>
                  <span className="text-sm text-gray-600">{count} proposal{count !== 1 ? 's' : ''}</span>
                </div>
                <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${severity === 'CRITICAL' ? 'bg-red-500' : severity === 'HIGH' ? 'bg-orange-500' : severity === 'MEDIUM' ? 'bg-yellow-500' : 'bg-blue-500'}`}
                    style={{ width: totalProposals > 0 ? `${(count / totalProposals) * 100}%` : '0%' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Average Confidence */}
        <div className="bg-white rounded-lg p-3 border border-blue-200">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs text-gray-600">Average Confidence</div>
            <div className="text-lg font-bold text-gray-900">{avgConfidence}%</div>
          </div>
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500"
              style={{ width: `${parseFloat(avgConfidence as string) || 0}%` }}
            />
          </div>
        </div>

        {/* Low Confidence Warning */}
        {lowConfidenceCount > 0 && (
          <div className="bg-yellow-50 border border-yellow-300 rounded p-2 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
            <div className="text-xs text-yellow-800">
              <strong>{lowConfidenceCount}</strong> proposal{lowConfidenceCount !== 1 ? 's' : ''} have 
              confidence below 60% — verify reasoning carefully
            </div>
          </div>
        )}

        {/* Proposal-Only Banner */}
        <div className="bg-blue-100 border border-blue-300 rounded p-2">
          <p className="text-xs text-blue-900">
            <strong>🧠 Proposals Only:</strong> These are intelligence observations, not directives. 
            No code has been modified. All data is immutable and replayable from the ledger.
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
