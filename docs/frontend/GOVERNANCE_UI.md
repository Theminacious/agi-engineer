# Governance UI Documentation

## Overview

The **Proof & Governance** section is a **READ-ONLY** dashboard that provides immutable, cryptographically verifiable proof of what happened during a run. This section exists to solve the **"verify without trusting"** problem: you can prove that the AGI Engineer system behaved correctly without having to trust the AI.

## Philosophy: Ledger > Logs, Replay > Monitoring

### Why Ledger > Logs?

Traditional logs are mutable and can be edited, filtered, or deleted. The AGI Engineer uses an **append-only ledger** instead:

- **Immutable**: Once an event is written, it cannot be modified or deleted
- **Sequence-ordered**: Every event has a monotonically increasing sequence number
- **Cryptographically signed**: Events can be verified for tampering
- **Source of truth**: The ledger is the canonical record of what happened

### Why Replay > Monitoring?

Traditional monitoring observes behavior in real-time but cannot prove what happened after the fact. AGI Engineer uses **deterministic replay**:

- **Deterministic**: Replaying the same events always produces the same result
- **Verifiable**: Anyone can replay the ledger and verify the outcome
- **Auditable**: Compliance teams can inspect the replay without trusting the AI
- **Mathematical proof**: Invariants can be checked to prove correctness

## Architecture

### Data Flow

```
Run Execution (Backend)
  ↓
Ledger Writer (append-only)
  ↓
Event Ledger (immutable storage)
  ↓
Governance UI (read-only visualization)
```

The governance UI **never writes** to the ledger. It only reads frozen snapshots.

### Components

#### Data Layer
- **`lib/ledgerReader.ts`**: Read-only data access module
  - `readLedgerMetadata(runId)`: Fetch run metadata (branch, policy, timestamps, final state)
  - `readLedgerEvents(runId)`: Fetch all events in sequence order
  - `readReplaySummary(runId)`: Fetch replay summary (fixes count, approvals, violations)
  - `readInspectionReport(runId)`: Fetch detailed inspection report
  - `listAvailableRuns()`: List all frozen runs
  - `checkInvariants(events, metadata)`: Verify mathematical invariants

#### UI Components
- **`components/governance/GovernanceIntro.tsx`**: Landing page explanation
  - Explains read-only nature with visual cards
  - Lists what you CAN and CANNOT do
  
- **`components/governance/RunLedgerTimeline.tsx`**: Event timeline visualization
  - Displays events in sequence order with icons and colors
  - Highlights critical events (approvals, safety checks, completion)
  - Shows human actors with special badges
  
- **`components/governance/ReplaySummaryPanel.tsx`**: Replay summary card
  - Final state, event count, fixes count, duration
  - Plan approval and safety check status
  - EDR (Engineering Decision Report) ID
  - Invariant violation count
  
- **`components/governance/InvariantStatus.tsx`**: Invariant checks display
  - Shows 5 mathematical invariants with PASS/FAIL status
  - Explains what each invariant means
  - Overall status indicator
  
- **`components/governance/AuditTable.tsx`**: Tabular event view
  - All events in a sortable/filterable table
  - Columns: sequence, timestamp, event type, actor, role, phase, payload
  - Exportable for compliance
  
- **`components/governance/ReadOnlyBadge.tsx`**: Reusable read-only indicator
  - Three variants: lock (Read-Only), eye (View Only), archive (Frozen)

#### Pages
- **`app/governance/page.tsx`**: Landing page
  - GovernanceIntro component
  - List of all frozen runs
  - Read-only warning banner
  
- **`app/governance/[run_id]/page.tsx`**: Run detail page
  - Run metadata header
  - Two-column layout: timeline + summary/invariants
  - Audit table below
  - Cryptographic proof footer

### Navigation
- Added to sidebar: `/governance` → "Proof & Governance" (Shield icon)
- Active state detection for `/governance/*` routes

## Invariants

The governance UI checks 5 mathematical invariants that **MUST** hold for every valid run:

1. **Sequence Contiguous**: Event sequence numbers are continuous (0, 1, 2, ..., N) without gaps
2. **Terminal Event Present**: Ledger contains a terminal event (`RUN_COMPLETED`, `RUN_ABORTED`, or `PLAN_REJECTED`)
3. **Approval Before Fix**: `PLAN_APPROVED` must precede all `FIX_APPLIED` events
4. **Safety Before Fix**: `SAFETY_CHECK_PASSED` must precede all `FIX_APPLIED` events
5. **Terminal State Match**: Final state in metadata matches the terminal event type

