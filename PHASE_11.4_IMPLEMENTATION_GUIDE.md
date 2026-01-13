# Phase 11.4 Implementation Guide

## Quick Reference

### What Was Done

✅ **4 New React Components Created**
- IntelligenceOverviewPanel.tsx - Aggregate statistics
- IntelligenceProposalCard.tsx - Individual proposal display
- IntelligenceProposalList.tsx - List with ledger ordering
- ProposalReadOnlyBanner.tsx - Static banner

✅ **1 File Modified**
- frontend/app/governance/[run_id]/page.tsx - Added integration

✅ **0 Backend Changes**
- No API modifications
- No database changes
- No intelligence logic changes

---

## Component Overview

### IntelligenceOverviewPanel
```tsx
<IntelligenceOverviewPanel proposals={proposals} />
```
**Shows**: Total count, severity breakdown, average confidence  
**Use**: Summary view of all proposals  
**Lines**: 181

### IntelligenceProposalCard
```tsx
<IntelligenceProposalCard proposal={proposal} sequenceNumber={1} />
```
**Shows**: Full proposal details with expandable strategies  
**Use**: Individual proposal in a list  
**Lines**: 287

### IntelligenceProposalList
```tsx
<IntelligenceProposalList proposals={proposals} />
```
**Shows**: All proposals grouped by severity, in ledger order  
**Use**: Complete proposal list for a run  
**Lines**: 117

### ProposalReadOnlyBanner
```tsx
<ProposalReadOnlyBanner />
```
**Shows**: Explanatory banner about immutability  
**Use**: Top of proposal list or sections  
**Lines**: 20

---

## Integration Pattern

### In Governance Page

```tsx
import IntelligenceProposalList from '@/components/governance/intelligence/IntelligenceProposalList'

// Extract proposals from ledger events
const intelligenceProposals = events
  .filter(event => event.event_type === 'INTELLIGENCE_PROPOSAL')
  .map(event => event.payload)
  .filter((payload): payload is Record<string, any> => Boolean(payload))

// Render conditional section
{intelligenceProposals.length > 0 && (
  <Card className="border-purple-200 bg-purple-50">
    <CardContent className="p-6">
      <IntelligenceProposalList proposals={intelligenceProposals as any} />
    </CardContent>
  </Card>
)}
```

---

## Data Structure

### Intelligence Proposal (from Ledger)

```typescript
interface IntelligenceProposal {
  proposal_id: string
  analyzer_name: string
  bug_class: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  confidence: number  // 0.0 to 1.0
  problem_statement: string
  root_cause_hypothesis: string
  risk_explanation: string
  affected_files: Array<{
    path: string
    line_range?: string
    severity?: string
  }>
  suggested_strategies: Array<{
    id: string
    name?: string
    description: string
    effort_estimate?: string
    prerequisites: string[]
    assumptions: string[]
    risks: string[]
  }>
  prerequisite_actions?: string[]
  conflicting_analysis_ids?: string[]
}
```

---

## Key Design Decisions

### 1. Ledger Sequence Order (NOT Ranked)
- Proposals are displayed in exact ledger order
- Visual grouping by severity is for UX readability only
- Reordering would contradict immutability principle
- Order may indicate analyzer execution sequence

### 2. Collapsible Strategies
- Reduces cognitive load (overview first, details on demand)
- Mobile-friendly (prevents excessive scrolling)
- Users can explore specific strategy details

### 3. Confidence Warnings
- Confidence < 0.6 shows orange warning
- Helps users identify proposals needing verification
- Emphasizes uncertainty in analysis

### 4. Conflict Indicators
- Yellow alert if proposal conflicts with other analyzers
- Multiple analyzers may propose solutions for same issue
- Users can see competing proposals at a glance

### 5. Immutable Banners
- Every section emphasizes "immutable and replayable"
- "No code has been modified" reinforces trust
- Multiple notices ensure users understand intent

---

## Styling & Colors

### Severity Colors
```
CRITICAL = red-100 text-red-700
HIGH     = orange-100 text-orange-700  
MEDIUM   = yellow-100 text-yellow-700
LOW      = blue-100 text-blue-700
```

### Component Background Colors
```
Intelligence Section = purple-50 (distinguishes from other run elements)
Assumptions         = blue-50 (informational)
Risks              = orange-50 (warning)
General Cards      = white (default)
```

### Icons Used
```
Brain              = Intelligence context
AlertTriangle      = Warnings/Low confidence
ChevronUp/Down     = Expandable sections
Info              = Informational banners
Lock               = Read-only notices
```

---

## Read-Only Constraints Enforced

