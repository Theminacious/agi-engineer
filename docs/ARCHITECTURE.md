# AGI Engineer — Technical Architecture

**A deterministic, governed autonomous engineering system built on immutable audit trails.**

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Execution vs Governance Separation](#execution-vs-governance-separation)
3. [Why Ledger ≠ Logs](#why-ledger--logs)
4. [Why Replay > Monitoring](#why-replay--monitoring)
5. [Why the UI Cannot Mutate State](#why-the-ui-cannot-mutate-state)
6. [Authority Flow Diagram](#authority-flow-diagram)
7. [Component Responsibilities](#component-responsibilities)
8. [Event Lifecycle](#event-lifecycle)
9. [Invariant System](#invariant-system)
10. [Deterministic Replay Mechanics](#deterministic-replay-mechanics)
11. [Query & Inspection APIs](#query--inspection-apis)
12. [Failure Modes & Safety](#failure-modes--safety)
13. [Design Tradeoffs](#design-tradeoffs)
14. [Non-Goals](#non-goals)

---

## System Overview

AGI Engineer is **not** a chatbot, agent framework, or developer replacement. It is a **governed execution system** that separates:

- **Execution** (AI-driven, fallible, non-authoritative)
- **Governance** (policy-driven, immutable, authoritative)

Every action is recorded in an **immutable run ledger**, enabling:
- **Deterministic replay** (reconstruct state from events)
- **Human auditability** (verify without trusting AI)
- **Compliance-ready traces** (prove what happened, when, and who approved it)

### Core Architectural Principle

> **"If it's not in the ledger, it didn't happen."**

The ledger is the **single source of truth**. All other systems (UI, queries, monitoring) are secondary observations.

---

## Execution vs Governance Separation

### The Fundamental Split

Traditional autonomous tools conflate execution and authority:

```
┌─────────────────────────────────────────┐
│     Traditional Autonomous Tool         │
│                                         │
│  • AI decides what to fix               │
│  • AI executes the fix                  │
│  • AI records that it worked            │
│                                         │
│  Problem: AI is judge, jury, executor   │
└─────────────────────────────────────────┘
```

AGI Engineer separates these concerns:

```
┌─────────────────────────────────────────┐
│         EXECUTION LAYER (Fallible)      │
│  • Scanner proposes issues              │
│  • Planner proposes fixes               │
│  • Fixer attempts application           │
│                                         │
│  ↓ Events emitted (proposals only)     │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       GOVERNANCE LAYER (Authority)      │
│  • Ledger records events                │
│  • Policies approve/reject              │
│  • Humans override                      │
│  • Terminal states seal decisions       │
└─────────────────────────────────────────┘
```

### Why This Matters

| Aspect | Traditional | AGI Engineer |
|--------|------------|--------------|
| **Authority** | Execution holds authority | Governance holds authority |
| **Trust** | "Trust the AI to be smart" | "Verify the ledger; replay the run" |
| **Failure** | Lost logs, unclear blame | Ledger persists, blame recorded |
| **Replay** | Impossible (non-deterministic) | Guaranteed (deterministic) |
| **Auditability** | Post-hoc (read logs) | Pre-action (approve before execution) |

### Execution Can Fail; Governance Cannot

- **Execution crashes?** Ledger persists. Replay shows where execution stopped.
- **AI hallucinates?** Approval event is missing. Replay detects this.
- **Fix breaks code?** Safety check event is recorded. Blame is clear.

**Principle:** Execution is subordinate to governance. Execution proposes; governance authorizes.

---

## Why Ledger ≠ Logs

### The Fundamental Difference

**Logs** are secondary observations. They record what happened as a side effect of execution.

**Ledgers** are primary authority. They define what happened. Execution reads from the ledger to know what to do next.

### Comparison Table

| Property | Logs | Ledger |
|----------|------|--------|
| **Purpose** | Debugging, monitoring | Source of truth |
| **Mutability** | Can be truncated, rotated, deleted | Immutable, append-only |
| **Authority** | Secondary (derived from execution) | Primary (defines execution) |
| **Replay** | Non-deterministic (logs may be incomplete) | Deterministic (events are complete) |
| **Structure** | Unstructured text | Structured JSON (schema-validated) |
| **Sequence** | Timestamp-ordered (may conflict) | Sequence-ordered (no ambiguity) |
| **Trust** | Trust that logs are complete | Verify via replay |

### Example: Logs vs Ledger

**System logs (traditional):**
```
2026-01-12 10:00:00 INFO: Starting run
2026-01-12 10:01:15 INFO: Found 47 issues
2026-01-12 10:01:30 INFO: Plan created
2026-01-12 10:02:00 INFO: Applying fix 1
...
(logs may be truncated, lost, or non-deterministic)
```

**Run ledger (AGI Engineer):**
```jsonl
{"sequence":0,"event_type":"RUN_CREATED","timestamp":"2026-01-12T10:00:00Z",...}
{"sequence":1,"event_type":"ISSUE_DETECTED","timestamp":"2026-01-12T10:01:15Z","payload":{"count":47},...}
{"sequence":2,"event_type":"PLAN_CREATED","timestamp":"2026-01-12T10:01:30Z",...}
{"sequence":3,"event_type":"PLAN_APPROVED","actor":"alice@company.com","actor_role":"Human",...}
{"sequence":4,"event_type":"FIX_APPLIED","payload":{"rule":"F401","file":"main.py"},...}
...
{"sequence":25,"event_type":"RUN_COMPLETED","timestamp":"2026-01-12T10:05:30Z",...}
```

**Ledger guarantees:**
- **Immutable:** Once written, events cannot be modified or deleted.
- **Sequenced:** Events have deterministic order (0, 1, 2, ...).
- **Complete:** All authoritative state is recorded (approvals, overrides, failures).
- **Replayable:** Applying events in sequence order reconstructs state deterministically.

### When Logs Disagree with Ledger

**Rule:** The ledger wins.

If logs say "fix applied" but ledger has no `FIX_APPLIED` event, the fix **did not happen**. The absence of an event is itself authoritative.

---

## Why Replay > Monitoring

### The Trust Problem with Monitoring

Monitoring observes execution in real-time. It answers: *"What is happening right now?"*

But monitoring cannot answer:
- *"Why did execution take this path?"*
- *"Was approval recorded before fixes were applied?"*
- *"If I re-run this, will I get the same result?"*

### Replay as Proof

Replay reconstructs execution from events. It answers: *"Given these events, what state MUST result?"*

Replay provides:
- **Deterministic verification:** Re-run produces identical state.
- **Causal tracing:** Every decision has a recorded cause (approval, policy, override).
- **Invariant checking:** Detect sequence gaps, missing approvals, terminal mismatches.

### Comparison Table

| Property | Monitoring | Replay |
|----------|-----------|--------|
| **When** | Real-time (during execution) | Post-execution (any time) |
| **Trust** | Trust that metrics are accurate | Verify by replaying events |
| **State** | Observes current state | Reconstructs state deterministically |
| **Causality** | Correlational (may miss causes) | Causal (events record decisions) |
| **Failure detection** | Alerts on anomalies | Detects invariant violations |
| **Rollback** | Cannot undo execution | Can replay to any event |

### Example: Monitoring vs Replay

**Monitoring dashboard:**
```
✅ Run completed
✅ 18 fixes applied
✅ No errors
```

**Replay verification:**
```
✅ Event sequences contiguous (0-25)
✅ Approval recorded before fixes (seq=3 < seq=4)
✅ Safety check passed before fixes (seq=5)
✅ Terminal event matches ledger state (RUN_COMPLETED + COMPLETE)
✅ No sequence gaps
✅ No invariant violations
```

**What replay proves that monitoring cannot:**
- Approval was recorded (not assumed).
- Safety check preceded fixes (not just "no errors").
- Sequence is causally correct (approval → safety → fixes → completion).
- State is deterministic (replay produces same result).

---

## Why the UI Cannot Mutate State

### The Hidden Mutation Problem

In traditional systems, UIs can create runs, approve plans, or trigger actions. This creates hidden mutation paths:

```
User → UI → Database → Execution
```

Problem: If the UI can mutate state, the ledger is not authoritative. Events can be created retroactively, approvals can be fabricated, and blame becomes unclear.

### AGI Engineer's Design

The UI is **read-only**. It can only query the ledger.

```
User → CLI → Orchestrator → Ledger
                              ↓ (read-only)
                             UI
```

**All mutations go through the orchestrator.** The orchestrator emits events, which are written to the ledger. The UI observes the ledger but cannot change it.

### What This Prevents

| Violation | Traditional | AGI Engineer |
|-----------|------------|--------------|
| **Retroactive approval** | UI can create approval event after fix | Impossible (UI cannot write events) |
| **Hidden overrides** | UI can bypass policies | Impossible (UI cannot mutate ledger) |
| **Ambiguous blame** | UI and CLI both create runs | Impossible (only CLI can create runs) |
| **Non-deterministic replay** | UI state may differ from ledger | Impossible (UI reads from ledger) |

### Design Principle

> **"The UI is powerless. Authority flows through the ledger."**

If the UI crashes, nothing changes. If the ledger is corrupted, the UI shows errors. The UI is a **secondary observer**, not a primary actor.

---

## Authority Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER / DEVELOPER                        │
│         (initiates run via CLI command)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CLI (agi_engineer_v3.py)                       │
│  • Validates arguments                                      │
│  • Initializes ledger                                       │
│  • Invokes orchestrator                                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            ORCHESTRATOR (Execution Controller)              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Scanner (agent/analyze.py)                           │  │
│  │ • Detects issues (Ruff, ESLint)                     │  │
│  │ • Emits: ISSUE_DETECTED                             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Classifier (agent/rule_classifier.py)                │  │
│  │ • Categorizes rules (safe, review, suggestions)     │  │
│  │ • Emits: POLICY_RESOLVED                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Planner (agent/fix_orchestrator.py)                 │  │
│  │ • Creates fix plan                                   │  │
│  │ • Emits: PLAN_CREATED                               │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Approval (Human or Policy)                           │  │
│  │ • Approves or rejects plan                          │  │
│  │ • Emits: PLAN_APPROVED or PLAN_REJECTED             │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Safety Checker (agent/safety_checker.py)            │  │
│  │ • Validates fixes are safe                          │  │
│  │ • Emits: SAFETY_CHECK_PASSED or SAFETY_CHECK_FAILED │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Fixer (applies fixes)                                │  │
│  │ • Applies approved fixes                            │  │
│  │ • Emits: FIX_APPLIED                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ EDR Generator (agent/edr.py)                        │  │
│  │ • Produces Engineering Decision Report              │  │
│  │ • Emits: EDR_FINALIZED                              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Terminal Sealer                                      │  │
│  │ • Seals run with terminal state                     │  │
│  │ • Emits: RUN_COMPLETED, RUN_ABORTED, RUN_REJECTED   │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ (emit events ONLY)
┌─────────────────────────────────────────────────────────────┐
│           IMMUTABLE RUN LEDGER (Authority)                  │
│                                                              │
│  Location: ~/.agi-engineer/ledger/{run_id}/                │
│                                                              │
│  Files:                                                     │
│  • ledger.json (metadata: run_id, started_at, final_state) │
│  • events.jsonl (append-only event stream)                 │
│                                                              │
│  Guarantees:                                                │
│  • Append-only (no edits, no deletes)                      │
│  • Sequence-ordered (0, 1, 2, ...)                         │
│  • Schema-validated (all events follow EventSchema)        │
│  • Terminal-sealed (one terminal event per run)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ (read-only access)
┌─────────────────────────────────────────────────────────────┐
│          QUERY / REPLAY / INSPECT MODULES                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Query API (agent/run_ledger_query.py)               │  │
│  │ • get_full_timeline(run_id)                         │  │
│  │ • get_run_summary(run_id)                           │  │
│  │ • get_events_by_phase(run_id, phase)                │  │
│  │ • get_events_by_type(run_id, event_type)            │  │
│  │ • get_audit_view(run_id)                            │  │
│  │ • trace_causality(run_id, payload_ref)              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Replay Engine (agent/run_replay.py)                 │  │
│  │ • replay_run(run_id) → ReplayRunState               │  │
│  │ • Applies events in sequence order                   │  │
│  │ • Checks invariants (gaps, terminal, consistency)   │  │
│  │ • Produces deterministic state reconstruction       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Inspection (agent/run_inspect.py)                   │  │
│  │ • inspect_run(run_id) → JSON report                 │  │
│  │ • Combines replay + query into comprehensive view   │  │
│  │ • Includes timeline, decisions, fixes, safety, edr  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ (read-only)
┌─────────────────────────────────────────────────────────────┐
│              UI / REPORTS / AUDIT TOOLS                     │
│  • Dashboard (read-only)                                    │
│  • Reports (PDF, JSON)                                      │
│  • Compliance exports                                       │
│  • Third-party verification tools                           │
│                                                              │
│  Constraint: Cannot write to ledger                         │
└─────────────────────────────────────────────────────────────┘
```

### Key Authority Flow Rules

1. **User → CLI → Orchestrator → Ledger**  
   All mutations flow through this path. No shortcuts.

2. **Ledger → Query/Replay/Inspect → UI**  
   All reads flow from the ledger. UI cannot bypass queries.

3. **UI cannot write events**  
   The UI is a secondary observer, not a primary actor.

4. **Orchestrator cannot read from execution state**  
   State is derived from the ledger, not from runtime variables.

---

## Component Responsibilities

### 1. CLI (agi_engineer_v3.py)

**Role:** Entry point for human users.

**Responsibilities:**
- Validate command-line arguments
- Initialize run ledger (create `ledger.json`)
- Invoke orchestrator
- Report terminal state to user

**Constraints:**
- Cannot bypass orchestrator
- Cannot mutate ledger directly (only via ledger writer)

---

### 2. Orchestrator (Execution Controller)

**Role:** Coordinates execution components.

**Responsibilities:**
- Invoke scanner, classifier, planner, safety checker, fixer
- Emit events to ledger
- Enforce execution sequence (scan → plan → approve → fix)

**Constraints:**
- Cannot decide policy (policy is read from `.agi-engineer.yml`)
- Cannot approve plans (approval comes from human or policy)
- Cannot skip safety checks

---

### 3. Scanner (agent/analyze.py)

**Role:** Detect code issues using linters.

**Responsibilities:**
- Run Ruff (Python) and ESLint (JavaScript/TypeScript)
- Parse linter output into structured issues
- Emit `ISSUE_DETECTED` event

**Constraints:**
- Cannot fix issues (only detects)
- Cannot classify rules (classification is separate)

---

### 4. Classifier (agent/rule_classifier.py)

**Role:** Categorize rules as safe, review-required, or suggestions.

**Responsibilities:**
- Read policy from `.agi-engineer.yml`
- Classify rules (safe, review, suggestions)
- Emit `POLICY_RESOLVED` event

**Constraints:**
- Cannot modify policy (policy is user-defined)
- Cannot auto-approve (approval is separate)

---

### 5. Planner (agent/fix_orchestrator.py)

**Role:** Create fix plan.

**Responsibilities:**
- Group fixes by file and rule
- Determine which fixes are auto-approvable (per policy)
- Emit `PLAN_CREATED` event

**Constraints:**
- Cannot execute fixes (only plans)
- Cannot approve plan (approval is separate)

---

### 6. Approval (Human or Policy)

**Role:** Authorize plan execution.

**Responsibilities:**
- Review plan
- Emit `PLAN_APPROVED` or `PLAN_REJECTED` event

**Constraints:**
- Cannot skip safety checks
- Cannot retroactively approve (approval must precede fixes)

---

### 7. Safety Checker (agent/safety_checker.py)

**Role:** Validate fixes are safe.

**Responsibilities:**
- Record before/after state
- Run tests (if configured)
- Check for regressions
- Emit `SAFETY_CHECK_PASSED` or `SAFETY_CHECK_FAILED` event

**Constraints:**
- Cannot skip checks (safety is mandatory)
- Cannot auto-pass (must actually validate)

---

### 8. Fixer (Applies Fixes)

**Role:** Apply approved, safety-validated fixes.

**Responsibilities:**
- Apply fixes to code
- Emit `FIX_APPLIED` event

**Constraints:**
- Cannot apply unapproved fixes
- Cannot skip safety checks

---

### 9. EDR Generator (agent/edr.py)

**Role:** Produce Engineering Decision Report.

**Responsibilities:**
- Summarize run (issues, fixes, decisions)
- Record rationale for decisions
- Emit `EDR_FINALIZED` event

**Constraints:**
- Cannot modify ledger (only reads)
- Cannot change decisions (only documents)

---

### 10. Terminal Sealer

**Role:** Seal run with terminal state.

**Responsibilities:**
- Emit terminal event (`RUN_COMPLETED`, `RUN_ABORTED`, `RUN_REJECTED`)
- Update `ledger.json` with `final_state`

**Constraints:**
- Cannot reopen sealed runs
- Cannot emit multiple terminal events

---

### 11. Ledger Writer (agent/run_ledger.py)

**Role:** Write events to disk.

**Responsibilities:**
- Append events to `events.jsonl`
- Update `ledger.json` metadata
- Enforce schema validation
- Enforce sequence ordering

**Constraints:**
- Cannot edit existing events
- Cannot delete events
- Cannot reorder events

---

### 12. Query API (agent/run_ledger_query.py)

**Role:** Read-only ledger inspection.

**Responsibilities:**
- Provide helper functions for common queries
- Return JSON-safe results
- Gracefully handle missing ledgers

**Constraints:**
- Cannot mutate ledger
- Cannot execute code (read-only)

---

### 13. Replay Engine (agent/run_replay.py)

**Role:** Deterministic state reconstruction.

**Responsibilities:**
- Apply events in sequence order
- Check invariants (gaps, terminal, consistency)
- Produce `ReplayRunState` (decisions, fixes, safety, edr, overrides)

**Constraints:**
- Cannot modify ledger
- Cannot skip events
- Cannot assume state (must derive from events)

---

### 14. Inspection (agent/run_inspect.py)

**Role:** Comprehensive run report.

**Responsibilities:**
- Combine replay + query results
- Produce JSON-safe report
- Include timeline, decisions, fixes, safety, edr, invariants

**Constraints:**
- Cannot mutate ledger
- Cannot execute code (read-only)

---

### 15. UI (Dashboard)

**Role:** Human-readable run visualization.

**Responsibilities:**
- Display run timeline
- Show issues, fixes, approvals
- Provide export options (PDF, JSON)

**Constraints:**
- **Cannot write to ledger**
- **Cannot create runs**
- **Cannot approve plans**
- **Cannot trigger execution**

---

## Event Lifecycle

### 1. RUN_CREATED (seq=0)

**Trigger:** CLI initializes ledger.

**Payload:**
```json
{
  "sequence": 0,
  "event_type": "RUN_CREATED",
  "timestamp": "2026-01-12T10:00:00Z",
  "actor": "user@company.com",
  "actor_role": "Human",
  "payload": {}
}
```

**State change:** Run begins.

---

### 2. ISSUE_DETECTED (seq=1)

**Trigger:** Scanner completes.

**Payload:**
```json
{
  "sequence": 1,
  "event_type": "ISSUE_DETECTED",
  "timestamp": "2026-01-12T10:01:15Z",
  "actor": "Scanner",
  "actor_role": "System",
  "payload": {
    "count": 47,
    "breakdown": {"F401": 12, "E711": 8, "W291": 27}
  }
}
```

**State change:** Issues recorded.

---

### 3. POLICY_RESOLVED (seq=2)

**Trigger:** Classifier completes.

**Payload:**
```json
{
  "sequence": 2,
  "event_type": "POLICY_RESOLVED",
  "timestamp": "2026-01-12T10:01:20Z",
  "actor": "Classifier",
  "actor_role": "System",
  "payload": {
    "policy": "default-v1",
    "safe_rules": ["F401", "W291"],
    "review_rules": ["E711"]
  }
}
```

**State change:** Policy applied.

---

### 4. PLAN_CREATED (seq=3)

**Trigger:** Planner completes.

**Payload:**
```json
{
  "sequence": 3,
  "event_type": "PLAN_CREATED",
  "timestamp": "2026-01-12T10:01:25Z",
  "actor": "Planner",
  "actor_role": "System",
  "payload": {
    "auto_fixes": 39,
    "manual_fixes": 8
  }
}
```

**State change:** Plan ready for approval.

---

### 5. PLAN_APPROVED (seq=4)

**Trigger:** Human or policy approves.

**Payload:**
```json
{
  "sequence": 4,
  "event_type": "PLAN_APPROVED",
  "timestamp": "2026-01-12T10:01:30Z",
  "actor": "alice@company.com",
  "actor_role": "Human",
  "payload": {}
}
```

**State change:** Fixes authorized.

---

### 6. SAFETY_CHECK_PASSED (seq=5)

**Trigger:** Safety checker completes.

**Payload:**
```json
{
  "sequence": 5,
  "event_type": "SAFETY_CHECK_PASSED",
  "timestamp": "2026-01-12T10:01:45Z",
  "actor": "SafetyChecker",
  "actor_role": "System",
  "payload": {
    "checks_run": ["syntax", "imports", "regressions"],
    "all_passed": true
  }
}
```

**State change:** Fixes validated.

---

### 7. FIX_APPLIED (seq=6-44)

**Trigger:** Fixer applies each fix.

**Payload:**
```json
{
  "sequence": 6,
  "event_type": "FIX_APPLIED",
  "timestamp": "2026-01-12T10:02:00Z",
  "actor": "Fixer",
  "actor_role": "System",
  "payload": {
    "file": "main.py",
    "rule": "F401",
    "description": "Remove unused import 'os'"
  }
}
```

**State change:** Code modified.

---

### 8. EDR_FINALIZED (seq=45)

**Trigger:** EDR generator completes.

**Payload:**
```json
{
  "sequence": 45,
  "event_type": "EDR_FINALIZED",
  "timestamp": "2026-01-12T10:04:30Z",
  "actor": "EDRGenerator",
  "actor_role": "System",
  "payload": {
    "edr_id": "edr-2026-01-12-abc123",
    "path": "~/.agi-engineer/edrs/edr-2026-01-12-abc123.md"
  }
}
```

**State change:** EDR available.

---

### 9. RUN_COMPLETED (seq=46)

**Trigger:** Orchestrator finishes successfully.

**Payload:**
```json
{
  "sequence": 46,
  "event_type": "RUN_COMPLETED",
  "timestamp": "2026-01-12T10:05:30Z",
  "actor": "Orchestrator",
  "actor_role": "System",
  "payload": {}
}
```

**State change:** Run sealed. No more events can be added.

---

## Invariant System

### What Are Invariants?

Invariants are **mandatory properties that must hold**. They are not suggestions or heuristics—they are hard constraints.

If an invariant is violated, the run is invalid.

### Core Invariants

#### Invariant 1: Sequence Contiguity

**Rule:** Event sequences must be contiguous: 0, 1, 2, 3, ...

**Violation:**
```jsonl
{"sequence":0,...}
{"sequence":1,...}
{"sequence":3,...}  ← Gap! (missing sequence=2)
```

**Detection:** Replay engine checks `sequences == list(range(len(events)))`.

**Impact:** Cannot replay (missing causal link).

---

#### Invariant 2: Terminal Event Presence

**Rule:** Every run must have exactly one terminal event (`RUN_COMPLETED`, `RUN_ABORTED`, `RUN_REJECTED`).

**Violation:**
```jsonl
{"sequence":0,"event_type":"RUN_CREATED",...}
{"sequence":1,"event_type":"ISSUE_DETECTED",...}
(no terminal event)
```

**Detection:** Replay engine checks `last_event['event_type'] in TERMINAL_EVENTS`.

**Impact:** Run is unsealed (ambiguous state).

---

#### Invariant 3: Approval Precedes Fixes

**Rule:** `PLAN_APPROVED` must occur before `FIX_APPLIED`.

**Violation:**
```jsonl
{"sequence":3,"event_type":"FIX_APPLIED",...}  ← Applied before approval!
{"sequence":4,"event_type":"PLAN_APPROVED",...}
```

**Detection:** Replay engine checks `plan_approved` flag before applying fixes.

**Impact:** Unauthorized execution.

---

#### Invariant 4: Safety Check Precedes Fixes

**Rule:** `SAFETY_CHECK_PASSED` must occur before `FIX_APPLIED`.

**Violation:**
```jsonl
{"sequence":3,"event_type":"FIX_APPLIED",...}  ← Applied before safety check!
{"sequence":4,"event_type":"SAFETY_CHECK_PASSED",...}
```

**Detection:** Replay engine checks `safety_passed` flag before applying fixes.

**Impact:** Unsafe execution.

---

#### Invariant 5: Terminal Event Matches Ledger State

**Rule:** The last event's type must match `ledger.json`'s `final_state`.

**Violation:**
```json
// ledger.json
{"final_state": "COMPLETE"}

// events.jsonl (last event)
{"sequence":25,"event_type":"RUN_ABORTED",...}  ← Mismatch!
```

**Detection:** Replay engine compares `last_event['event_type']` to `ledger['final_state']`.

**Impact:** Corrupted ledger.

---

#### Invariant 6: Policy Consistency

**Rule:** Fixes must match the policy recorded in `POLICY_RESOLVED`.

**Violation:**
```jsonl
{"sequence":2,"event_type":"POLICY_RESOLVED","payload":{"safe_rules":["F401"]}}
{"sequence":6,"event_type":"FIX_APPLIED","payload":{"rule":"E711"}}  ← Not in policy!
```

**Detection:** Replay engine checks applied rules against `policy['safe_rules']`.

**Impact:** Policy violation (unauthorized fix).

---

### How Invariants Are Enforced

**At write time (run_ledger.py):**
- Schema validation (all events match `EventSchema`)
- Sequence ordering (next sequence = previous + 1)
- Terminal sealing (cannot append after terminal event)

**At replay time (run_replay.py):**
- Sequence contiguity (no gaps)
- Approval precedence (approvals before fixes)
- Safety precedence (safety checks before fixes)
- Terminal presence (run must be sealed)
- Terminal consistency (last event matches ledger state)

**At query time (run_ledger_query.py):**
- No invariants enforced (read-only)

---

## Deterministic Replay Mechanics

### Replay Algorithm

```python
def replay_run(run_id: str) -> ReplayRunState:
    ledger = _read_ledger(run_id)
    events = _read_events(run_id)
    
    state = ReplayRunState()  # Empty state
    
    for event in sorted(events, key=lambda e: e['sequence']):
        apply_event(state, event)
    
    check_invariants(state, ledger)
    
    return state
```

### Event Handlers

Each event type has a handler that mutates `ReplayRunState`:

```python
def apply_event(state: ReplayRunState, event: dict):
    event_type = event['event_type']
    
    if event_type == 'RUN_CREATED':
        state.started_at = event['timestamp']
    
    elif event_type == 'ISSUE_DETECTED':
        state.issues_detected = event['payload']['count']
    
    elif event_type == 'PLAN_APPROVED':
        state.decisions['plan_approved'] = True
        state.decisions['approved_by'] = event['actor']
    
    elif event_type == 'FIX_APPLIED':
        if not state.decisions['plan_approved']:
            raise InvariantViolation("Fix applied before approval")
        state.fixes.append(event['payload'])
    
    elif event_type == 'RUN_COMPLETED':
        state.final_state = 'COMPLETE'
    
    # ... (other event types)
```

### Why Replay Is Deterministic

1. **Events are ordered by sequence** (not timestamp).
2. **State is derived only from events** (no runtime variables).
3. **Event handlers are pure functions** (no side effects).
4. **No external state** (no database reads, no API calls).

**Result:** Applying the same events in the same order always produces the same state.

---

## Query & Inspection APIs

### Query API (agent/run_ledger_query.py)

**Purpose:** Provide helper functions for common ledger queries.

**Functions:**
- `get_full_timeline(run_id)` → All events, sorted by sequence
- `get_run_summary(run_id)` → Derived summary (duration, fix counts, approvals, policies, edr_id)
- `get_events_by_phase(run_id, phase)` → Filter by phase (scanning, planning, fixing, completing)
- `get_events_by_type(run_id, event_type)` → Filter by event type
- `get_audit_view(run_id)` → Flattened timeline (CSV-friendly)
- `trace_causality(run_id, payload_ref)` → Filter by payload reference (e.g., find all events related to a specific edr_id)

**Constraints:**
- Read-only (cannot mutate ledger)
- Side-effect free (no database writes, no API calls)
- JSON-safe (returns dicts, lists, primitives only)

---

### Replay Engine (agent/run_replay.py)

**Purpose:** Deterministic state reconstruction.

**Function:**
- `replay_run(run_id)` → `ReplayRunState`

**ReplayRunState fields:**
- `decisions` (plan_approved, approved_by, safety_passed)
- `fixes` (list of applied fixes)
- `safety` (checks_run, all_passed)
- `edr` (edr_id, path)
- `overrides` (list of human overrides)
- `invariants` (list of detected violations)

**Constraints:**
- Read-only (cannot mutate ledger)
- Deterministic (same events → same state)
- Invariant-checking (detects violations)

---

### Inspection (agent/run_inspect.py)

**Purpose:** Comprehensive JSON report.

**Function:**
- `inspect_run(run_id)` → JSON report

**Report sections:**
- `metadata` (run_id, started_at, ended_at, duration, final_state)
- `timeline` (event_count, phases_histogram, event_types_histogram)
- `decisions` (plan_approved, approved_by, safety_passed)
- `fixes` (count, breakdown by rule/file)
- `safety` (checks_run, all_passed)
- `edr` (edr_id, path)
- `overrides` (count, list)
- `issues` (detected, resolved, unresolved)
- `invariants` (violation_count, violations)
- `audit_preview` (first 5 events)
- `query_summary` (run_summary from query API)
- `causality_trace` (events related to edr_id)

**Constraints:**
- Read-only (cannot mutate ledger)
- JSON-safe (no datetimes, no custom objects)

---

## Failure Modes & Safety

### Failure Mode 1: Execution Crashes

**Scenario:** Orchestrator crashes mid-execution.

**What happens:**
- Ledger persists (all events up to crash point are recorded).
- Run is left in `INCOMPLETE` state (no terminal event).

**Recovery:**
- Replay shows exactly where execution stopped.
- User can re-run or manually complete.

**Safety:** Ledger is authoritative. Execution can be retried without losing history.

---

### Failure Mode 2: Invariant Violation

**Scenario:** Replay detects sequence gap or missing approval.

**What happens:**
- Replay engine raises `InvariantViolation`.
- Run is flagged as invalid.

**Recovery:**
- Ledger is corrupt (manual inspection required).
- User cannot trust this run.

**Safety:** Replay detects corruption. Invalid runs are not silent.

---

### Failure Mode 3: Policy Override

**Scenario:** Human overrides policy and approves risky fix.

**What happens:**
- `PLAN_APPROVED` event is recorded with `actor_role=Human`.
- Override is visible in ledger.

**Recovery:**
- Blame is clear (override is recorded).
- Replay shows who approved and when.

**Safety:** Overrides do not erase history. Governance is preserved.

---

### Failure Mode 4: Safety Check Fails

**Scenario:** Safety checker detects regression.

**What happens:**
- `SAFETY_CHECK_FAILED` event is emitted.
- Orchestrator aborts run.
- `RUN_ABORTED` event seals ledger.

**Recovery:**
- Fixes are not applied (abort before FIX_APPLIED).
- Ledger shows why run failed.

**Safety:** Failure is loud, not silent. No hidden breaks.

---

### Failure Mode 5: Ledger Corruption

**Scenario:** `ledger.json` or `events.jsonl` is manually edited or corrupted.

**What happens:**
- Replay engine detects invariant violations.
- Run is flagged as invalid.

**Recovery:**
- Cannot trust this run.
- Must restore from backup or discard.

**Safety:** Corruption is detectable. Invalid runs are not trusted.

---

## Design Tradeoffs

### Tradeoff 1: Immutability vs Flexibility

**Decision:** Ledger is immutable. Events cannot be edited or deleted.

**Benefit:** Trust without code execution. Replay is deterministic.

**Cost:** Cannot fix mistakes retroactively. Overrides create new events, not edits.

**Justification:** For regulated environments, auditability > flexibility.

---

### Tradeoff 2: Sequence-Based vs Timestamp-Based Ordering

**Decision:** Events are ordered by sequence (0, 1, 2, ...), not timestamp.

**Benefit:** No clock skew, no ambiguous ordering, deterministic replay.

**Cost:** Timestamps are secondary (informational only).

**Justification:** Determinism > convenience.

---

### Tradeoff 3: Ledger Size vs Completeness

**Decision:** Record all events, even granular ones (e.g., one event per fix).

**Benefit:** Complete audit trail. Precise causality.

**Cost:** Large ledgers (e.g., 1000 fixes = 1000 events).

**Justification:** Completeness > efficiency. Disk is cheap; trust is expensive.

---

### Tradeoff 4: Read-Only UI vs Powerful UI

**Decision:** UI cannot mutate ledger. All mutations go through CLI.

**Benefit:** Authority is clear. No hidden mutation paths.

**Cost:** UI is less convenient (cannot trigger runs directly).

**Justification:** Governance > convenience.

---

### Tradeoff 5: JSON vs Binary

**Decision:** Ledger uses JSON (human-readable).

**Benefit:** Inspectable without tools. Easy to verify externally.

**Cost:** Larger file size, slower parsing.

**Justification:** Auditability > performance.

---

## Non-Goals

### ❌ Not a Real-Time System

AGI Engineer is **not** optimized for real-time execution. Ledger writes are synchronous and may be slow for massive runs.

**Why:** Correctness > speed.

---

### ❌ Not a Distributed System

AGI Engineer does **not** support distributed execution. Runs are single-process, single-machine.

**Why:** Simplicity > scalability.

---

### ❌ Not a Machine Learning System

AGI Engineer does **not** learn from past runs. Policies are explicit, not inferred.

**Why:** Determinism > adaptability.

---

### ❌ Not a Code Assistant

AGI Engineer does **not** suggest fixes interactively. It executes autonomously based on policy.

**Why:** Governance > convenience.

---

### ❌ Not a Monitoring System

AGI Engineer does **not** replace monitoring. It provides post-execution replay, not real-time alerts.

**Why:** Audit > observability.

---

## Summary

AGI Engineer is a **governed execution system** built on three core principles:

1. **Execution ≠ Authority** (proposals vs authorization)
2. **Ledger > Logs** (primary vs secondary)
3. **Replay > Trust** (verification vs assumption)

The architecture separates execution (fallible, AI-driven) from governance (immutable, policy-bound), enabling:
- **Deterministic replay** (same events → same state)
- **Human auditability** (verify without trusting AI)
- **Compliance-ready traces** (prove what happened, when, who approved)

For teams that need this—regulated environments, long-lived systems, high-stakes code—AGI Engineer is necessary.

For teams that don't—startups, throwaway scripts, exploration—AGI Engineer is overkill.

**Trust is replaced by proof. And proof is stronger than trust.**
