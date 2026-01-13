# Phase 13.2: User Analyzer Configuration (Selection)

Status: COMPLETE

Purpose: Introduce a governed, deterministic configuration layer that declares which analyzers a run is allowed to execute — without changing analyzer logic, execution behavior, or UI.

This phase answers: "What is the user allowed to run — and how do we prove it later?"

---

## Data Model: AnalyzerSelection (Pure Data)

File: `agent/intelligence/selection.py`

- `plan`: `developer | team | enterprise`
- `enabled_analyzers`: list of stable analyzer IDs (from registry)
- Deterministic JSON via `to_dict()` (IDs sorted for serialization only)
- No behavior, no validation, no inference
- Ledger-recordable via ledger adapter (Phase 13.2 helper)

Example:
```json
{
  "plan": "team",
  "enabled_analyzers": [
    "architectural",
    "enhanced_architectural",
    "enhanced_performance",
    "security"
  ]
}
```

---

## Registry-Based Validation

File: `agent/intelligence/selection_validation.py`

Rules:
- Source of truth: Phase 13.1 `ANALYZER_REGISTRY`
- Analyzer IDs must exist (no unknown IDs)
- Analyzer IDs must not duplicate
- Analyzer IDs must be permitted by `min_plan` (registry)
- Deterministic ordering for execution: `compute_execution_order()` sorts by analyzer ID
- Fail-fast: Raises `SelectionValidationError` with explicit messages
- Never guess or auto-correct input

---

## Ledger Integration (Append-Only, Non-Fatal)

File: `agent/intelligence/ledger_adapter.py`

- `selection_to_runledger_format(selection)`
- Emits event: `ANALYZER_SELECTION_DEFINED`
- Actor: `intelligence-orchestrator`, Role: `Orchestrator`, Phase: `PHASE_13`
- Deterministic `payload_ref`: `selection:<plan>:<sorted_ids_csv>`
- Recorded before proposals; ledger failures remain non-fatal

---

## Orchestrator Wiring (No Logic Changes)

File: `agent/intelligence/orchestrator.py`

- Accepts optional `selection: AnalyzerSelection`
- Validates via registry; fail-fast on invalid selection
- Filters analyzers strictly by `(registry + selection)`
- Deterministic order via sorted analyzer IDs
- If no selection provided: behavior IDENTICAL to Phase 13.1 (all analyzers as before)
- Writes `ANALYZER_SELECTION_DEFINED` to ledger before proposals if ledger is provided

Non-Goals (Enforced):
- No analyzer logic changes
- No proposal schema changes
- No scoring changes
- No UI changes
- No billing/auth code
- No defaults or heuristics added

---

## Tests

Files:
- `tests/test_analyzer_selection.py`: Model determinism; validation failure cases; deterministic ordering
- `tests/test_orchestrator_selection.py`: Ledger selection event ordering; missing selection preserves behavior

Covers:
- Deterministic serialization
- Unknown ID failure
- Duplicate ID failure
- Plan violation failure
- Deterministic execution ordering
- Selection ledger event recorded before proposals
- No selection → no selection event

---

## Backward Compatibility

- 100% backward compatible
- No changes to analyzer logic, proposal schemas, or ledger schemas
- Default behavior unchanged when selection is absent
- Replay-safe and deterministic

---

## Non-Goals (Explicit)

- No orchestrator strategy changes
- No execution reordering beyond deterministic sorting when selection is provided
- No plan inference or billing logic
- No UI components

---

## Summary

Phase 13.2 adds a robust, registry-driven, deterministic configuration layer. It enables explicit analyzer selection, validates it against the registry and plan metadata, records it immutably in the ledger, and preserves exact prior behavior when selection is not provided.

This is governance infrastructure, not UX or billing. It prepares for:
- Phase 13.3: Orchestrator wiring to use registry fully
- Phase 13.4: Subscription capability gating
