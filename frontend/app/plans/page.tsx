'use client'

import { useState } from 'react'
import { AppShell, ErrorAlert } from '@/components/layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { usePlanSelection } from '@/hooks/usePlanSelection'
import { 
  CheckCircle2, 
  Shield, 
  Lock,
  AlertCircle,
  Check
} from 'lucide-react'

const PLAN_ID_MAP = {
  core: 'developer',
  advanced: 'team',
  autonomous: 'enterprise',
} as const

const PLANS = [
  {
    id: 'core',
    name: 'Core Engineer',
    price: 'Free',
    users: 'Single user',
    runs: '100/month',
    support: 'Community',
    retention: '30 days',
    features: {
      arch: 'Basic patterns',
      perf: 'Basic anti-patterns',
      concurrency: 'Basic hazards',
      team: false,
      priority: false,
    }
  },
  {
    id: 'advanced',
    name: 'Advanced Engineer',
    price: '$99/mo',
    users: 'Up to 10',
    runs: '1,000/month',
    support: 'Priority',
    retention: '90 days',
    popular: true,
    features: {
      arch: 'Deep multi-hop',
      perf: 'N+1, memory leaks',
      concurrency: 'Advanced patterns',
      team: true,
      priority: true,
    }
  },
  {
    id: 'autonomous',
    name: 'Autonomous Engineer',
    price: 'Custom',
    users: 'Unlimited',
    runs: 'Unlimited',
    support: 'Dedicated + SLA',
    retention: 'Unlimited',
    features: {
      arch: 'Deep multi-hop',
      perf: 'N+1, memory leaks',
      concurrency: 'Advanced patterns',
      team: true,
      priority: true,
    }
  },
]

const CAPABILITIES = [
  {
    category: 'Architecture Analysis',
    key: 'arch' as const,
  },
  {
    category: 'Performance Intelligence',
    key: 'perf' as const,
  },
  {
    category: 'Concurrency Analysis',
    key: 'concurrency' as const,
  },
  {
    category: 'Team Workspaces',
    key: 'team' as const,
  },
  {
    category: 'Priority Support',
    key: 'priority' as const,
  },
]

