'use client'

/**
 * Phase 15.1: Governed Fix Approval Card
 * 
 * Displays AI-generated fix with approval/rejection workflow:
 * - Status badge (proposed/approved/rejected/applied/failed)
 * - Approve/Reject buttons (plan-gated)
 * - Apply fix button (for approved fixes)
 * - Patch preview
 * - Ledger trail integration
 * - Plan-based access control
 * 
 * Capabilities by plan:
 * - Core (developer): View-only
 * - Advanced (team): Approve, reject, apply
 * - Autonomous (enterprise): Approve, reject, apply, batch (future)
 */

import { useState } from 'react'
import { usePlanSelection } from '@/hooks/usePlanSelection'
import SectionCard from '@/components/ui/SectionCard'
import AuditPanel from '@/components/ui/AuditPanel'
import StatusBadge from '@/components/ui/StatusBadge'
import { Button } from '@/components/ui'
import { Check, X, Play, Eye, Lock, AlertCircle, CheckCircle2, XCircle, Sparkles } from 'lucide-react'

interface Fix {
  id: number
  result_id: number
  file_path?: string
  original_code: string
  fixed_code: string
  explanation?: string
  patch?: string
  status: 'proposed' | 'approved' | 'rejected' | 'applied' | 'failed'
  
  // Governance
  approved_by?: string
  approved_at?: string
  approval_plan?: string
  
  applied_by?: string
  applied_at?: string
  application_plan?: string
  
  rejected_by?: string
  rejected_at?: string
  rejection_reason?: string
  
  // Ledger
  ledger_run_id?: string
  approval_ledger_event_id?: string
  application_ledger_event_id?: string
  
  application_error?: string
}

interface FixApprovalCardProps {
  fix: Fix
  onApprove?: (fixId: number) => void
  onReject?: (fixId: number, reason?: string) => void
  onApply?: (fixId: number, dryRun?: boolean) => void
  issue?: {
    rule_id: string
    name: string
    message: string
    severity: string
  }
}

