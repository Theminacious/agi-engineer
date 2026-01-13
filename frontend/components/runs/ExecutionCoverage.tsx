/**
 * Execution Coverage Section for Run Detail Page
 * 
 * Phase 13.4: Show which analyzers ran vs were skipped due to plan
 * 
 * READ-ONLY: Display only, no mutation
 */

'use client'

import { useMemo } from 'react'
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui'
import { 
  getAllAnalyzers,
  getAnalyzersForPlan,
  isAnalyzerAvailableForPlan,
  getPlanLabel,
  type PlanType,
} from '@/lib/analyzerRegistry'
import { CheckCircle2, SkipForward, AlertCircle } from 'lucide-react'

interface ExecutionCoverageProps {
  plan: PlanType | null
  executedAnalyzers: string[]
  skippedAnalyzers?: string[]
}

export default function ExecutionCoverage({ 
  plan, 
  executedAnalyzers,
  skippedAnalyzers = [],
}: ExecutionCoverageProps) {
  const allAnalyzers = useMemo(() => getAllAnalyzers(), [])
  
  const planAnalyzers = useMemo(() => {
    if (!plan) return new Set<string>()
    return new Set(getAnalyzersForPlan(plan).map(a => a.id))
  }, [plan])

  const executedSet = useMemo(() => new Set(executedAnalyzers), [executedAnalyzers])
  const skippedSet = useMemo(() => new Set(skippedAnalyzers), [skippedAnalyzers])

  // Categorize analyzers
  const executed = useMemo(
    () => allAnalyzers.filter(a => executedSet.has(a.id)),
    [allAnalyzers, executedSet]
  )

  const planLocked = useMemo(
    () => allAnalyzers.filter(
      a => !planAnalyzers.has(a.id) && !executedSet.has(a.id)
    ),
    [allAnalyzers, planAnalyzers, executedSet]
  )

  const skipped = useMemo(
    () => allAnalyzers.filter(a => skippedSet.has(a.id)),
    [allAnalyzers, skippedSet]
  )

  const planLabel = plan ? getPlanLabel(plan) : 'Unknown'

  return (
    <Card className="border-l-4 border-l-purple-500">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Execution Coverage</CardTitle>
          <Badge variant="outline" className="text-xs">
            Plan: {planLabel}
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {/* Execution banner */}
          <div className="bg-purple-50 border border-purple-200 rounded p-3">
            <p className="text-xs text-purple-700">
              <strong>Immutable:</strong> Analyzer availability and execution are determined before running and recorded immutably in the ledger.
            </p>
          </div>

          {/* Summary stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-green-50 border border-green-200 rounded p-3">
              <div className="text-lg font-bold text-green-700">{executed.length}</div>
              <div className="text-xs text-green-600 font-medium">Executed</div>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded p-3">
              <div className="text-lg font-bold text-amber-700">{planLocked.length}</div>
              <div className="text-xs text-amber-600 font-medium">Plan-Locked</div>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <div className="text-lg font-bold text-blue-700">{skipped.length}</div>
              <div className="text-xs text-blue-600 font-medium">Skipped</div>
            </div>
          </div>

          {/* Executed analyzers */}
          {executed.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-600" />
                Executed Analyzers ({executed.length})
              </h4>
              <div className="space-y-2 pl-2">
                {executed.map(analyzer => (
                  <div 
                    key={analyzer.id}
                    className="flex items-start gap-3 p-2 rounded text-sm bg-green-50 border border-green-100"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <CheckCircle2 className="w-4 h-4 text-green-600" />
                    </div>
                    <div className="flex-grow">
                      <div className="font-medium text-gray-900">{analyzer.id}</div>
                      <div className="text-xs text-gray-600">{analyzer.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Plan-locked analyzers */}
          {planLocked.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-600" />
                Locked by Plan ({planLocked.length})
              </h4>
              <div className="space-y-2 pl-2">
                {planLocked.map(analyzer => (
                  <div 
                    key={analyzer.id}
                    className="flex items-start gap-3 p-2 rounded text-sm bg-amber-50 border border-amber-100"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <AlertCircle className="w-4 h-4 text-amber-600" />
                    </div>
                    <div className="flex-grow">
                      <div className="font-medium text-gray-900">{analyzer.id}</div>
                      <div className="text-xs text-gray-600">{analyzer.description}</div>
                      <div className="text-xs text-amber-600 font-semibold mt-1">
                        Requires: {getPlanLabel(analyzer.min_plan)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Skipped analyzers */}
          {skipped.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
                <SkipForward className="w-4 h-4 text-blue-600" />
                Skipped ({skipped.length})
              </h4>
              <div className="space-y-2 pl-2">
                {skipped.map(analyzer => (
                  <div 
                    key={analyzer.id}
                    className="flex items-start gap-3 p-2 rounded text-sm bg-blue-50 border border-blue-100"
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      <SkipForward className="w-4 h-4 text-blue-600" />
                    </div>
                    <div className="flex-grow">
                      <div className="font-medium text-gray-900">{analyzer.id}</div>
                      <div className="text-xs text-gray-600">{analyzer.description}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
