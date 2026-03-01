"""
Analyzer Registry (Phase 13.1)

- Static, explicit registry of all analyzers
- Stable, human-readable IDs (no auto-generation)
- Deterministic iteration and plan filtering
- No analyzer logic changes, no orchestration changes

Categories: architecture | performance | concurrency | security | testing | configuration
Plans: developer < team < enterprise (for metadata only; no billing logic here)
"""

from __future__ import annotations

from typing import Dict, Any, List, Tuple

# Import analyzer classes (no logic changes)
from agent.intelligence.analyzers.architectural import ArchitecturalAnalyzer
from agent.intelligence.analyzers.enhanced_architectural import (
    EnhancedArchitecturalAnalyzer,
)
from agent.intelligence.analyzers.performance import PerformanceAnalyzer
from agent.intelligence.analyzers.enhanced_performance import (
    EnhancedPerformanceAnalyzer,
)
from agent.intelligence.analyzers.concurrency import ConcurrencyAnalyzer
from agent.intelligence.analyzers.enhanced_concurrency import (
    EnhancedConcurrencyAnalyzer,
)
from agent.intelligence.analyzers.security import SecurityAnalyzer
from agent.intelligence.analyzers.test_coverage import TestCoverageAnalyzer
from agent.intelligence.analyzers.configuration import ConfigurationDriftAnalyzer
from agent.intelligence.analyzers.dependencies import DependencyMisuseAnalyzer
from agent.intelligence.analyzers.api_contracts import APIContractAnalyzer
from agent.intelligence.analyzers.abstraction import AbstractionLeakageAnalyzer
from agent.intelligence.analyzers.god_objects import GodObjectsAnalyzer
from agent.intelligence.analyzers.broken_invariants import BrokenInvariantsAnalyzer

# Phase 16: Reliability Intelligence Engine
from agent.intelligence.analyzers.reliability.crash_risk import CrashRiskAnalyzer
from agent.intelligence.analyzers.reliability.resource_leak import ResourceLeakAnalyzer
from agent.intelligence.analyzers.reliability.reliability_pattern import ReliabilityPatternAnalyzer
from agent.intelligence.analyzers.reliability.scalability_risk import ScalabilityRiskAnalyzer
from agent.intelligence.analyzers.reliability.edge_case_logic import EdgeCaseLogicAnalyzer

# Plan ordering for deterministic comparison (no billing logic)
_PLAN_ORDER = {
    "developer": 0,
    "team": 1,
    "enterprise": 2,
}

# Allowed category set (documentation aid / validation use in tests)
_ALLOWED_CATEGORIES = {
    "architecture",
    "performance",
    "concurrency",
    "security",
    "testing",
    "configuration",
    "reliability",  # Phase 16
}

# Static, explicit registry. Keys are stable, human-readable IDs.
# No auto-generation. Do not reorder entries dynamically –
# helper functions provide sorted iteration.
ANALYZER_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Architecture
    "architectural": {
        "class": ArchitecturalAnalyzer,
        "category": "architecture",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects architectural violations and circular dependencies (baseline)",
    },
    "enhanced_architectural": {
        "class": EnhancedArchitecturalAnalyzer,
        "category": "architecture",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects architectural violations, multi-hop cycles, domain leakage, coupling",
    },
    "abstraction": {
        "class": AbstractionLeakageAnalyzer,
        "category": "architecture",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects abstraction leakage and boundary problems",
    },
    "api_contracts": {
        "class": APIContractAnalyzer,
        "category": "architecture",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects API contract violations across modules/services",
    },
    "god_objects": {
        "class": GodObjectsAnalyzer,
        "category": "architecture",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects large, do-everything classes/modules (god objects)",
    },

    # Performance
    "performance": {
        "class": PerformanceAnalyzer,
        "category": "performance",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects performance anti-patterns (baseline)",
    },
    "enhanced_performance": {
        "class": EnhancedPerformanceAnalyzer,
        "category": "performance",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects N+1 queries, blocking I/O, memory growth, inefficient algorithms",
    },

    # Concurrency
    "concurrency": {
        "class": ConcurrencyAnalyzer,
        "category": "concurrency",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects basic concurrency hazards (baseline)",
    },
    "enhanced_concurrency": {
        "class": EnhancedConcurrencyAnalyzer,
        "category": "concurrency",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects shared state, thread-safety issues, async anti-patterns, lock risks",
    },

    # Security
    "security": {
        "class": SecurityAnalyzer,
        "category": "security",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects security misconfigurations and risks",
    },

    # Testing
    "test_coverage": {
        "class": TestCoverageAnalyzer,
        "category": "testing",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects test coverage blind spots and testing risks",
    },
    "broken_invariants": {
        "class": BrokenInvariantsAnalyzer,
        "category": "testing",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects broken invariants and integrity issues",
    },

    # Configuration
    "configuration": {
        "class": ConfigurationDriftAnalyzer,
        "category": "configuration",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects configuration drift and config inconsistencies",
    },
    "dependencies": {
        "class": DependencyMisuseAnalyzer,
        "category": "configuration",
        "min_plan": "developer",
        "default_enabled": True,
        "description": "Detects dependency misuse, deprecated APIs, and version conflicts",
    },

    # Phase 16: Reliability Intelligence Engine
    "crash_risk": {
        "class": CrashRiskAnalyzer,
        "category": "reliability",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects null dereference, missing error handling, unchecked returns, recursion risks",
    },
    "resource_leak": {
        "class": ResourceLeakAnalyzer,
        "category": "reliability",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects file handle, connection, memory, and thread leaks",
    },
    "reliability_pattern": {
        "class": ReliabilityPatternAnalyzer,
        "category": "reliability",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects retry without backoff, missing timeouts, silent failures, blocking in async",
    },
    "scalability_risk": {
        "class": ScalabilityRiskAnalyzer,
        "category": "reliability",
        "min_plan": "enterprise",
        "default_enabled": True,
        "description": "Detects N+1 queries, inefficient algorithms, unbounded queries, heavy computation",
    },
    "edge_case_logic": {
        "class": EdgeCaseLogicAnalyzer,
        "category": "reliability",
        "min_plan": "team",
        "default_enabled": True,
        "description": "Detects division by zero, float comparison, timezone issues, array bounds errors",
    },
}


def list_all_analyzers() -> List[Tuple[str, Dict[str, Any]]]:
    """Return a deterministic, sorted list of (analyzer_id, meta)."""
    return [(k, ANALYZER_REGISTRY[k]) for k in sorted(ANALYZER_REGISTRY.keys())]


def get_analyzer_by_id(analyzer_id: str) -> Dict[str, Any]:
    """Return analyzer metadata by stable ID. Raises KeyError if missing."""
    return ANALYZER_REGISTRY[analyzer_id]


def list_analyzers_for_plan(plan: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Deterministically list analyzers available for a subscription plan.
    No billing or gating logic here; simple metadata-based filter using plan order.
    """
    if plan not in _PLAN_ORDER:
        raise ValueError(f"Unknown plan: {plan}")
    cutoff = _PLAN_ORDER[plan]
    eligible = [
        (aid, meta)
        for aid, meta in ANALYZER_REGISTRY.items()
        if _PLAN_ORDER.get(meta.get("min_plan", "developer"), 0) <= cutoff
    ]
    # Deterministic ordering by analyzer ID
    return sorted(eligible, key=lambda x: x[0])


__all__ = [
    "ANALYZER_REGISTRY",
    "list_all_analyzers",
    "get_analyzer_by_id",
    "list_analyzers_for_plan",
]