# AGI Engineer

**A deterministic, governed autonomous engineering system built on immutable audit trails.**

---

## What AGI Engineer Is

AGI Engineer is a deterministic autonomous code fixing system that maintains an **immutable run ledger** of all execution decisions, scans, approvals, safety checks, and outcomes. It separates execution (fallible, AI-driven) from governance (immutable, policy-bound), ensuring every action is recorded, replayable, and auditable.

**It is not:**
- A chatbot or code assistant (not GitHub Copilot)
- A general-purpose agent framework (not LangChain)
- An autonomous developer replacement (not Devin)

**It is:**
- A governed execution system with deterministic replay
- A compliance-ready audit trail for code changes
- A proof-of-work system where replay replaces trust

---

## What Problem It Solves

**The Trust Crisis in Autonomous Code Tools:**

Every autonomous coding tool faces the same problem: *How do you trust it?*

- **GitHub Copilot:** Suggests code, but leaves no audit trail. If a suggestion causes a problem, you cannot prove what was suggested or why.
- **Autonomous bots (Devin, Claude agents):** Execute changes autonomously, but their logs are mutable, incomplete, or lost. Blame is diffuse.
- **Agent frameworks:** Flexible but non-deterministic. Hidden state in LLM context, memory stores, and runtime variables makes replay impossible.

**AGI Engineer solves this by replacing trust with proof:**

| Traditional Approach | AGI Engineer |
|---------------------|--------------|
| "Trust the AI to be smart" | "Verify the ledger; replay the run" |
| Logs are secondary observations | Ledger is the source of truth |
| Post-hoc verification (read logs) | Pre-action governance (approve before execution) |
| Non-deterministic replay | Deterministic replay guaranteed |
| Blame is unclear | Blame is recorded (actor + timestamp) |

---

## What It Explicitly Does NOT Do

### ❌ No Silent Execution
Fixes are never applied without explicit approval (human or policy). Approval is recorded as an immutable event.

### ❌ No Self-Learning
The system does not adapt, learn, or modify its behavior based on past runs. Policies are versioned and explicit.

### ❌ No Hidden State
Every decision that affects the outcome is recorded in the ledger. State that exists only in code, memory, or configuration is not authoritative.

### ❌ No Retroactive Mutation
Once an event is written to the ledger, it cannot be edited or deleted. Overrides create new events; they do not erase history.

### ❌ No Heuristic Trust
Safety is enforced by invariants (mandatory properties that must hold), not heuristics (rules of thumb that may fail).

---

## Core Guarantees

### 1. Immutable Run Ledger
- Every run creates an append-only ledger (`ledger.json` + `events.jsonl`).
- Events are sequenced (0, 1, 2, ...) and cannot be reordered, deleted, or modified.
- The ledger is sealed with a terminal event (`RUN_COMPLETED`, `RUN_ABORTED`, `RUN_REJECTED`).

### 2. Deterministic Replay
- Any run can be replayed by applying events in sequence order.
- Replay must produce the same state (same fixes, same approvals, same decisions).
- Divergence from the original run is detected as an invariant violation.

### 3. Human Approval & Override
- Humans (or policies) must approve before fixes are applied.
- Approval is recorded as an event with actor, role, and timestamp.
- Humans can override, but overrides do not erase history—they create new events.

### 4. No Hidden State
- All authoritative state is in the ledger.
- Configuration and environment variables may *inform* execution, but they do not override the ledger.
- "If it's not in the ledger, it didn't happen."

### 5. Explicit Terminal States
- Every run ends with a terminal state: `COMPLETE`, `INCOMPLETE`, `ABORTED`, or `REJECTED`.
- No run is left in an ambiguous state.
- Terminal events cannot be added retroactively.

---

## High-Level Architecture

### Authority Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     USER / CLI                              │
│              (python3 agi_engineer_v3.py)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              ORCHESTRATOR (agi_engineer_v3.py)              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Scanner  │  │ Planner  │  │  Safety  │  │ Fix Engine │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘ │
│                    ↓ (emit events only)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            IMMUTABLE RUN LEDGER (AUTHORITY)                 │
│                                                              │
│  • ledger.json (metadata: started_at, final_state)         │
│  • events.jsonl (append-only: RUN_CREATED → RUN_COMPLETED) │
│                                                              │
│  Guarantees:                                                │
│  - Append-only (no edits, no deletes)                      │
│  - Sequence-based (0, 1, 2, ...)                           │
│  - Terminal sealing (one terminal event per run)           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼ (read-only)
┌─────────────────────────────────────────────────────────────┐
│           QUERY / REPLAY / INSPECT MODULES                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Query API    │  │ Replay Engine│  │ Inspection   │     │
│  │ (Phase 7.3)  │  │ (Phase 7.4)  │  │ (Phase 7.5)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              UI / REPORTS / AUDIT TOOLS                     │
│         (read-only; cannot mutate ledger)                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

