"""
Phase 13.2: Analyzer Selection Validation

Rules:
- Source of truth is ANALYZER_REGISTRY
- Analyzer IDs must exist in registry
- Analyzer IDs must be permitted for the selected plan (min_plan <= plan)
- No duplicates
- Deterministic ordering for output list (sorted by analyzer id)
- Fail fast with explicit error messages
- Never guess, auto-correct, or infer intent

Note: This module only validates and computes a deterministic execution list.
It does NOT mutate the AnalyzerSelection object.
"""
from __future__ import annotations

from typing import List, Tuple

from agent.intelligence.registry import ANALYZER_REGISTRY

_PLAN_ORDER = {"developer": 0, "team": 1, "enterprise": 2}


class SelectionValidationError(Exception):
    pass


def validate_selection(plan: str, enabled_ids: List[str]) -> None:
    """Validate the selection against the registry. Raises SelectionValidationError."""
    # Plan must be recognized
    if plan not in _PLAN_ORDER:
        raise SelectionValidationError(f"Invalid plan: {plan}")

    # Duplicates not allowed
    seen = set()
    for aid in enabled_ids:
        if aid in seen:
            raise SelectionValidationError(f"Duplicate analyzer id: {aid}")
        seen.add(aid)

    # All IDs must exist and be allowed for plan
    for aid in enabled_ids:
        if aid not in ANALYZER_REGISTRY:
            raise SelectionValidationError(f"Unknown analyzer id: {aid}")
        min_plan = ANALYZER_REGISTRY[aid].get("min_plan", "developer")
        if _PLAN_ORDER[plan] < _PLAN_ORDER[min_plan]:
            raise SelectionValidationError(
                f"Analyzer '{aid}' requires plan '{min_plan}', but selection plan is '{plan}'"
            )


def compute_execution_order(enabled_ids: List[str]) -> List[str]:
    """Return a deterministic, sorted list of analyzer IDs for execution."""
    return sorted(enabled_ids)
