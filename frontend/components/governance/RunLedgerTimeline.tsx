'use client'

import { LedgerEvent } from '@/lib/ledgerReader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { 
  CheckCircle2, 
  AlertCircle, 
  Shield, 
  FileCheck, 
  GitBranch,
  Clock,
  User,
  Zap
} from 'lucide-react'

interface RunLedgerTimelineProps {
  events: LedgerEvent[]
}

const eventTypeConfig: Record<string, { 
  icon: any
  color: string
  bg: string
  label: string 
}> = {
  RUN_CREATED: { 
    icon: GitBranch, 
    color: 'text-blue-600', 
    bg: 'bg-blue-50',
    label: 'Run Created' 
  },
  RUN_STARTED: { 
    icon: Zap, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'Run Started' 
  },
  ISSUE_DETECTED: { 
    icon: AlertCircle, 
    color: 'text-amber-600', 
    bg: 'bg-amber-50',
    label: 'Issues Detected' 
  },
  POLICY_RESOLVED: { 
    icon: Shield, 
    color: 'text-purple-600', 
    bg: 'bg-purple-50',
    label: 'Policy Resolved' 
  },
  PLAN_CREATED: { 
    icon: FileCheck, 
    color: 'text-indigo-600', 
    bg: 'bg-indigo-50',
    label: 'Plan Created' 
  },
  PLAN_APPROVED: { 
    icon: CheckCircle2, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'Plan Approved' 
  },
  SAFETY_CHECK_STARTED: { 
    icon: Shield, 
    color: 'text-blue-600', 
    bg: 'bg-blue-50',
    label: 'Safety Check Started' 
  },
  SAFETY_CHECK_PASSED: { 
    icon: Shield, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'Safety Check Passed' 
  },
  FIX_APPLIED: { 
    icon: CheckCircle2, 
    color: 'text-blue-600', 
    bg: 'bg-blue-50',
    label: 'Fix Applied' 
  },
  TEST_VALIDATION_STARTED: { 
    icon: FileCheck, 
    color: 'text-purple-600', 
    bg: 'bg-purple-50',
    label: 'Test Validation Started' 
  },
  TEST_VALIDATION_PASSED: { 
    icon: FileCheck, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'Test Validation Passed' 
  },
  EDR_GENERATION_STARTED: { 
    icon: FileCheck, 
    color: 'text-indigo-600', 
    bg: 'bg-indigo-50',
    label: 'EDR Generation Started' 
  },
  EDR_FINALIZED: { 
    icon: FileCheck, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'EDR Finalized' 
  },
  RUN_COMPLETED: { 
    icon: CheckCircle2, 
    color: 'text-green-600', 
    bg: 'bg-green-50',
    label: 'Run Completed' 
  },
  RUN_ABORTED: { 
    icon: AlertCircle, 
    color: 'text-red-600', 
    bg: 'bg-red-50',
    label: 'Run Aborted' 
  },
  RUN_REJECTED: { 
    icon: AlertCircle, 
    color: 'text-red-600', 
    bg: 'bg-red-50',
    label: 'Run Rejected' 
  }
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

export default function RunLedgerTimeline({ events }: RunLedgerTimelineProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Ledger Timeline
          <Badge variant="outline" className="ml-2">
            {events.length} Events
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {events.map((event, idx) => {
            const config = eventTypeConfig[event.event_type] || {
              icon: AlertCircle,
              color: 'text-gray-600',
              bg: 'bg-gray-50',
              label: event.event_type
            }
            
            const Icon = config.icon
            const isHighlight = [
              'PLAN_APPROVED',
              'SAFETY_CHECK_PASSED',
              'RUN_COMPLETED',
              'EDR_FINALIZED'
            ].includes(event.event_type)
            
            return (
              <div 
                key={event.sequence}
                className={`relative flex gap-4 pb-8 ${idx === events.length - 1 ? 'pb-0' : ''}`}
              >
                {/* Timeline Line */}
                {idx !== events.length - 1 && (
                  <div className="absolute left-[18px] top-[36px] bottom-0 w-px bg-gray-200" />
                )}
                
                {/* Icon */}
                <div className={`relative z-10 flex-shrink-0 w-9 h-9 rounded-full ${config.bg} flex items-center justify-center ${isHighlight ? 'ring-2 ring-offset-2 ring-green-500' : ''}`}>
                  <Icon className={`w-4 h-4 ${config.color}`} />
                </div>
                
                {/* Content */}
                <div className="flex-1 pt-1">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`font-medium ${config.color}`}>
                          {config.label}
                        </span>
                        <Badge variant="secondary" className="text-xs">
                          seq={event.sequence}
                        </Badge>
                        {event.actor_role === 'Human' && (
                          <Badge className="bg-green-100 text-green-700 border-green-300">
                            <User className="w-3 h-3 mr-1" />
                            Human
                          </Badge>
                        )}
                      </div>
                      
                      <div className="text-xs text-gray-500 mb-2">
                        {formatTimestamp(event.timestamp)}
                        {event.actor && (
                          <span className="ml-2">
                            • Actor: <span className="font-mono">{event.actor}</span>
                          </span>
                        )}
                        {event.phase && (
                          <span className="ml-2">
                            • Phase: <span className="font-mono">{event.phase}</span>
                          </span>
                        )}
                      </div>
                      
                      {event.payload && Object.keys(event.payload).length > 0 && (
                        <div className="text-xs bg-gray-50 rounded p-2 font-mono text-gray-700">
                          {Object.entries(event.payload).map(([key, value]) => (
                            <div key={key}>
                              <span className="text-gray-500">{key}:</span>{' '}
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
