'use client'

/**
 * Phase 15.1: Fix List View
 * Phase 15.2: Batch Fix Operations (Enhanced)
 *
 * Displays list of fixes with status summary:
 * - Status counts (proposed/approved/applied/rejected/failed)
 * - Filter by status
 * - Checkbox selection for batch operations
 * - Batch action toolbar
 */

import { useState } from 'react'
import { FixApprovalCard } from './FixApprovalCard'
import { CheckCircle2, XCircle, Sparkles, AlertCircle } from 'lucide-react'

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
  onBatchApprove?: (fixIds: number[]) => void
  onBatchReject?: (fixIds: number[], reason?: string) => void
  onBatchApply?: (fixIds: number[]) => void
  onBatchPreview?: (fixIds: number[]) => void
}

export function FixListView({
  fixes,
  onApprove,
  onReject,
  onApply,
  onBatchApprove,
  onBatchReject,
  onBatchApply,
  onBatchPreview,
}: FixListViewProps) {
  const [filter, setFilter] = useState<string>('all')
  const [selectedFixIds, setSelectedFixIds] = useState<Set<number>>(new Set())

  const statusCounts = fixes.reduce(
    (acc, fix) => {
      acc[fix.status] = (acc[fix.status] || 0) + 1
      return acc
    },
    {
      proposed: 0,
      approved: 0,
      rejected: 0,
      applied: 0,
      failed: 0,
    } as Record<Fix['status'], number>,
  )

  const filteredFixes = filter === 'all' ? fixes : fixes.filter((fix) => fix.status === filter)
  const allSelected = filteredFixes.length > 0 && selectedFixIds.size === filteredFixes.length
  const someSelected = selectedFixIds.size > 0 && !allSelected

  const toggleFixSelection = (fixId: number) => {
    const nextSelection = new Set(selectedFixIds)
    if (nextSelection.has(fixId)) {
      nextSelection.delete(fixId)
    } else {
      nextSelection.add(fixId)
    }
    setSelectedFixIds(nextSelection)
  }

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedFixIds(new Set())
      return
    }

    setSelectedFixIds(new Set(filteredFixes.map((fix) => fix.id)))
  }

  const clearSelection = () => {
    setSelectedFixIds(new Set())
  }

  const statusFilters = [
    { key: 'all', label: 'All', count: fixes.length, icon: Sparkles },
    { key: 'proposed', label: 'Proposed', count: statusCounts.proposed, icon: Sparkles },
    { key: 'approved', label: 'Approved', count: statusCounts.approved, icon: CheckCircle2 },
    { key: 'applied', label: 'Applied', count: statusCounts.applied, icon: CheckCircle2 },
    { key: 'rejected', label: 'Rejected', count: statusCounts.rejected, icon: XCircle },
    { key: 'failed', label: 'Failed', count: statusCounts.failed, icon: AlertCircle },
  ]

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {statusFilters.map(({ key, label, count, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`
                flex items-center gap-1 rounded border px-2 py-1 text-xs font-medium transition-colors
                ${
                  filter === key
                    ? 'border-neutral-700 bg-neutral-800 text-neutral-100'
                    : 'border-neutral-800 bg-neutral-900 text-neutral-400 hover:bg-neutral-850'
                }
              `}
            >
              <Icon className="h-3 w-3" />
              <span>{label}</span>
              <span className="ml-1 text-[10px] opacity-70">({count})</span>
            </button>
          ))}
        </div>

        {filteredFixes.length > 0 && (
          <button
            onClick={toggleSelectAll}
            className="text-xs text-neutral-400 transition-colors hover:text-neutral-200"
          >
            {allSelected ? 'Deselect All' : someSelected ? 'Select All' : 'Select All'}
          </button>
        )}
      </div>

      {selectedFixIds.size > 0 && (
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 rounded border border-neutral-800 bg-neutral-900/95 p-2 backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs text-neutral-400">{selectedFixIds.size} selected</span>
            <button
              onClick={clearSelection}
              className="text-xs text-neutral-500 underline transition-colors hover:text-neutral-300"
            >
              Clear
            </button>
          </div>

          <div className="flex items-center gap-2">
            {onBatchPreview && (
              <button
                onClick={() => onBatchPreview(Array.from(selectedFixIds))}
                className="rounded border border-neutral-700 bg-neutral-800 px-3 py-1 text-xs text-neutral-200 transition-colors hover:bg-neutral-750"
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
                className="rounded border border-green-800 bg-green-900/30 px-3 py-1 text-xs text-green-300 transition-colors hover:bg-green-900/50"
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
                className="rounded border border-red-800 bg-red-900/30 px-3 py-1 text-xs text-red-300 transition-colors hover:bg-red-900/50"
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
                className="rounded border border-blue-800 bg-blue-900/30 px-3 py-1 text-xs text-blue-300 transition-colors hover:bg-blue-900/50"
              >
                Apply Selected
              </button>
            )}
          </div>
        </div>
      )}

      {filteredFixes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-800 py-8 text-center">
          <p className="text-xs text-neutral-500">
            {filter === 'all' ? 'No fixes generated yet' : `No ${filter} fixes`}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredFixes.map((fix) => (
            <div key={fix.id} className="flex items-start gap-2">
              <div className="pt-3">
                <input
                  type="checkbox"
                  checked={selectedFixIds.has(fix.id)}
                  onChange={() => toggleFixSelection(fix.id)}
                  className="h-4 w-4 cursor-pointer rounded border-neutral-700 bg-neutral-900 text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                />
              </div>

              <div className="flex-1">
                <FixApprovalCard
                  fix={fix}
                  onApprove={onApprove}
                  onReject={onReject}
                  onApply={onApply}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