export default function PlansPage() {
  const { plan: currentPlan, selectPlan, isLoading } = usePlanSelection()
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  
  const handleSelectPlan = (planId: string) => {
    const technicalPlan = PLAN_ID_MAP[planId as keyof typeof PLAN_ID_MAP]
    selectPlan(technicalPlan)
    
    const planName = PLANS.find(p => p.id === planId)?.name || 'plan'
    setSuccessMessage(`Switched to ${planName}. This will affect future runs only.`)
    
    setTimeout(() => setSuccessMessage(null), 5000)
  }
  
  const isActivePlan = (planId: string) => {
    const technicalPlan = PLAN_ID_MAP[planId as keyof typeof PLAN_ID_MAP]
    return currentPlan === technicalPlan
  }
  
  return (
    <AppShell>
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Plans</h1>
          <p className="text-sm text-muted-foreground mt-1">Choose the intelligence level for your engineering needs</p>
        </div>

        {successMessage && (
          <div className="border border-green-500/20 bg-green-500/10 rounded p-4 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm text-foreground">{successMessage}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Past runs remain immutable in the ledger
              </p>
            </div>
          </div>
        )}

        {/* Important Notice */}
        <div className="border border-border rounded p-4 flex items-start gap-3">
          <Shield className="w-5 h-5 text-primary flex-shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <p className="text-sm text-foreground">
              <strong>Demo environment:</strong> No billing required. Plan selection affects analysis behavior only.
            </p>
            <ul className="text-xs text-muted-foreground space-y-1">
              <li>• Historical runs: Locked in ledger with original plan context</li>
              <li>• Future runs: Use your new intelligence level</li>
              <li>• Complete transparency: Every run records which plan was active</li>
            </ul>
          </div>
        </div>

        {/* Plan Comparison Table */}
        <div className="border border-border rounded">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-48">Plan</TableHead>
                {PLANS.map(plan => (
                  <TableHead key={plan.id} className="text-center">
                    <div className="space-y-2">
                      <div className="flex items-center justify-center gap-2">
                        <span className="font-semibold">{plan.name}</span>
                        {plan.popular && (
                          <Badge variant="default" className="text-xs">Popular</Badge>
                        )}
                      </div>
                      <div className="text-base font-semibold text-foreground">{plan.price}</div>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Users */}
              <TableRow>
                <TableCell className="font-medium">Users</TableCell>
                {PLANS.map(plan => (
                  <TableCell key={plan.id} className="text-center text-muted-foreground">
                    {plan.users}
                  </TableCell>
                ))}
              </TableRow>

              {/* Runs */}
              <TableRow>
                <TableCell className="font-medium">Monthly Runs</TableCell>
                {PLANS.map(plan => (
                  <TableCell key={plan.id} className="text-center text-muted-foreground">
                    {plan.runs}
                  </TableCell>
                ))}
              </TableRow>

              {/* Support */}
              <TableRow>
                <TableCell className="font-medium">Support</TableCell>
                {PLANS.map(plan => (
                  <TableCell key={plan.id} className="text-center text-muted-foreground">
                    {plan.support}
                  </TableCell>
                ))}
              </TableRow>

              {/* Retention */}
              <TableRow>
                <TableCell className="font-medium">Audit Retention</TableCell>
                {PLANS.map(plan => (
                  <TableCell key={plan.id} className="text-center text-muted-foreground">
                    {plan.retention}
                  </TableCell>
                ))}
              </TableRow>

              {/* Divider */}
              <TableRow>
                <TableCell colSpan={4} className="bg-muted h-2"></TableCell>
              </TableRow>

              {/* Capabilities */}
              {CAPABILITIES.map(capability => (
                <TableRow key={capability.key}>
                  <TableCell className="font-medium">{capability.category}</TableCell>
                  {PLANS.map(plan => {
                    const value = plan.features[capability.key]
                    return (
                      <TableCell key={plan.id} className="text-center">
                        {typeof value === 'boolean' ? (
                          value ? (
                            <Check className="w-4 h-4 mx-auto text-primary" />
                          ) : (
                            <Lock className="w-4 h-4 mx-auto text-muted-foreground opacity-30" />
                          )
                        ) : (
                          <span className="text-sm text-muted-foreground">{value}</span>
                        )}
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))}

              {/* CTAs */}
              <TableRow>
                <TableCell className="font-medium">Action</TableCell>
                {PLANS.map(plan => (
                  <TableCell key={plan.id} className="text-center">
                    {isActivePlan(plan.id) ? (
                      <div className="inline-flex items-center gap-2 text-xs text-green-400">
                        <Check className="w-4 h-4" />
                        <span>Active Plan</span>
                      </div>
                    ) : plan.id === 'autonomous' ? (
                      <Button variant="outline" size="sm" disabled>
                        Contact Sales
                      </Button>
                    ) : (
                      <Button 
                        variant={plan.popular ? 'default' : 'outline'}
                        size="sm"
                        onClick={() => handleSelectPlan(plan.id)}
                        disabled={isLoading}
                      >
                        Select Plan
                      </Button>
                    )}
                  </TableCell>
                ))}
              </TableRow>
            </TableBody>
          </Table>
        </div>

        {/* Governance Guarantees */}
        <div className="grid grid-cols-3 gap-6">
          <div className="border border-border rounded p-4">
            <Shield className="w-5 h-5 text-primary mb-3" />
            <h3 className="text-sm font-semibold mb-2">Immutable Governance</h3>
            <p className="text-xs text-muted-foreground">
              Every analysis is recorded in an immutable ledger with complete history
            </p>
          </div>
          
          <div className="border border-border rounded p-4">
            <CheckCircle2 className="w-5 h-5 text-primary mb-3" />
            <h3 className="text-sm font-semibold mb-2">Deterministic Execution</h3>
            <p className="text-xs text-muted-foreground">
              Same code, same analysis, every time. Complete replayability
            </p>
          </div>
          
          <div className="border border-border rounded p-4">
            <AlertCircle className="w-5 h-5 text-primary mb-3" />
            <h3 className="text-sm font-semibold mb-2">Proof Over Trust</h3>
            <p className="text-xs text-muted-foreground">
              Verify AI decisions with complete transparency and audit trails
            </p>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
