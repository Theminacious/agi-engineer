"""Module-level dependency mapping.

Analyses ``import`` / ``from … import`` statements extracted by
:class:`SymbolExtractor` and emits ``EdgeType.IMPORTS`` edges
linking file nodes in the :class:`CodeGraph`.

This enables downstream consumers (architecture analysis, risk
propagation) to answer questions like *"which modules depend on
database.py?"*.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath
from typing import Dict, List, Optional

from .graph_store import CodeGraph, Edge, EdgeType, Node, NodeType
from .symbol_extractor import ImportInfo, SymbolTable

logger = logging.getLogger(__name__)


class DependencyMapper:
    """Populate ``IMPORTS`` edges between file / module nodes.

    Usage::

        mapper = DependencyMapper()
        mapper.build(graph, symbol_tables, repo_root="backend")
    """

    def build(
        self,
        graph: CodeGraph,
        symbol_tables: List[SymbolTable],
        repo_root: str = "",
    ) -> None:
        """Resolve imports to known file nodes and add edges.

        Parameters
        ----------
        graph:
            Must already contain ``NodeType.FILE`` / ``NodeType.MODULE`` nodes.
        symbol_tables:
            One per parsed Python file.
        repo_root:
            Prefix stripped from file paths when building the module-name
            lookup table (e.g. ``"backend"``).
        """
        # Build lookup: dotted.module.name -> file node-id
        module_index = self._build_module_index(graph, repo_root)

        for table in symbol_tables:
            source_id = table.file_path
            for imp in table.imports:
                target_ids = self._resolve_import(imp, module_index)
                for tid in target_ids:
                    if tid == source_id:
                        continue
                    graph.add_edge(Edge(
                        source_id=source_id,
                        target_id=tid,
                        edge_type=EdgeType.IMPORTS,
                        metadata={
                            "module": imp.module,
                            "names": imp.names,
                            "is_from": imp.is_from,
                        },
                    ))

    # ── Internal ─────────────────────────────────────────────────

    @staticmethod
    def _build_module_index(graph: CodeGraph, repo_root: str) -> Dict[str, str]:
        """Map dotted module paths to file-node ids.

        Example: ``"app.services.auth"`` → ``"backend/app/services/auth.py"``
        """
        index: Dict[str, str] = {}
        for node_id, node in graph.nodes.items():
            if node.node_type not in (NodeType.FILE, NodeType.MODULE):
                continue

            path = node.file_path or node_id
            # Strip optional repo_root prefix
            rel = path
            if repo_root and rel.startswith(repo_root):
                rel = rel[len(repo_root):].lstrip("/")

            # Convert path to dotted module name
            module_name = (
                rel
                .replace("/", ".")
                .replace("\\", ".")
                .removesuffix(".py")
                .removesuffix(".__init__")
            )
            if module_name:
                index[module_name] = node_id

            # Also index by filename stem (e.g. "auth")
            stem = PurePosixPath(path).stem
            if stem != "__init__":
                index.setdefault(stem, node_id)

        return index

    @staticmethod
    def _resolve_import(
        imp: ImportInfo,
        module_index: Dict[str, str],
    ) -> List[str]:
        """Try to map an import to one or more file-node ids."""
        candidates: List[str] = []

        # Direct match on full module path
        if imp.module in module_index:
            candidates.append(module_index[imp.module])
            return candidates

        # Try progressively shorter prefixes
        # e.g. "app.services.auth.utils" → "app.services.auth" → …
        parts = imp.module.split(".")
        for i in range(len(parts) - 1, 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in module_index:
                candidates.append(module_index[prefix])
                return candidates

        # Fallback: match on the last segment (short name)
        short = parts[-1] if parts else ""
        if short and short in module_index:
            candidates.append(module_index[short])

        return candidates
