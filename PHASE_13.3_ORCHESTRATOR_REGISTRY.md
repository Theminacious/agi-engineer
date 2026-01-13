# Phase 13.3: Orchestrator ↔ Analyzer Registry Unification

Status: COMPLETE | Locked

Purpose: Make the Analyzer Registry the single source of truth for orchestrator analyzer discovery, enabling deterministic execution, subscription-aware filtering, and future gating — without changing analyzer logic, proposal schemas, ledger schemas, or UI.

---

## What Changed

- Orchestrator now instantiates analyzers **only** from `ANALYZER_REGISTRY`.
- Execution order is deterministic: lexicographic by analyzer ID.
- Priority for analyzer resolution:
  1. AnalyzerSelection (explicit list + plan)
  2. Explicit plan parameter (plan-based registry filter)
  3. Default developer plan (backward-compatible baseline)
- Selection event remains optional; proposal events unchanged.

---

## Files

- Updated: `agent/intelligence/orchestrator.py`
  - Registry-driven instantiation
  - Optional `plan` parameter
  - Selection → plan → default resolution
  - Keeps `self.analyzers` in sync with the resolved list
- Tests: `tests/test_orchestrator_registry_integration.py`
- Docs: This file; `PHASE_13.3_FINAL_STATUS.md`

---

## Determinism & Replayability

- Analyzer IDs are sorted lexicographically for execution.
- No dynamic imports, no reflection, no randomness.
- Same input (code + selection/plan) → same analyzer list → same proposals.
- Ledger events unchanged except optional selection event when provided.

---

## Backward Compatibility

- If no selection and no plan are provided, orchestrator runs the **developer plan** set, matching prior Phase 13.2 behavior (baseline analyzers only; enhanced analyzers excluded by `min_plan`).
- Proposal schema unchanged; analyzer logic unchanged; ledger schema unchanged; UI untouched.

---

## Tests (Key Assertions)

- Registry-only instantiation (no hardcoded analyzers).
- Default behavior excludes enhanced analyzers (developer plan).
- Plan filtering: developer vs enterprise.
- Selection filtering: only selected analyzers run; deterministic ordering.

---

## Non-Goals (Explicit)

- No analyzer logic changes.
- No proposal schema changes.
- No ledger schema changes.
- No UI or billing/auth logic.
- No inference or heuristics; strictly registry-driven.

---

## Why This Matters

- **Subscription-ready:** plan metadata now drives analyzer availability deterministically.
- **Enterprise-safe:** analyzer discovery is centralized and auditable.
- **Future-proof:** enables Phase 13.4 gating and Phase 14 billing without touching analyzer logic.

---

## Lock Statement

Analyzer discovery is now registry-only. Orchestrator behavior is deterministic, replayable, and subscription-ready. Phase 13.3 is LOCKED.
