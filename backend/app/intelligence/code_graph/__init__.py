"""Phase 19 — Code Intelligence Graph Engine.

Provides a semantic graph representation of a Python codebase:
files, classes, functions, imports, call relationships, and
module-level dependencies.

Quick start
-----------
>>> from app.intelligence.code_graph import CodeGraphBuilder
>>> graph = CodeGraphBuilder().build_graph("repo/")
>>> print(graph.summary())
"""

from .graph_store import CodeGraph, NodeType, EdgeType, Node, Edge
from .symbol_extractor import SymbolExtractor, SymbolTable
from .call_graph import CallGraphBuilder
from .dependency_mapper import DependencyMapper
from .code_graph_builder import CodeGraphBuilder

__all__ = [
    "CodeGraph",
    "CodeGraphBuilder",
    "CallGraphBuilder",
    "DependencyMapper",
    "SymbolExtractor",
    "SymbolTable",
    "NodeType",
    "EdgeType",
    "Node",
    "Edge",
]