**1. Execution ≠ Authority**
- Execution (scanner, planner, fixer) proposes actions.
- Governance (ledger, policies, approvals) authorizes actions.
- Execution can crash; governance remains intact.

**2. Ledger Is the Source of Truth**
- Logs are secondary; the ledger is primary.
- If ledger and logs disagree, ledger wins.
- Queries and replay read from the ledger, never from runtime state.

**3. UI Is Powerless**
- The UI (dashboard, reports) can only read the ledger.
- It cannot create runs, approve plans, or modify events.
- This prevents hidden mutations and ensures all changes go through the orchestrator.

**4. Replay Is Stronger Than Monitoring**
- Monitoring observes execution in real-time; replay reconstructs it deterministically.
- If replay diverges from the original, you have proof something is wrong.
- Replay enables deterministic rollback and precise debugging.

---

## One Run — Conceptual Walkthrough

A typical run follows this lifecycle:

1. **RUN_CREATED** (seq=0)  
   Ledger initialized; run begins.

2. **ISSUE_DETECTED** (seq=1)  
   Scanner finds 47 issues in the codebase.

3. **POLICY_RESOLVED** (seq=2)  
   Policy determines which fixes are auto-approvable vs requiring human approval.

4. **PLAN_CREATED** (seq=3)  
   System creates a plan: fix 18 issues automatically, escalate 12 for human review.

5. **PLAN_APPROVED** (seq=4)  
   Human (alice@company.com) approves the plan.

6. **SAFETY_CHECK_PASSED** (seq=5)  
   Safety validation confirms fixes are policy-compliant and deterministic.

7. **FIX_APPLIED** (seq=6-23)  
   18 fixes are applied in sequence. Each fix is a separate event.

8. **EDR_FINALIZED** (seq=24)  
   Engineering Decision Report is generated and linked.

9. **RUN_COMPLETED** (seq=25)  
   Terminal event seals the ledger. No more events can be appended.

**What cannot happen:**
- No fix can be applied before approval (sequence enforced).
- No approval can be retroactively removed (immutable).
- No event can be hidden or skipped (sequence gaps detected by replay).

---

## How To Verify a Run (No Trust Required)

You can independently verify any run without trusting the AI or reading the source code.

### Step 1: Inspect the Run

```bash
python3 agent/run_inspect.py examples/sample_run
```

**What this proves:**
- The ledger is structurally valid.
- No invariant violations (sequence gaps, missing terminal events).
- Run completed successfully.

### Step 2: Replay the Run

```bash
python3 agent/run_replay.py examples/sample_run
```

**What this proves:**
- Replay produces the same state as the original run.
- Event sequencing is correct.
- Decisions were deterministic.

### Step 3: Verify Event Sequences

```bash
python3 -c "
import json
with open('examples/sample_run/events.jsonl', 'r') as f:
    events = [json.loads(line) for line in f if line.strip()]
sequences = [e['sequence'] for e in events]
expected = list(range(len(events)))
print('Valid:', sequences == expected)
"
```

**What this proves:**
- No sequence gaps (events are contiguous: 0, 1, 2, ...).
- No out-of-order events.

### Step 4: Verify Human Approval

```bash
python3 -c "
import json
with open('examples/sample_run/events.jsonl', 'r') as f:
    events = [json.loads(line) for line in f if line.strip()]
approvals = [e for e in events if e['event_type'] == 'PLAN_APPROVED']
for a in approvals:
    print(f\"Actor: {a['actor']} | Role: {a['actor_role']} | Time: {a['timestamp']}\")
"
```

**What this proves:**
- A human explicitly approved the plan.
- The approval is recorded with actor and timestamp.
- The approval cannot be denied or erased.

**For detailed verification, see: [docs/PROOF_OF_TRUST.md](docs/PROOF_OF_TRUST.md)**

---

## Who This Is For / Not For

### ✅ Built For

**Regulated teams:**
- Healthcare (HIPAA), Finance (SOX, PCI), Government (FedRAMP, CJIS)
- Requirement: "We must prove what we did, when, and who approved it."

**Large, long-lived codebases:**
- 100K+ lines of code, 10+ years of active development
- Requirement: "Changes must be reproducible, traceable, and revertible."

**Environments where blame and accountability matter:**
- High-stakes code, production systems, compliance-heavy organizations
- Requirement: "When something breaks, we need to know why and how to fix it, provably."

### ❌ Not Built For

**Hackathons and throwaway scripts:**
- Ledger overhead is not worth it for ephemeral work.
- Better tool: Copilot, shell scripts, manual fixes.

