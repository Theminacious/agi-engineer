"""Base agent class for specialized code analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of specialized agents."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    TEST = "test"
    DOCUMENTATION = "documentation"


class IssueSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"  # Must fix immediately
    HIGH = "high"          # Should fix soon
    MEDIUM = "medium"      # Should fix eventually
    LOW = "low"            # Nice to have
    INFO = "info"          # Informational only


@dataclass
class AgentIssue:
    """Issue detected by an agent."""
    file_path: str
    line_number: int
    issue_type: str
    severity: IssueSeverity
    title: str
    description: str
    recommendation: str
    code_snippet: Optional[str] = None
    references: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0.0 to 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'issue_type': self.issue_type,
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'recommendation': self.recommendation,
            'code_snippet': self.code_snippet,
            'references': self.references,
            'tags': self.tags,
            'confidence': self.confidence,
        }


@dataclass
class AgentResult:
    """Result from agent analysis."""
    agent_type: AgentType
    issues: List[AgentIssue]
    metrics: Dict[str, Any]
    summary: str
    execution_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'agent_type': self.agent_type.value,
            'issues': [issue.to_dict() for issue in self.issues],
            'metrics': self.metrics,
            'summary': self.summary,
            'execution_time_ms': self.execution_time_ms,
        }


class BaseAgent(ABC):
    """Base class for all specialized agents."""
    
    def __init__(self, agent_type: AgentType, config: Optional[Dict[str, Any]] = None):
        """Initialize agent.
        
        Args:
            agent_type: Type of this agent
            config: Optional configuration dictionary
        """
        self.agent_type = agent_type
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{agent_type.value}")
    
    @abstractmethod
    async def analyze(self, repo_path: str, files: List[str]) -> AgentResult:
        """Analyze repository.
        
        Args:
            repo_path: Path to repository root
            files: List of files to analyze
            
        Returns:
            AgentResult with findings
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities.
        
        Returns:
            Dictionary describing what this agent can do
        """
        pass
    
    def filter_files(self, files: List[str], extensions: List[str]) -> List[str]:
        """Filter files by extension.
        
        Args:
            files: List of file paths
            extensions: List of extensions to keep (e.g., ['.py', '.js'])
            
        Returns:
            Filtered list of files
        """
        return [f for f in files if any(f.endswith(ext) for ext in extensions)]
    
    def log_analysis_start(self, repo_path: str, file_count: int) -> None:
        """Log analysis start."""
        self.logger.info(
            f"{self.agent_type.value.title()}Agent starting analysis: "
            f"{file_count} files in {repo_path}"
        )
    
    def log_analysis_complete(self, issue_count: int, execution_time_ms: float) -> None:
        """Log analysis completion."""
        self.logger.info(
            f"{self.agent_type.value.title()}Agent complete: "
            f"{issue_count} issues found in {execution_time_ms:.2f}ms"
        )
