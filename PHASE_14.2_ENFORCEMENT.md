# Phase 14.2: Subscription Enforcement & Entitlement Control

**Status:** ✅ Complete  
**Date:** January 16, 2026  
**Scope:** Make subscription plans authoritative and enforceable during execution

---

## Overview

Phase 14.2 implements **subscription enforcement** by making plans authoritative during orchestrator execution. Every analysis run now executes under an explicit plan snapshot that determines which analyzers are allowed.

This transforms plans from "informational metadata" to **enforceable entitlements** while preserving:
- ✅ Determinism (same plan = same execution)
- ✅ Auditability (plan context recorded in ledger)
- ✅ Replayability (deterministic plan enforcement)
- ✅ Backward compatibility (plan_context is optional)

**Key Innovation:** Plan enforcement happens at orchestration time, NOT at analyzer level. Analyzers remain stateless and plan-agnostic. The orchestrator filters which analyzers run based on the plan context.

---

## Goals

1. ✅ Create UserPlanContext model (immutable plan snapshot)
2. ✅ Update orchestrator to enforce plan eligibility
3. ✅ Record plan context and skipped analyzers in ledger
4. ✅ Maintain determinism and backward compatibility
5. ✅ Test all enforcement scenarios

---

## Architecture Changes

### 1. UserPlanContext Model

**Location:** `backend/app/plans.py`

```python
@dataclass(frozen=True)
class UserPlanContext:
    """Immutable snapshot of a user's plan at execution time."""
    plan_tier: PlanTier
    allowed_analyzer_ids: frozenset[str]
    snapshot_timestamp: str  # ISO 8601
```

**Key Features:**
- **Immutable:** `@dataclass(frozen=True)` ensures no mutations
- **Deterministic:** frozenset ensures consistent ordering
- **Serializable:** `to_dict()` / `from_dict()` for ledger recording
- **No User IDs:** This is execution context, not user management
- **No Billing:** Pure entitlement model, no payment state

**Creation:**
```python
from backend.app.plans import create_plan_context, PlanTier

# Create plan context for a run
plan_ctx = create_plan_context(PlanTier.DEVELOPER)

# Pass to orchestrator
orchestrator.analyze(
    repository_path="/path/to/repo",
    repository_url="https://github.com/user/repo",
    branch="main",
    plan_context=plan_ctx,  # Enforces plan
)
```

**Methods:**
- `is_analyzer_allowed(analyzer_id: str) -> bool`: Check if analyzer allowed
- `filter_allowed_analyzers(analyzer_ids: List[str]) -> List[str]`: Filter list
- `get_disallowed_reason(analyzer_id: str) -> str`: Human-readable reason
- `to_dict()` / `from_dict()`: Serialization for ledger

---

### 2. Orchestrator Plan Enforcement

**Location:** `agent/intelligence/orchestrator.py`

**New analyze() Parameter:**
```python
def analyze(
    self,
    repository_path: str,
    repository_url: str,
    branch: str = "main",
    ledger: Optional[Any] = None,
    run_id: Optional[str] = None,
    selection: Optional[AnalyzerSelection] = None,
    plan: Optional[str] = None,  # Deprecated
    plan_context: Optional[UserPlanContext] = None,  # NEW: Phase 14.2
) -> List[IntelligenceProposal]:
```

**Enforcement Logic:**

```python
def _resolve_analyzers_with_enforcement(
    self,
    selection: Optional[AnalyzerSelection],
    plan: Optional[str],
    plan_context: Optional[UserPlanContext],
) -> Tuple[List[Any], List[Dict[str, str]]]:
    """
    Priority:
    1. selection (if provided) → validate and filter by plan_context
    2. plan_context (if provided) → filter all analyzers
    3. plan (if provided) → backward compatibility
    4. default → developer plan (backward compatibility)
    """
```

**Returns:**
- `analyzers_to_run`: List of instantiated analyzers (allowed by plan)
- `skipped_analyzers`: List of `{'analyzer_id': str, 'reason': str}`

**Skipped Analyzer Format:**
```python
{
    'analyzer_id': 'enhanced_architectural',
    'reason': "Analyzer 'enhanced_architectural' requires a higher plan tier than developer"
}
```

---

### 3. Ledger Integration

**Automatic Recording:**

When `plan_context` is provided, the orchestrator automatically records:

