# Phase 15.1: Governed Fix Approval & Application

**Status:** 🔒 **LOCKED**  
**Date:** January 16, 2026  
**Objective:** Close the loop from intelligence → action while preserving human control, determinism, and ledger auditability

---

## 🎯 Purpose

Phase 15.1 introduces **governed fix approval and application** to AGI Engineer, enabling the system to not just find problems—but safely fix them under explicit human oversight.

### Why Fixes Are Governed

**The Autonomy Problem:**  
Autonomous code changes without human approval create:
- Trust violations (silent modifications)
- Audit gaps (no decision trail)
- Safety risks (incorrect fixes applied automatically)
- Compliance failures (no human-in-the-loop)

**The Governance Solution:**  
Every fix follows an explicit approval workflow:
1. AI proposes fix (analysis phase)
2. Human reviews and approves (governance phase)
3. Human explicitly applies (execution phase)
4. All actions recorded in immutable ledger

### Why Autonomy Is Forbidden

**Phase 15.1 Explicit Non-Goals:**
- ❌ No automatic fix application
- ❌ No background fix execution
- ❌ No learning from past approvals
- ❌ No retroactive changes to past runs
- ❌ No "auto-approve" based on heuristics

**Rationale:**
- **Trust:** Code changes must be explicit and visible
- **Safety:** Incorrect fixes can break production systems
- **Auditability:** Every decision must have a human actor
- **Determinism:** Same input → same fix proposal (no auto-learning)
- **Compliance:** Regulatory requirements mandate human approval for code changes

---

## 🔄 Fix Lifecycle

### State Machine

```
PROPOSED
  ├─ approve() → APPROVED → apply() → APPLIED ✅
  │                             └─ (on error) → FAILED ⚠️
  └─ reject() → REJECTED ❌
```

### State Definitions

| State | Description | Next Actions | Ledger Event |
|-------|-------------|--------------|--------------|
| **PROPOSED** | AI generated fix, awaiting review | approve, reject | FIX_PROPOSED |
| **APPROVED** | Human approved, ready for application | apply | FIX_APPROVED |
| **REJECTED** | Human rejected, will not be applied | (none - terminal) | FIX_REJECTED |
| **APPLIED** | Successfully applied to codebase | (none - terminal) | FIX_APPLIED |
| **FAILED** | Application failed (technical error) | (none - terminal) | FIX_FAILED |

### State Transitions

**PROPOSED → APPROVED:**
- Requires: Human approval + Advanced/Autonomous plan
- Action: `POST /api/fixes/{id}/approve`
- Records: approved_by, approved_at, approval_plan, ledger_event_id
- Ledger: `FIX_APPROVED` event with actor, timestamp, plan context

**PROPOSED → REJECTED:**
- Requires: Human rejection + Advanced/Autonomous plan
- Action: `POST /api/fixes/{id}/reject`
- Records: rejected_by, rejected_at, rejection_reason
- Ledger: `FIX_REJECTED` event with actor, timestamp, reason

**APPROVED → APPLIED:**
- Requires: Human application + Advanced/Autonomous plan
- Action: `POST /api/fixes/{id}/apply-governed`
- Validation: File exists, content matches original, patch generates
- Execution: Backup created, patch applied, backup removed
- Rollback: On error, restores from backup
- Records: applied_by, applied_at, application_plan, patch, metadata
- Ledger: `FIX_APPLIED` event with actor, timestamp, file path

**APPROVED → FAILED:**
- Trigger: Application attempt encounters error
- Causes: File changed since proposal, invalid patch, write error
- Records: application_error, maintains APPROVED state metadata
- Ledger: `FIX_FAILED` event with error details

---

## 🔐 Plan Enforcement

### Capability Matrix

| Plan | View Fixes | Approve Fixes | Apply Fixes | Batch Approve |
|------|-----------|---------------|-------------|---------------|
| **Core Engineer** (developer) | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Advanced Engineer** (team) | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **Autonomous Engineer** (enterprise) | ✅ Yes | ✅ Yes | ✅ Yes | 🔮 Future (Phase 15.2) |

### Service Capabilities

**Phase 15.1 added 4 new service capabilities to plan definitions:**

```python
class ServiceCapability(str, Enum):
    # Fix Management Services (Phase 15.1)
    VIEW_FIX_PROPOSALS = "view_fix_proposals"       # All plans
    APPROVE_FIXES = "approve_fixes"                 # Advanced+
    APPLY_FIXES = "apply_fixes"                     # Advanced+
    BATCH_FIX_APPROVAL = "batch_fix_approval"       # Enterprise (future)
```

### Enforcement Points

