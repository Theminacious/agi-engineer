"""Intra- and inter-file call-graph construction.

Walks the AST of every function / method body to discover which other
functions are invoked, then emits ``EdgeType.CALLS`` edges into the
``CodeGraph``.

Design
------
* Call targets are resolved *by name* (best-effort static analysis).
* Fully-qualified node-ids are matched when possible; unresolved names
  are stored as metadata so LLM-based resolution can be added later.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .graph_store import CodeGraph, Edge, EdgeType, Node, NodeType
from .symbol_extractor import ClassInfo, FunctionInfo, SymbolTable

logger = logging.getLogger(__name__)


class CallGraphBuilder:
    """Populate ``CALLS`` edges in a :class:`CodeGraph`.

    Usage::

        builder = CallGraphBuilder()
        builder.build(graph, symbol_tables)

    Where *symbol_tables* is the list of ``SymbolTable`` objects
    produced by :class:`SymbolExtractor` for every file in the repo.
    """

    def build(
        self,
        graph: CodeGraph,
        symbol_tables: List[SymbolTable],
    ) -> None:
        """Analyse every function body and emit call edges.

        Parameters
        ----------
        graph:
            The graph to mutate (must already contain function / method nodes).
        symbol_tables:
            One per parsed Python file.
        """
        # Build a lookup: short_name -> list of node-ids that match.
        name_index = self._build_name_index(graph)

        for table in symbol_tables:
            # Top-level functions
            for func in table.functions:
                source_id = f"{table.file_path}::{func.name}"
                self._emit_calls(graph, source_id, func.calls, name_index, table.file_path)

            # Methods inside classes
            for cls in table.classes:
                for method in cls.methods:
                    source_id = f"{table.file_path}::{cls.name}.{method.name}"
                    self._emit_calls(graph, source_id, method.calls, name_index, table.file_path)

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _build_name_index(graph: CodeGraph) -> Dict[str, List[str]]:
        """Map short names (and dotted names) to their full node ids."""
        index: Dict[str, List[str]] = {}
        for node_id, node in graph.nodes.items():
            if node.node_type in (NodeType.FUNCTION, NodeType.METHOD):
                # "my_func" or "MyClass.my_method"
                index.setdefault(node.name, []).append(node_id)
                # Also index by "Class.method" form
                parts = node_id.rsplit("::", 1)
                if len(parts) == 2:
                    short = parts[1]
                    index.setdefault(short, []).append(node_id)
        return index

    def _emit_calls(
        self,
        graph: CodeGraph,
        source_id: str,
        call_names: List[str],
        name_index: Dict[str, List[str]],
        source_file: str,
    ) -> None:
        """Resolve *call_names* to node-ids and add edges."""
        seen: set = set()
        for raw_name in call_names:
            # Normalise: "self.foo" → "foo"
            name = raw_name.rsplit("self.", 1)[-1] if "self." in raw_name else raw_name

            targets = self._resolve(name, name_index, source_file)
            for target_id in targets:
                pair = (source_id, target_id)
                if pair in seen or source_id == target_id:
                    continue
                seen.add(pair)
                graph.add_edge(Edge(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=EdgeType.CALLS,
                    metadata={"raw_name": raw_name},
                ))

    @staticmethod
    def _resolve(
        name: str,
        name_index: Dict[str, List[str]],
        source_file: str,
    ) -> List[str]:
        """Best-effort resolution of a call target.

        Preference order:
        1. Exact match in the same file.
        2. Any match across the codebase.
        """
        candidates = name_index.get(name, [])
        if not candidates:
            # Try the tail segment for dotted names (e.g. "db.query" → "query")
            tail = name.rsplit(".", 1)[-1]
            candidates = name_index.get(tail, [])

        if not candidates:
            return []

        # Prefer same-file match
        local = [c for c in candidates if c.startswith(source_file + "::")]
        return local if local else candidates
