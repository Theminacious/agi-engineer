'use client'

import { ShieldCheck, Lock, Eye } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

/**
 * Governance Section Introduction
 * 
 * Phase 14.1: Harmonized with dashboard styling
 * Explains the read-only nature and purpose of this UI
 */
export default function GovernanceIntro() {
  return (
    <div className="space-y-6">
      {/* Read-Only Banner */}
      <Card className="border-l-4 border-l-blue-500 bg-blue-50 border-blue-200">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Lock className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-lg text-blue-900">Read-Only Proof & Governance</CardTitle>
              <CardDescription className="text-sm text-blue-700">
                This section is immutable and exists to prove what happened
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-start gap-3">
            <Badge variant="outline" className="bg-white text-blue-600 border-blue-300 text-xs font-medium">
              <Eye className="w-3 h-3 mr-1" />
              VIEW ONLY
            </Badge>
            <p className="text-sm text-blue-800">
              This page cannot mutate state, trigger execution, or approve plans.
              It only displays frozen audit trails from completed runs.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Explanation Cards */}
      <div className="grid md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-green-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-green-600" />
              Why This Exists
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>
              This UI demonstrates <strong>proof over trust</strong>.
            </p>
            <p>
              You can verify runs without trusting AI, by inspecting
              the immutable ledger and deterministic replay.
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-amber-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Lock className="w-4 h-4 text-amber-600" />
              Ledger {'>'} Logs
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>
              The ledger is the <strong>source of truth</strong>.
            </p>
            <p>
              Events are append-only, sequence-ordered, and immutable.
              If it's not in the ledger, it didn't happen.
            </p>
          </CardContent>
        </Card>

        <Card className="border-l-4 border-l-purple-500">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Eye className="w-4 h-4 text-purple-600" />
              Replay {'>'} Monitoring
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-gray-600 space-y-2">
            <p>
              Deterministic replay reconstructs state from events.
            </p>
            <p>
              This proves causality: approvals preceded fixes,
              safety checks passed, and terminal states sealed correctly.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* What You Can Do */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">What You Can Do Here</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-gray-700">
            <li className="flex items-start gap-2">
              <span className="text-green-600 mt-0.5">✓</span>
              <span>View completed run timelines (sequence-ordered events)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 mt-0.5">✓</span>
              <span>Inspect replay summaries (deterministic state reconstruction)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 mt-0.5">✓</span>
              <span>Verify invariants (sequence gaps, missing approvals, terminal mismatches)</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 mt-0.5">✓</span>
              <span>Export audit tables for compliance teams</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-600 mt-0.5">✓</span>
              <span>Demo the system to investors, regulators, and skeptical engineers</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* What You CANNOT Do */}
      <Card className="border-red-200 bg-red-50">
        <CardHeader>
          <CardTitle className="text-base text-red-900">What You CANNOT Do Here</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-red-800">
            <li className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">✗</span>
              <span>Trigger new runs or execute fixes</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">✗</span>
              <span>Approve plans or override policies</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">✗</span>
              <span>Modify ledger events or replay results</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">✗</span>
              <span>Create PRs or schedule runs</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-red-600 mt-0.5">✗</span>
              <span>Edit policies or change configuration</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  )
}