**API Layer:**
- All fix endpoints check `UserPlanContext.plan_id`
- Return 403 Forbidden if plan lacks capability
- Error message includes required plan tier

**UI Layer:**
- Buttons disabled/hidden if plan lacks capability
- Upgrade prompt shown: "Upgrade to Advanced Engineer to approve fixes"
- Plan badge shown on approved/applied fixes

**Example Enforcement (Backend):**
```python
def can_approve_fixes(self, plan_context: UserPlanContext) -> bool:
    return plan_context.plan_id in ["team", "enterprise"]
```

**Example Enforcement (Frontend):**
```tsx
const canApprove = plan !== 'developer' // Advanced+ can approve
{canApprove ? (
  <Button onClick={handleApprove}>Approve Fix</Button>
) : (
  <div>Upgrade to Advanced Engineer to approve fixes</div>
)}
```

---

## 📝 Ledger Events

### Event Taxonomy

Phase 15.1 introduces 4 new ledger event types:

#### 1. FIX_PROPOSED
```json
{
  "event_type": "FIX_PROPOSED",
  "actor": "system",
  "actor_role": "System",
  "phase": "PHASE_15.1",
  "summary": "Fix #42 proposed for file src/utils.py",
  "payload_ref": "fix-uuid-123"
}
```

#### 2. FIX_APPROVED
```json
{
  "event_type": "FIX_APPROVED",
  "actor": "user@example.com",
  "actor_role": "Human",
  "phase": "PHASE_15.1",
  "summary": "Fix #42 approved for application by user@example.com",
  "payload_ref": "approval-event-uuid-456"
}
```

#### 3. FIX_REJECTED
```json
{
  "event_type": "FIX_REJECTED",
  "actor": "user@example.com",
  "actor_role": "Human",
  "phase": "PHASE_15.1",
  "summary": "Fix #42 rejected by user@example.com: Introduces breaking changes",
  "payload_ref": null
}
```

#### 4. FIX_APPLIED
```json
{
  "event_type": "FIX_APPLIED",
  "actor": "user@example.com",
  "actor_role": "Human",
  "phase": "PHASE_15.1",
  "summary": "Fix #42 successfully applied to src/utils.py by user@example.com",
  "payload_ref": "application-event-uuid-789"
}
```

#### 5. FIX_FAILED
```json
{
  "event_type": "FIX_FAILED",
  "actor": "user@example.com",
  "actor_role": "Human",
  "phase": "PHASE_15.1",
  "summary": "Fix #42 application failed: File content has changed since fix was generated",
  "payload_ref": null
}
```

### Ledger Integration

**Database Schema:**
```python
class CodeFix:
    # Ledger references
    ledger_run_id: str                    # Run ID for ledger lookup
    approval_ledger_event_id: str         # UUID of FIX_APPROVED event
    application_ledger_event_id: str      # UUID of FIX_APPLIED event
```

**Event Append (Backend):**
```python
ledger_writer.append_event(
    event_type="FIX_APPROVED",
    summary=f"Fix #{fix_id} approved for application by {approved_by}",
    actor=approved_by,
    actor_role="Human",
    phase="PHASE_15.1",
    payload_ref=ledger_event_id
)
```

**Query (Frontend):**
```tsx
const events = await readLedgerEvents(run_id)
const fixEvents = events.filter(e => 
  ['FIX_APPROVED', 'FIX_REJECTED', 'FIX_APPLIED', 'FIX_FAILED'].includes(e.event_type)
)
```

---

## 🛡️ Safety Guarantees

### 1. No Silent Changes

**Guarantee:** Every code modification requires explicit human action.

**Implementation:**
- All fixes start in PROPOSED state
- Approval requires explicit API call with user identity
- Application requires separate explicit API call
- No cron jobs, no background workers, no automatic application

**Verification:**
- Check ledger: Every APPLIED fix has corresponding APPROVED event with human actor
- Check database: Every applied fix has approved_by and applied_by fields populated

### 2. Deterministic Patches

**Guarantee:** Same original code + same fixed code = same patch.

**Implementation:**
```python
def generate_patch(original_code: str, fixed_code: str, file_path: str) -> str:
    original_lines = original_code.splitlines(keepends=True)
    fixed_lines = fixed_code.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm=""
    )
    
    return "".join(diff)
```

**Verification:**
- Generate patch twice → identical output
- Store patch in database for reproducibility
- Ledger records patch hash (future enhancement)

### 3. Rollback on Failure

**Guarantee:** If application fails, original code is restored.

