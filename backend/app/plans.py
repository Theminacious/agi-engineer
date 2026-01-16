"""
Subscription Plan Definitions (Phase 14.1 & 14.2)

Service-centric plan model that defines capabilities as services, not analyzers.
Analyzers are implementation details; plans provide services.

Plans are immutable, deterministic, and versionable.
NO billing logic, NO Stripe integration, NO payment processing.

Phase 14.2 Additions:
- UserPlanContext: Immutable snapshot of plan at execution time
- Plan enforcement during orchestrator execution
- Ledger recording of plan context and skipped services

Plan Philosophy:
- Developer: Solo safety & insight
- Team: Collaborative intelligence  
- Enterprise: Governed autonomous engineering

Each plan defines:
- Services (analysis depth, governance, collaboration)
- Limits (users, executions, approvals)
- Non-goals (explicit exclusions)
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class PlanTier(str, Enum):
    """Subscription plan tiers (immutable ordering)."""
    DEVELOPER = "developer"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class ServiceCapability(str, Enum):
    """Service capabilities that plans provide."""
    # Analysis Services
    BASIC_ARCHITECTURE_ANALYSIS = "basic_architecture_analysis"
    ADVANCED_ARCHITECTURE_ANALYSIS = "advanced_architecture_analysis"
    BASIC_PERFORMANCE_ANALYSIS = "basic_performance_analysis"
    ADVANCED_PERFORMANCE_ANALYSIS = "advanced_performance_analysis"
    BASIC_CONCURRENCY_ANALYSIS = "basic_concurrency_analysis"
    ADVANCED_CONCURRENCY_ANALYSIS = "advanced_concurrency_analysis"
    SECURITY_ANALYSIS = "security_analysis"
    TEST_COVERAGE_ANALYSIS = "test_coverage_analysis"
    CONFIGURATION_ANALYSIS = "configuration_analysis"
    
    # Governance Services
    IMMUTABLE_LEDGER = "immutable_ledger"
    REPLAY_VERIFICATION = "replay_verification"
    AUDIT_TRAIL = "audit_trail"
    COMPLIANCE_REPORTS = "compliance_reports"
    
    # Collaboration Services
    MULTI_USER_ACCESS = "multi_user_access"
    TEAM_WORKSPACES = "team_workspaces"
    SHARED_GOVERNANCE = "shared_governance"
    
    # Automation Services
    AUTO_FIX_SAFE = "auto_fix_safe"
    AUTO_FIX_ADVANCED = "auto_fix_advanced"
    SCHEDULED_ANALYSIS = "scheduled_analysis"
    
    # Fix Management Services (Phase 15.1)
    VIEW_FIX_PROPOSALS = "view_fix_proposals"       # All plans: view AI-generated fixes
    APPROVE_FIXES = "approve_fixes"                 # Advanced+: approve fixes for application
    APPLY_FIXES = "apply_fixes"                     # Advanced+: apply approved fixes
    BATCH_FIX_APPROVAL = "batch_fix_approval"       # Enterprise: batch approve multiple fixes


@dataclass(frozen=True)
class PlanLimits:
    """Immutable limits for a plan."""
    max_users: Optional[int]  # None = unlimited
    max_monthly_executions: Optional[int]  # None = unlimited
    max_concurrent_runs: int
    max_repositories: Optional[int]  # None = unlimited
    max_file_size_mb: int
    retention_days: int


@dataclass(frozen=True)
class SubscriptionPlan:
    """
    Immutable subscription plan definition.
    
    Plans define SERVICES, not analyzers.
    Analyzers are implementation details that deliver services.
    """
    tier: PlanTier
    display_name: str
    tagline: str
    description: str
    
    # Service capabilities this plan provides
    services: frozenset[ServiceCapability]
    
    # Limits
    limits: PlanLimits
    
    # Pricing (informational only, no billing logic)
    price_display: str
    
    # Analyzer mapping (internal implementation detail)
    # Maps service capabilities to analyzer IDs
    _service_to_analyzers: Dict[ServiceCapability, List[str]] = field(default_factory=dict)
    
    def includes_service(self, capability: ServiceCapability) -> bool:
        """Check if plan includes a service capability."""
        return capability in self.services
    
    def get_analyzers_for_service(self, capability: ServiceCapability) -> List[str]:
        """Get analyzer IDs that implement a service (internal use only)."""
        return self._service_to_analyzers.get(capability, [])
    
    def get_all_analyzer_ids(self) -> List[str]:
        """Get all analyzer IDs available in this plan (implementation detail)."""
        analyzer_ids = set()
        # Only include analyzers for services this plan has
        for service in self.services:
            analyzers = self._service_to_analyzers.get(service, [])
            analyzer_ids.update(analyzers)
        return sorted(list(analyzer_ids))


@dataclass(frozen=True)
class UserPlanContext:
    """
    Immutable snapshot of a user's plan at execution time.
    
    Phase 14.2: Used for plan enforcement during orchestration.
    
    This captures:
    - Which plan tier the user has
    - Which analyzers are allowed
    - When the snapshot was taken
    
    This is NOT a database record. It's an in-memory snapshot
    that gets recorded in the ledger for auditability.
    
    NO user_id, NO billing info, NO payment state.
    Just: "For THIS run, use THIS plan."
    """
    plan_tier: PlanTier
    allowed_analyzer_ids: frozenset[str]  # Deterministic, sorted set
    snapshot_timestamp: str  # ISO 8601 timestamp
    
    @classmethod
    def from_plan(cls, plan: SubscriptionPlan) -> 'UserPlanContext':
        """Create a plan context snapshot from a subscription plan."""
        return cls(
            plan_tier=plan.tier,
            allowed_analyzer_ids=frozenset(plan.get_all_analyzer_ids()),
            snapshot_timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def is_analyzer_allowed(self, analyzer_id: str) -> bool:
        """Check if an analyzer is allowed in this plan context."""
        return analyzer_id in self.allowed_analyzer_ids
    
    def filter_allowed_analyzers(self, analyzer_ids: List[str]) -> List[str]:
        """Filter a list of analyzers to only those allowed by the plan."""
        return [aid for aid in analyzer_ids if self.is_analyzer_allowed(aid)]
    
    def get_disallowed_reason(self, analyzer_id: str) -> str:
        """Get a human-readable reason why an analyzer is disallowed."""
        if self.is_analyzer_allowed(analyzer_id):
            return ""
        return f"Analyzer '{analyzer_id}' requires a higher plan tier than {self.plan_tier.value}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for ledger recording."""
        return {
            'plan_tier': self.plan_tier.value,
            'allowed_analyzer_ids': sorted(list(self.allowed_analyzer_ids)),
            'snapshot_timestamp': self.snapshot_timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPlanContext':
        """Deserialize from dict (e.g., from ledger replay)."""
        return cls(
            plan_tier=PlanTier(data['plan_tier']),
            allowed_analyzer_ids=frozenset(data['allowed_analyzer_ids']),
            snapshot_timestamp=data['snapshot_timestamp'],
        )


# ----------------------------------------------------------------------
# Plan Definitions (Immutable, Versionable)
# ----------------------------------------------------------------------

# Service to Analyzer Mapping (Implementation Detail)
# This maps high-level services to the analyzers that deliver them
_SERVICE_TO_ANALYZER_MAP: Dict[ServiceCapability, List[str]] = {
    # Basic Architecture Services
    ServiceCapability.BASIC_ARCHITECTURE_ANALYSIS: [
        "architectural",
        "abstraction",
        "api_contracts",
        "god_objects",
    ],
    
    # Advanced Architecture Services
    ServiceCapability.ADVANCED_ARCHITECTURE_ANALYSIS: [
        "enhanced_architectural",
    ],
    
    # Basic Performance Services
    ServiceCapability.BASIC_PERFORMANCE_ANALYSIS: [
        "performance",
    ],
    
    # Advanced Performance Services
    ServiceCapability.ADVANCED_PERFORMANCE_ANALYSIS: [
        "enhanced_performance",
    ],
    
    # Basic Concurrency Services
    ServiceCapability.BASIC_CONCURRENCY_ANALYSIS: [
        "concurrency",
    ],
    
    # Advanced Concurrency Services
    ServiceCapability.ADVANCED_CONCURRENCY_ANALYSIS: [
        "enhanced_concurrency",
    ],
    
    # Security Services
    ServiceCapability.SECURITY_ANALYSIS: [
        "security",
    ],
    
    # Test Coverage Services
    ServiceCapability.TEST_COVERAGE_ANALYSIS: [
        "test_coverage",
        "broken_invariants",
    ],
    
    # Configuration Services
    ServiceCapability.CONFIGURATION_ANALYSIS: [
        "configuration",
        "dependencies",
    ],
}


# Developer Plan: Solo Safety & Insight
DEVELOPER_PLAN = SubscriptionPlan(
    tier=PlanTier.DEVELOPER,
    display_name="Developer",
    tagline="Solo safety & insight for independent builders",
    description="Essential code intelligence for individual developers. Get immediate feedback on architectural issues, performance bottlenecks, and security risks.",
    
    services=frozenset([
        # Basic analysis across all categories
        ServiceCapability.BASIC_ARCHITECTURE_ANALYSIS,
        ServiceCapability.BASIC_PERFORMANCE_ANALYSIS,
        ServiceCapability.BASIC_CONCURRENCY_ANALYSIS,
        ServiceCapability.SECURITY_ANALYSIS,
        ServiceCapability.TEST_COVERAGE_ANALYSIS,
        ServiceCapability.CONFIGURATION_ANALYSIS,
        
        # Basic governance
        ServiceCapability.IMMUTABLE_LEDGER,
        ServiceCapability.AUDIT_TRAIL,
        
        # Basic automation
        ServiceCapability.AUTO_FIX_SAFE,
        
        # Fix management (Phase 15.1): View-only
        ServiceCapability.VIEW_FIX_PROPOSALS,
    ]),
    
    limits=PlanLimits(
        max_users=1,
        max_monthly_executions=100,
        max_concurrent_runs=1,
        max_repositories=3,
        max_file_size_mb=50,
        retention_days=30,
    ),
    
    price_display="Free",
    
    _service_to_analyzers=_SERVICE_TO_ANALYZER_MAP,
)


# Team Plan: Collaborative Intelligence
TEAM_PLAN = SubscriptionPlan(
    tier=PlanTier.TEAM,
    display_name="Team",
    tagline="Collaborative intelligence for engineering teams",
    description="Advanced analysis and team collaboration. Deep insights into performance, concurrency, and architecture with multi-user workspaces and shared governance.",
    
    services=frozenset([
        # All Developer services
        ServiceCapability.BASIC_ARCHITECTURE_ANALYSIS,
        ServiceCapability.BASIC_PERFORMANCE_ANALYSIS,
        ServiceCapability.BASIC_CONCURRENCY_ANALYSIS,
        ServiceCapability.SECURITY_ANALYSIS,
        ServiceCapability.TEST_COVERAGE_ANALYSIS,
        ServiceCapability.CONFIGURATION_ANALYSIS,
        
        # Advanced analysis (Team exclusive)
        ServiceCapability.ADVANCED_ARCHITECTURE_ANALYSIS,
        ServiceCapability.ADVANCED_PERFORMANCE_ANALYSIS,
        ServiceCapability.ADVANCED_CONCURRENCY_ANALYSIS,
        
        # Advanced governance
        ServiceCapability.IMMUTABLE_LEDGER,
        ServiceCapability.REPLAY_VERIFICATION,
        ServiceCapability.AUDIT_TRAIL,
        
        # Collaboration (Team exclusive)
        ServiceCapability.MULTI_USER_ACCESS,
        ServiceCapability.TEAM_WORKSPACES,
        ServiceCapability.SHARED_GOVERNANCE,
        
        # Advanced automation
        ServiceCapability.AUTO_FIX_SAFE,
        ServiceCapability.AUTO_FIX_ADVANCED,
        ServiceCapability.SCHEDULED_ANALYSIS,
        
        # Fix management (Phase 15.1): Approve & Apply
        ServiceCapability.VIEW_FIX_PROPOSALS,
        ServiceCapability.APPROVE_FIXES,
        ServiceCapability.APPLY_FIXES,
    ]),
    
    limits=PlanLimits(
        max_users=10,
        max_monthly_executions=1000,
        max_concurrent_runs=3,
        max_repositories=20,
        max_file_size_mb=100,
        retention_days=90,
    ),
    
    price_display="$99/month",
    
    _service_to_analyzers=_SERVICE_TO_ANALYZER_MAP,
)


# Enterprise Plan: Governed Autonomous Engineering
ENTERPRISE_PLAN = SubscriptionPlan(
    tier=PlanTier.ENTERPRISE,
    display_name="Enterprise",
    tagline="Governed autonomous engineering at scale",
    description="Complete engineering intelligence with compliance-grade governance. Unlimited access to all analysis services, compliance reports, and enterprise-grade support.",
    
    services=frozenset([
        # All services (complete coverage)
        ServiceCapability.BASIC_ARCHITECTURE_ANALYSIS,
        ServiceCapability.ADVANCED_ARCHITECTURE_ANALYSIS,
        ServiceCapability.BASIC_PERFORMANCE_ANALYSIS,
        ServiceCapability.ADVANCED_PERFORMANCE_ANALYSIS,
        ServiceCapability.BASIC_CONCURRENCY_ANALYSIS,
        ServiceCapability.ADVANCED_CONCURRENCY_ANALYSIS,
        ServiceCapability.SECURITY_ANALYSIS,
        ServiceCapability.TEST_COVERAGE_ANALYSIS,
        ServiceCapability.CONFIGURATION_ANALYSIS,
        
        # Enterprise governance
        ServiceCapability.IMMUTABLE_LEDGER,
        ServiceCapability.REPLAY_VERIFICATION,
        ServiceCapability.AUDIT_TRAIL,
        ServiceCapability.COMPLIANCE_REPORTS,
        
        # Enterprise collaboration
        ServiceCapability.MULTI_USER_ACCESS,
        ServiceCapability.TEAM_WORKSPACES,
        ServiceCapability.SHARED_GOVERNANCE,
        
        # Enterprise automation
        ServiceCapability.AUTO_FIX_SAFE,
        ServiceCapability.AUTO_FIX_ADVANCED,
        ServiceCapability.SCHEDULED_ANALYSIS,
        
        # Fix management (Phase 15.1): Full capabilities + Batch
        ServiceCapability.VIEW_FIX_PROPOSALS,
        ServiceCapability.APPROVE_FIXES,
        ServiceCapability.APPLY_FIXES,
        ServiceCapability.BATCH_FIX_APPROVAL,
    ]),
    
    limits=PlanLimits(
        max_users=None,  # Unlimited
        max_monthly_executions=None,  # Unlimited
        max_concurrent_runs=10,
        max_repositories=None,  # Unlimited
        max_file_size_mb=500,
        retention_days=365,
    ),
    
    price_display="Custom",
    
    _service_to_analyzers=_SERVICE_TO_ANALYZER_MAP,
)


# Plan Registry (Immutable)
PLAN_REGISTRY: Dict[PlanTier, SubscriptionPlan] = {
    PlanTier.DEVELOPER: DEVELOPER_PLAN,
    PlanTier.TEAM: TEAM_PLAN,
    PlanTier.ENTERPRISE: ENTERPRISE_PLAN,
}


# Plan Ordering (for comparisons)
PLAN_ORDER: Dict[PlanTier, int] = {
    PlanTier.DEVELOPER: 0,
    PlanTier.TEAM: 1,
    PlanTier.ENTERPRISE: 2,
}


# ----------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------

def get_plan(tier: PlanTier) -> SubscriptionPlan:
    """Get plan definition by tier."""
    return PLAN_REGISTRY[tier]


def get_all_plans() -> List[SubscriptionPlan]:
    """Get all plans in order (developer → team → enterprise)."""
    return [
        PLAN_REGISTRY[PlanTier.DEVELOPER],
        PLAN_REGISTRY[PlanTier.TEAM],
        PLAN_REGISTRY[PlanTier.ENTERPRISE],
    ]


def plan_includes_service(tier: PlanTier, capability: ServiceCapability) -> bool:
    """Check if a plan includes a service capability."""
    plan = PLAN_REGISTRY[tier]
    return plan.includes_service(capability)


def get_plan_for_user(user_id: Optional[int] = None) -> SubscriptionPlan:
    """
    Get subscription plan for a user.
    
    Phase 14.1: Always returns Developer (no billing yet).
    Phase 14.2+: Will query subscription database.
    """
    # TODO Phase 14.2: Query subscription table
    return DEVELOPER_PLAN


def compare_plans(tier_a: PlanTier, tier_b: PlanTier) -> int:
    """
    Compare two plans.
    
    Returns:
        -1 if tier_a < tier_b
        0 if tier_a == tier_b
        1 if tier_a > tier_b
    """
    order_a = PLAN_ORDER[tier_a]
    order_b = PLAN_ORDER[tier_b]
    
    if order_a < order_b:
        return -1
    elif order_a > order_b:
        return 1
    else:
        return 0


def get_locked_services(user_plan: PlanTier, required_plan: PlanTier) -> List[ServiceCapability]:
    """
    Get services that are locked for user_plan but available in required_plan.
    
    Used for UI to explain "why locked?"
    """
    user_services = PLAN_REGISTRY[user_plan].services
    required_services = PLAN_REGISTRY[required_plan].services
    
    return sorted([s for s in required_services if s not in user_services])


# ----------------------------------------------------------------------
# Phase 14.2: Plan Context Creation (Enforcement)
# ----------------------------------------------------------------------

def create_plan_context(plan_tier: PlanTier) -> UserPlanContext:
    """
    Create an immutable plan context snapshot for execution.
    
    This is the entry point for plan enforcement.
    Every run execution should call this to get a plan context.
    
    Args:
        plan_tier: The plan tier to create context for
        
    Returns:
        Immutable UserPlanContext for this execution
        
    Example:
        plan_ctx = create_plan_context(PlanTier.DEVELOPER)
        # Now pass plan_ctx to orchestrator
    """
    plan = get_plan(plan_tier)
    return UserPlanContext.from_plan(plan)


def create_default_plan_context() -> UserPlanContext:
    """
    Create a default plan context (Developer tier).
    
    Used when no explicit plan is specified.
    Safe fallback for testing and development.
    """
    return create_plan_context(PlanTier.DEVELOPER)
