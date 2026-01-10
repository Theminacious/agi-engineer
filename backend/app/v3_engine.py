"""AGI Engineer v3 - Multi-Agent Analysis Engine.

This module provides the advanced multi-agent analysis system that coordinates
specialized agents for comprehensive code analysis.
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from agent.specialized.orchestrator import AgentOrchestrator
from agent.specialized.security_agent import SecurityAgent
from agent.specialized.performance_agent import PerformanceAgent
from agent.specialized.architecture_agent import ArchitectureAgent
from agent.specialized.test_agent import TestAgent
from agent.specialized.documentation_agent import DocumentationAgent

logger = logging.getLogger(__name__)


class V3AnalysisEngine:
    """AGI Engineer v3 - Multi-agent analysis engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize v3 engine with specialized agents.
        
        Args:
            config: Optional configuration for agents
        """
        self.config = config or {}
        self.orchestrator = AgentOrchestrator()
        
        # Register specialized agents
        self._register_agents()
        
        logger.info("AGI Engineer v3 initialized with multi-agent system")
    
    def _register_agents(self) -> None:
        """Register all specialized agents."""
        # Security Agent
        security_config = self.config.get('security', {})
        self.orchestrator.register_agent(SecurityAgent(security_config))
        
        # Performance Agent
        perf_config = self.config.get('performance', {})
        self.orchestrator.register_agent(PerformanceAgent(perf_config))
        
        # Architecture Agent
        arch_config = self.config.get('architecture', {})
        self.orchestrator.register_agent(ArchitectureAgent(arch_config))
        
        # Test Agent
        test_config = self.config.get('test', {})
        self.orchestrator.register_agent(TestAgent())
        
        # Documentation Agent
        doc_config = self.config.get('documentation', {})
        self.orchestrator.register_agent(DocumentationAgent())
        
        logger.info(f"Registered {len(self.orchestrator.agents)} specialized agents")
    
    async def analyze_repository(
        self,
        repo_path: str,
        files: Optional[List[str]] = None,
        agents: Optional[List[str]] = None,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """Analyze repository with multi-agent system.
        
        Args:
            repo_path: Path to repository
            files: Specific files to analyze (None = all)
            agents: Specific agents to run (None = all)
            parallel: Run agents in parallel (True) or sequential (False)
            
        Returns:
            Comprehensive analysis results from all agents
        """
        start_time = time.time()
        
        logger.info(
            f"Starting v3 analysis: repo={repo_path}, "
            f"files={len(files) if files else 'all'}, "
            f"agents={agents or 'all'}, "
            f"parallel={parallel}"
        )
        
        # Convert agent names to AgentType if provided
        agent_types = None
        if agents:
            from agent.specialized.base_agent import AgentType
            agent_type_map = {
                'security': AgentType.SECURITY,
                'performance': AgentType.PERFORMANCE,
                'architecture': AgentType.ARCHITECTURE,
            }
            agent_types = [agent_type_map[a] for a in agents if a in agent_type_map]
        
        # Run analysis
        if parallel:
            results = await self.orchestrator.analyze_parallel(
                repo_path=repo_path,
                files=files,
                agent_types=agent_types
            )
        else:
            results = await self.orchestrator.analyze_sequential(
                repo_path=repo_path,
                files=files,
                agent_types=agent_types
            )
        
        # Add v3 metadata
        results['v3_metadata'] = {
            'version': '3.0.0',
            'parallel_execution': parallel,
            'total_execution_time_ms': (time.time() - start_time) * 1000,
            'agents_available': list(self.orchestrator.agents.keys()),
        }
        
        logger.info(
            f"v3 analysis complete: {results['total_issues']} issues found "
            f"in {results['execution_time_ms']:.2f}ms"
        )
        
        return results
    
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of all registered agents.
        
        Returns:
            Dictionary of agent capabilities
        """
        return self.orchestrator.get_agent_capabilities()
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names.
        
        Returns:
            List of agent type names
        """
        return [agent_type.value for agent_type in self.orchestrator.agents.keys()]


def create_v3_engine(config: Optional[Dict[str, Any]] = None) -> V3AnalysisEngine:
    """Factory function to create v3 analysis engine.
    
    Args:
        config: Optional configuration
        
    Returns:
        Initialized V3AnalysisEngine
    """
    return V3AnalysisEngine(config)