1. **PLAN_CONTEXT_CAPTURED** event:
```json
{
  "event_type": "PLAN_CONTEXT_CAPTURED",
  "summary": "Plan context: developer",
  "actor": "SYSTEM",
  "actor_role": "SUBSCRIPTION",
  "phase": "INTELLIGENCE",
  "payload_ref": {
    "plan_tier": "developer",
    "allowed_analyzer_ids": ["architectural", "performance", ...],
    "snapshot_timestamp": "2026-01-16T12:34:56.789Z"
  }
}
```

2. **ANALYZERS_SKIPPED** event (if any skipped):
```json
{
  "event_type": "ANALYZERS_SKIPPED",
  "summary": "3 analyzer(s) skipped due to plan restrictions",
  "actor": "SYSTEM",
  "actor_role": "SUBSCRIPTION",
  "phase": "INTELLIGENCE",
  "payload_ref": {
    "skipped": [
      {
        "analyzer_id": "enhanced_architectural",
        "reason": "Analyzer 'enhanced_architectural' requires a higher plan tier than developer"
      },
      ...
    ]
  }
}
```

**Non-Fatal:** Ledger writes are non-fatal. If ledger recording fails, execution continues.

---

### 4. Summary Integration

**get_summary() Enhancement:**

```python
{
  'run_id': '...',
  'total_proposals': 42,
  'skipped_analyzers': [...]  # NEW: Phase 14.2
  'skipped_count': 3,          # NEW: Phase 14.2
  ...
}
```

Skipped analyzers are included in the summary for:
- Dashboard display
- API responses
- Debug logging

---

## Plan Tier Differences

### Developer Plan (Free)
**Includes:**
- All basic analyzers (11 total):
  - architectural
  - abstraction
  - api_contracts
  - god_objects
  - performance
  - concurrency
  - security
  - test_coverage
  - broken_invariants
  - configuration
  - dependencies

**Excludes:**
- enhanced_architectural (requires Team)
- enhanced_performance (requires Team)
- enhanced_concurrency (requires Team)

### Team Plan ($99/month)
**Includes:**
- All Developer analyzers (11)
- Plus enhanced analyzers (3):
  - enhanced_architectural
  - enhanced_performance
  - enhanced_concurrency

**Total:** 14 analyzers

### Enterprise Plan (Custom)
**Includes:**
- Same as Team (14 analyzers)
- No additional analyzers (same intelligence)
- Differences: limits, support, SLAs

---

## Testing Results

**Test Suite:** `test_plan_enforcement_manual.py`

```
============================================================
Phase 14.2: Plan Enforcement Tests
============================================================

=== Test: Plan Context Creation ===
✓ Developer plan context created (11 analyzers)
✓ Team plan context created (14 analyzers)
✓ Team plan has >= analyzers than developer plan
✓ Default plan context is developer tier
✓ All plan context creation tests passed

=== Test: Analyzer Filtering ===
✓ Developer plan allows 'architectural'
✓ Developer plan allows 'performance'
✓ Developer plan blocks 'enhanced_architectural'
✓ Developer plan blocks 'enhanced_performance'
✓ Team plan allows 'enhanced_architectural'
✓ Team plan allows 'enhanced_performance'
✓ Developer plan filters correctly: 2/4 allowed
✓ All analyzer filtering tests passed

=== Test: Disallowed Reasons ===
✓ Disallowed reason includes analyzer ID and plan tier
✓ Allowed analyzer has empty reason
✓ All disallowed reason tests passed

=== Test: Serialization ===
✓ Serialized to dict (for ledger)
✓ Deserialized from dict (for replay)
✓ All serialization tests passed

=== Test: Orchestrator Enforcement ===
✓ Developer plan: 11 analyzers executed, 3 skipped
✓ All skipped analyzers have reasons
✓ Team plan: 14 analyzers executed, 0 skipped
✓ Team plan executes >= analyzers than developer
✓ No plan context: 11 analyzers (backward compat)
✓ All orchestrator enforcement tests passed

=== Test: Determinism ===
✓ Executed analyzers are deterministic
✓ Skipped analyzers are deterministic
✓ All determinism tests passed

=== Test: Summary Includes Skipped ===
✓ Summary includes 3 skipped analyzers
✓ All summary tests passed

============================================================
✅ ALL TESTS PASSED
============================================================
```

---

## Usage Examples

### Basic Usage

