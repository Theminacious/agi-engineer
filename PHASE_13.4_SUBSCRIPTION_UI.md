# Phase 13.4: Subscription-Aware Governance UI (READ-ONLY)

Status: COMPLETE | Locked

Date: 2026-01-14

## Objective

Expose subscription-aware transparency across the UI without modifying:
- Analyzer logic
- Orchestrator behavior
- Billing or payment logic
- Existing APIs or routes
- Determinism or replayability

This phase is **UI-only + data wiring**, fully **read-only**.

---

## Implementation

### 1. Analyzer Registry (Frontend Mirror)

**File:** `frontend/lib/analyzerRegistry.ts`

- Static mirror of backend `agent/intelligence/registry.py`
- Contains all analyzer metadata: id, category, min_plan, description
- Deterministic sorting and filtering functions
- **Zero business logic duplication** — only data structures

Functions:
- `getAllAnalyzers()` — Deterministic list
- `getAnalyzersForPlan(plan)` — Plan-filtered list
- `isAnalyzerAvailableForPlan(id, plan)` — Boolean check
- `groupAnalyzersByCategory()` — UI rendering helper
- `getCategoryLabel(category)` — Display names
- `getPlanLabel(plan)` — Display names

### 2. Dashboard Analyzer Coverage Panel

**File:** `frontend/components/dashboard/AnalyzerCoveragePanel.tsx`

**Location:** Dashboard page, prominently above metrics

**Shows:**
- ✅ Current plan badge
- ✅ Total analyzers available (enabled/locked split)
- ✅ Analyzers grouped by category
- ✅ Status per analyzer (✅ enabled, 🔒 locked)
- ✅ Required plan for locked analyzers
- ✅ Immutability banner

**Props:**
```typescript
interface AnalyzerCoveragePanelProps {
  currentPlan: PlanType | null
}
```

**No mutations:**
- No "upgrade" buttons
- No billing calls
- No state changes
- Display only

### 3. Run Detail Execution Coverage Section

**File:** `frontend/components/runs/ExecutionCoverage.tsx`

**Location:** Run detail page, after summary info

**Shows:**
- ✅ Analyzers that executed
- ✅ Analyzers locked by plan (not available for this run)
- ✅ Analyzers skipped (intentionally excluded)
- ✅ Immutability banner
- ✅ Summary stats (executed, locked, skipped counts)

**Props:**
```typescript
interface ExecutionCoverageProps {
  plan: PlanType | null
  executedAnalyzers: string[]
  skippedAnalyzers?: string[]
}
```

**Data source:**
- `plan` from run metadata
- `executedAnalyzers` from ledger ANALYZER_SELECTION_DEFINED event or run metadata
- `skippedAnalyzers` from run data (optional)

### 4. Governance Plan Context Block

**File:** `frontend/components/governance/PlanContextBlock.tsx`

**Location:** Governance page `/governance/[run_id]`, after header

**Shows:**
- ✅ Subscription plan (immutable badge)
- ✅ Analyzers enabled for this plan
- ✅ Analyzers locked
- ✅ Timestamp when recorded
- ✅ Analyzer eligibility summary
- ✅ Governance explanation (immutability statement)

**Props:**
```typescript
interface PlanContextBlockProps {
  plan: PlanType | null
  timestamp?: string
}
```

**No mutations:**
- Frozen ledger display
- No plan changes
- No upgrade flows

---

## UI Changes Summary

| Page | Component | Change | Immutable |
|------|-----------|--------|-----------|
| Dashboard | AnalyzerCoveragePanel | New section | ✅ Display only |
| Run Detail | ExecutionCoverage | New section after summary | ✅ Display only |
| Governance | PlanContextBlock | New section after header | ✅ Ledger-backed |

---

## Data Flow

```
Backend Registry (Python)
    ↓ (mirrors)
Frontend Registry (TypeScript)
    ↓ (used by)
UI Components
    ↓ (display)
User (read-only)
```

**No circular dependencies.**
**No business logic in frontend.**

---

## Non-Goals (Verified)

- ❌ No analyzer logic changes
- ❌ No orchestrator behavior changes
- ❌ No new APIs or routes
- ❌ No billing or payment integration
- ❌ No mutation paths
- ❌ No breaking changes to existing UI
- ❌ No TypeScript errors

---

## Why This Matters

After Phase 13.4, you can:
- **Show** which analyzers are available by plan
- **Explain** why analyzers are locked
- **Justify** pricing with transparency
- **Demo** subscription value
- **Onboard** enterprises with confidence

This is where engineering meets company.

---

## Verification Checklist

✅ UI renders correctly for all 3 plans (developer, team, enterprise)
✅ No TypeScript errors
✅ No backend changes
✅ No breaking changes to existing routes
✅ No mutation paths (read-only only)
✅ All content is read-only and immutable
✅ Registry data mirrors backend exactly
✅ Determinism preserved (sorted IDs, no randomness)

---

## Lock Statement

🔒 **Phase 13.4 is OFFICIALLY LOCKED**

- Subscription-aware UI is complete and read-only
- All transparency components integrated
- No mutation paths exposed
- System remains deterministic and auditable
- Ready for pricing, billing, and GTM
- **This is where engineering becomes a company.**

