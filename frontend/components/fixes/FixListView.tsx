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
import StatusBadge from '@/components/ui/StatusBadge'
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
    { key: 'all', label: 'All', count: fixes.length, icon: null },
    { key: 'proposed', label: 'Proposed', count: statusCounts.proposed || 0, icon: Eye },
    { key: 'approved', label: 'Approved', count: statusCounts.approved || 0, icon: CheckCircle2 },
    { key: 'applied', label: 'Applied', count: statusCounts.applied || 0, icon: Sparkles },
    { key: 'rejected', label: 'Rejected', count: statusCounts.rejected || 0, icon: XCircle },
    { key: 'failed', label: 'Failed', count: statusCounts.failed || 0, icon: AlertCircle },
  ]

  return (
    <div className="space-y-2">
      {/* Status Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {statusFilters.map(({ key, label, count, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`
              px-2 py-1 rounded text-xs font-medium transition-colors
              flex items-center gap-1 border
              ${
                filter === key
                  ? 'bg-neutral-800 text-neutral-100 border-neutral-700'
                  : 'bg-neutral-900 text-neutral-400 border-neutral-800 hover:bg-neutral-850'
              }
            `}
          >
            {Icon && <Icon className="w-3 h-3" />}
            <span>{label}</span>
            <span className="ml-1 text-[10px] opacity-70">({count})</span>
          </button>
        ))}
      </div>
      
      {/* Fixes List */}
      {filteredFixes.length === 0 ? (
        <div className="text-center py-8 border border-dashed border-neutral-800 rounded-lg">
          <p className="text-neutral-500 text-xs">
            {filter === 'all' 
              ? 'No fixes generated yet' 
              : `No ${filter} fixes`
            }
          </p>
        </div>
      ) : (
        <div className="space-y-2">
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
