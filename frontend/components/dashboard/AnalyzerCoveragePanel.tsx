/**
 * Analyzer Coverage Panel for Dashboard
 * 
 * Phase 14.3: Experience-Based Intelligence Display
 * 
 * Presents capabilities as "what your AGI can do":
 * - Uses experience language: "Core Engineer", "Advanced Engineer", "Autonomous Engineer"
 * - Focus on benefits and outcomes, not technical features
 * - Locked services explain upgrade value, not technical limitations
 * 
 * READ-ONLY: No mutation, no upgrades, no billing logic
 */

'use client'

import { useMemo } from 'react'
import { 
  getAllAnalyzers, 
  getAnalyzersForPlan, 
  groupAnalyzersByCategory,
  getCategoryLabel,
  getPlanLabel,
  type PlanType,
  type AnalyzerCategory,
} from '@/lib/analyzerRegistry'
import { Lock, CheckCircle2, Info } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface AnalyzerCoveragePanelProps {
  currentPlan: PlanType | null
}

export default function AnalyzerCoveragePanel({ currentPlan }: AnalyzerCoveragePanelProps) {
  const grouped = useMemo(() => groupAnalyzersByCategory(), [])
  
  const availableForPlan = useMemo(() => {
    if (!currentPlan) return new Set<string>()
    return new Set(getAnalyzersForPlan(currentPlan).map(a => a.id))
  }, [currentPlan])

  const totalAnalyzers = useMemo(() => getAllAnalyzers().length, [])
  const enabledCount = useMemo(() => availableForPlan.size, [availableForPlan])

  // Map technical plan names to experience language
  const planExperienceMap: Record<PlanType, string> = {
    developer: 'Core Engineer',
    team: 'Advanced Engineer',
    enterprise: 'Autonomous Engineer',
  }
  const currentPlanLabel = currentPlan ? planExperienceMap[currentPlan] : 'Unknown'

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-2xl font-semibold text-green-600">{enabledCount}</div>
          <div className="text-sm text-muted-foreground">Active</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-semibold text-amber-600">{totalAnalyzers - enabledCount}</div>
          <div className="text-sm text-muted-foreground">Requires Upgrade</div>
        </div>
      </div>

      {/* Service list by category */}
      <div className="space-y-4">
        {(Object.keys(grouped) as AnalyzerCategory[]).map(category => {
          const analyzers = grouped[category]
          if (analyzers.length === 0) return null

          return (
            <div key={category}>
              <h4 className="text-sm font-medium text-muted-foreground mb-2">
                {getCategoryLabel(category)}
              </h4>
              <div className="space-y-2">
                {analyzers.map(analyzer => {
                  const isEnabled = availableForPlan.has(analyzer.id)
                  return (
                    <div 
                      key={analyzer.id} 
                      className="flex items-start gap-3 p-3 rounded-md border bg-card"
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        {isEnabled ? (
                          <CheckCircle2 className="w-4 h-4 text-green-600" />
                        ) : (
                          <Lock className="w-4 h-4 text-muted-foreground" />
                        )}
                      </div>
                      <div className="flex-grow">
                        <div className="font-medium text-sm">
                          {analyzer.service_description}
                        </div>
                        {!isEnabled && (
                          <div className="flex items-start gap-1 mt-1">
                            <Badge variant="outline" className="text-xs">
                              Requires {planExperienceMap[analyzer.min_plan]}
                            </Badge>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
