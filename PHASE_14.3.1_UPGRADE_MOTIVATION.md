# Phase 14.3.1: Upgrade Motivation & Friction Layer

**Status:** ✅ COMPLETE  
**Date:** January 16, 2026  
**Objective:** Increase plan conversion with contextual upgrade prompts based on skipped intelligence

---

## 🎯 Phase Objective

Add contextual upgrade motivation at key friction points where users encounter plan limitations. Show users what intelligence they're missing without being pushy or using dark patterns.

### Design Philosophy: Honest, Transparent, Compelling

The upgrade prompts should:
- **Use real data:** Show actual skipped analyzers, not fake scarcity
- **Be contextual:** Appear when limitations are experienced, not randomly
- **Emphasize benefits:** "What you'll gain" not "what you're missing"
- **Maintain trust:** Explain immutable governance (past runs unchanged)
- **Recommend intelligently:** Highlight Advanced Engineer as sweet spot

---

## ✅ Implementation Summary

### 1. UpgradePrompt Component ✅

**File:** `frontend/components/subscription/UpgradePrompt.tsx` (NEW)

A reusable upgrade prompt component that shows contextual motivation when capabilities are unavailable.

#### Key Features

**Contextual Intelligence Display:**
- Shows actual skipped analyzers grouped by category
- Uses experience-based descriptions (not technical names)
- Example: "Architecture Intelligence Unavailable"
  - "Traces multi-hop dependencies across your system"
  - "Identifies domain boundary violations before they cause problems"

**Advanced Engineer Highlights:**
- Focuses on team plan as recommended upgrade path
- Shows 5 key benefits:
  1. Deep multi-hop architecture analysis
  2. N+1 query detection
  3. Advanced concurrency intelligence
  4. 1,000 runs/month (10x capacity)
  5. Team collaboration (up to 10 users)

**Trust & Transparency Copy:**
- Immutable governance badge
- "Past runs remain unchanged in the ledger"
- "Upgrades only affect future analyses"

**Clear CTA:**
- "Compare Plans" button linking to `/plans`
- Demo environment notice (no billing required)

#### Props Interface
```typescript
interface UpgradePromptProps {
  currentPlan: PlanType           // User's current plan tier
  skippedAnalyzers: string[]      // IDs of unavailable analyzers
  className?: string              // Optional styling
}
```

#### Visual Design
- Purple gradient card with purple-200 border
- Sparkles icon (intelligence theme)
- Badge showing count: "3 Capabilities Unavailable"
- Grouped capabilities with AlertTriangle icons
- Benefit list with CheckCircle2 icons
- Blue trust indicator with Shield icon

### 2. ExecutionCoverage Integration ✅

**File:** `frontend/components/runs/ExecutionCoverage.tsx` (MODIFIED)

Updated execution coverage panel to Phase 14.3.1 with:

#### Changes Made

**Header Updates:**
- Phase 14.1 → Phase 14.3.1 documentation
- "Service Execution Transparency" → "Intelligence Execution Report"
- "Plan: Developer" → "Experience: Core Engineer"

**Terminology:**
- "Services Executed" → "Capabilities Executed"
- "Premium Locked" → "Advanced Unavailable"
- "Executed Services" → "Active Capabilities"
- "Premium Services Locked" → "Advanced Capabilities Unavailable"

**Upgrade Prompt Integration:**
```tsx
{/* Upgrade prompt if capabilities were skipped */}
{planLocked.length > 0 && plan && (
  <div className="mb-4">
    <UpgradePrompt 
      currentPlan={plan}
      skippedAnalyzers={planLocked.map(a => a.id)}
    />
  </div>
)}
```

**Benefit-Focused Messaging:**
- Before: "This service requires Team plan to unlock..."
- After: "Unlock with Advanced Engineer: Get deeper {category} insights that catch issues before they impact your team."

### 3. PlanContextBlock Integration ✅

**File:** `frontend/components/governance/PlanContextBlock.tsx` (MODIFIED)

Updated governance plan context to Phase 14.3.1 with:

#### Changes Made

**Header Updates:**
- Phase 14.1 → Phase 14.3.1 documentation
- "Plan Context" → "Intelligence Experience Context"
- "Subscription Plan" → "Intelligence Experience"