**Implementation:**
```python
# Create backup
backup_path = f"{file_path}.backup"
with open(file_path, 'r') as f:
    backup_content = f.read()
with open(backup_path, 'w') as f:
    f.write(backup_content)

try:
    # Apply fix
    with open(file_path, 'w') as f:
        f.write(fixed_code)
    os.remove(backup_path)  # Success
except Exception as e:
    # Rollback
    with open(backup_path, 'r') as f:
        original = f.read()
    with open(file_path, 'w') as f:
        f.write(original)
    os.remove(backup_path)
    raise e
```

**Verification:**
- Introduce write error → original content restored
- Check application_error field in database
- Ledger contains FIX_FAILED event

### 4. Immutable History

**Guarantee:** Past runs and their fixes remain unchanged forever.

**Implementation:**
- Fix records never deleted, only state transitions
- Ledger is append-only (no edits, no deletes)
- All state changes recorded with timestamps and actors
- Past run ledgers never modified

**Verification:**
- Check ledger file modification time (should never change after seal)
- Check fix created_at vs updated_at timestamps
- Query historical fixes by run_id → always returns same results

---

## 🏗️ Architecture

### Backend Components

**1. Data Model** (`backend/app/models/code_fix.py`)
- Extended `CodeFix` model with governance fields
- State: proposed/approved/rejected/applied/failed
- Approval tracking: approved_by, approved_at, approval_plan
- Application tracking: applied_by, applied_at, application_plan
- Rejection tracking: rejected_by, rejected_at, rejection_reason
- Ledger integration: ledger_run_id, approval_ledger_event_id, application_ledger_event_id
- Safety: patch, file_path, application_error, application_metadata

**2. Approval Service** (`backend/app/services/fix_approval.py`)
- `approve_fix()` - Approve proposed fix with plan enforcement
- `reject_fix()` - Reject fix with optional reason
- `can_approve_fixes()` - Check plan capabilities
- `get_fixes_for_run()` - Query fixes by run ID
- Ledger integration for all approval/rejection events

**3. Application Service** (`backend/app/services/fix_application.py`)
- `apply_fix()` - Safely apply approved fix
- `validate_fix()` - Pre-application validation (file exists, content matches)
- `generate_patch()` - Create unified diff patch
- Backup/rollback mechanism
- Dry-run mode for testing
- Ledger integration for application events

**4. API Endpoints** (`backend/app/routers/fixes.py`)
- `POST /api/fixes/{id}/approve` - Approve fix (plan-gated)
- `POST /api/fixes/{id}/reject` - Reject fix (plan-gated)
- `POST /api/fixes/{id}/apply-governed` - Apply fix (validated, plan-gated)
- `GET /api/fixes/run/{run_id}` - List all fixes for run with status counts

**5. Plan Definitions** (`backend/app/plans.py`)
- Added 4 new ServiceCapability enum values
- Updated DEVELOPER_PLAN: VIEW_FIX_PROPOSALS only
- Updated TEAM_PLAN: VIEW_FIX_PROPOSALS, APPROVE_FIXES, APPLY_FIXES
- Updated ENTERPRISE_PLAN: All fix capabilities + BATCH_FIX_APPROVAL (future)

### Frontend Components

**1. FixApprovalCard** (`frontend/components/fixes/FixApprovalCard.tsx`)
- Full fix details with code preview
- Status badge (proposed/approved/rejected/applied/failed)
- Approve/Reject buttons (plan-gated with upgrade prompts)
- Apply Fix button with dry-run validation
- Patch preview (collapsible unified diff)
- Audit trail display (actors, timestamps, plan tiers)
- Rejection dialog with reason input
- Error display for failed applications

**2. FixListView** (`frontend/components/fixes/FixListView.tsx`)
- Status filter tabs with counts
- Renders list of FixApprovalCard components
- Empty state handling
- Status-based filtering

**3. Governance Page Integration** (`frontend/app/governance/[run_id]/page.tsx`)
- **PRIMARY CONTROL SURFACE** for all fix actions
- Fetches fixes via `GET /api/fixes/run/{run_id}`
- Displays FixListView with all fixes
- Human approval required banner
- Plan-based access control enforced

**4. Run Detail Page Integration** (`frontend/app/runs/[id]/page.tsx`)
- **SECONDARY VIEW** for visibility only
- Compact fix summary card showing counts
- No action buttons (approve/reject/apply)
- Links to governance page for all actions
- Audit compliance reminder

### Data Flow

**Approval Flow:**
```
User clicks "Approve" 
  → FixApprovalCard.handleApprove()
  → POST /api/fixes/{id}/approve (plan_tier, approved_by)
  → FixApprovalService.approve_fix()
  → Check plan capabilities
  → Update fix status to APPROVED
  → Append FIX_APPROVED to ledger
  → Return success
  → UI shows "Approved" badge
```

