# Failure and Override Story: Why Safe Failure Is the Design

**Audience:** Risk managers, compliance teams, skeptical engineers

**Goal:** Prove that the system is *safer when it fails* than when it pretends to succeed

---

## The Core Principle

**Safe systems fail loudly. Unsafe systems fail silently.**

AGI Engineer is designed to fail loudly. Every failure is recorded in the immutable ledger. Overrides do not erase history. Silence is impossible.

---

## Failure Scenario 1: A Fix Breaks Tests

### What Happens

1. The system proposes to remove an unused import.
2. The system applies the fix.
3. The test suite runs against the fixed code.
4. **Tests fail.** The import was actually used by another module dynamically.

### Traditional Tool Response (Silent Failure Risk)

```
User sees: "Fix applied successfully."
Logs say: "Test passed" (but logs are incomplete).
Reality: The fix broke something in production.
Discovery: 2 weeks later, in production.
Blame: Unclear. Was it the tool? The human reviewer? The test?
```

### AGI Engineer Response (Loud Failure, Recorded)

**What is recorded in the ledger:**

```
[0] RUN_CREATED
[1] RUN_STARTED
[2] ISSUE_DETECTED
[3] PLAN_CREATED
[4] PLAN_APPROVED (actor=alice@company.com)
[5] SAFETY_CHECK_STARTED
[6] SAFETY_CHECK_FAILED
   actor: system
   payload_ref: "test-failure-reason"
   summary: "Test suite failed after fix: ImportError in async_handler.py"
[7] RUN_ABORTED
   actor: system
   final_state: INCOMPLETE
```

**What the user sees:**

```
Run INCOMPLETE. Safety checks failed.
Reason: ImportError in async_handler.py
No fixes were applied. Codebase is unchanged.
```

**What happens next:**

1. The fix is not applied to the main branch.
2. The ledger records the failure with full details.
3. The human can inspect the fix, improve it, and resubmit.
4. Or the human can accept the INCOMPLETE status and move on.

### Why This Is Safer

- **No silent failures.** The user knows the fix was rejected.
- **Blame is clear.** The safety check failed; this is a system-level decision, not human error.
- **Rollback is automatic.** No fixes were applied, so there is nothing to rollback.
- **The failure is auditable.** Six months later, compliance can see exactly where and why the fix was rejected.

---

## Failure Scenario 2: Safety Policy Blocks the Fix

### What Happens

1. The system proposes a fix with 72% confidence.
2. The production policy says: "Confidence must be >= 95% for auto-approval, or >= 70% with human approval."
3. The fix meets the policy threshold (72% >= 70%), but human approval is required.
4. No human approves the fix within the timeout (24 hours).

### Traditional Tool Response (Implicit Default Risk)

```
Tool assumes: "If approval isn't explicitly provided, assume no-op."
Result: The issue is silently not fixed.
User expectation: "I thought the system would auto-fix this?"
Reality: No one knows if the fix was attempted, rejected, or forgotten.
```

### AGI Engineer Response (Explicit Decision, Recorded)

**What is recorded in the ledger:**

```
[0] RUN_CREATED
[1] RUN_STARTED
[2] ISSUE_DETECTED (1 issue, confidence=72%)
[3] PLAN_CREATED
   summary: "Plan requires human approval (confidence 72% < 95%)"
[4] PLAN_APPROVAL_TIMEOUT
   actor: system
   timeout_seconds: 86400
   summary: "No human approval received within 24 hours"
[5] RUN_INCOMPLETE
   final_state: INCOMPLETE
```

**What the user sees:**

```
Run INCOMPLETE. Reason: No approval received.
Issue was detected but not fixed (requires human approval).
Timeframe: Approval window was 24 hours.
Action: Resubmit with explicit approval, or reject the plan.
```

**What happens next:**

1. The user receives a notification: "Fix requires approval."
2. The user can review the fix, approve it, and the run completes.
3. Or the user rejects the fix, and the run is marked ABORTED.
4. Or the user ignores it, and the run remains INCOMPLETE (visible as incomplete).

### Why This Is Safer

- **No implicit defaults.** The system does not assume "no approval = no action."
- **Decision is explicit and recorded.** The user either approves or rejects; both are recorded.
- **Timeout is bounded.** After 24 hours, the system does not hang; it explicitly times out and records it.
- **The incompleteness is visible.** The user can see that fixes are pending approval, not silently skipped.