**Terminology:**
- "Services Enabled" → "Capabilities Enabled"
- "Premium Locked" → "Advanced Unavailable"
- "Enabled Services" → "Active Capabilities"

**Upgrade Prompt Integration:**
```tsx
{/* Upgrade prompt if capabilities are locked */}
{lockedCount > 0 && plan && (
  <div className="mb-4">
    <UpgradePrompt 
      currentPlan={plan}
      skippedAnalyzers={lockedAnalyzers}
    />
  </div>
)}
```

**Experience Language:**
- Uses `planExperienceMap` to translate technical names
- "Your Core Engineer experience includes..."
- "Your AGI's capabilities are determined by your intelligence experience..."

### 4. Run Detail Page Updates ✅

**File:** `frontend/app/runs/[id]/page.tsx` (MODIFIED)

Updated run detail page to show realistic demo data:

```tsx
<ExecutionCoverage 
  plan="developer"
  executedAnalyzers={[
    'architectural',
    'abstraction',
    'api_contracts',
    'god_objects',
    'performance',
    'concurrency',
    'security',
    'test_coverage',
    'broken_invariants',
    'configuration',
    'dependencies'
  ]}
  skippedAnalyzers={[]}
/>
```

This simulates a developer plan run that executed 11 capabilities and has 3 advanced capabilities locked (enhanced_architectural, enhanced_performance, enhanced_concurrency).

---

## 📊 Upgrade Friction Points

### Where Upgrade Prompts Appear

1. **Run Detail Page** (`/runs/[id]`)
   - After viewing execution results
   - When locked capabilities are present
   - Context: User just experienced limitation

2. **Governance Page** (`/governance/[run_id]`)
   - When viewing plan context in ledger
   - Explains unavailable intelligence at governance level
   - Context: User is auditing what ran

### Why These Locations?

**Post-Run = High Intent:**
- User just completed an analysis
- Limitation was actively experienced
- Clear understanding of what was missed
- High motivation to unlock more intelligence

**Governance = Trust Building:**
- User is verifying immutability
- Shows transparency about limitations
- Reinforces trust before suggesting upgrade
- Context-aware (knows what was unavailable)

---

## 🎨 User Experience Flow

### Scenario: Developer Plan User Viewing Run Results

1. **User navigates to run detail page** (`/runs/123`)

2. **Sees execution summary:**
   - "11 Capabilities Executed" (green)
   - "3 Advanced Unavailable" (amber)
   - "0 Skipped" (blue)

3. **Upgrade prompt appears at top:**
   ```
   🌟 Unlock Deeper Intelligence
   [3 Capabilities Unavailable]
   
   Your Core Engineer plan skipped 3 advanced capabilities during this run.
   Upgrade to Advanced Engineer to catch issues before they impact your team.
   
   📦 Architecture Intelligence Unavailable
   • Traces multi-hop dependencies across your system
   • Identifies domain boundary violations before they cause problems
   
   ⚡ Performance Intelligence Unavailable
   • Catches N+1 database queries before they impact users
   • Identifies blocking I/O operations
   
   🔄 Concurrency Intelligence Unavailable
   • Analyzes shared state patterns
   • Verifies thread-safety
   
   What You Get with Advanced Engineer:
   ✓ Deep multi-hop architecture analysis
   ✓ N+1 query detection
   ✓ Advanced concurrency intelligence
   ✓ 1,000 runs/month (10x capacity)
   ✓ Team collaboration (up to 10 users)
   
   🛡️ Immutable Governance: Past runs remain unchanged in the ledger.
   Upgrades only affect future analyses.
   
   [Compare Plans →]  ℹ️ Demo environment - no billing required
   ```

4. **Scrolls down to detailed execution coverage:**
   - Lists all 11 active capabilities
   - Shows 3 unavailable capabilities with upgrade messaging
   - Each locked capability explains benefit of unlocking

5. **Clicks "Compare Plans":**
   - Navigates to `/plans` page
   - Sees full Netflix-style plan comparison
   - Can make informed upgrade decision

### Scenario: Governance Audit

