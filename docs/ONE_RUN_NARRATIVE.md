# One Run Narrative: Walk Through a Real Execution

**Audience:** New engineers, decision-makers who want to see the system in action

**Goal:** Make the system intuitive in 10 minutes by following one complete run from start to finish

---

## The Scenario

A team has a Python codebase with 50K lines of code across 200 files. They want AGI Engineer to scan for code quality issues and apply safe fixes. Let's walk through what happens.

---

## Step 1: Run Creation

**User runs:**
```bash
python3 agi_engineer_v3.py \
  --repo-path ./myproject \
  --analysis-only false \
  --policy production
```

**What happens:**
1. A unique run ID is generated (e.g., `run-2026-01-12-a1b2c3d4`).
2. A directory is created: `~/.agi-engineer/ledger/run-2026-01-12-a1b2c3d4/`.
3. `ledger.json` is written with metadata:
   ```json
   {
     "run_id": "run-2026-01-12-a1b2c3d4",
     "repo_id": "myproject",
     "environment": "DEV",
     "started_at": "2026-01-12T14:00:00Z",
     "ended_at": null,
     "final_state": null,
     "run_policy_id": "production",
     "initiated_by": "CLI"
   }
   ```

**What is recorded in the ledger:**

```
[0] RUN_CREATED
   sequence: 0
   timestamp: 2026-01-12T14:00:00Z
   actor: system
   actor_role: System
   summary: "Run initialized for myproject"
```

**Why this matters:**
- The ledger is now the source of truth. Everything that happens goes into this ledger.
- The ledger cannot be modified after it is created.
- If the ledger creation fails, the system falls back to LEGACY mode (no ledger, but execution continues).

---

## Step 2: Scan & Analysis

**What happens:**
1. Static analysis scanner runs against the codebase.
2. Issues are detected: 47 total issues across 12 categories (unused imports, type mismatches, style violations, etc.).

**What is recorded:**

```
[1] RUN_STARTED
   sequence: 1
   timestamp: 2026-01-12T14:00:05Z
   actor: system
   actor_role: System
   summary: "Execution begun"

[2] ISSUE_DETECTED (repeated for each issue, shown once here)
   sequence: 2
   timestamp: 2026-01-12T14:00:10Z
   actor: system
   actor_role: System
   summary: "Found 47 issues: F401 (unused import, 18), E501 (line too long, 12), ..."
```

**Why this matters:**
- Every issue is detected and recorded before any decisions are made.
- The count is immutable in the ledger.
- Replay will show the exact same 47 issues in the same sequence.

---

## Step 3: Policy Resolution & Planning

**What happens:**
1. The policy `production` is loaded. It says:
   - "Approve fixes with confidence >= 95% automatically."
   - "Require human approval for fixes with confidence 70–94%."
   - "Reject fixes with confidence < 70%."
2. The system plans which issues can be fixed:
   - 18 unused imports → confidence 98% → automatic approval
   - 12 line-too-long → confidence 75% → needs human approval
   - 17 others → confidence < 70% → rejected
3. The plan is created: fix 18 unused imports automatically, flag 12 for human review.

**What is recorded:**

```
[3] POLICY_RESOLVED
   sequence: 3
   timestamp: 2026-01-12T14:00:15Z
   actor: system
   actor_role: System
   payload_ref: "policy-production-v1-2026-01-12"
   summary: "Production policy resolved; 18 auto-fixable, 12 need approval, 17 rejected"

[4] PLAN_CREATED
   sequence: 4
   timestamp: 2026-01-12T14:00:16Z
   actor: system
   actor_role: System
   summary: "Plan created: Fix 18 issues with high confidence, escalate 12"
```

**Why this matters:**
- Policy is recorded, so you can audit which policy was applied to which run.
- The plan is immutable; if it changes later, the change is a new event, not a modification.

---

## Step 4: Human Review & Approval (30 minutes later)

**What happens:**
1. A human engineer receives a notification to review the plan.
2. They review the 12 issues that need manual approval.
3. They decide: "Approve the 12 line-too-long fixes. They look safe."
4. They click "Approve" in the dashboard.

**What is recorded:**

```
[5] PLAN_APPROVED
   sequence: 5
   timestamp: 2026-01-12T14:30:00Z
   actor: "alice@company.com"
   actor_role: "Human"
   summary: "Human approved plan; 12 line-too-long fixes approved"
```

