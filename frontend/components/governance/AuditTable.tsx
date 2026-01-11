'use client'

import { LedgerEvent } from '@/lib/ledgerReader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, FileText, User } from 'lucide-react'

interface AuditTableProps {
  events: LedgerEvent[]
}

export default function AuditTable({ events }: AuditTableProps) {
  const formatTimestamp = (ts: string) => {
    const date = new Date(ts)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }

  const truncatePayload = (payload: any) => {
    const str = JSON.stringify(payload, null, 0)
    return str.length > 60 ? str.substring(0, 57) + '...' : str
  }

  const eventTypeColor = (eventType: string) => {
    if (eventType.includes('CREATED') || eventType.includes('STARTED')) return 'bg-blue-100 text-blue-700'
    if (eventType.includes('PASSED') || eventType.includes('COMPLETED')) return 'bg-green-100 text-green-700'
    if (eventType.includes('APPROVED')) return 'bg-green-100 text-green-700'
    if (eventType.includes('DETECTED') || eventType.includes('WARNING')) return 'bg-amber-100 text-amber-700'
    if (eventType.includes('ABORTED') || eventType.includes('REJECTED') || eventType.includes('FAILED')) return 'bg-red-100 text-red-700'
    if (eventType.includes('POLICY')) return 'bg-purple-100 text-purple-700'
    if (eventType.includes('SAFETY')) return 'bg-indigo-100 text-indigo-700'
    return 'bg-gray-100 text-gray-700'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Table className="w-5 h-5" />
          Audit Log (Tabular)
          <Badge variant="outline" className="ml-2">
            {events.length} Events
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="text-left p-2 font-semibold text-gray-700">Seq</th>
                <th className="text-left p-2 font-semibold text-gray-700">Timestamp</th>
                <th className="text-left p-2 font-semibold text-gray-700">Event Type</th>
                <th className="text-left p-2 font-semibold text-gray-700">Actor</th>
                <th className="text-left p-2 font-semibold text-gray-700">Role</th>
                <th className="text-left p-2 font-semibold text-gray-700">Phase</th>
                <th className="text-left p-2 font-semibold text-gray-700">Payload Preview</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event, idx) => (
                <tr 
                  key={idx}
                  className="border-b hover:bg-gray-50 transition-colors"
                >
                  <td className="p-2">
                    <Badge variant="outline" className="font-mono text-xs">
                      {event.sequence}
                    </Badge>
                  </td>
                  
                  <td className="p-2 text-xs text-gray-600 font-mono">
                    {formatTimestamp(event.timestamp)}
                  </td>
                  
                  <td className="p-2">
                    <Badge className={`text-xs ${eventTypeColor(event.event_type)}`}>
                      {event.event_type}
                    </Badge>
                  </td>
                  
                  <td className="p-2">
                    <div className="flex items-center gap-1">
                      {event.actor_role === 'Human' && (
                        <User className="w-3 h-3 text-green-600" />
                      )}
                      <span className="text-xs font-mono text-gray-700">
                        {event.actor}
                      </span>
                    </div>
                  </td>
                  
                  <td className="p-2">
                    {event.actor_role === 'Human' ? (
                      <Badge className="bg-green-100 text-green-700 text-xs">
                        Human
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs">
                        {event.actor_role}
                      </Badge>
                    )}
                  </td>
                  
                  <td className="p-2 text-xs font-mono text-gray-600">
                    {event.phase || '-'}
                  </td>
                  
                  <td className="p-2">
                    <div className="text-xs font-mono text-gray-500 max-w-xs overflow-hidden">
                      {truncatePayload(event.payload)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Export Notice */}
        <div className="mt-4 text-xs text-gray-500 italic p-2 bg-gray-50 rounded">
          ℹ️ This audit log is exportable for compliance and regulatory review.
          Each row represents a cryptographically signed event in the immutable ledger.
        </div>
      </CardContent>
    </Card>
  )
}