1. **User navigates to governance page** (`/governance/456`)

2. **Upgrade prompt appears before plan context:**
   - Same format as run detail page
   - Contextual to the specific run's limitations

3. **Plan context shows:**
   - "Intelligence Experience: Core Engineer"
   - "11 Capabilities Enabled"
   - "3 Advanced Unavailable"

4. **User understands:**
   - Exactly what ran (immutable ledger)
   - What was unavailable (transparent limitation)
   - How to unlock more (upgrade path)

---

## 🔑 Key Design Decisions

### 1. Recommend Advanced Engineer, Not Enterprise

**Rationale:**
- Team plan ($99/mo) is the sweet spot for most users
- Unlocks all advanced analyzers (enhanced_architectural, enhanced_performance, enhanced_concurrency)
- Enterprise plan ($Custom) is overkill for conversion optimization
- Clear upgrade path: Developer → Team (most users)

### 2. Group Capabilities by Category

**Rationale:**
- Makes it clear what type of intelligence is missing
- Easier to scan than flat list
- Maps to user's mental model ("I need better architecture insights")
- Categories: Architecture, Performance, Concurrency

### 3. Show Benefits, Not Just Features

**Rationale:**
- "Catches N+1 queries before they impact users" > "N+1 query detection"
- Outcome-focused language resonates more
- Emphasizes prevention ("before they cause problems")
- Connects to user pain points

### 4. Trust-First Approach

**Rationale:**
- Users might worry upgrade affects past runs
- Explicitly state: "Past runs remain unchanged"
- Reinforces immutable governance value prop
- Builds confidence before asking for commitment

### 5. No Dark Patterns

**Rationale:**
- Use real skipped analyzer data (no fake scarcity)
- No countdown timers ("Upgrade now!")
- No misleading claims ("90% of users upgrade")
- Transparent about demo environment (no surprise billing)

---

## 📈 Expected Impact

### Conversion Metrics (Hypothetical)

**Before Phase 14.3.1:**
- Users see locked capabilities in coverage panel
- Generic messaging: "Requires Team plan"
- No contextual motivation
- Low conversion rate (baseline)

**After Phase 14.3.1:**
- Prominent upgrade prompt at friction points
- Specific capabilities grouped by category
- Clear benefits explained
- Trust copy addresses concerns
- Expected: 2-3x conversion rate improvement

### User Sentiment

**Positive Indicators:**
- "I understand exactly what I'm getting"
- "The upgrade prompt showed me what I was missing"
- "I appreciate that past runs won't change"

**Avoid Negative Sentiment:**
- "This feels pushy"
- "I'm being pressured to upgrade"
- "The upgrade prompt is annoying"

---

## 🚀 Technical Implementation

### Files Modified/Created

1. **frontend/components/subscription/UpgradePrompt.tsx** (NEW)
   - 211 lines
   - Reusable upgrade prompt component
   - Contextual intelligence display
   - Advanced Engineer highlights
   - Trust & transparency copy

2. **frontend/components/runs/ExecutionCoverage.tsx** (MODIFIED)
   - Updated header comment (Phase 14.3.1)
   - Imported UpgradePrompt component
   - Added planExperienceMap for tier translation
   - Integrated upgrade prompt before coverage card
   - Updated all labels to experience language
   - Enhanced locked capability messaging

3. **frontend/components/governance/PlanContextBlock.tsx** (MODIFIED)
   - Updated header comment (Phase 14.3.1)
   - Imported UpgradePrompt component
   - Added planExperienceMap for tier translation
   - Integrated upgrade prompt before context card
   - Updated all labels to experience language
   - Added lockedAnalyzers computation for prompt

4. **frontend/app/runs/[id]/page.tsx** (MODIFIED)
   - Updated ExecutionCoverage with realistic demo data
   - Shows 11 executed analyzers (developer plan)
   - Simulates 3 locked advanced capabilities

### No Backend Changes ✅

Phase 14.3.1 is **purely a frontend enhancement**. No backend changes required:
- Backend enforcement unchanged (Phase 14.2)
- Ledger recording unchanged
- Plan context snapshots unchanged
- Orchestrator logic unchanged

### Component Dependencies

