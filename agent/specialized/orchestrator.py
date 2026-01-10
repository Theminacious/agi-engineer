"""Agent orchestrator for coordinating multiple specialized agents."""

import asyncio
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from .base_agent import BaseAgent, AgentResult, AgentType, IssueSeverity

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates multiple specialized agents for comprehensive analysis."""
    
    def __init__(self, agents: Optional[List[BaseAgent]] = None):
        """Initialize orchestrator.
        
        Args:
            agents: List of agents to coordinate (will auto-discover if None)
        """
        self.agents: Dict[AgentType, BaseAgent] = {}
        if agents:
            for agent in agents:
                self.register_agent(agent)
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent.
        
        Args:
            agent: Agent to register
        """
        self.agents[agent.agent_type] = agent
        logger.info(f"Registered agent: {agent.agent_type.value}")
    
    def unregister_agent(self, agent_type: AgentType) -> None:
        """Unregister an agent.
        
        Args:
            agent_type: Type of agent to remove
        """
        if agent_type in self.agents:
            del self.agents[agent_type]
            logger.info(f"Unregistered agent: {agent_type.value}")
    
    async def analyze_parallel(
        self, 
        repo_path: str, 
        files: Optional[List[str]] = None,
        agent_types: Optional[List[AgentType]] = None
    ) -> Dict[str, Any]:
        """Run all agents in parallel.
        
        Args:
            repo_path: Path to repository
            files: List of files to analyze (None = all files)
            agent_types: Specific agents to run (None = all registered)
            
        Returns:
            Aggregated results from all agents
        """
        start_time = time.time()
        
        # Discover files if not provided
        if files is None:
            files = self._discover_files(repo_path)
        
        # Determine which agents to run
        agents_to_run = []
        if agent_types:
            agents_to_run = [self.agents[at] for at in agent_types if at in self.agents]
        else:
            agents_to_run = list(self.agents.values())
        
        if not agents_to_run:
            logger.warning("No agents available to run")
            return self._empty_result()
        
        logger.info(f"Running {len(agents_to_run)} agents in parallel on {len(files)} files")
        
        # Run agents concurrently
        tasks = [agent.analyze(repo_path, files) for agent in agents_to_run]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        aggregated = self._aggregate_results(results, agents_to_run)
        aggregated['execution_time_ms'] = (time.time() - start_time) * 1000
        
        logger.info(
            f"Analysis complete: {aggregated['total_issues']} issues found "
            f"in {aggregated['execution_time_ms']:.2f}ms"
        )
        
        return aggregated
    
    async def analyze_sequential(
        self,
        repo_path: str,
        files: Optional[List[str]] = None,
        agent_types: Optional[List[AgentType]] = None
    ) -> Dict[str, Any]:
        """Run agents sequentially (useful for debugging).
        
        Args:
            repo_path: Path to repository
            files: List of files to analyze
            agent_types: Specific agents to run
            
        Returns:
            Aggregated results
        """
        start_time = time.time()
        
        if files is None:
            files = self._discover_files(repo_path)
        
        agents_to_run = []
        if agent_types:
            agents_to_run = [self.agents[at] for at in agent_types if at in self.agents]
        else:
            agents_to_run = list(self.agents.values())
        
        results = []
        for agent in agents_to_run:
            try:
                result = await agent.analyze(repo_path, files)
                results.append(result)
            except Exception as e:
                logger.error(f"Agent {agent.agent_type.value} failed: {e}", exc_info=True)
                results.append(e)
        
        aggregated = self._aggregate_results(results, agents_to_run)
        aggregated['execution_time_ms'] = (time.time() - start_time) * 1000
        
        return aggregated
    
    def _discover_files(self, repo_path: str) -> List[str]:
        """Discover all relevant files in repository.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            List of file paths relative to repo_path
        """
        repo = Path(repo_path)
        files = []
        
        # Extensions to analyze
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rb', '.php', '.cs'}
        
        # Directories to skip
        skip_dirs = {'node_modules', '.git', '__pycache__', 'venv', 'env', '.next', 'dist', 'build'}
        
        for file_path in repo.rglob('*'):
            if file_path.is_file():
                # Skip if in excluded directory
                if any(skip_dir in file_path.parts for skip_dir in skip_dirs):
                    continue
                
                # Keep if has relevant extension
                if file_path.suffix in extensions:
                    relative_path = str(file_path.relative_to(repo))
                    files.append(relative_path)
        
        logger.info(f"Discovered {len(files)} files for analysis")
        return files
    
    def _aggregate_results(
        self,
        results: List[Any],
        agents: List[BaseAgent]
    ) -> Dict[str, Any]:
        """Aggregate results from multiple agents.
        
        Args:
            results: List of AgentResult or Exception objects
            agents: List of agents that ran
            
        Returns:
            Aggregated analysis result
        """
        all_issues = []
        agent_results = {}
        metrics = {}
        errors = []
        
        for agent, result in zip(agents, results):
            agent_type = agent.agent_type.value
            
            if isinstance(result, Exception):
                errors.append({
                    'agent': agent_type,
                    'error': str(result)
                })
                logger.error(f"Agent {agent_type} failed: {result}")
                continue
            
            if isinstance(result, AgentResult):
                all_issues.extend(result.issues)
                agent_results[agent_type] = result.to_dict()
                metrics[agent_type] = result.metrics
        
        # Sort issues by severity
        severity_order = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 1,
            IssueSeverity.MEDIUM: 2,
            IssueSeverity.LOW: 3,
            IssueSeverity.INFO: 4,
        }
        all_issues.sort(key=lambda x: severity_order.get(x.severity, 999))
        
        # Calculate statistics
        severity_counts = {}
        for issue in all_issues:
            severity = issue.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            'total_issues': len(all_issues),
            'issues': [issue.to_dict() for issue in all_issues],
            'severity_breakdown': severity_counts,
            'agent_results': agent_results,
            'metrics': metrics,
            'errors': errors,
            'agents_run': [a.agent_type.value for a in agents],
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'total_issues': 0,
            'issues': [],
            'severity_breakdown': {},
            'agent_results': {},
            'metrics': {},
            'errors': [],
            'agents_run': [],
            'execution_time_ms': 0,
        }
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all registered agents.
        
        Returns:
            Dictionary of agent capabilities
        """
        capabilities = {}
        for agent_type, agent in self.agents.items():
            capabilities[agent_type.value] = agent.get_capabilities()
        return capabilities
