'use client'

/**
 * Phase 15.1: Fix List View
 * 
 * Displays list of fixes with status summary:
 * - Status counts (proposed/approved/applied/rejected)
 * - Filter by status
 * - Compact card view
 * - Quick actions
 */

import { useState } from 'react'
import { FixApprovalCard } from './FixApprovalCard'
import { Badge } from '@/components/ui'
import { Eye, CheckCircle2, XCircle, Sparkles, AlertCircle } from 'lucide-react'

interface Fix {
  id: number
  result_id: number
  file_path?: string
  original_code: string
  fixed_code: string
  explanation?: string
  patch?: string
  status: 'proposed' | 'approved' | 'rejected' | 'applied' | 'failed'
  
  approved_by?: string
  approved_at?: string
  rejected_by?: string
  rejected_at?: string
  applied_by?: string
  applied_at?: string
}

interface FixListViewProps {
  fixes: Fix[]
  onApprove?: (fixId: number) => void
  onReject?: (fixId: number, reason?: string) => void
  onApply?: (fixId: number, dryRun?: boolean) => void
}

export function FixListView({ fixes, onApprove, onReject, onApply }: FixListViewProps) {
  const [filter, setFilter] = useState<string>('all')
  
  // Count by status
  const statusCounts = fixes.reduce((acc, fix) => {
    acc[fix.status] = (acc[fix.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)
  
  // Filter fixes
  const filteredFixes = filter === 'all' 
    ? fixes 
    : fixes.filter(f => f.status === filter)
  
  // Status config
  const statusFilters = [
    { key: 'all', label: 'All', count: fixes.length, icon: null, color: 'bg-gray-100 text-gray-800' },
    { key: 'proposed', label: 'Proposed', count: statusCounts.proposed || 0, icon: Eye, color: 'bg-blue-100 text-blue-800' },
    { key: 'approved', label: 'Approved', count: statusCounts.approved || 0, icon: CheckCircle2, color: 'bg-green-100 text-green-800' },
    { key: 'applied', label: 'Applied', count: statusCounts.applied || 0, icon: Sparkles, color: 'bg-emerald-100 text-emerald-800' },
    { key: 'rejected', label: 'Rejected', count: statusCounts.rejected || 0, icon: XCircle, color: 'bg-red-100 text-red-800' },
    { key: 'failed', label: 'Failed', count: statusCounts.failed || 0, icon: AlertCircle, color: 'bg-orange-100 text-orange-800' },
  ]

  return (
    <div className="space-y-4">
      {/* Status Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {statusFilters.map(({ key, label, count, icon: Icon, color }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`
              px-3 py-1.5 rounded-md text-sm font-medium transition-colors
              flex items-center gap-1.5 border
              ${filter === key 
                ? `${color} border-current` 
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
              }
            `}
          >
            {Icon && <Icon className="w-3.5 h-3.5" />}
            <span>{label}</span>
            <Badge className="ml-1 text-xs bg-white/30 text-inherit border-white/20">
              {count}
            </Badge>
          </button>
        ))}
      </div>
      
      {/* Fixes List */}
      {filteredFixes.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
          <p className="text-gray-500 text-sm">
            {filter === 'all' 
              ? 'No fixes generated yet' 
              : `No ${filter} fixes`
            }
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFixes.map((fix) => (
            <FixApprovalCard
              key={fix.id}
              fix={fix}
              onApprove={onApprove}
              onReject={onReject}
              onApply={onApply}
            />
          ))}
        </div>
      )}
    </div>
  )
}
