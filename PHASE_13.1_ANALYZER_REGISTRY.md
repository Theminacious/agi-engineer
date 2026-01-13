# Phase 13.1: Analyzer Registry

Status: COMPLETE

Purpose: Introduce a static, deterministic Analyzer Registry that centrally declares all available analyzers with stable IDs, categories, minimum subscription plan metadata, and default enabled state — without changing analyzer logic, orchestrator behavior, or UI.

---

## Goals

- Centralize analyzer declarations in a single, explicit module.
- Guarantee stable, human-readable analyzer IDs (no auto-generation).
- Provide deterministic listing and filtering helpers.
- Attach non-executable metadata: category, min_plan, default_enabled, description.
- Maintain full backward compatibility and preserve determinism.

## Non-Goals (Explicit)

- No analyzer logic changes.
- No intelligence behavior changes.
- No orchestrator wiring changes yet.
- No UI changes.
- No ledger or schema changes.
- No billing or Stripe integration (min_plan is metadata only).

---

## File

- agent/intelligence/registry.py

Exports:
- `ANALYZER_REGISTRY`: Static dict keyed by stable analyzer IDs.
- `list_all_analyzers()`: Deterministic list of (id, meta), sorted by id.
- `get_analyzer_by_id(id)`: Lookup metadata by stable ID.
- `list_analyzers_for_plan(plan)`: Deterministic filtered list by plan (developer < team < enterprise).

---

## Data Model

- ID: stable, human-readable string (lowercase with underscores; never generated).
- `class`: Python class object of the analyzer (no instantiation performed).
- `category`: One of: architecture | performance | concurrency | security | testing | configuration.
- `min_plan`: One of: developer | team | enterprise. Metadata only.
- `default_enabled`: bool. Suggested default toggle for future UI.
- `description`: Brief plaintext summary.

Example:
```python
ANALYZER_REGISTRY = {
  "enhanced_architectural": {
    "class": EnhancedArchitecturalAnalyzer,
    "category": "architecture",
    "min_plan": "team",
    "default_enabled": True,
    "description": "Detects architectural violations and circular dependencies"
  }
}
```

---

## Determinism Guarantees

- Static dictionary defined in source (no runtime discovery).
- All helpers sort by analyzer ID before returning.
- No environment-based branching.
- No randomness.

---

## Plans and Categories

- Plans (metadata only): developer < team < enterprise
- Categories: architecture | performance | concurrency | security | testing | configuration

Note: These are descriptive and prepare for Phase 13.4; they do not gate execution in Phase 13.1.

---

## Test Coverage

File: tests/test_analyzer_registry.py

- Registry integrity: required fields present, allowed category/plan values.
- Deterministic ordering: list_all_analyzers() is sorted and stable.
- Stable IDs: human-readable, lower_snake_case, non-numeric.
- Plan filtering: list_analyzers_for_plan() respects developer < team < enterprise ordering deterministically.

---

## Backward Compatibility

- No changes to analyzer classes.
- No changes to orchestrator, ledger, or UI.
- Purely additive module with metadata and helpers.
- 100% deterministic and replayable.

---

## Next Phases

- Phase 13.2: User configuration surface (enable/disable per analyzer).
- Phase 13.3: Orchestrator wiring to use registry for execution order and selection.
- Phase 13.4: Subscription capability gating (using min_plan metadata).

---

## Summary

Phase 13.1 introduces a production-grade, deterministic Analyzer Registry that cleanly centralizes analyzer declarations and metadata without altering system behavior. It sets the foundation for configuration, orchestration, and plan-based capability gating in subsequent phases.
