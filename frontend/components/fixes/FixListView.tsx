'use client'

/**
 * Phase 15.1: Fix List View
 * Phase 15.2: Batch Fix Operations (Enhanced)
 * 
 * Displays list of fixes with status summary:
 * - Status counts (proposed/approved/applied/rejected)
 * - Filter by status
 * - Compact card view
 * - Quick actions
 * - Checkbox selection for batch operations (Phase 15.2)
 * - Batch action toolbar (Phase 15.2)
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
  // Phase 15.2: Batch operations
  onBatchApprove?: (fixIds: number[]) => void
  onBatchReject?: (fixIds: number[], reason?: string) => void
  onBatchApply?: (fixIds: number[]) => void
  onBatchPreview?: (fixIds: number[]) => void
}

export function FixListView({ fixes, onApprove, onReject, onApply, onBatchApprove, onBatchReject, onBatchApply, onBatchPreview }: FixListViewProps) {
  const [filter, setFilter] = useState<string>('all')
  
  // Phase 15.2: Batch selection state
  const [selectedFixIds, setSelectedFixIds] = useState<Set<number>>(new Set())
  
  // Count by status
  const statusCounts = fixes.reduce((acc, fi
  
  // Phase 15.2: Selection handlers
  const toggleFixSelection = (fixId: number) => {
    const newSelection = new Set(selectedFixIds)
    if (newSelection.has(fixId)) {
      newSelection.delete(fixId)
    } else {
      newSelection.add(fixId)
    }
    setSelectedFixIds(newSelection)
  }
  
  const toggleSelectAll = () => {
    if (selectedFixIds.size === filteredFixes.length) {
      // Deselect all
      setSelectedFixIds(new Set())
    } else {
      // Select all visible
      setSelectedFixIds(new Set(filteredFixes.map(f => f.id)))
    }
  }
  
  const clearSelection = ()items-center justify-between gap-4">
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
        
        {/* Phase 15.2: Select All/None */}
        {filteredFixes.length > 0 && (
          <button
            onClick={toggleSelectAll}
            className="text-xs text-neutral-400 hover:text-neutral-200 transition-colors"
          >
            {allSelected ? 'Deselect All' : someSelected ? 'Select All' : 'Select All'}
          </button>
        : 'rejected', label: 'Rejected', count: statusCounts.rejected || 0, icon: XCircle },
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
          Phase 15.2: Batch Action Toolbar */}
      {selectedFixIds.size > 0 && (
        <div className="sticky top-0 z-10 bg-neutral-900/95 backdrop-blur-sm border border-neutral-800 rounded p-2 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400">
              {selectedFixIds.size} selected
            </span>
            <button
              onClick={clearSelection}
              className="text-xs text-neutral-500 hover:text-neutral-300 underline"
            >
              Clear
            </button>
          </div>
          
          <div className="flex items-center gap-2">
            {onBatchPreview && (
              <button
                onClick={() => onBatchPreview(Array.from(selectedFixIds))}
                className="px-3 py-1 text-xs bg-neutral-800 hover:bg-neutral-750 text-neutral-200 rounded border border-neutral-700 transition-colors"
              >
                Preview Patch
              </button>
            )}
            {onBatchApprove && (
              <button
                onClick={() => {
                  onBatchApprove(Array.from(selectedFixIds))
                  clearSelection()
                }}
                className="px-3 py-1 text-xs bg-green-900/30 hover:bg-green-900/50 text-green-300 rounded border border-green-800 transition-colors"
              >
                Approve Selected
              </button>
            )}
            {onBatchReject && (
              <button
                onClick={() => {
                  onBatchReject(Array.from(selectedFixIds))
                  clearSelection()
                }}
                className="px-3 py-1 text-xs bg-red-900/30 hover:bg-red-900/50 text-red-300 rounded border border-red-800 transition-colors"
              >
                Reject Selected
              </button>
            )}
            {onBatchApply && (
              <button
                onClick={() => {
                  onBatchApply(Array.from(selectedFixIds))
                  clearSelection()
                }}
                className="px-3 py-1 text-xs bg-blue-900/30 hover:bg-blue-900/50 text-blue-300 rounded border border-blue-800 transition-colors"
              >
                Apply Selected
              </button>
            )}
          </div>
        </div>
      )}
      
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
            <div key={fix.id} className="flex items-start gap-2">
              {/* Phase 15.2: Checkbox Selection */}
              <div className="pt-3">
                <input
                  type="checkbox"
                  checked={selectedFixIds.has(fix.id)}
                  onChange={() => toggleFixSelection(fix.id)}
                  className="w-4 h-4 rounded border-neutral-700 bg-neutral-900 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
                />
              </div>
              
              <div className="flex-1">
                <FixApprovalCard
                  key={fix.id}
                  fix={fix}
                  onApprove={onApprove}
                  onReject={onReject}
                  onApply={onApply}
                />
              </div>
            </div
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
