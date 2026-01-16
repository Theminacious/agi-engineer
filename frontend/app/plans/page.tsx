/**
 * Choose Your AGI Engineer Page
 * 
 * Phase 14.4: Plan Selection Finalization (Pre-Billing)
 * 
 * Presents plans as intelligence experiences with interactive selection:
 * - Core Engineer (Developer plan) - Free
 * - Advanced Engineer (Team plan) - $99/mo (mock)
 * - Autonomous Engineer (Enterprise plan) - Custom (mock)
 * 
 * Features:
 * - Interactive plan selection (no billing)
 * - Persists to localStorage
 * - Shows "Active Plan" indicator
 * - Success messaging on selection
 * - Trust copy: "Upgrades affect future runs only"
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { usePlanSelection, getPlanExperienceName } from '@/hooks/usePlanSelection'
import { 
  CheckCircle2, 
  Sparkles, 
  Zap, 
  Shield, 
  Users,
  Lock,
  ArrowRight,
  Star,
  Check,
  Info
} from 'lucide-react'

// Plan tier definitions (experience-based)
// Map internal IDs to technical plan types
const PLAN_ID_MAP = {
  core: 'developer',
  advanced: 'team',
  autonomous: 'enterprise',
} as const

const PLANS = [
  {
    id: 'core',
    name: 'Core Engineer',
    tagline: 'Essential intelligence for solo developers',
    price: 'Free',
    priceDetail: 'Always free',
    icon: Sparkles,
    color: 'blue',
    capabilities: [
      'Detects architectural violations and circular dependencies',
      'Identifies performance anti-patterns and bottlenecks',
      'Spots concurrency hazards and race conditions',
      'Finds security misconfigurations',
      'Analyzes test coverage blind spots',
      'Tracks configuration drift',
    ],
    limits: [
      'Single user',
      '100 runs per month',
      'Community support',
      '30-day audit retention',
    ],
    whoItsFor: 'Solo developers and small projects',
    bestFor: [
      'Learning AGI-assisted development',
      'Personal projects',
      'Open source contributions',
    ],
  },
  {
    id: 'advanced',
    name: 'Advanced Engineer',
    tagline: 'Deep intelligence for engineering teams',
    price: '$99',
    priceDetail: 'per month',
    icon: Zap,
    color: 'purple',
    popular: true,
    capabilities: [
      'Everything in Core Engineer, plus:',
      'Multi-hop dependency analysis and domain boundary detection',
      'N+1 query detection, I/O blocking, and memory leak analysis',
      'Advanced concurrency intelligence with shared state analysis',
      'Team workspaces with shared governance',
      'Priority support and dedicated assistance',
    ],
    limits: [
      'Up to 10 users',
      '1,000 runs per month',
      'Priority support',
      '90-day audit retention',
    ],
    whoItsFor: 'Engineering teams and growing products',
    bestFor: [
      'Team collaboration',
      'Production systems',
      'Continuous integration',
    ],
  },
  {
    id: 'autonomous',
    name: 'Autonomous Engineer',
    tagline: 'Governed autonomous engineering at scale',
    price: 'Custom',
    priceDetail: 'contact sales',
    icon: Shield,
    color: 'indigo',
    capabilities: [
      'Everything in Advanced Engineer, plus:',
      'Unlimited analysis depth and scale',
      'Compliance-grade governance and audit trails',
      'Custom integrations and enterprise SSO',
      'Dedicated support with SLA guarantees',
      'Advanced reporting and analytics',
    ],
    limits: [
      'Unlimited users',
      'Unlimited runs',
      'Dedicated support + SLA',
      'Unlimited audit retention',
    ],
    whoItsFor: 'Enterprises with compliance requirements',
    bestFor: [
      'Regulated industries',
      'Large engineering organizations',
      'Enterprise governance',
    ],
  },
]

export default function PlansPage() {
  const { plan: currentPlan, selectPlan, isLoading } = usePlanSelection()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  
  // Handle plan selection
  const handleSelectPlan = (planId: string) => {
    const technicalPlan = PLAN_ID_MAP[planId as keyof typeof PLAN_ID_MAP]
    selectPlan(technicalPlan)
    
    const planName = PLANS.find(p => p.id === planId)?.name || 'plan'
    setSuccessMessage(`✓ Switched to ${planName}! This will affect future runs only.`)
    
    // Clear message after 5 seconds
    setTimeout(() => setSuccessMessage(null), 5000)
  }
  
  // Check if plan is currently active
  const isActivePlan = (planId: string) => {
    const technicalPlan = PLAN_ID_MAP[planId as keyof typeof PLAN_ID_MAP]
    return currentPlan === technicalPlan
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      <div className="container mx-auto px-6 py-12">{/* Success message */}
        {successMessage && (
          <div className="mb-6 max-w-3xl mx-auto">
            <div className="bg-green-50 border-2 border-green-500 rounded-lg p-4 flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-green-900">{successMessage}</p>
                <p className="text-xs text-green-700 mt-1">
                  Past runs remain immutable in the ledger. Only future analyses use your new intelligence level.
                </p>
              </div>
            </div>
          </div>
        )}
        
        {/* Hero Section */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            Choose Your AGI Engineer
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Select the intelligence level that matches your engineering needs.
            All plans include immutable governance, deterministic execution, and complete transparency.
          </p>
          
          <div className="mt-6 inline-flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2">
            <Shield className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-700 font-medium">
              No billing required. Demo environment. Read-only UI.
            </span>
          </div>
        </div>

        {/* Plan Cards */}
        <div className="grid md:grid-cols-3 gap-8 max-w-7xl mx-auto mb-12">
          {PLANS.map((plan) => {
            const Icon = plan.icon
            const isPopular = plan.popular
            
            return (
              <Card 
                key={plan.id}
                className={`relative border-2 transition-all hover:shadow-xl ${
                  isPopular 
                    ? 'border-purple-500 shadow-lg scale-105' 
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                {isPopular && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                    <Badge className="bg-purple-600 text-white px-4 py-1 flex items-center gap-1">
                      <Star className="w-3 h-3" />
                      Most Popular
                    </Badge>
                  </div>
                )}
                
                <CardHeader className="pb-4">
                  <div className={`w-12 h-12 rounded-lg bg-${plan.color}-100 flex items-center justify-center mb-4`}>
                    <Icon className={`w-6 h-6 text-${plan.color}-600`} />
                  </div>
                  
                  <CardTitle className="text-2xl font-bold text-gray-900">
                    {plan.name}
                  </CardTitle>
                  
                  <p className="text-sm text-gray-600 mt-2">
                    {plan.tagline}
                  </p>
                  
                  <div className="mt-4">
                    <div className="flex items-baseline gap-1">
                      <span className="text-4xl font-bold text-gray-900">
                        {plan.price}
                      </span>
                      {plan.priceDetail !== 'Always free' && (
                        <span className="text-gray-600 text-sm">
                          /{plan.priceDetail}
                        </span>
                      )}
                    </div>
                    {plan.priceDetail === 'Always free' && (
                      <span className="text-sm text-gray-600">{plan.priceDetail}</span>
                    )}
                  </div>
                </CardHeader>
                
                <CardContent className="space-y-6">
                  {/* Capabilities */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-3">
                      What It Does:
                    </h4>
                    <ul className="space-y-2">
                      {plan.capabilities.map((capability, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                          <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                          <span>{capability}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  {/* Who It's For */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">
                      Who It's For:
                    </h4>
                    <p className="text-sm text-gray-600">
                      {plan.whoItsFor}
                    </p>
                  </div>
                  
                  {/* Best For */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">
                      Best For:
                    </h4>
                    <ul className="space-y-1">
                      {plan.bestFor.map((item, idx) => (
                        <li key={idx} className="text-sm text-gray-600 flex items-center gap-2">
                          <div className="w-1 h-1 rounded-full bg-gray-400" />
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  {/* Limits */}
                  <div className="border-t pt-4">
                    <h4 className="text-xs font-semibold text-gray-700 mb-2 uppercase">
                      Includes:
                    </h4>
                    <ul className="space-y-1">
                      {plan.limits.map((limit, idx) => (
                        <li key={idx} className="text-xs text-gray-600">
                          • {limit}
                        </li>
                      ))}
                    </ul>
                  </div>
                  
                  {/* CTA Button */}
                  {isActivePlan(plan.id) ? (
                    <div className="space-y-2">
                      <Button 
                        className="w-full bg-green-600 hover:bg-green-700 cursor-default"
                        disabled
                      >
                        <Check className="w-4 h-4 mr-2" />
                        Active Plan
                      </Button>
                      <p className="text-xs text-green-700 text-center font-medium">
                        ✓ Currently using this intelligence level
                      </p>
                    </div>
                  ) : plan.id === 'autonomous' ? (
                    <div className="space-y-2">
                      <Button 
                        className="w-full bg-indigo-600 hover:bg-indigo-700"
                        disabled
                      >
                        Contact Sales
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                      <p className="text-xs text-gray-500 text-center">
                        Custom pricing for enterprises
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <Button 
                        className={`w-full ${
                          isPopular 
                            ? 'bg-purple-600 hover:bg-purple-700' 
                            : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                        onClick={() => handleSelectPlan(plan.id)}
                        disabled={isLoading}
                      >
                        {plan.id === 'core' ? 'Switch to Core' : 'Unlock Advanced Intelligence'}
                        <Sparkles className="w-4 h-4 ml-2" />
                      </Button>
                      <p className="text-xs text-gray-500 text-center">
                        No billing • Affects future runs only
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>

        {/* Feature Comparison */}
        <div className="max-w-6xl mx-auto mb-12">
          <Card className="border-2 border-gray-200">
            <CardHeader>
              <CardTitle className="text-2xl font-bold text-gray-900">
                Intelligence Capabilities Comparison
              </CardTitle>
              <p className="text-sm text-gray-600 mt-2">
                Understand what improves as you upgrade
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">
                        Capability
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-blue-600">
                        Core
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-purple-600">
                        Advanced
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-indigo-600">
                        Autonomous
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Architecture Analysis
                      </td>
                      <td className="text-center py-3 px-4 text-gray-600">
                        Basic patterns
                      </td>
                      <td className="text-center py-3 px-4 text-purple-600 font-semibold">
                        Deep multi-hop
                      </td>
                      <td className="text-center py-3 px-4 text-indigo-600 font-semibold">
                        Deep multi-hop
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Performance Intelligence
                      </td>
                      <td className="text-center py-3 px-4 text-gray-600">
                        Basic anti-patterns
                      </td>
                      <td className="text-center py-3 px-4 text-purple-600 font-semibold">
                        N+1, memory leaks
                      </td>
                      <td className="text-center py-3 px-4 text-indigo-600 font-semibold">
                        N+1, memory leaks
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Concurrency Analysis
                      </td>
                      <td className="text-center py-3 px-4 text-gray-600">
                        Basic hazards
                      </td>
                      <td className="text-center py-3 px-4 text-purple-600 font-semibold">
                        Advanced patterns
                      </td>
                      <td className="text-center py-3 px-4 text-indigo-600 font-semibold">
                        Advanced patterns
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Team Collaboration
                      </td>
                      <td className="text-center py-3 px-4">
                        <Lock className="w-4 h-4 text-gray-400 mx-auto" />
                      </td>
                      <td className="text-center py-3 px-4">
                        <CheckCircle2 className="w-5 h-5 text-purple-600 mx-auto" />
                      </td>
                      <td className="text-center py-3 px-4">
                        <CheckCircle2 className="w-5 h-5 text-indigo-600 mx-auto" />
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Monthly Runs
                      </td>
                      <td className="text-center py-3 px-4 text-gray-600">
                        100
                      </td>
                      <td className="text-center py-3 px-4 text-purple-600 font-semibold">
                        1,000
                      </td>
                      <td className="text-center py-3 px-4 text-indigo-600 font-semibold">
                        Unlimited
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 px-4 font-medium text-gray-900">
                        Support Level
                      </td>
                      <td className="text-center py-3 px-4 text-gray-600">
                        Community
                      </td>
                      <td className="text-center py-3 px-4 text-purple-600 font-semibold">
                        Priority
                      </td>
                      <td className="text-center py-3 px-4 text-indigo-600 font-semibold">
                        Dedicated + SLA
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Future-Only Trust Messaging (Phase 14.4) */}
        <div className="max-w-4xl mx-auto mb-12">
          <Card className="border-2 border-indigo-200 bg-gradient-to-br from-indigo-50 to-purple-50">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 rounded-full bg-indigo-100 border-2 border-indigo-300 flex items-center justify-center">
                    <Lock className="w-6 h-6 text-indigo-600" />
                  </div>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    Your Past Runs Are Immutable
                  </h3>
                  <p className="text-sm text-gray-700 mb-3">
                    Switching plans only affects <strong>future analyses</strong>. All past runs remain exactly as recorded in the immutable ledger—no retroactive changes, ever.
                  </p>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span><strong>Historical runs:</strong> Locked in the ledger with original plan context</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span><strong>Future runs:</strong> Use your new intelligence level</span>
                    </div>
                    <div className="flex items-start gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <span><strong>Complete transparency:</strong> Every run records which plan was active</span>
                    </div>
                  </div>
                  <div className="mt-4 p-3 bg-white/70 border border-indigo-200 rounded-lg">
                    <p className="text-xs text-indigo-800">
                      <Info className="w-3 h-3 inline mr-1" />
                      This guarantees reproducibility and audit compliance. You can always verify exactly what intelligence was available for any past analysis.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Trust Indicators */}
        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
          <Card className="border-l-4 border-l-green-500">
            <CardContent className="p-6">
              <Shield className="w-8 h-8 text-green-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">
                Immutable Governance
              </h3>
              <p className="text-sm text-gray-600">
                Every analysis is recorded in an immutable ledger. Know exactly what happened, when, and why.
              </p>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-blue-500">
            <CardContent className="p-6">
              <CheckCircle2 className="w-8 h-8 text-blue-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">
                Deterministic Execution
              </h3>
              <p className="text-sm text-gray-600">
                Same code, same analysis, every time. No surprises, no randomness, complete replayability.
              </p>
            </CardContent>
          </Card>
          
          <Card className="border-l-4 border-l-purple-500">
            <CardContent className="p-6">
              <Users className="w-8 h-8 text-purple-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">
                Proof Over Trust
              </h3>
              <p className="text-sm text-gray-600">
                Verify AI decisions with complete transparency. The ledger proves what the AGI did.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
