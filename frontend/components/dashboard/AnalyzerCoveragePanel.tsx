/**
 * Analyzer Coverage Panel for Dashboard
 * 
 * Phase 13.4: Display all analyzers with their status (enabled/locked)
 * for the current subscription plan.
 * 
 * READ-ONLY: No mutation, no upgrades, no billing logic
 */

'use client'

import { useMemo } from 'react'
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui'
import { 
  getAllAnalyzers, 
  getAnalyzersForPlan, 
  groupAnalyzersByCategory,
  getCategoryLabel,
  getPlanLabel,
  type PlanType,
  type AnalyzerCategory,
} from '@/lib/analyzerRegistry'
import { Lock, CheckCircle2 } from 'lucide-react'

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

  const currentPlanLabel = currentPlan ? getPlanLabel(currentPlan) : 'Unknown'

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Analyzer Coverage</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs font-medium">
              Plan: {currentPlanLabel}
            </Badge>
            <Badge variant="default" className="text-xs font-medium bg-blue-600">
              {enabledCount}/{totalAnalyzers} Active
            </Badge>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="space-y-4">
          {/* Summary stats */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-green-50 border border-green-200 rounded p-3">
              <div className="text-2xl font-bold text-green-700">{enabledCount}</div>
              <div className="text-xs text-green-600 font-medium">Enabled Analyzers</div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded p-3">
              <div className="text-2xl font-bold text-amber-700">{totalAnalyzers - enabledCount}</div>
              <div className="text-xs text-amber-600 font-medium">Locked (Requires Plan)</div>
            </div>
          </div>

          {/* Analyzer list by category */}
          <div className="space-y-4">
            {(Object.keys(grouped) as AnalyzerCategory[]).map(category => {
              const analyzers = grouped[category]
              if (analyzers.length === 0) return null

              return (
                <div key={category}>
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">
                    {getCategoryLabel(category)}
                  </h4>
                  <div className="space-y-2 pl-2">
                    {analyzers.map(analyzer => {
                      const isEnabled = availableForPlan.has(analyzer.id)
                      return (
                        <div 
                          key={analyzer.id} 
                          className={`flex items-start gap-3 p-2 rounded text-sm ${
                            isEnabled 
                              ? 'bg-green-50 border border-green-100' 
                              : 'bg-gray-50 border border-gray-200'
                          }`}
                        >
                          <div className="flex-shrink-0 mt-0.5">
                            {isEnabled ? (
                              <CheckCircle2 className="w-4 h-4 text-green-600" />
                            ) : (
                              <Lock className="w-4 h-4 text-gray-400" />
                            )}
                          </div>
                          <div className="flex-grow">
                            <div className="font-medium text-gray-900">
                              {analyzer.id}
                            </div>
                            <div className="text-xs text-gray-600 mt-0.5">
                              {analyzer.description}
                            </div>
                            {!isEnabled && (
                              <div className="text-xs text-amber-600 font-semibold mt-1">
                                Requires: {getPlanLabel(analyzer.min_plan)}
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

          {/* Info banner */}
          <div className="bg-blue-50 border border-blue-200 rounded p-3 mt-4">
            <p className="text-xs text-blue-700">
              <strong>Note:</strong> Analyzer availability is determined by your subscription plan and recorded immutably in each run.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