**"Just fix it fast" workflows:**
- Approval gates and governance slow down rapid iteration.
- Better tool: Autonomous bots (Devin), quick scripting.

**Exploratory or experimental code:**
- Immutability is antithetical to exploration.
- Better tool: Interactive IDE, REPL, direct experimentation.

**For detailed audience analysis, see: [docs/WHO_THIS_IS_FOR.md](docs/WHO_THIS_IS_FOR.md)**

---

## Project Phase Status

AGI Engineer has been developed across multiple locked phases. Each phase is immutable and cannot be retroactively modified.

### Completed & Locked Phases

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1-6.2** | Core execution (scanner, classifier, planner, safety, fixer, PR integration) | ✅ LOCKED |
| **Phase 6.3** | Run Ledger & Execution Timeline design (schemas, invariants, event taxonomy) | ✅ LOCKED |
| **Phase 7.1** | Run Ledger writer (append-only, sequence-based, JSON persistence) | ✅ LOCKED |
| **Phase 7.2** | Ledger integration into CLI (event emission, optional ledger, non-fatal errors) | ✅ LOCKED |
| **Phase 7.3** | Run Ledger Query API (read-only helpers for inspection) | ✅ LOCKED |
| **Phase 7.4** | Deterministic Replay Engine (reconstruct state from events) | ✅ LOCKED |
| **Phase 7.5** | Run Inspection & Visualization (JSON-safe audit reports) | ✅ LOCKED |
| **Phase 8** | System Narrative & Positioning (architectural explanation) | ✅ LOCKED |
| **Phase 9A** | External Trust Overview (non-technical explanation) | ✅ LOCKED |
| **Phase 9B** | Proof-of-Trust Artifacts (frozen sample run for verification) | ✅ LOCKED |
| **Phase 10.1** | Packaging & Architecture Diagram (this README) | ✅ LOCKED |

### What "LOCKED" Means

- **No retroactive changes:** Past phases cannot be modified or refactored.
- **No breaking changes:** Future phases must preserve backward compatibility.
- **No weakening of guarantees:** Immutability, determinism, and governance cannot be relaxed.

---

## Quick Start

### Prerequisites

- Python 3.8+
- No external dependencies for core execution
- Optional: pytest for running tests

### Run a Scan (Analyze Only)

```bash
python3 agi_engineer_v3.py \
  --repo-path ./your-repo \
  --analysis-only true
```

### Run Fixes (With Ledger)

```bash
python3 agi_engineer_v3.py \
  --repo-path ./your-repo \
  --analysis-only false
```

Ledger will be created at: `~/.agi-engineer/ledger/<run-id>/`

### Inspect a Run

```bash
python3 agent/run_inspect.py <run-id>
```

### Replay a Run

```bash
python3 agent/run_replay.py <run-id>
```

---

## Documentation

- **[PROOF_OF_TRUST.md](docs/PROOF_OF_TRUST.md)** — Independent verification guide (5-minute verification)
- **[EXTERNAL_TRUST_OVERVIEW.md](docs/EXTERNAL_TRUST_OVERVIEW.md)** — Why this is different from Copilot/Devin (for investors, regulators)
- **[ONE_RUN_NARRATIVE.md](docs/ONE_RUN_NARRATIVE.md)** — Walk through a real run, step by step
- **[FAILURE_AND_OVERRIDE_STORY.md](docs/FAILURE_AND_OVERRIDE_STORY.md)** — How the system fails safely
- **[WHY_THIS_IS_NOT_JUST_AUTOMATION.md](docs/WHY_THIS_IS_NOT_JUST_AUTOMATION.md)** — Comparison with other tools
- **[WHO_THIS_IS_FOR.md](docs/WHO_THIS_IS_FOR.md)** — Target and non-target audiences
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Technical architecture and authority flow
- **[PHASE_8_SYSTEM_NARRATIVE.md](docs/PHASE_8_SYSTEM_NARRATIVE.md)** — System definition and core principles

---

## Testing

Run the test suite:

```bash
python3 -m pytest tests/ -v
```

All 19 tests must pass for a valid build.

---

## License

[Add license here]

---

## Contributing

This project follows strict governance principles. Contributions must:
- Preserve immutability of the ledger
- Maintain deterministic replay
- Not weaken governance guarantees
- Pass all existing tests

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## Final Note

AGI Engineer is not smarter than Copilot. It is not faster than Devin. It is not more flexible than agent frameworks.

**It is more auditable, more replayable, and more compliant.**

For teams that need this—regulated environments, long-lived systems, high-stakes code—AGI Engineer is not just better. It is necessary.

For teams that don't need it—startups, throwaway scripts, exploration—AGI Engineer is overkill and annoying.

Both are correct answers. The question is which one applies to you.

---

**Trust is replaced by proof. And proof is stronger than trust.**