**Application Flow:**
```
User clicks "Apply Fix"
  → FixApprovalCard.handleApply()
  → POST /api/fixes/{id}/apply-governed (plan_tier, applied_by)
  → FixApplicationService.apply_fix()
  → Check plan capabilities
  → Validate fix (file exists, content matches)
  → Generate patch (unified diff)
  → Create backup
  → Write fixed code
  → Delete backup
  → Update fix status to APPLIED
  → Append FIX_APPLIED to ledger
  → Return success with patch
  → UI shows "Applied" badge
```

---

## 📖 Usage Guide

### For Core Engineer Users (View-Only)

**What you can do:**
- View all fix proposals in governance page
- See fix explanations and code diffs
- Review approval/rejection history in audit trail

**What you cannot do:**
- Approve or reject fixes (requires Advanced Engineer)
- Apply fixes to codebase (requires Advanced Engineer)

**Upgrade prompt shown:**
```
🔒 Upgrade to Advanced Engineer to approve and apply fixes
```

### For Advanced Engineer Users (Full Control)

**Reviewing fixes:**
1. Navigate to `/governance/{run_id}`
2. Scroll to "🛠️ Governed Fixes" section
3. Review each fix proposal:
   - Original issue description
   - AI explanation
   - Fixed code preview
   - Unified diff patch

**Approving a fix:**
1. Click "Approve Fix" button (green)
2. Fix status changes to APPROVED
3. Audit trail shows: "Approved by user@example.com on [timestamp]"
4. Ledger records FIX_APPROVED event

**Rejecting a fix:**
1. Click "Reject" button (red)
2. Enter rejection reason (optional but recommended)
3. Click "Confirm Rejection"
4. Fix status changes to REJECTED
5. Audit trail shows reason and actor

**Applying an approved fix:**
1. Ensure fix status is APPROVED
2. Click "Validate (Dry Run)" to test (optional but recommended)
3. Review validation results and patch preview
4. Click "Apply Fix" to execute
5. On success:
   - Fix status changes to APPLIED
   - File is modified in codebase
   - Audit trail shows application details
   - Ledger records FIX_APPLIED event
6. On failure:
   - Fix status changes to FAILED
   - Original code is restored (rollback)
   - Error message displayed
   - Ledger records FIX_FAILED event

### For Autonomous Engineer Users (Enterprise)

**Phase 15.1:** Same capabilities as Advanced Engineer

**Phase 15.2 (Future):** Batch approval workflow
- Approve multiple fixes at once
- Bulk rejection with category reasons
- Batch application with transaction rollback

---

## 🧪 Testing Guide

### Manual Testing Checklist

**Test 1: View-Only (Core Plan)**
- [ ] Set plan to 'developer' in localStorage
- [ ] Navigate to governance page with fixes
- [ ] Verify "Approve" button shows upgrade prompt
- [ ] Verify "Apply" button shows upgrade prompt
- [ ] Verify fix details are visible

**Test 2: Approval Flow (Advanced Plan)**
- [ ] Set plan to 'team'
- [ ] Navigate to governance page
- [ ] Click "Approve Fix" on PROPOSED fix
- [ ] Verify status changes to APPROVED
- [ ] Verify audit trail shows approved_by and timestamp
- [ ] Check ledger for FIX_APPROVED event

**Test 3: Rejection Flow**
- [ ] Click "Reject" on PROPOSED fix
- [ ] Enter rejection reason
- [ ] Click "Confirm Rejection"
- [ ] Verify status changes to REJECTED
- [ ] Verify rejection reason displayed in audit trail
- [ ] Check ledger for FIX_REJECTED event

**Test 4: Application Flow**
- [ ] Approve a fix first
- [ ] Click "Validate (Dry Run)"
- [ ] Review patch in alert
- [ ] Click "Apply Fix"
- [ ] Verify file is modified
- [ ] Verify status changes to APPLIED
- [ ] Check ledger for FIX_APPLIED event

**Test 5: Validation Failure**
- [ ] Manually modify target file after fix is proposed
- [ ] Attempt to apply fix
- [ ] Verify validation fails with error message
- [ ] Verify original content preserved

**Test 6: Application Failure**
- [ ] Create fix for read-only file
- [ ] Approve fix
- [ ] Attempt to apply
- [ ] Verify rollback occurs
- [ ] Verify status changes to FAILED
- [ ] Verify error message shown
- [ ] Check ledger for FIX_FAILED event

