/**
 * Plan Context Block for Governance Page
 * 
 * Phase 14.4: Plan Selection Finalization (Pre-Billing)
 * 
 * Shows intelligence experience and capability eligibility.
 * Reads active plan from localStorage via usePlanSelection hook.
 * Falls back to prop if provided (for historical runs).
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
import UpgradePrompt from '@/components/subscription/UpgradePrompt'
import { usePlanSelection } from '@/hooks/usePlanSelection'
import { Shield, Lock, CheckCircle2 } from 'lucide-react'
import { useMemo } from 'react'

interface PlanContextBlockProps {
  plan?: PlanType | null  // Optional: for historical runs
  timestamp?: string
}

export default function PlanContextBlock({ plan: propPlan, timestamp }: PlanContextBlockProps) {
  const { plan: selectedPlan } = usePlanSelection()
  
  // Use prop plan if provided (historical run), otherwise use selected plan
  const plan = propPlan || selectedPlan
  const allAnalyzers = useMemo(() => getAllAnalyzers(), [])
  
  const planAnalyzers = useMemo(() => {
    if (!plan) return new Set<string>()
    return new Set(getAnalyzersForPlan(plan).map(a => a.id))
  }, [plan])

  const enabledCount = planAnalyzers.size
  const lockedCount = allAnalyzers.length - enabledCount
  const planLabel = plan ? getPlanLabel(plan) : 'Unknown'
  
  // Experience-based plan names
  const planExperienceMap: Record<PlanType, string> = {
    developer: 'Core Engineer',
    team: 'Advanced Engineer',
    enterprise: 'Autonomous Engineer',
  }
  const experienceName = plan ? planExperienceMap[plan] : 'Unknown'
  
  // Get locked analyzers for upgrade prompt
  const lockedAnalyzers = useMemo(() => {
    return allAnalyzers
      .filter(a => !planAnalyzers.has(a.id))
      .map(a => a.id)
  }, [allAnalyzers, planAnalyzers])

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
    <>
      {/* Upgrade prompt if capabilities are locked */}
      {lockedCount > 0 && plan && (
        <div className="mb-4">
          <UpgradePrompt 
            currentPlan={plan}
            skippedAnalyzers={lockedAnalyzers}
          />
        </div>
      )}
      
      <Card className="border-l-4 border-l-indigo-500 mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="w-5 h-5 text-indigo-600" />
            Intelligence Experience Context
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
                Intelligence Experience
              </div>
              <div className="text-lg font-bold text-indigo-900 mt-1">
                {experienceName}
              </div>
            </div>

            <div className="bg-green-50 border border-green-200 rounded p-3">
              <div className="text-xs text-green-600 font-semibold uppercase">
                Capabilities Enabled
              </div>
              <div className="text-lg font-bold text-green-900 mt-1">
                {enabledCount}
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded p-3">
              <div className="text-xs text-amber-600 font-semibold uppercase">
                Advanced Unavailable
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
              <strong>Immutable Governance:</strong> Your AGI's capabilities are determined by your intelligence experience before execution and recorded permanently in the ledger. This ensures transparent, auditable access control for every analysis run.
            </p>
          </div>

          {/* Service eligibility summary */}
          {plan && (
            <div className="bg-gray-50 border border-gray-200 rounded p-3">
              <div className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Active Capabilities
              </div>
              <div className="text-xs text-gray-700 space-y-2">
                <p className="font-medium">
                  Your <strong>{experienceName}</strong> experience includes <strong>{enabledCount}</strong> intelligence capabilities:
                </p>
                <ul className="space-y-1 mt-2">
                  {getAllAnalyzers()
                    .filter(a => planAnalyzers.has(a.id))
                    .slice(0, 5)
                    .map(a => (
                      <li key={a.id} className="flex items-start gap-2 text-gray-600">
                        <CheckCircle2 className="w-3 h-3 text-green-600 mt-0.5 flex-shrink-0" />
                        <span>{a.service_description}</span>
                      </li>
                    ))}
                  {enabledCount > 5 && (
                    <li className="text-gray-500 italic pl-5">
                      + {enabledCount - 5} more capabilities...
                    </li>
                  )}
                </ul>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
    </>
  )
}
