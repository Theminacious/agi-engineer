'use client'

/**
 * Phase 15.2: Batch Risk Modal
 * 
 * Displays risk assessment before batch operations:
 * - Batch size
 * - Highest severity level
 * - Files impacted
 * - Conflict warnings (multiple fixes to same file)
 * - Recommended limits
 * 
 * Design: Neutral dialog with muted colors, clear risk indicators
 */

import { AlertTriangle, FileWarning, CheckCircle2, Info } from 'lucide-react'

interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
  fix_count: number
  files_affected: string[]
  conflicts: Array<{
    file_path: string
    fix_ids: number[]
  }>
  risk_level: 'low' | 'medium' | 'high'
  requires_review: boolean
}

interface BatchRiskModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  validation: ValidationResult
  actionType: 'approve' | 'reject' | 'apply'
}

export function BatchRiskModal({
  isOpen,
  onClose,
  onConfirm,
  validation,
  actionType
}: BatchRiskModalProps) {
  if (!isOpen) return null

  const actionLabels = {
    approve: { verb: 'Approve', color: 'green', icon: CheckCircle2 },
    reject: { verb: 'Reject', color: 'red', icon: AlertTriangle },
    apply: { verb: 'Apply', color: 'blue', icon: Info }
  }

  const { verb, color, icon: ActionIcon } = actionLabels[actionType]

  const riskConfig = {
    low: { label: 'Low Risk', color: 'text-green-400', bg: 'bg-green-900/20', border: 'border-green-800' },
    medium: { label: 'Medium Risk', color: 'text-yellow-400', bg: 'bg-yellow-900/20', border: 'border-yellow-800' },
    high: { label: 'High Risk', color: 'text-red-400', bg: 'bg-red-900/20', border: 'border-red-800' }
  }

  const risk = riskConfig[validation.risk_level]

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ActionIcon className={`w-5 h-5 text-${color}-400`} />
              <h2 className="text-lg font-medium text-neutral-100">
                {verb} {validation.fix_count} Fixes
              </h2>
            </div>
            <button
              onClick={onClose}
              className="text-neutral-500 hover:text-neutral-300 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4 overflow-y-auto flex-1">
          
          {/* Risk Level Badge */}
          <div className={`${risk.bg} ${risk.border} border rounded-lg p-3 flex items-center gap-2`}>
            <AlertTriangle className={`w-4 h-4 ${risk.color}`} />
            <div className="flex-1">
              <div className={`text-sm font-medium ${risk.color}`}>{risk.label}</div>
              <div className="text-xs text-neutral-400 mt-1">
                {validation.fix_count} fixes affecting {validation.files_affected.length} files
              </div>
            </div>
          </div>

          {/* Errors */}
          {validation.errors.length > 0 && (
            <div className="bg-red-900/20 border border-red-800 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <div className="text-sm font-medium text-red-400">Errors</div>
              </div>
              <ul className="space-y-1 ml-6">
                {validation.errors.map((error, idx) => (
                  <li key={idx} className="text-xs text-red-300">• {error}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {validation.warnings.length > 0 && (
            <div className="bg-yellow-900/20 border border-yellow-800 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <FileWarning className="w-4 h-4 text-yellow-400" />
                <div className="text-sm font-medium text-yellow-400">Warnings</div>
              </div>
              <ul className="space-y-1 ml-6">
                {validation.warnings.map((warning, idx) => (
                  <li key={idx} className="text-xs text-yellow-300">• {warning}</li>
                ))}
              </ul>
            </div>
          )}

          {/* File Conflicts */}
          {validation.conflicts.length > 0 && (
            <div className="bg-orange-900/20 border border-orange-800 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <FileWarning className="w-4 h-4 text-orange-400" />
                <div className="text-sm font-medium text-orange-400">
                  File Conflicts ({validation.conflicts.length})
                </div>
              </div>
              <div className="space-y-2 ml-1">
                {validation.conflicts.map((conflict, idx) => (
                  <div key={idx} className="text-xs">
                    <div className="text-neutral-300 font-mono">{conflict.file_path}</div>
                    <div className="text-neutral-500 ml-4">
                      {conflict.fix_ids.length} fixes modifying this file
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Files Affected */}
          <div className="border border-neutral-800 rounded-lg p-3">
            <div className="text-sm font-medium text-neutral-300 mb-2">
              Files Affected ({validation.files_affected.length})
            </div>
            <div className="max-h-40 overflow-y-auto">
              <div className="space-y-1">
                {validation.files_affected.map((file, idx) => (
                  <div key={idx} className="text-xs font-mono text-neutral-500">
                    {file}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Review Required Notice */}
          {validation.requires_review && (
            <div className="bg-blue-900/20 border border-blue-800 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <Info className="w-4 h-4 text-blue-400" />
                <div className="text-sm text-blue-300">
                  Manual review recommended for batch operations of this size
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-800 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm bg-neutral-800 hover:bg-neutral-750 text-neutral-300 rounded border border-neutral-700 transition-colors"
          >
            Cancel
          </button>
          
          <button
            onClick={() => {
              onConfirm()
              onClose()
            }}
            disabled={!validation.valid}
            className={`
              px-4 py-2 text-sm rounded border transition-colors
              ${validation.valid
                ? `bg-${color}-900/30 hover:bg-${color}-900/50 text-${color}-300 border-${color}-800`
                : 'bg-neutral-800 text-neutral-600 border-neutral-800 cursor-not-allowed'
              }
            `}
          >
            {verb} {validation.fix_count} Fixes
          </button>
        </div>

      </div>
    </div>
  )
}