```
UpgradePrompt
├── @/lib/analyzerRegistry (getAnalyzer)
├── @/components/ui (Card, CardContent, Badge)
└── lucide-react icons

ExecutionCoverage
├── UpgradePrompt
├── @/lib/analyzerRegistry
├── @/components/ui
└── lucide-react icons

PlanContextBlock
├── UpgradePrompt
├── @/lib/analyzerRegistry
├── @/components/ui
└── lucide-react icons
```

---

## 📋 Testing & Validation

### Manual Testing Checklist

- [x] UpgradePrompt component renders correctly
- [x] Skipped analyzers grouped by category
- [x] Advanced Engineer benefits listed
- [x] Trust copy shows immutable governance message
- [x] "Compare Plans" button links to `/plans`
- [x] Demo environment notice present
- [x] ExecutionCoverage shows upgrade prompt when locked capabilities exist
- [x] ExecutionCoverage uses experience language
- [x] PlanContextBlock shows upgrade prompt when capabilities locked
- [x] PlanContextBlock uses experience language
- [x] Run detail page shows realistic demo data
- [x] All terminology consistent (capabilities not services)

### User Experience Testing

**Scenario 1: Developer Plan User**
- Navigate to `/runs/[id]`
- Verify upgrade prompt appears at top
- Verify "3 Capabilities Unavailable" badge
- Verify grouped intelligence categories
- Verify Advanced Engineer benefits listed
- Verify trust copy present
- Click "Compare Plans" → Navigate to `/plans`

**Scenario 2: Team Plan User** (hypothetical)
- Would show 0 locked capabilities
- No upgrade prompt shown
- All 14 capabilities marked as "Active"

**Scenario 3: Governance Audit**
- Navigate to `/governance/[run_id]`
- Verify upgrade prompt before plan context
- Verify plan context uses experience language
- Verify locked capabilities count matches

---

## 🎯 Success Criteria

### Delivered ✅

- [x] Created reusable UpgradePrompt component
- [x] Integrated upgrade prompt into run detail page
- [x] Integrated upgrade prompt into governance page
- [x] Used experience-based language throughout
- [x] Showed real skipped analyzer data (no fake scarcity)
- [x] Highlighted Advanced Engineer as recommended plan
- [x] Added trust copy about immutable governance
- [x] No billing integration (demo environment)
- [x] No backend changes (presentation layer only)
- [x] No plan enforcement changes (uses existing data)

### User Experience Goals

- [x] **Honest:** Uses real skipped analyzer data
- [x] **Contextual:** Appears at friction points (post-run, governance)
- [x] **Transparent:** Explains immutable governance
- [x] **Compelling:** Shows clear benefits and upgrade path
- [x] **No dark patterns:** No fake scarcity, no misleading claims

---

## 📚 Related Documentation

- **PHASE_14.3_EXPERIENCE_UI.md:** Netflix-style subscription page
- **PHASE_14.3_FINAL_STATUS.md:** Experience-based UI completion
- **PHASE_14.2_ENFORCEMENT.md:** Plan enforcement implementation
- **PHASE_14.1_SERVICE_FOUNDATION.md:** Service-centric plan definitions
- **frontend/components/subscription/UpgradePrompt.tsx:** Upgrade prompt component
- **frontend/lib/analyzerRegistry.ts:** Experience-based service descriptions

---

## 🚦 Phase 14.3.1 Status: COMPLETE

Phase 14.3.1 is complete and ready for demo. The upgrade motivation layer now:
- **Shows contextual prompts** at key friction points
- **Uses real data** (no dark patterns)
- **Emphasizes benefits** (outcome-focused)
- **Maintains trust** (immutable governance messaging)
- **Recommends intelligently** (Advanced Engineer as sweet spot)

**Next Phase:** Phase 15 (TBD - potential future enhancements)

---

**Phase 14.3.1 Complete:** Upgrade Motivation & Friction Layer ✅  
**Date Locked:** January 16, 2026  
**Files Changed:** 4 files (1 new, 3 modified)  
**Backend Changes:** 0 (presentation layer only)  
**Conversion Impact:** Expected 2-3x improvement in plan conversion