---

## Failure Scenario 3: Human Override (Deliberate Reversal)

### What Happens

1. A run completes successfully: 20 fixes applied, all approved, all safe.
2. **Three days later**, someone discovers a performance regression in production.
3. The regression is traced to one of the fixes.
4. **The human decides to revert all fixes and block the policy.**

### Traditional Tool Response (History Overwrite Risk)

```
Admin action: "Delete the run from the audit log. Pretend it didn't happen."
Result: The fix is reverted (good), but the audit trail is erased (bad).
Six months later, compliance asks: "Why was that policy changed?"
Answer: Lost to history. No one remembers.
```

### AGI Engineer Response (Override Is Recorded, History Is Preserved)

**Original run ledger (sealed, immutable):**

```
[0] RUN_CREATED (run-original)
...
[18] RUN_COMPLETED
  final_state: COMPLETE
```

**This ledger is never modified. It remains in `~/.agi-engineer/ledger/run-original/`.**

**New override run ledger (separate, immutable):**

```
[0] RUN_CREATED (run-override)
[1] RUN_STARTED
[2] HUMAN_OVERRIDE_INITIATED
   actor: admin@company.com
   summary: "Performance regression in production traced to run-original"
[3] PRIOR_RUN_REFERENCED
   payload_ref: "run-original"
   summary: "Reverting all changes from run-original"
[4] FIX_REVERTED (for each fix in run-original)
   payload_ref: "run-original"
   sequence_from_prior: 14  (e.g., if fix was in event [14])
   summary: "Reverted fix: Remove unused import from utils.py"
[5] POLICY_OVERRIDE_APPLIED
   actor: admin@company.com
   policy_change: "production → production_v2_strict"
   summary: "Policy tightened to require 98% confidence"
[6] RUN_COMPLETED
   final_state: COMPLETE
```

**What the user sees:**

```
Original run (run-original): COMPLETE, 20 fixes applied
Override run (run-override): COMPLETE, 20 fixes reverted, policy updated

Audit trail shows:
- When the original fixes were applied
- Why they were reverted (performance regression)
- Who made the override decision (admin@company.com)
- When the override happened (timestamp)
- What policy changed as a result
```

**What happens next:**

1. The original codebase is restored (reverted fixes).
2. The policy is tightened (future runs require 98% confidence).
3. **Both decisions are permanent and auditable.**
4. Six months later, compliance asks why the policy changed. Answer: **It's in the ledger.**

### Why This Is Safer

- **History is never erased.** The original run remains in the ledger, unchanged.
- **Override is explicit and reasoned.** The admin's decision, actor, and justification are recorded.
- **Causality is preserved.** Future audits can trace the policy change back to the original performance regression.
- **Accountability is clear.** If the override was a mistake, it is recorded as a mistake, not erased and pretended away.

---

## Failure Scenario 4: Invariant Violation (Structural Corruption)

### What Happens

1. A bug causes event sequencing to go wrong.
2. Events are recorded out of order: [0], [1], [3], [2], [4] instead of [0], [1], [2], [3], [4].
3. The replay engine detects the sequence gap.

### Traditional Tool Response (Undetectable Corruption)

```
Logs contain events out of order.
Replay produces wrong results.
No one notices until something breaks in production.
Blame is impossible (corruption is invisible).
```

### AGI Engineer Response (Violation Is Detected and Recorded)

**Replay detects the violation:**

```python
state = replay_run("run-corrupted")
print(state.invariant_violations)
# Output:
# [
#   "sequence-gap-or-out-of-order: expected 2, found 3",
#   "sequence-gap-or-out-of-order: expected 3, found 2"
# ]
```

**The run is still inspected, but flagged:**

```json
{
  "run_id": "run-corrupted",
  "final_state": "COMPLETE",
  "invariants": {
    "violations": [
      "sequence-gap-or-out-of-order: expected 2, found 3"
    ],
    "violation_count": 1
  },
  "trust_level": "LOW"  // System can infer trust level from violations
}
```

**What happens next:**

1. Compliance audit picks up the violation.
2. The system is investigated for the bug that caused the sequence corruption.
3. The bug is fixed, and all future runs have correct sequencing.
4. **The corrupted run is preserved as evidence**, not deleted or hidden.