**Why this matters:**
- The approval is recorded with the specific human and timestamp.
- If something goes wrong later, you can see exactly who approved it and when.
- The approval is immutable. Alice cannot retroactively claim she didn't approve it.

---

## Step 5: Safety Checks

**What happens:**
1. The system performs safety checks:
   - Does the fix violate the production policy? No.
   - Will the fix break existing tests? Runs test suite against proposed fixes. All pass.
   - Is the fix deterministic? Yes, it's a straightforward fix.
2. All checks pass.

**What is recorded:**

```
[6] SAFETY_CHECK_PASSED
   sequence: 6
   timestamp: 2026-01-12T14:30:05Z
   actor: system
   actor_role: System
   policy_ref: "policy-production-v1"
   summary: "Safety checks passed; fixes are deterministic and policy-compliant"
```

**Why this matters:**
- The safety check is recorded. If the fix causes a problem later, you can see that safety checks were run and passed.
- If safety checks had *failed*, the system would emit `SAFETY_CHECK_FAILED` and abort the run. The failure would be recorded.
- No silent failures. The ledger tells you if safety was checked or not.

---

## Step 6: Fixes Applied

**What happens:**
1. The system applies the fixes:
   - 18 unused imports are removed.
   - 12 line-too-long violations are fixed (by wrapping or refactoring).
2. Each fix is applied in sequence and recorded.

**What is recorded:**

```
[7] FIX_APPLIED
   sequence: 7
   timestamp: 2026-01-12T14:30:10Z
   actor: system
   actor_role: System
   summary: "Removed unused import: collections in utils.py"

[8] FIX_APPLIED
   sequence: 8
   timestamp: 2026-01-12T14:30:11Z
   actor: system
   actor_role: System
   summary: "Removed unused import: typing_extensions in models.py"

... (16 more FIX_APPLIED events) ...

[24] FIX_APPLIED
   sequence: 24
   timestamp: 2026-01-12T14:30:25Z
   actor: system
   actor_role: System
   summary: "Wrapped long line in handler.py (121 chars → 100 chars)"
```

**Why this matters:**
- Every fix is recorded as a separate event with a timestamp and description.
- If a fix causes a problem, you can see exactly what was fixed and when.
- Replay will apply the same fixes in the same order and produce the same result.

---

## Step 7: Engineering Decision Report (EDR)

**What happens:**
1. The system generates an EDR summarizing the run.
2. The EDR includes:
   - Run metadata (ID, repo, start/end time, duration).
   - Issues detected (47 total, 30 fixed, 17 rejected).
   - Safety assessment (confidence: 95%, risk: low).
   - Fixes applied (with details for each).
   - Rollback instructions (how to revert the changes).

**What is recorded:**

```
[25] EDR_FINALIZED
   sequence: 25
   timestamp: 2026-01-12T14:30:26Z
   actor: system
   actor_role: System
   payload_ref: "edr-2026-01-12-a1b2c3d4"
   summary: "Engineering Decision Report finalized; 30 fixes applied, 95% confidence"
```

The EDR itself is stored separately (in `~/.agi-engineer/edr/<run-id>.json`), but the ledger records that it was finalized and includes a reference to it.

**Why this matters:**
- The EDR is linked to the run via the ledger event.
- The EDR is immutable once finalized.
- If someone later claims "the EDR said this was unsafe," you can verify exactly what the EDR said at that time.

---

## Step 8: Run Completion & Ledger Sealing

**What happens:**
1. All fixes have been applied.
2. The run is complete.
3. The system emits a terminal event and seals the ledger.

**What is recorded:**

```
[26] RUN_COMPLETED
   sequence: 26
   timestamp: 2026-01-12T14:30:30Z
   actor: system
   actor_role: System
   summary: "Run finished with state: COMPLETE"
```

The `ledger.json` is updated to include:
```json
{
  "run_id": "run-2026-01-12-a1b2c3d4",
  "repo_id": "myproject",
  "environment": "DEV",
  "started_at": "2026-01-12T14:00:00Z",
  "ended_at": "2026-01-12T14:30:30Z",
  "final_state": "COMPLETE",
  "run_policy_id": "production",
  "initiated_by": "CLI"
}
```

The `events.jsonl` file now contains 27 lines (events 0-26), and no more events can be appended. The ledger is sealed.

**Why this matters:**
- The ledger is now immutable. No changes, no edits, no retroactive modifications.
- The final state is recorded as `COMPLETE`.
- If something goes wrong later, the ledger is the permanent record of what happened.

---

