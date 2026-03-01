"""
Phase 13.2: Analyzer Selection Tests

Covers:
- Deterministic JSON serialization
- Registry-based validation errors (unknown ID, duplicates, plan violations)
- Deterministic execution ordering
"""

import pytest

from agent.intelligence.selection import AnalyzerSelection
from agent.intelligence.selection_validation import (
    validate_selection,
    compute_execution_order,
    SelectionValidationError,
)


def test_selection_json_is_deterministic():
    sel = AnalyzerSelection(plan="team", enabled_analyzers=["security", "architectural", "enhanced_performance"]) 
    d = sel.to_dict()
    assert d["enabled_analyzers"] == sorted(["security", "architectural", "enhanced_performance"])  # deterministic order for JSON


def test_validation_unknown_id():
    with pytest.raises(SelectionValidationError) as e:
        validate_selection("developer", ["not_an_analyzer"])
    assert "Unknown analyzer id" in str(e.value)


def test_validation_duplicate_ids():
    with pytest.raises(SelectionValidationError) as e:
        validate_selection("developer", ["architectural", "architectural"]) 
    assert "Duplicate analyzer id" in str(e.value)


def test_validation_plan_violation():
    # enhanced_performance min_plan is team; developer should fail
    with pytest.raises(SelectionValidationError) as e:
        validate_selection("developer", ["enhanced_performance"]) 
    assert "requires plan" in str(e.value)


def test_compute_execution_order_sorted():
    order = compute_execution_order(["security", "architectural", "enhanced_performance"]) 
    assert order == ["architectural", "enhanced_performance", "security"]
