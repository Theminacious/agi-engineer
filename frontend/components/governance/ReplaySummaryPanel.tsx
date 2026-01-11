'use client'

import { ReplaySummary } from '@/lib/ledgerReader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  FileCheck,
  Shield,
  Clock
} from 'lucide-react'

interface ReplaySummaryPanelProps {
  summary: ReplaySummary
}

export default function ReplaySummaryPanel({ summary }: ReplaySummaryPanelProps) {
  const stateColors: Record<string, string> = {
    COMPLETE: 'bg-green-100 text-green-700 border-green-300',
    INCOMPLETE: 'bg-amber-100 text-amber-700 border-amber-300',
    ABORTED: 'bg-red-100 text-red-700 border-red-300',
    REJECTED: 'bg-red-100 text-red-700 border-red-300'
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}m ${secs}s`
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileCheck className="w-5 h-5" />
          Replay Summary
          <Badge variant="outline" className="ml-2">
            Deterministic
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Final State */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="text-sm font-medium text-gray-700">Final State</span>
          <Badge className={stateColors[summary.final_state] || 'bg-gray-100'}>
            {summary.final_state}
          </Badge>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-blue-50 rounded-lg">
            <div className="text-xs text-blue-600 mb-1">Events</div>
            <div className="text-2xl font-bold text-blue-900">{summary.event_count}</div>
          </div>
          
          <div className="p-3 bg-green-50 rounded-lg">
            <div className="text-xs text-green-600 mb-1">Fixes Applied</div>
            <div className="text-2xl font-bold text-green-900">{summary.fixes_count}</div>
          </div>
          
          {summary.issues_detected !== undefined && (
            <div className="p-3 bg-amber-50 rounded-lg">
              <div className="text-xs text-amber-600 mb-1">Issues Detected</div>
              <div className="text-2xl font-bold text-amber-900">{summary.issues_detected}</div>
            </div>
          )}
          
          {summary.duration_seconds !== undefined && (
            <div className="p-3 bg-purple-50 rounded-lg">
              <div className="text-xs text-purple-600 mb-1">Duration</div>
              <div className="text-2xl font-bold text-purple-900">
                {formatDuration(summary.duration_seconds)}
              </div>
            </div>
          )}
        </div>

        {/* Decision Indicators */}
        <div className="space-y-2">
          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50">
            <div className="flex items-center gap-2 text-sm">
              {summary.plan_approved ? (
                <CheckCircle2 className="w-4 h-4 text-green-600" />
              ) : (
                <XCircle className="w-4 h-4 text-red-600" />
              )}
              <span className={summary.plan_approved ? 'text-green-700' : 'text-red-700'}>
                Plan Approved
              </span>
            </div>
            <Badge variant={summary.plan_approved ? 'default' : 'destructive'} className="text-xs">
              {summary.plan_approved ? 'Yes' : 'No'}
            </Badge>
          </div>

          <div className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50">
            <div className="flex items-center gap-2 text-sm">
              {summary.safety_passed ? (
                <Shield className="w-4 h-4 text-green-600" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-red-600" />
              )}
              <span className={summary.safety_passed ? 'text-green-700' : 'text-red-700'}>
                Safety Checks Passed
              </span>
            </div>
            <Badge variant={summary.safety_passed ? 'default' : 'destructive'} className="text-xs">
              {summary.safety_passed ? 'Yes' : 'No'}
            </Badge>
          </div>
        </div>

        {/* EDR */}
        {summary.edr_id && (
          <div className="p-3 bg-indigo-50 rounded-lg">
            <div className="text-xs text-indigo-600 mb-1">EDR (Engineering Decision Report)</div>
            <div className="text-sm font-mono text-indigo-900">{summary.edr_id}</div>
          </div>
        )}

        {/* Invariant Violations */}
        <div className="p-3 border rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Invariant Violations</span>
            <Badge 
              variant={summary.invariant_violations.length === 0 ? 'default' : 'destructive'}
              className={summary.invariant_violations.length === 0 ? 'bg-green-100 text-green-700' : ''}
            >
              {summary.invariant_violations.length}
            </Badge>
          </div>
          
          {summary.invariant_violations.length === 0 ? (
            <div className="flex items-center gap-2 text-sm text-green-700">
              <CheckCircle2 className="w-4 h-4" />
              <span>No violations detected</span>
            </div>
          ) : (
            <div className="space-y-1">
              {summary.invariant_violations.map((violation, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm text-red-700">
                  <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <span>{violation}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Read-Only Notice */}
        <div className="text-xs text-gray-500 italic p-2 bg-gray-50 rounded">
          ℹ️ This summary was generated by deterministic replay.
          Replaying the same events will always produce identical results.
        </div>
      </CardContent>
    </Card>
  )
}
