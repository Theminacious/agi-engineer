"""Data models for AGI Engineer V2."""

from app.db.base import Base

# Import all models to register them with SQLAlchemy
from app.models.installation import Installation
from app.models.repository import Repository
from app.models.analysis_run import AnalysisRun
from app.models.analysis_result import AnalysisResult

__all__ = ["Base", "Installation", "Repository", "AnalysisRun", "AnalysisResult"]
