/**
 * Plan Context Block for Governance Page
 * 
 * Phase 13.4: Show subscription plan and analyzer eligibility for immutable governance
 * 
 * READ-ONLY: Display immutable plan context from ledger
 */

'use client'

import { 
  getAllAnalyzers,
  getAnalyzersForPlan,
  getPlanLabel,
  type PlanType,
} from '@/lib/analyzerRegistry'
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui'
import { Shield, Lock } from 'lucide-react'
import { useMemo } from 'react'

interface PlanContextBlockProps {
  plan: PlanType | null
  timestamp?: string
}

export default function PlanContextBlock({ plan, timestamp }: PlanContextBlockProps) {
  const allAnalyzers = useMemo(() => getAllAnalyzers(), [])
  
  const planAnalyzers = useMemo(() => {
    if (!plan) return new Set<string>()
    return new Set(getAnalyzersForPlan(plan).map(a => a.id))
  }, [plan])

  const enabledCount = planAnalyzers.size
  const lockedCount = allAnalyzers.length - enabledCount
  const planLabel = plan ? getPlanLabel(plan) : 'Unknown'

  const formatTimestamp = (ts?: string) => {
    if (!ts) return '—'
    try {
      const date = new Date(ts)
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    } catch {
      return ts
    }
  }

  return (
    <Card className="border-l-4 border-l-indigo-500 mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            Plan Context
          </CardTitle>
          <Badge className="bg-indigo-100 text-indigo-700 border-indigo-300">
            Immutable Record
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* Key info */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-indigo-50 border border-indigo-200 rounded p-3">
              <div className="text-xs text-indigo-600 font-semibold uppercase">
                Subscription Plan
              </div>
              <div className="text-lg font-bold text-indigo-900 mt-1">
                {planLabel}
              </div>
            </div>

            <div className="bg-green-50 border border-green-200 rounded p-3">
              <div className="text-xs text-green-600 font-semibold uppercase">
                Analyzers Enabled
              </div>
              <div className="text-lg font-bold text-green-900 mt-1">
                {enabledCount}
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded p-3">
              <div className="text-xs text-amber-600 font-semibold uppercase">
                Locked
              </div>
              <div className="text-lg font-bold text-amber-900 mt-1">
                {lockedCount}
              </div>
            </div>
          </div>

          {/* Timestamp if available */}
          {timestamp && (
            <div className="bg-gray-50 border border-gray-200 rounded p-3">
              <div className="text-xs text-gray-600 font-semibold uppercase">
                Recorded At
              </div>
              <div className="text-sm text-gray-900 font-mono mt-1">
                {formatTimestamp(timestamp)}
              </div>
            </div>
          )}

          {/* Explanation */}
          <div className="bg-blue-50 border border-blue-200 rounded p-4">
            <p className="text-xs text-blue-700 leading-relaxed">
              <Lock className="w-3 h-3 text-blue-600 inline-block mr-1" />
              <strong>Immutable Governance:</strong> Analyzer availability is determined by the subscription plan before execution and recorded immutably in the ledger. This ensures transparent, auditable access control for every analysis run.
            </p>
          </div>

          {/* Analyzer eligibility summary */}
          {plan && (
            <div className="bg-gray-50 border border-gray-200 rounded p-3">
              <div className="text-sm font-semibold text-gray-900 mb-2">
                Analyzer Eligibility
              </div>
              <div className="text-xs text-gray-700 space-y-1">
                <p>
                  <strong>{planLabel}</strong> plan includes <strong>{enabledCount}</strong> analyzers across all categories:
                </p>
                <ul className="list-disc list-inside pl-2 mt-1">
                  {getAllAnalyzers()
                    .filter(a => planAnalyzers.has(a.id))
                    .slice(0, 5)
                    .map(a => (
                      <li key={a.id} className="text-gray-600">
                        {a.id}
                      </li>
                    ))}
                  {enabledCount > 5 && (
                    <li className="text-gray-600 italic">
                      + {enabledCount - 5} more...
                    </li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