If any invariant fails, it indicates:
- Bug in the execution system
- Corrupted ledger data
- Replay inconsistency

## What You CAN Do

✅ **View Timelines**: See all events in sequence order with timestamps and actors  
✅ **Inspect Replays**: Examine replay summaries with fixes, approvals, and violations  
✅ **Verify Invariants**: Check that mathematical properties hold for the run  
✅ **Export Audits**: Export the audit table for compliance and regulatory review  
✅ **Demo System**: Show the governance dashboard to investors/regulators/compliance teams

## What You CANNOT Do

❌ **No Execution**: Cannot trigger new runs from the governance dashboard  
❌ **No Approvals**: Cannot approve or reject plans  
❌ **No Mutations**: Cannot edit, delete, or modify any ledger data  
❌ **No PRs**: Cannot create GitHub pull requests  
❌ **No Scheduling**: Cannot schedule runs

**Why?** The governance dashboard is for **proof, not control**. Execution happens in the main Dashboard → Runs section.

## Use Cases

### 1. Compliance & Regulatory Audits
Regulators can inspect the governance dashboard to verify that:
- Human approvals were required and obtained
- Safety checks passed before code was modified
- All changes are traceable to specific events
- Invariants hold (system behaved correctly)

### 2. Investor Demonstrations
Show investors that the system is:
- Transparent: Every action is logged
- Auditable: Complete event history is available
- Trustworthy: Cryptographic proofs replace trust

### 3. Internal Trust Building
Engineering teams can:
- Verify that AI agents followed policy
- Inspect decision-making process (why fixes were applied)
- Debug issues by replaying failed runs
- Prove system correctness without trusting the AI

### 4. Security & Forensics
Security teams can:
- Investigate incidents by replaying runs
- Verify that safety checks were not bypassed
- Trace all actions to specific actors (AI or human)
- Prove that no unauthorized changes were made

## Data Sources

Currently, the governance UI reads from hardcoded sample data in `lib/ledgerReader.ts`:

- **Sample Run**: `run-2026-01-12-sample`
- **18 Events**: From initialization to completion
- **5 Fixes Applied**: F401 (2), F541 (2), W291 (1)
- **Human Approval**: By alice@company.com
- **0 Invariant Violations**: All checks passed

**Future**: The ledger reader will fetch data from:
- `examples/sample_run/ledger.json` (frozen run metadata)
- `examples/sample_run/events.jsonl` (event stream)
- `examples/sample_run/replay_summary.json` (replay results)
- Backend API endpoint: `/api/governance/runs/{run_id}/ledger`

## Why This Matters

Traditional AI systems require you to **trust** that they behaved correctly. AGI Engineer provides **proof** instead:

- **Ledger > Logs**: Immutable, sequence-ordered, cryptographically signed events
- **Replay > Monitoring**: Deterministic reconstruction of state from events
- **Invariants > Tests**: Mathematical properties that must hold for every run
- **Proof > Trust**: Anyone can verify correctness without trusting the AI

This is **not just automation**. It's a **verifiable governance system** for AI-driven engineering.

## Implementation Notes

### Additive Only
Phase 10.2 was implemented with **zero modifications** to existing frontend functionality:
- All new files in `app/governance/`, `components/governance/`, `lib/ledgerReader.ts`
- One new navigation item in `components/layout.tsx`
- No changes to existing API client (`lib/api.ts`)
- No changes to existing pages (`/dashboard`, `/runs`, `/analytics`, `/v3-analysis`)

### Read-Only by Design
Every component in the governance UI is read-only:
- No buttons that trigger execution
- No forms that submit data
- No API calls that mutate state
- All operations are GET-only (or read from static JSON)

### Future Enhancements
- **Real-time updates**: Subscribe to ledger events via WebSocket
- **Export formats**: CSV, JSON, PDF for audit reports
- **Search & filter**: Find specific events by type, actor, or timestamp
- **Comparison**: Diff two runs to see what changed
- **Cryptographic verification**: Verify event signatures on the client

## Conclusion

The Proof & Governance dashboard is the **trust layer** for the AGI Engineer system. It provides:
- Immutable proof of what happened
- Deterministic replay for verification
- Mathematical invariants for correctness
- Read-only access for compliance

**Without this section, you have to trust the AI. With this section, you can verify the AI.**