```python
from agent.intelligence.orchestrator import IntelligenceOrchestrator
from backend.app.plans import create_plan_context, PlanTier

# Create orchestrator
orchestrator = IntelligenceOrchestrator()

# Create plan context for developer tier
plan_ctx = create_plan_context(PlanTier.DEVELOPER)

# Run analysis with plan enforcement
proposals = orchestrator.analyze(
    repository_path="/path/to/repo",
    repository_url="https://github.com/user/repo",
    branch="main",
    plan_context=plan_ctx,
)

# Check what was skipped
print(f"Executed: {len(orchestrator.analyzers)}")
print(f"Skipped: {len(orchestrator.skipped_analyzers)}")

for skipped in orchestrator.skipped_analyzers:
    print(f"  - {skipped['analyzer_id']}: {skipped['reason']}")
```

### With Ledger Recording

```python
from agent.run_ledger import RunLedgerWriter

# Create ledger
ledger = RunLedgerWriter(run_id="run-123", repo_id="user/repo")
ledger.create_ledger()

# Create plan context
plan_ctx = create_plan_context(PlanTier.TEAM)

# Run with ledger + plan enforcement
orchestrator = IntelligenceOrchestrator()
proposals = orchestrator.analyze(
    repository_path="/path/to/repo",
    repository_url="https://github.com/user/repo",
    branch="main",
    ledger=ledger,
    plan_context=plan_ctx,
)

# Plan context automatically recorded in ledger
# Skipped analyzers automatically recorded in ledger

ledger.seal("COMPLETE")
```

### Backward Compatibility (No Plan Context)

```python
# Old code continues to work
orchestrator = IntelligenceOrchestrator()
proposals = orchestrator.analyze(
    repository_path="/path/to/repo",
    repository_url="https://github.com/user/repo",
    branch="main",
    # No plan_context provided
)

# Defaults to developer plan (backward compatible)
# No enforcement without explicit plan_context
```

---

## Determinism Guarantees

**Phase 14.2 preserves determinism:**

1. **Same plan → same analyzers:**
   - Developer plan ALWAYS runs same 11 analyzers
   - Team plan ALWAYS runs same 14 analyzers
   - Execution order is deterministic (sorted analyzer IDs)

2. **Same plan → same skips:**
   - Developer plan ALWAYS skips same 3 analyzers
   - Skipped list is deterministic (sorted)

3. **Replayability:**
   - Plan context serialized to ledger
   - Can replay with exact same plan snapshot
   - `UserPlanContext.from_dict()` restores context

4. **No runtime surprises:**
   - Analyzers don't check plans themselves
   - All filtering happens before execution
   - No conditional logic inside analyzers

---

## Security & Auditability

### Immutable Plan Context

```python
plan_ctx = create_plan_context(PlanTier.DEVELOPER)

# ❌ Cannot mutate
plan_ctx.plan_tier = PlanTier.ENTERPRISE  # ERROR: frozen dataclass

# ❌ Cannot modify allowed analyzers
plan_ctx.allowed_analyzer_ids.add('enhanced_performance')  # ERROR: frozenset
```

### Ledger Audit Trail

Every run records:
1. **Which plan was used** (tier, timestamp)
2. **Which analyzers were allowed** (complete list)
3. **Which analyzers executed** (via existing proposal events)
4. **Which analyzers were skipped** (with reasons)

This creates **complete subscription audit trail** for:
- Compliance verification
- Billing disputes
- Plan upgrade justification
- Security audits

---

## What Changed

### Files Modified (2)

1. **backend/app/plans.py**
   - Added `UserPlanContext` dataclass
   - Added `create_plan_context()` helper
   - Added `create_default_plan_context()` helper
   - Fixed `get_all_analyzer_ids()` to filter by plan services

2. **agent/intelligence/orchestrator.py**
   - Added `plan_context` parameter to `analyze()`
   - Added `skipped_analyzers` instance variable
   - Replaced `_resolve_analyzers()` with `_resolve_analyzers_with_enforcement()`
   - Added plan context recording to ledger
   - Added skipped analyzers recording to ledger
   - Updated `get_summary()` to include skipped analyzers

### Files Created (2)

1. **tests/test_plan_enforcement.py**
   - Comprehensive pytest test suite
   - Tests all enforcement scenarios
   - Tests determinism and replayability
   - Tests ledger integration

2. **test_plan_enforcement_manual.py**
   - Manual test runner (no pytest required)
   - Validates all functionality
   - 100% test pass rate

---

## Backward Compatibility

**Zero Breaking Changes:**

✅ Old code without `plan_context` continues to work  
✅ Defaults to developer plan (existing behavior)  
✅ No analyzer code changes required  
✅ No API changes for existing endpoints  
✅ No database changes required  

