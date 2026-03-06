"""High-level orchestrator that builds a full :class:`CodeGraph`.

Walks a repository directory, extracts symbols from every Python file,
and delegates to :class:`CallGraphBuilder` and :class:`DependencyMapper`
to populate all edges.

Usage
-----
>>> from app.intelligence.code_graph import CodeGraphBuilder
>>> graph = CodeGraphBuilder().build_graph("repo/")
>>> print(graph.summary())
CodeGraph: 42 nodes, 87 edges
  Node types: {'file': 8, 'class': 10, 'function': 14, 'method': 10}
  Edge types: {'defines': 24, 'contains': 10, 'calls': 38, 'imports': 15}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Set

from .call_graph import CallGraphBuilder
from .dependency_mapper import DependencyMapper
from .graph_store import CodeGraph, Edge, EdgeType, Node, NodeType
from .symbol_extractor import SymbolExtractor, SymbolTable

logger = logging.getLogger(__name__)

# Directories to always skip
_DEFAULT_SKIP_DIRS: Set[str] = {
    "__pycache__", ".git", ".venv", "venv", "node_modules",
    ".mypy_cache", ".pytest_cache", ".tox", "dist", "build",
    "egg-info", ".eggs",
}


class CodeGraphBuilder:
    """One-call entry point for constructing a repository code graph.

    Parameters
    ----------
    skip_dirs:
        Directory basenames to skip during the walk.
    """

    def __init__(self, skip_dirs: Optional[Set[str]] = None) -> None:
        self._skip_dirs = skip_dirs or _DEFAULT_SKIP_DIRS
        self._extractor = SymbolExtractor()
        self._call_builder = CallGraphBuilder()
        self._dep_mapper = DependencyMapper()

    def build_graph(self, repo_path: str) -> CodeGraph:
        """Walk *repo_path*, parse every ``.py`` file, and return a graph.

        Parameters
        ----------
        repo_path:
            Path to the repository root (absolute or relative).

        Returns
        -------
        CodeGraph
            Fully populated graph with nodes and all edge types.
        """
        root = Path(repo_path).resolve()
        if not root.is_dir():
            raise FileNotFoundError(f"Repository path does not exist: {root}")

        graph = CodeGraph()
        symbol_tables: List[SymbolTable] = []

        # Phase 1 — discover files and extract symbols
        py_files = self._collect_python_files(root)
        logger.info("Found %d Python files in %s", len(py_files), root)

        for py_file in py_files:
            rel_path = str(py_file.relative_to(root))
            table = self._extractor.extract(str(py_file))
            # Normalise file_path to relative
            table.file_path = rel_path
            symbol_tables.append(table)
            self._add_file_nodes(graph, rel_path, table)

        # Phase 2 — call graph
        self._call_builder.build(graph, symbol_tables)

        # Phase 3 — module dependencies
        self._dep_mapper.build(graph, symbol_tables)

        logger.info("Graph built: %s", graph.summary())
        return graph

    # ── Private helpers ──────────────────────────────────────────

    def _collect_python_files(self, root: Path) -> List[Path]:
        """Recursively gather ``.py`` files, skipping excluded dirs."""
        files: List[Path] = []
        for item in sorted(root.rglob("*.py")):
            # Check whether any parent directory should be skipped
            if any(part in self._skip_dirs for part in item.relative_to(root).parts):
                continue
            files.append(item)
        return files

    def _add_file_nodes(
        self,
        graph: CodeGraph,
        rel_path: str,
        table: SymbolTable,
    ) -> None:
        """Create nodes for the file and all symbols it defines."""

        # 1. File node
        file_node = Node(
            id=rel_path,
            node_type=NodeType.FILE,
            name=Path(rel_path).name,
            file_path=rel_path,
            metadata={"module_docstring": table.module_docstring},
        )
        graph.add_node(file_node)

        # 2. Top-level functions
        for func in table.functions:
            func_id = f"{rel_path}::{func.name}"
            graph.add_node(Node(
                id=func_id,
                node_type=NodeType.FUNCTION,
                name=func.name,
                file_path=rel_path,
                line_number=func.line_number,
                metadata={
                    "args": func.args,
                    "decorators": func.decorators,
                    "is_async": func.is_async,
                    "docstring": func.docstring,
                },
            ))
            graph.add_edge(Edge(
                source_id=rel_path,
                target_id=func_id,
                edge_type=EdgeType.DEFINES,
            ))

        # 3. Classes and their methods
        for cls in table.classes:
            cls_id = f"{rel_path}::{cls.name}"
            graph.add_node(Node(
                id=cls_id,
                node_type=NodeType.CLASS,
                name=cls.name,
                file_path=rel_path,
                line_number=cls.line_number,
                metadata={
                    "bases": cls.bases,
                    "decorators": cls.decorators,
                    "docstring": cls.docstring,
                },
            ))
            graph.add_edge(Edge(
                source_id=rel_path,
                target_id=cls_id,
                edge_type=EdgeType.DEFINES,
            ))

            # Inheritance edges
            for base_name in cls.bases:
                graph.add_edge(Edge(
                    source_id=cls_id,
                    target_id=base_name,   # may be unresolved; consumer handles
                    edge_type=EdgeType.INHERITS,
                    metadata={"raw_base": base_name},
                ))

            # Methods
            for method in cls.methods:
                method_id = f"{rel_path}::{cls.name}.{method.name}"
                graph.add_node(Node(
                    id=method_id,
                    node_type=NodeType.METHOD,
                    name=method.name,
                    file_path=rel_path,
                    line_number=method.line_number,
                    metadata={
                        "args": method.args,
                        "decorators": method.decorators,
                        "is_async": method.is_async,
                        "docstring": method.docstring,
                    },
                ))
                graph.add_edge(Edge(
                    source_id=cls_id,
                    target_id=method_id,
                    edge_type=EdgeType.CONTAINS,
                ))
