"""
Phase 13.1: Analyzer Registry Tests

Verifies:
- Registry integrity (required keys and types)
- Deterministic ordering (sorted by analyzer ID)
- Stable, human-readable IDs
- Plan filtering is deterministic and respects plan order
- Categories and plans are restricted to allowed sets
"""

import re
import pytest

from agent.intelligence.registry import (
    ANALYZER_REGISTRY,
    list_all_analyzers,
    get_analyzer_by_id,
    list_analyzers_for_plan,
)

ALLOWED_CATEGORIES = {
    "architecture",
    "performance",
    "concurrency",
    "security",
    "testing",
    "configuration",
}

ALLOWED_PLANS = ["developer", "team", "enterprise"]

EXPECTED_IDS = [
    # Architecture
    "abstraction",
    "api_contracts",
    "architectural",
    "enhanced_architectural",
    "god_objects",
    # Concurrency
    "concurrency",
    "enhanced_concurrency",
    # Performance
    "performance",
    "enhanced_performance",
    # Security
    "security",
    # Testing
    "test_coverage",
    "broken_invariants",
    # Configuration
    "configuration",
    "dependencies",
]


def test_registry_contains_expected_ids():
    ids = sorted(ANALYZER_REGISTRY.keys())
    assert sorted(EXPECTED_IDS) == ids, f"Registry IDs mismatch.\nExpected: {sorted(EXPECTED_IDS)}\nActual:   {ids}"


def test_ids_are_human_readable_and_stable():
    for aid in ANALYZER_REGISTRY.keys():
        assert re.match(r"^[a-z0-9_]+$", aid), f"Invalid analyzer id format: {aid}"
        assert not aid.isdigit(), "IDs must not be purely numeric"


def test_metadata_integrity():
    for aid, meta in ANALYZER_REGISTRY.items():
        assert "class" in meta and meta["class"], f"Missing class for {aid}"
        assert meta.get("category") in ALLOWED_CATEGORIES, f"Invalid category for {aid}"
        assert meta.get("min_plan") in ALLOWED_PLANS, f"Invalid plan for {aid}"
        assert isinstance(meta.get("default_enabled"), bool), f"default_enabled must be bool for {aid}"
        desc = meta.get("description")
        assert isinstance(desc, str) and desc.strip(), f"description required for {aid}"


def test_list_all_analyzers_sorted_and_deterministic():
    first = list_all_analyzers()
    second = list_all_analyzers()
    # Deterministic length and order
    assert [aid for aid, _ in first] == [aid for aid, _ in second]
    assert [aid for aid, _ in first] == sorted(EXPECTED_IDS)


def test_get_analyzer_by_id_round_trip():
    meta = get_analyzer_by_id("enhanced_architectural")
    assert meta["category"] == "architecture"
    assert meta["min_plan"] in ALLOWED_PLANS


@pytest.mark.parametrize("plan,expected_includes,expected_excludes", [
    ("developer", {"architectural", "performance", "concurrency", "security", "test_coverage", "configuration", "dependencies", "abstraction", "api_contracts", "god_objects", "broken_invariants"}, {"enhanced_architectural", "enhanced_performance", "enhanced_concurrency"}),
    ("team", {"enhanced_architectural", "enhanced_performance", "enhanced_concurrency", "architectural"}, set()),
    ("enterprise", set(EXPECTED_IDS), set()),
])
def test_list_analyzers_for_plan(plan, expected_includes, expected_excludes):
    result_ids = [aid for aid, _ in list_analyzers_for_plan(plan)]
    # Deterministic order
    assert result_ids == sorted(result_ids)
    # Inclusion/exclusion checks
    for x in expected_includes:
        if x in EXPECTED_IDS and (_plan_leq(plan, _min_plan_of(x))):
            assert x in result_ids
    for x in expected_excludes:
        assert x not in result_ids


def _min_plan_of(analyzer_id: str) -> str:
    return ANALYZER_REGISTRY[analyzer_id]["min_plan"]


def _plan_leq(left: str, right: str) -> bool:
    order = {"developer": 0, "team": 1, "enterprise": 2}
    return order[left] >= order[right]
