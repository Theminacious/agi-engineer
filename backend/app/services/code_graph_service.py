"""Service layer for the Code Intelligence Graph Engine.

Provides a thin integration facade used by routers, background tasks,
and other services to generate, cache, and query code graphs.

Usage from a FastAPI endpoint::

    from app.services.code_graph_service import CodeGraphService

    svc = CodeGraphService()
    graph = svc.generate_repo_graph("/repos/my-app")
    impact = svc.get_impact_set(graph, "src/auth.py::login")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from app.intelligence.code_graph import (
    CodeGraph,
    CodeGraphBuilder,
    NodeType,
)

logger = logging.getLogger(__name__)


@dataclass
class GraphGenerationResult:
    """Metadata returned alongside a freshly-built graph."""

    graph: CodeGraph
    repo_path: str
    file_count: int
    node_count: int
    edge_count: int
    build_time_ms: float
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "file_count": self.file_count,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "build_time_ms": round(self.build_time_ms, 2),
            "errors": self.errors,
            "summary": self.graph.summary(),
        }


class CodeGraphService:
    """Application-level service for code-graph operations.

    Stateless by design — each call rebuilds the graph.  A future
    iteration can add caching (Redis / in-process LRU) keyed by
    ``(repo_path, commit_sha)``.
    """

    def __init__(self, skip_dirs: Optional[Set[str]] = None) -> None:
        self._builder = CodeGraphBuilder(skip_dirs=skip_dirs)

    # ── Primary entry point ──────────────────────────────────────

    def generate_repo_graph(self, repo_path: str) -> GraphGenerationResult:
        """Build a full code graph for the repository at *repo_path*.

        Returns
        -------
        GraphGenerationResult
            The graph plus metadata about the build.
        """
        t0 = time.monotonic()
        errors: List[str] = []

        try:
            graph = self._builder.build_graph(repo_path)
        except FileNotFoundError as exc:
            logger.error("Repo path not found: %s", exc)
            raise
        except Exception as exc:
            logger.exception("Unexpected error building graph for %s", repo_path)
            raise RuntimeError(f"Graph build failed: {exc}") from exc

        elapsed_ms = (time.monotonic() - t0) * 1000
        file_count = len(graph.get_nodes_by_type(NodeType.FILE))

        result = GraphGenerationResult(
            graph=graph,
            repo_path=repo_path,
            file_count=file_count,
            node_count=len(graph.nodes),
            edge_count=len(graph.edges),
            build_time_ms=elapsed_ms,
            errors=errors,
        )
        logger.info(
            "Graph generated for %s in %.1f ms — %d nodes, %d edges",
            repo_path, elapsed_ms, result.node_count, result.edge_count,
        )
        return result

    # ── Query helpers (delegate to CodeGraph) ────────────────────

    @staticmethod
    def get_impact_set(
        graph: CodeGraph,
        node_id: str,
        max_depth: int = 3,
    ) -> Set[str]:
        """Return the set of node-ids transitively affected by *node_id*."""
        return graph.get_impact_set(node_id, max_depth=max_depth)

    @staticmethod
    def get_file_dependencies(graph: CodeGraph, file_path: str) -> List[str]:
        """Return file-node ids that *file_path* depends on."""
        deps = graph.get_dependencies(file_path)
        return [d.id for d in deps]

    @staticmethod
    def get_file_dependents(graph: CodeGraph, file_path: str) -> List[str]:
        """Return file-node ids that depend on *file_path*."""
        deps = graph.get_dependents(file_path)
        return [d.id for d in deps]