## The Complete Timeline in Ledger Form

Here is the complete event sequence for this run:

```
[0] RUN_CREATED (seq=0)
[1] RUN_STARTED (seq=1)
[2] ISSUE_DETECTED (seq=2, count=47)
[3] POLICY_RESOLVED (seq=3, policy=production-v1)
[4] PLAN_CREATED (seq=4)
[5] PLAN_APPROVED (seq=5, actor=alice@company.com)
[6] SAFETY_CHECK_PASSED (seq=6)
[7-24] FIX_APPLIED (seq=7-24, 18 fixes)
[25] EDR_FINALIZED (seq=25, edr_id=edr-2026-01-12-a1b2c3d4)
[26] RUN_COMPLETED (seq=26, final_state=COMPLETE)
```

**Total: 27 events, 30 seconds of wall-clock time, 100% deterministic, 100% auditable.**

---

## What Cannot Happen

**Scenario 1: Silent failure**
- If a fix fails partway through, the system aborts and records `FIX_FAILED`.
- No fixes are applied after the failure.
- The ledger remains sealed with `final_state=INCOMPLETE`.
- The failure is visible in the ledger.

**Scenario 2: Retroactive approval**
- Alice cannot go back and remove her approval from event [5].
- Alice cannot claim she didn't approve the fixes.
- Event [5] is immutable. If Alice wants to reverse the decision, she must emit a new event `RUN_ABORTED`.

**Scenario 3: Missing policy**
- If the policy `production` cannot be found, the system detects an invariant violation.
- The violation is recorded in the replay state.
- The run still completes, but the invariant violation is flagged during audit.

**Scenario 4: Out-of-order events**
- Events are sequence-checked during replay.
- If event [5] appears before event [4], the replay engine detects a sequence gap and records an invariant violation.

**Scenario 5: Hidden modifications**
- Someone cannot add a "secret" event to the ledger after the fact.
- The ledger file format is JSON. Any tampering changes the cryptographic hash (in production, you would add signatures).
- Replay will detect the tampering.

---

## Audit: Answering "What Happened?"

**Six months later, an auditor asks: "What exactly did this run do on Jan 12?"**

The answer is deterministic and provable:

```bash
python3 agent/run_inspect.py run-2026-01-12-a1b2c3d4
```

Output:
```json
{
  "run_id": "run-2026-01-12-a1b2c3d4",
  "final_state": "COMPLETE",
  "total_events": 27,
  "duration": 30.5,
  "fixes": { "count": 30 },
  "decisions": { "plan_approved": true },
  "safety": { "passed": true },
  "edr_id": "edr-2026-01-12-a1b2c3d4",
  "audit_preview": [
    { "seq": 0, "event": "RUN_CREATED" },
    { "seq": 5, "event": "PLAN_APPROVED", "actor": "alice@company.com" },
    ...
  ]
}
```

**Replay to verify determinism:**

```bash
python3 -c "
import sys
sys.path.insert(0, 'agent')
from run_replay import replay_run
state = replay_run('run-2026-01-12-a1b2c3d4')
print('Invariants:', state.invariant_violations)
print('Deterministic:', len(state.invariant_violations) == 0)
"
```

Output:
```
Invariants: []
Deterministic: True
```

---

## Why This Is Different From "Just Looking at Logs"

| With Logs | With Ledger + Replay |
|-----------|---------------------|
| Auditor reads logs and hopes they're complete. | Auditor runs inspection and gets the complete, immutable timeline. |
| Logs may have been rotated or deleted. | Ledger is permanently stored and cannot be deleted. |
| Logs may be ambiguous (was the issue fixed or not?). | Ledger is unambiguous (FIX_APPLIED event is definitive). |
| To verify, auditor must re-read logs and reconstruct in their head. | To verify, auditor replays and gets mathematical proof of determinism. |
| Blame is unclear (who made the decision?). | Blame is clear (actor is recorded in each event). |

---

## Conclusion: One Run, Fully Auditable

This is what a run looks like in AGI Engineer:

1. **Created:** Immutable ledger initialized.
2. **Executed:** 27 events, deterministically sequenced.
3. **Governed:** Policy applied, human approval recorded, safety checked.
4. **Recorded:** Every decision, actor, and timestamp in the ledger.
5. **Sealed:** Terminal event finalizes the run; no edits possible.
6. **Auditable:** Run can be replayed, inspected, and verified at any time.

This is the foundation of trust. Not trust in the AI. Trust in the process.