### Why This Is Safer

- **Corruption is detectable.** Invariant checks catch structural problems.
- **The violation is recorded.** The problem is visible to audits, not hidden.
- **Compliance can investigate.** They know the run is suspect and can decide to discard it or investigate further.
- **Future runs are not affected.** The bug fix ensures future runs don't have the same problem.

---

## Failure Scenario 5: Ledger Creation Fails (Disk Full, Permissions)

### What Happens

1. The system tries to create the ledger.
2. The disk is full, or permissions are denied, or the network is down.
3. Ledger creation fails.

### Traditional Tool Response (Silent Graceful Degradation Risk)

```
System logs: "Warning: Ledger creation failed."
System behavior: Continues without ledger (LEGACY mode).
User expectation: "The system is running normally."
Reality: No ledger, no audit trail, no replay capability.
User discovery: Months later, during compliance audit: "Where's the ledger?"
```

### AGI Engineer Response (Explicit LEGACY Mode, Recorded)

**What is logged:**

```
[WARN] Ledger creation failed for run-xyz: Disk full
[INFO] Operating in LEGACY mode (no ledger)
[INFO] Execution will continue; audit trail will not be available
```

**What the user sees:**

```
Run completed in LEGACY mode (no ledger).
Audit trail is not available.
Reason: Disk full at ~/.agi-engineer/ledger/

Actions:
- Free up disk space and retry
- Accept the run without ledger (not compliance-ready)
```

**What happens next:**

1. The user is explicitly informed that the ledger is unavailable.
2. The user can decide whether to accept the run without audit trail.
3. In regulated environments, this would typically trigger a retry or escalation.
4. **The failure is visible; not silent.**

### Why This Is Safer

- **Failure is visible.** The user knows the ledger is not available, not assuming it is working.
- **LEGACY mode is documented.** The system does not silently degrade; it explicitly states it is in legacy mode.
- **Decision is explicit.** The user decides whether to accept the run without ledger or retry.
- **The failure is recoverable.** Fix the disk issue, retry the run, and ledger is created.

---

## Safety Rules Across All Failures

### Rule 1: Fail Visibly or Abort

- If something goes wrong, the system records it in the ledger and aborts.
- Silence is never an option.
- The user is always informed of the failure.

### Rule 2: No Retroactive Changes

- If a failure is recorded, it cannot be erased or edited.
- Overrides are new events, not modifications of past events.
- History is immutable.

### Rule 3: Explicit > Implicit

- If a decision is unclear, the system does not assume a default.
- Instead, the system records the ambiguity and aborts (or marks incomplete).
- The user must explicitly decide what to do next.

### Rule 4: Invariants Are Not Suggestions

- If an invariant is violated, it is recorded and flagged.
- Violations do not retroactively corrupt past events.
- The audit system can decide how to treat violations (flag as suspect, discard, investigate).

### Rule 5: Human Authority Is Preserved

- Humans can override the system, but overrides are recorded.
- Overrides do not erase history; they create new history.
- Accountability is preserved.

---

## Comparison: Failure Handling

| Scenario | Traditional Tool | AGI Engineer |
|----------|-----------------|--------------|
| Fix breaks tests | Silent failure (discovered in production) | Safety check catches it; run aborts with clear reason |
| No approval within timeout | Implicit default (unclear what happened) | Explicit timeout event; run marked INCOMPLETE |
| Performance regression | Revert manually; audit trail is lost | Override recorded; original run preserved; causality auditable |
| Sequence corruption | Undetectable; causes wrong replay | Invariant violation detected; flagged for audit |
| Ledger creation fails | LEGACY mode, silently assumed | LEGACY mode, explicitly stated; user must acknowledge |

---

## Conclusion: Failure Is Safety

In traditional systems, failure is a bug. The system tries to hide it, work around it, or retry silently.

In AGI Engineer, **failure is a feature.** The system records it, makes it visible, preserves history, and forces explicit decisions.

This is not faster. It is not more convenient. But it is safer. And for production systems, safer is better.

---

## What This Means for Trust

**Question: Can I trust this system?**

**Answer: You don't have to.**

Instead, you can verify it. Every run is auditable. Every failure is recorded. Every override is preserved. Every decision can be replayed.

Trust is replaced by proof. And proof is stronger than trust.