export function FixApprovalCard({ fix, onApprove, onReject, onApply, issue }: FixApprovalCardProps) {
  const { plan } = usePlanSelection()
  const [loading, setLoading] = useState(false)
  const [showPatch, setShowPatch] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  
  // Plan capabilities
  const canApprove = plan !== 'developer' // Advanced+ can approve
  const canApply = plan !== 'developer'   // Advanced+ can apply
  
  // Status badge will be rendered using StatusBadge component
  
  // Handlers
  const handleApprove = async () => {
    if (!canApprove) return
    setLoading(true)
    try {
      if (onApprove) {
        await onApprove(fix.id)
      } else {
        // Default API call
        const response = await fetch(`/api/fixes/${fix.id}/approve`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
          },
          body: JSON.stringify({
            plan_tier: plan,
            approved_by: 'user@example.com', // TODO: Get from auth context
          }),
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to approve fix')
        }
        
        // Reload or update UI
        window.location.reload()
      }
    } catch (error) {
      console.error('Error approving fix:', error)
      alert(`Failed to approve fix: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setLoading(false)
    }
  }
  
  const handleReject = async () => {
    if (!canApprove) return
    setLoading(true)
    try {
      if (onReject) {
        await onReject(fix.id, rejectReason)
      } else {
        const response = await fetch(`/api/fixes/${fix.id}/reject`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
          },
          body: JSON.stringify({
            plan_tier: plan,
            rejected_by: 'user@example.com',
            reason: rejectReason || 'No reason provided',
          }),
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to reject fix')
        }
        
        window.location.reload()
      }
    } catch (error) {
      console.error('Error rejecting fix:', error)
      alert(`Failed to reject fix: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setLoading(false)
      setShowRejectDialog(false)
      setRejectReason('')
    }
  }
  
  const handleApply = async (dryRun: boolean = false) => {
    if (!canApply) return
    setLoading(true)
    try {
      if (onApply) {
        await onApply(fix.id, dryRun)
      } else {
        const response = await fetch(`/api/fixes/${fix.id}/apply-governed`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('jwt_token')}`,
          },
          body: JSON.stringify({
            plan_tier: plan,
            applied_by: 'user@example.com',
            dry_run: dryRun,
          }),
        })
        
        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to apply fix')
        }
        
        const result = await response.json()
        
        if (dryRun) {
          alert(`Validation successful! Patch preview:\n\n${result.patch}`)
        } else {
          alert(`Fix applied successfully to ${fix.file_path}`)
          window.location.reload()
        }
      }
    } catch (error) {
      console.error('Error applying fix:', error)
      alert(`Failed to apply fix: ${error instanceof Error ? error.message : String(error)}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <SectionCard>
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-neutral-300">🤖 Fix #{fix.id}</span>
            <StatusBadge status={fix.status} />
          </div>
          {fix.file_path && (
            <div className="font-mono text-xs text-neutral-500 mt-1">
              {fix.file_path}
            </div>
          )}
        </div>
      </div>
      
      <div className="space-y-2">
        {/* Issue Context */}
        {issue && (
          <AuditPanel>
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1">
              Fixes Issue
            </div>
            <div className="text-sm text-neutral-300">{issue.name}</div>
            <div className="text-xs text-neutral-500 mt-1">{issue.message}</div>
          </AuditPanel>
        )}
        
        {/* Explanation */}
        {fix.explanation && (
          <div>
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1">📝 Explanation</div>
            <div className="text-sm text-neutral-300 border border-neutral-800 rounded bg-neutral-900/80 p-2">
              {fix.explanation}
            </div>
          </div>
        )}
        
        {/* Code Preview */}
        <div>
          <div className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1">💚 Fixed Code</div>
          <div className="bg-neutral-950 border border-neutral-800 rounded p-2 overflow-x-auto max-h-64 overflow-y-auto">
            <pre className="text-xs font-mono text-green-400 whitespace-pre-wrap">
              {fix.fixed_code}
            </pre>
          </div>
        </div>
        
        {/* Patch Preview (Collapsible) */}
        {fix.patch && (
          <div>
            <button
              onClick={() => setShowPatch(!showPatch)}
              className="text-xs text-blue-400 hover:text-blue-300 mb-1 flex items-center gap-1"
            >
              {showPatch ? '▼' : '▶'} View Patch
            </button>
            {showPatch && (
              <div className="bg-neutral-950 border border-neutral-800 rounded p-2 overflow-x-auto max-h-48 overflow-y-auto">
                <pre className="text-xs font-mono text-neutral-400 whitespace-pre-wrap">
                  {fix.patch}
                </pre>
              </div>
            )}
          </div>
        )}
        
        {/* Governance Trail */}
        {(fix.approved_by || fix.rejected_by || fix.applied_by) && (
          <AuditPanel>
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-400 mb-1">
              🔒 Audit Trail
            </div>
            
            {fix.approved_by && (
              <div className="text-xs text-neutral-400">
                <span className="font-medium">Approved by:</span> {fix.approved_by}
                {fix.approved_at && ` on ${new Date(fix.approved_at).toLocaleString()}`}
                {fix.approval_plan && (
                  <span className="ml-2 text-[10px] text-green-400">({fix.approval_plan})</span>
                )}
              </div>
            )}
            
            {fix.rejected_by && (
              <div className="text-xs text-neutral-400">
                <span className="font-medium">Rejected by:</span> {fix.rejected_by}
                {fix.rejected_at && ` on ${new Date(fix.rejected_at).toLocaleString()}`}
                {fix.rejection_reason && (
                  <div className="mt-1 italic text-neutral-500">&ldquo;{fix.rejection_reason}&rdquo;</div>
                )}
              </div>
            )}
            
            {fix.applied_by && (
              <div className="text-xs text-neutral-400">
                <span className="font-medium">Applied by:</span> {fix.applied_by}
                {fix.applied_at && ` on ${new Date(fix.applied_at).toLocaleString()}`}
                {fix.application_plan && (
                  <span className="ml-2 text-[10px] text-emerald-400">({fix.application_plan})</span>
                )}
              </div>
            )}
          </AuditPanel>
        )}
        
        {/* Error Display */}
        {fix.application_error && (
          <AuditPanel className="border-red-700">
            <div className="text-xs font-medium text-red-400 mb-1">⚠️ Application Failed</div>
            <div className="text-xs text-red-500 font-mono">{fix.application_error}</div>
          </AuditPanel>
        )}
        
        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-neutral-800">
          {/* Proposed: Show Approve/Reject */}
          {fix.status === 'proposed' && (
            <>
              {canApprove ? (
                <>
                  <button
                    onClick={handleApprove}
                    disabled={loading}
                    className="px-2 py-1 bg-green-700 hover:bg-green-600 text-neutral-100 rounded text-xs flex items-center gap-1 disabled:opacity-50"
                  >
                    <Check className="w-3 h-3" />
                    Approve
                  </button>
                  <button
                    onClick={() => setShowRejectDialog(true)}
                    disabled={loading}
                    className="px-2 py-1 border border-red-700 text-red-400 hover:bg-red-900/20 rounded text-xs flex items-center gap-1 disabled:opacity-50"
                  >
                    <X className="w-3 h-3" />
                    Reject
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <Lock className="w-3 h-3" />
                  <span>Advanced plan required</span>
                </div>
              )}
            </>
          )}
          
          {/* Approved: Show Apply */}
          {fix.status === 'approved' && (
            <>
              {canApply ? (
                <>
                  <button
                    onClick={() => handleApply(false)}
                    disabled={loading}
                    className="px-2 py-1 bg-blue-700 hover:bg-blue-600 text-neutral-100 rounded text-xs flex items-center gap-1 disabled:opacity-50"
                  >
                    <Play className="w-3 h-3" />
                    Apply
                  </button>
                  <button
                    onClick={() => handleApply(true)}
                    disabled={loading}
                    className="px-2 py-1 border border-neutral-700 text-neutral-400 hover:bg-neutral-800 rounded text-xs flex items-center gap-1 disabled:opacity-50"
                  >
                    <Eye className="w-3 h-3" />
                    Validate
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-2 text-xs text-neutral-500">
                  <Lock className="w-3 h-3" />
                  <span>Advanced plan required</span>
                </div>
              )}
            </>
          )}
          
          {/* Applied: Show Success */}
          {fix.status === 'applied' && (
            <div className="flex items-center gap-1 text-xs text-emerald-400">
              <Sparkles className="w-3 h-3" />
              <span>Applied to codebase</span>
            </div>
          )}
          
          {/* Rejected: Show Reason */}
          {fix.status === 'rejected' && (
            <div className="flex items-center gap-1 text-xs text-red-400">
              <XCircle className="w-3 h-3" />
              <span>Rejected</span>
            </div>
          )}
        </div>
        
        {/* Reject Dialog */}
        {showRejectDialog && (
          <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-4 max-w-md w-full mx-4">
              <h3 className="text-sm font-medium text-neutral-100 mb-2">Reject Fix</h3>
              <p className="text-xs text-neutral-400 mb-2">
                Provide a reason for rejecting this fix (optional):
              </p>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., Introduces breaking changes, incorrect fix logic..."
                className="w-full px-2 py-2 bg-neutral-950 border border-neutral-800 rounded text-xs text-neutral-300 resize-none h-20 focus:outline-none focus:border-red-700"
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={handleReject}
                  disabled={loading}
                  className="flex-1 px-2 py-1 bg-red-700 hover:bg-red-600 text-neutral-100 rounded text-xs disabled:opacity-50"
                >
                  Confirm Rejection
                </button>
                <button
                  onClick={() => {
                    setShowRejectDialog(false)
                    setRejectReason('')
                  }}
                  disabled={loading}
                  className="flex-1 px-2 py-1 border border-neutral-700 text-neutral-400 hover:bg-neutral-800 rounded text-xs disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  )
}
