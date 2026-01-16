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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui'
import { Button, Badge } from '@/components/ui'
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
  
  // Status styling
  const statusConfig = {
    proposed: { color: 'bg-blue-100 text-blue-800 border-blue-200', icon: Eye, label: 'Proposed' },
    approved: { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle2, label: 'Approved' },
    rejected: { color: 'bg-red-100 text-red-800 border-red-200', icon: XCircle, label: 'Rejected' },
    applied: { color: 'bg-emerald-100 text-emerald-800 border-emerald-200', icon: Sparkles, label: 'Applied' },
    failed: { color: 'bg-orange-100 text-orange-800 border-orange-200', icon: AlertCircle, label: 'Failed' },
  }
  
  const statusInfo = statusConfig[fix.status] || statusConfig.proposed
  const StatusIcon = statusInfo.icon
  
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
    <Card className="border-2 hover:shadow-md transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <CardTitle className="text-lg">🤖 AI-Generated Fix #{fix.id}</CardTitle>
              <Badge className={`${statusInfo.color} flex items-center gap-1 px-2 py-0.5 font-medium border`}>
                <StatusIcon className="w-3 h-3" />
                {statusInfo.label}
              </Badge>
            </div>
            {fix.file_path && (
              <CardDescription className="font-mono text-xs">
                {fix.file_path}
              </CardDescription>
            )}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Issue Context */}
        {issue && (
          <div className="bg-gray-50 border border-gray-200 rounded-md p-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
              Fixes Issue
            </p>
            <p className="text-sm font-medium text-gray-900">{issue.name}</p>
            <p className="text-xs text-gray-600 mt-1">{issue.message}</p>
          </div>
        )}
        
        {/* Explanation */}
        {fix.explanation && (
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1.5">📝 Explanation:</p>
            <p className="text-sm text-gray-600 bg-white border border-gray-200 rounded-md p-3">
              {fix.explanation}
            </p>
          </div>
        )}
        
        {/* Code Preview */}
        <div>
          <p className="text-sm font-semibold text-gray-700 mb-1.5">💚 Fixed Code:</p>
          <div className="bg-gray-900 border border-gray-700 rounded-md p-3 overflow-x-auto max-h-64 overflow-y-auto">
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
              className="text-sm font-semibold text-blue-600 hover:text-blue-700 mb-1.5 flex items-center gap-1"
            >
              {showPatch ? '▼' : '▶'} View Patch
            </button>
            {showPatch && (
              <div className="bg-gray-900 border border-gray-700 rounded-md p-3 overflow-x-auto max-h-48 overflow-y-auto">
                <pre className="text-xs font-mono text-gray-300 whitespace-pre-wrap">
                  {fix.patch}
                </pre>
              </div>
            )}
          </div>
        )}
        
        {/* Governance Trail */}
        {(fix.approved_by || fix.rejected_by || fix.applied_by) && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-3 space-y-2">
            <p className="text-xs font-semibold text-blue-900 uppercase tracking-wide">
              🔒 Audit Trail
            </p>
            
            {fix.approved_by && (
              <div className="text-xs text-blue-800">
                <span className="font-medium">Approved by:</span> {fix.approved_by}
                {fix.approved_at && ` on ${new Date(fix.approved_at).toLocaleString()}`}
                {fix.approval_plan && (
                  <Badge className="ml-2 text-[10px] bg-blue-100 text-blue-700 border-blue-300">
                    {fix.approval_plan}
                  </Badge>
                )}
              </div>
            )}
            
            {fix.rejected_by && (
              <div className="text-xs text-red-800">
                <span className="font-medium">Rejected by:</span> {fix.rejected_by}
                {fix.rejected_at && ` on ${new Date(fix.rejected_at).toLocaleString()}`}
                {fix.rejection_reason && (
                  <p className="mt-1 italic text-red-700">"{fix.rejection_reason}"</p>
                )}
              </div>
            )}
            
            {fix.applied_by && (
              <div className="text-xs text-green-800">
                <span className="font-medium">Applied by:</span> {fix.applied_by}
                {fix.applied_at && ` on ${new Date(fix.applied_at).toLocaleString()}`}
                {fix.application_plan && (
                  <Badge className="ml-2 text-[10px] bg-green-100 text-green-700 border-green-300">
                    {fix.application_plan}
                  </Badge>
                )}
              </div>
            )}
          </div>
        )}
        
        {/* Error Display */}
        {fix.application_error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-xs font-semibold text-red-900 mb-1">⚠️ Application Failed</p>
            <p className="text-xs text-red-800 font-mono">{fix.application_error}</p>
          </div>
        )}
        
        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-200">
          {/* Proposed: Show Approve/Reject */}
          {fix.status === 'proposed' && (
            <>
              {canApprove ? (
                <>
                  <Button
                    onClick={handleApprove}
                    disabled={loading}
                    className="bg-green-600 hover:bg-green-700 text-white flex items-center gap-1.5"
                    size="sm"
                  >
                    <Check className="w-4 h-4" />
                    Approve Fix
                  </Button>
                  <Button
                    onClick={() => setShowRejectDialog(true)}
                    disabled={loading}
                    variant="outline"
                    className="border-red-300 text-red-700 hover:bg-red-50 flex items-center gap-1.5"
                    size="sm"
                  >
                    <X className="w-4 h-4" />
                    Reject
                  </Button>
                </>
              ) : (
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                  <Lock className="w-4 h-4" />
                  <span>
                    Upgrade to <span className="font-semibold text-purple-600">Advanced Engineer</span> to approve fixes
                  </span>
                </div>
              )}
            </>
          )}
          
          {/* Approved: Show Apply */}
          {fix.status === 'approved' && (
            <>
              {canApply ? (
                <>
                  <Button
                    onClick={() => handleApply(false)}
                    disabled={loading}
                    className="bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1.5"
                    size="sm"
                  >
                    <Play className="w-4 h-4" />
                    Apply Fix
                  </Button>
                  <Button
                    onClick={() => handleApply(true)}
                    disabled={loading}
                    variant="outline"
                    className="flex items-center gap-1.5"
                    size="sm"
                  >
                    <Eye className="w-4 h-4" />
                    Validate (Dry Run)
                  </Button>
                </>
              ) : (
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                  <Lock className="w-4 h-4" />
                  <span>
                    Upgrade to <span className="font-semibold text-purple-600">Advanced Engineer</span> to apply fixes
                  </span>
                </div>
              )}
            </>
          )}
          
          {/* Applied: Show Success */}
          {fix.status === 'applied' && (
            <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 border border-green-200 rounded px-3 py-2">
              <Sparkles className="w-4 h-4" />
              <span className="font-medium">Fix successfully applied to codebase</span>
            </div>
          )}
          
          {/* Rejected: Show Reason */}
          {fix.status === 'rejected' && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 w-full">
              <XCircle className="w-4 h-4" />
              <span className="font-medium">Fix rejected</span>
            </div>
          )}
        </div>
        
        {/* Reject Dialog */}
        {showRejectDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Reject Fix</h3>
              <p className="text-sm text-gray-600 mb-4">
                Please provide a reason for rejecting this fix (optional):
              </p>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g., Introduces breaking changes, incorrect fix logic..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm resize-none h-24 focus:outline-none focus:ring-2 focus:ring-red-500"
              />
              <div className="flex gap-2 mt-4">
                <Button
                  onClick={handleReject}
                  disabled={loading}
                  className="bg-red-600 hover:bg-red-700 text-white flex-1"
                >
                  Confirm Rejection
                </Button>
                <Button
                  onClick={() => {
                    setShowRejectDialog(false)
                    setRejectReason('')
                  }}
                  variant="outline"
                  disabled={loading}
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
