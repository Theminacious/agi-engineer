"""Data models for AGI Engineer V2."""

from app.db.base import Base

# Import all models to register them with SQLAlchemy
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.analysis_run import AnalysisRun
from app.models.analysis_result import AnalysisResult
from app.models.code_fix import CodeFix, GitHubPullRequest, FixStatus
from app.models.team import Team, ActivityLog
from app.models.user import User
from app.models.github_integration import (
	GitHubWebhookEvent,
	PRAnalysis,
	GitHubIntegrationConfig,
	WebhookEventType,
	PRAnalysisStatus,
	ReliabilityScore,
)
from app.models.reliability_metrics import (
	RepoMetrics,
	RiskSnapshot,
	ReliabilityScore as ReliabilityScoreMetric,
	ReliabilityHotspot,
)

__all__ = [
	"Base",
	"Installation",
	"Repository",
	"AnalysisRun",
	"AnalysisResult",
	"CodeFix",
	"GitHubPullRequest",
	"FixStatus",
	"Team",
	"ActivityLog",
	"User",
	"GitHubWebhookEvent",
	"PRAnalysis",
	"GitHubIntegrationConfig",
	"WebhookEventType",
	"PRAnalysisStatus",
	"ReliabilityScore",
	"RepoMetrics",
	"RiskSnapshot",
	"ReliabilityScoreMetric",
	"ReliabilityHotspot",
]