### What's NOT in Components
- ❌ No action buttons (Apply, Approve, Execute, Dismiss)
- ❌ No edit capabilities
- ❌ No delete capabilities
- ❌ No export/download (immutable data)
- ❌ No commenting/feedback
- ❌ No custom ranking/scoring
- ❌ No filtering/hiding
- ❌ No state mutations to proposals

### What IS in Components
- ✅ Full proposal visibility
- ✅ Expandable details (UI state only)
- ✅ Immutability notices
- ✅ Conflict indicators
- ✅ Confidence warnings
- ✅ Affected files display
- ✅ Strategy details
- ✅ Ledger sequence preservation

---

## Testing Checklist

- [ ] Navigate to /governance/run-2026-01-12-sample
- [ ] If proposals exist, see purple "Intelligence Proposals" card
- [ ] See proposal count in badge
- [ ] See "These are intelligence proposals..." banner
- [ ] See proposals grouped by severity
- [ ] Click strategy to expand details
- [ ] See confidence warnings if < 0.6
- [ ] See conflict indicator if conflicting_analysis_ids present
- [ ] See immutable notice at bottom of each proposal
- [ ] No action buttons visible
- [ ] No form inputs visible
- [ ] All text is read-only

---

## TypeScript Types

All components are fully typed:

```tsx
// IntelligenceProposalListProps
interface IntelligenceProposalListProps {
  proposals: IntelligenceProposal[]
}

// IntelligenceProposalCardProps
interface IntelligenceProposalCardProps {
  proposal: IntelligenceProposal
  sequenceNumber: number
}

// IntelligenceOverviewPanelProps (from component)
interface IntelligenceOverviewPanelProps {
  proposals: IntelligenceProposal[]
}
```

---

## Dependencies

### Imports Used
```tsx
// React
'use client'
import { useState, useMemo } from 'react'

// Next.js - None (no routing in components)

// UI Components (shadcn/ui)
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

// Icons
import { 
  ChevronDown, ChevronUp, AlertCircle, Info, Brain 
} from 'lucide-react'

// Styling
// Tailwind CSS (built-in)
```

---

## File Locations

```
frontend/
├── components/governance/intelligence/
│   ├── IntelligenceOverviewPanel.tsx
│   ├── IntelligenceProposalCard.tsx
│   ├── IntelligenceProposalList.tsx
│   └── ProposalReadOnlyBanner.tsx
├── app/governance/
│   └── [run_id]/
│       └── page.tsx (MODIFIED)
└── lib/
    └── ledgerReader.ts (unchanged - only used for reads)
```

---

## Deployment Notes

### Prerequisites
- Next.js 14+
- React 18+
- TypeScript 5+
- shadcn/ui components available
- lucide-react icons available

### No Configuration Changes Needed
- No environment variables
- No new API routes
- No database migrations
- No dependency installations (uses existing packages)

### Backward Compatibility
- ✅ Existing governance UI completely untouched
- ✅ New section only appears if proposals exist
- ✅ No changes to existing tabs/sections
- ✅ Old runs without proposals show no change

---

## Common Questions

### Q: Can users approve proposals?
A: No. The section is purely read-only. No action buttons are provided.

### Q: Can proposals be modified?
A: No. All data comes directly from immutable ledger. No mutations possible.

### Q: Are proposals in any particular order?
A: Yes. Proposals are in **ledger sequence order** (not ranked by severity/confidence). This preserves the exact analysis execution order.

### Q: What if there are no proposals?
A: The entire Intelligence section is hidden (conditional rendering). Users see the normal governance UI.

### Q: Can proposals be exported?
A: No. Phase 11.4 is read-only only. Export capabilities are proposed for future phases.

### Q: How is confidence displayed?
A: As a percentage with color coding:
- >= 0.8 = Green (confident)
- >= 0.6 = Yellow (moderate)
- < 0.6 = Orange warning (low confidence)

### Q: What are conflicts?
A: When multiple analyzers detect the same issue, they may propose different solutions. Conflicts are indicated in yellow alerts.

---

## Integration Checklist

- [ ] Copy 4 component files to frontend/components/governance/intelligence/
- [ ] Update frontend/app/governance/[run_id]/page.tsx with integration code
- [ ] Verify imports are correct
- [ ] Run `npm run build` to check for TypeScript errors
- [ ] Test in browser at /governance/run-2026-01-12-sample
- [ ] Verify proposals display correctly
- [ ] Verify no action buttons appear
- [ ] Verify collapsible strategies work
- [ ] Verify immutable notices display
- [ ] Test with run that has no proposals (section should be hidden)

---

## Phase 11.4 Completion

✅ All 4 components created  
✅ Integration added to governance page  
✅ 0 TypeScript errors  
✅ 0 breaking changes  
✅ All constraints verified  
✅ Read-only enforced  
✅ Immutability preserved  
✅ Documentation complete  

Ready for deployment.
