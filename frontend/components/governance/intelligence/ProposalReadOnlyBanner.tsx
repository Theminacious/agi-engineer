'use client'

import { Info } from 'lucide-react'

/**
 * Phase 11.4: Proposal Read-Only Banner
 * 
 * Static explanatory banner emphasizing immutability and replay capability.
 * Displayed above proposals to clarify their nature.
 */
export default function ProposalReadOnlyBanner() {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
      <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
      <div className="text-sm text-blue-900">
        <p>
          <strong>These are intelligence proposals.</strong> The analyzers have identified potential issues 
          and suggested strategies. No code has been modified. All data is immutable and replayable.
        </p>
        <p className="mt-2 text-xs text-blue-700">
          Each proposal includes a root cause hypothesis, affected files, suggested strategies, risks, 
          and prerequisites. Multiple analyzers may propose solutions for the same issue. This is normal.
        </p>
      </div>
    </div>
  )
}
