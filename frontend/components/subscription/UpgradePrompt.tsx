/**
 * Upgrade Prompt Component
 * 
 * Phase 14.3.1: Upgrade Motivation & Friction Layer
 * 
 * Contextual upgrade prompt shown when analyzers are skipped due to plan limitations.
 * Emphasizes intelligence capabilities gained, not just features unlocked.
 * 
 * Design Principles:
 * - Honest: Uses real skipped analyzer data
 * - Transparent: Explains what intelligence was unavailable
 * - Trust-first: Past runs remain immutable, upgrades affect future only
 * - Benefit-focused: Highlights Advanced Engineer capabilities
 * - No dark patterns: No fake scarcity, no misleading claims
 * 
 * READ-ONLY: Demo UI, no billing integration
 */

'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { Card, CardContent, Badge } from '@/components/ui'
import { 
  getAnalyzer,
  type PlanType,
  type AnalyzerCategory,
} from '@/lib/analyzerRegistry'
import { 
  Sparkles, 
  TrendingUp, 
  Shield, 
  ArrowRight, 
  CheckCircle2,
  AlertTriangle,
  Info,
} from 'lucide-react'

interface UpgradePromptProps {
  currentPlan: PlanType
  skippedAnalyzers: string[]
  className?: string
}

interface SkippedCapability {
  id: string
  description: string
  category: AnalyzerCategory
  requiredPlan: PlanType
}

export default function UpgradePrompt({ 
  currentPlan, 
  skippedAnalyzers, 
  className = '' 
}: UpgradePromptProps) {
  // Parse skipped analyzers to get capability details
  const skippedCapabilities = useMemo<SkippedCapability[]>(() => {
    return skippedAnalyzers
      .map(id => {
        const analyzer = getAnalyzer(id)
        if (!analyzer) return null
        return {
          id: analyzer.id,
          description: analyzer.service_description,
          category: analyzer.category,
          requiredPlan: analyzer.min_plan,
        }
      })
      .filter((item): item is SkippedCapability => item !== null)
  }, [skippedAnalyzers])

  // Group by category for better organization
  const groupedByCategory = useMemo(() => {
    const groups: Record<string, SkippedCapability[]> = {}
    skippedCapabilities.forEach(cap => {
      if (!groups[cap.category]) {
        groups[cap.category] = []
      }
      groups[cap.category].push(cap)
    })
    return groups
  }, [skippedCapabilities])

  // Don't show if no skipped capabilities
  if (skippedCapabilities.length === 0) {
    return null
  }

  // Plan experience names
  const planNames: Record<PlanType, string> = {
    developer: 'Core Engineer',
    team: 'Advanced Engineer',
    enterprise: 'Autonomous Engineer',
  }

  // Recommend Advanced Engineer (team plan) as the default upgrade path
  const recommendedPlan = 'team'
  const currentPlanName = planNames[currentPlan]
  const recommendedPlanName = planNames[recommendedPlan]

  return (
    <Card className={`border-2 border-purple-200 bg-gradient-to-br from-purple-50 to-blue-50 ${className}`}>
      <CardContent className="p-6">
        <div className="flex items-start gap-4">
          {/* Icon */}
          <div className="flex-shrink-0">
            <div className="w-12 h-12 rounded-full bg-purple-100 border-2 border-purple-300 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-purple-600" />
            </div>
          </div>

          {/* Content */}
          <div className="flex-grow">
            {/* Header */}
            <div className="mb-3">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-lg font-semibold text-gray-900">
                  Unlock Deeper Intelligence
                </h3>
                <Badge className="bg-purple-600 text-white text-xs">
                  {skippedCapabilities.length} Capabilities Unavailable
                </Badge>
              </div>
              <p className="text-sm text-gray-700">
                Your <strong>{currentPlanName}</strong> plan skipped {skippedCapabilities.length} advanced {skippedCapabilities.length === 1 ? 'capability' : 'capabilities'} during this run. 
                Upgrade to <strong>{recommendedPlanName}</strong> to catch issues before they impact your team.
              </p>
            </div>

            {/* Skipped capabilities by category */}
            <div className="mb-4 space-y-3">
              {Object.entries(groupedByCategory).map(([category, capabilities]) => (
                <div key={category} className="bg-white/70 border border-purple-200 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-purple-900 uppercase tracking-wide mb-2">
                    {category} Intelligence Unavailable
                  </h4>
                  <ul className="space-y-1.5">
                    {capabilities.map(cap => (
                      <li key={cap.id} className="flex items-start gap-2 text-sm text-gray-700">
                        <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                        <span>{cap.description}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>

            {/* Advanced Engineer highlights */}
            <div className="mb-4 bg-white/70 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-5 h-5 text-purple-600" />
                <h4 className="text-sm font-semibold text-gray-900">
                  What You Get with {recommendedPlanName}
                </h4>
              </div>
              <ul className="space-y-2">
                <li className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span><strong>Deep multi-hop architecture analysis</strong> - Trace dependencies across your entire system</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span><strong>N+1 query detection</strong> - Catch database performance issues before production</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span><strong>Advanced concurrency intelligence</strong> - Verify thread-safety and async patterns</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span><strong>1,000 runs/month</strong> - 10x capacity for continuous integration</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-gray-700">
                  <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span><strong>Team collaboration</strong> - Shared workspaces with up to 10 users</span>
                </li>
              </ul>
            </div>

            {/* Trust & transparency copy */}
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Shield className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-blue-800">
                  <strong>Immutable Governance:</strong> Past runs remain unchanged in the ledger. 
                  Upgrades only affect future analyses, ensuring complete transparency and reproducibility.
                </div>
              </div>
            </div>

            {/* CTA */}
            <div className="flex items-center gap-3">
              <Link 
                href="/plans"
                className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors"
              >
                Compare Plans
                <ArrowRight className="w-4 h-4" />
              </Link>
              <div className="text-xs text-gray-600">
                <Info className="w-3 h-3 inline mr-1" />
                Demo environment - no billing required
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