**Test 7: Run Detail Summary**
- [ ] Navigate to /runs/{id} with fixes
- [ ] Verify fix summary card displays
- [ ] Verify counts are correct
- [ ] Click "Review in Governance" link
- [ ] Verify navigates to governance page

**Test 8: Ledger Immutability**
- [ ] Apply multiple fixes
- [ ] Check ledger events file
- [ ] Verify all events present in order
- [ ] Verify timestamps monotonically increase
- [ ] Attempt to modify ledger file (should be prevented)

### API Testing (cURL)

**Approve Fix:**
```bash
curl -X POST http://localhost:8000/api/fixes/42/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plan_tier": "team",
    "approved_by": "user@example.com"
  }'
```

**Reject Fix:**
```bash
curl -X POST http://localhost:8000/api/fixes/42/reject \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plan_tier": "team",
    "rejected_by": "user@example.com",
    "reason": "Introduces breaking changes"
  }'
```

**Apply Fix (Dry Run):**
```bash
curl -X POST http://localhost:8000/api/fixes/42/apply-governed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plan_tier": "team",
    "applied_by": "user@example.com",
    "dry_run": true
  }'
```

**Apply Fix (Real):**
```bash
curl -X POST http://localhost:8000/api/fixes/42/apply-governed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "plan_tier": "team",
    "applied_by": "user@example.com",
    "dry_run": false
  }'
```

**Get Fixes for Run:**
```bash
curl http://localhost:8000/api/fixes/run/run-123 \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🚫 Explicit Non-Goals

Phase 15.1 is intentionally limited to human-governed workflows. The following are **explicitly forbidden** and relegated to future phases:

### Not Implemented (By Design)

**1. Automatic Fix Application**
- ❌ No auto-apply based on confidence scores
- ❌ No auto-apply for "safe" fix categories
- ❌ No background workers applying fixes
- ❌ No cron jobs checking for new fixes

**2. Learning from Approvals**
- ❌ No ML model training on approval history
- ❌ No "smart approval" based on past decisions
- ❌ No approval recommendations
- ❌ No confidence scoring based on user patterns

**3. Batch Operations**
- ❌ No bulk approve (coming in Phase 15.2)
- ❌ No bulk apply
- ❌ No transaction-based multi-fix application

**4. Retroactive Changes**
- ❌ No applying fixes to past runs
- ❌ No modifying historical ledger entries
- ❌ No "replay with fixes" mode

**5. Role-Based Access Control**
- ❌ No team lead approval requirements
- ❌ No multi-stage approval workflows
- ❌ No approval delegation

**6. Billing Integration**
- ❌ No metered fix approvals
- ❌ No usage-based pricing for applied fixes
- ❌ No Stripe integration

---

## 🔮 Future Enhancements

### Phase 15.2: Batch Fix Operations (Enterprise)
- Approve multiple fixes in single transaction
- Bulk rejection with category-based reasons
- Transaction-based multi-fix application with all-or-nothing rollback
- BATCH_FIX_APPROVAL service capability

### Phase 15.3: Advanced Validation
- Pre-apply linting and syntax checking
- Test execution before application
- Dependency conflict detection
- Breaking change analysis

### Phase 15.4: Collaboration Features
- Multi-user approval workflows (team lead + engineer)
- Approval comments and discussions
- Fix review assignments
- Notification system for pending approvals

### Phase 16: Automated Fix Generation
- Generate fixes during analysis phase (currently manual trigger)
- Confidence scoring for automatic proposal
- Context-aware fix suggestions
- Multi-strategy fix proposals

---

## 🔒 Phase Lock Statement

**Phase 15.1 is now LOCKED.**

AGI Engineer can now:
- ✅ Propose fixes for detected issues
- ✅ Accept human approval/rejection with plan enforcement
- ✅ Safely apply approved fixes with validation and rollback
- ✅ Record all actions in immutable ledger with actor attribution
- ✅ Provide complete audit trail for compliance

**Guarantees maintained:**
- ✅ No silent code changes
- ✅ No automatic fix application
- ✅ No background execution
- ✅ No retroactive modifications
- ✅ Complete determinism and reproducibility

**What remains forbidden:**
- ❌ Autonomous code changes without explicit human approval
- ❌ Learning from approval patterns
- ❌ Automatic fix application based on heuristics
- ❌ Batch operations (deferred to Phase 15.2)

**The system is now production-ready for governed fix workflows under explicit human control with complete immutable audit trail.**

---

**Phase 15.1 Complete:** January 16, 2026  
**Status:** 🔒 LOCKED  
**Next Phase:** 15.2 - Batch Fix Operations (Enterprise)