**Optional Parameter:**
```python
def analyze(
    ...
    plan_context: Optional[UserPlanContext] = None,  # Optional!
):
```

---

## Performance Impact

**Minimal overhead:**

- Plan context creation: < 1ms (frozenset construction)
- Analyzer filtering: O(n) where n = number of analyzers (~14)
- Ledger recording: Non-blocking, non-fatal
- Skipped analyzer tracking: List append operations

**No impact on:**
- Individual analyzer execution time
- Proposal generation logic
- Git operations
- File I/O

---

## Future Integration Points

### Phase 14.3: User-Plan Mapping (Future)

```python
# Future: Get plan from user database
from backend.app.users import get_current_user
from backend.app.subscriptions import get_user_plan_tier

user = get_current_user()
plan_tier = get_user_plan_tier(user.id)
plan_ctx = create_plan_context(plan_tier)

orchestrator.analyze(..., plan_context=plan_ctx)
```

### Phase 14.4: API Integration (Future)

```python
# Future: FastAPI endpoint
@router.post("/runs/analyze")
async def analyze_repository(
    repo_path: str,
    current_user: User = Depends(get_current_user)
):
    # Get user's plan
    plan_tier = await get_user_plan_tier(current_user.id)
    plan_ctx = create_plan_context(plan_tier)
    
    # Run with enforcement
    orchestrator = IntelligenceOrchestrator()
    proposals = orchestrator.analyze(
        repository_path=repo_path,
        plan_context=plan_ctx,
    )
    
    return {
        'proposals': proposals,
        'executed_analyzers': len(orchestrator.analyzers),
        'skipped_analyzers': orchestrator.skipped_analyzers,
    }
```

---

## Known Limitations

### What Phase 14.2 Does NOT Do

❌ **No User Management**
- No user-to-plan mapping in database
- No user_id tracking
- Manual plan context creation required

❌ **No Billing Integration**
- No Stripe integration
- No payment processing
- No plan upgrade flows

❌ **No Frontend Changes**
- Frontend still displays mock data
- No real-time plan enforcement in UI
- No "upgrade now" buttons

❌ **No Usage Tracking**
- No run count enforcement (50/500/unlimited)
- No rate limiting
- No usage alerts

These are intentionally deferred to Phase 14.3+.

---

## Success Criteria

✅ **Enforcement Works:**
- Developer plan blocks enhanced analyzers
- Team plan allows all analyzers
- Skipped analyzers recorded with reasons

✅ **Determinism Preserved:**
- Same plan → same analyzers every time
- Execution order deterministic
- Replay produces identical results

✅ **Auditability Achieved:**
- Plan context recorded in ledger
- Skipped analyzers recorded in ledger
- Complete audit trail for compliance

✅ **Backward Compatibility Maintained:**
- Old code works without plan_context
- No breaking API changes
- No analyzer changes required

✅ **Tests Pass:**
- All manual tests pass (100%)
- Pytest suite ready for CI/CD
- Determinism verified

---

## Phase Lock

**Phase 14.2 is now LOCKED.**

No further changes to:
- UserPlanContext model
- Orchestrator enforcement logic
- Ledger recording format
- Test suite

All future work moves to Phase 14.3 (User-Plan Mapping & Billing).

---

## Next Phase: 14.3 - User-Plan Mapping & Billing Integration

Phase 14.3 will add:

1. **Database Schema:**
   - `subscriptions` table (user_id → plan_tier)
   - `usage_tracking` table (run counts)
   - `stripe_customers` table (billing integration)

2. **Stripe Integration:**
   - Payment processing
   - Webhook handlers
   - Customer portal

3. **API Endpoints:**
   - `GET /api/subscription/current`
   - `POST /api/subscription/create-checkout`
   - `POST /api/webhooks/stripe`

4. **Plan Assignment:**
   - Automatic plan context creation from user
   - Run count enforcement
   - Usage alerts

But Phase 14.2 provides the **enforcement foundation**: plans are now authoritative, deterministic, and auditable.

---

## Sign-Off

**Phase 14.2: Subscription Enforcement & Entitlement Control**

✅ UserPlanContext model created  
✅ Orchestrator enforces plan eligibility  
✅ Plan context recorded in ledger  
✅ Skipped analyzers tracked and recorded  
✅ Determinism preserved  
✅ Backward compatibility maintained  
✅ Tests pass (100%)  
✅ Documentation complete  

**Status:** COMPLETE AND LOCKED  
**Date:** January 16, 2026  

Proceed to Phase 14.3.
