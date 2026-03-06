"""In-memory semantic graph store.

Provides the core data structures — nodes, edges, and the ``CodeGraph``
container — used by every other component in the code-graph engine.

Design notes
------------
* Zero external dependencies (stdlib only).
* Dataclass-based for easy serialisation later (JSON / msgpack / LLM
  context windows).
* Indexed by node-id for O(1) lookups; adjacency lists for fast
  traversal.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set


# ── Node & Edge taxonomy ────────────────────────────────────────────

class NodeType(str, enum.Enum):
    """Semantic category of a graph node."""
    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


class EdgeType(str, enum.Enum):
    """Semantic relationship between two nodes."""
    IMPORTS = "imports"          # module A imports module B
    CALLS = "calls"             # function A calls function B
    DEFINES = "defines"         # file defines class / function
    CONTAINS = "contains"       # class contains method
    INHERITS = "inherits"       # class A inherits class B


# ── Data carriers ───────────────────────────────────────────────────

@dataclass
class Node:
    """A single entity in the code graph."""

    id: str                     # unique, e.g. "src/auth.py::AuthService"
    node_type: NodeType
    name: str                   # short human-readable label
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ── future: embedding vector for LLM similarity search
    # embedding: Optional[List[float]] = None


@dataclass
class Edge:
    """A directed relationship between two nodes."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)


# ── Graph container ─────────────────────────────────────────────────

class CodeGraph:
    """In-memory directed graph of code entities.

    Supports fast node lookup, neighbour traversal, and lightweight
    queries that downstream analysers (risk propagation, architecture
    review, LLM reasoning) will rely on.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Node] = {}
        self._edges: List[Edge] = []

        # Adjacency indexes — rebuilt lazily.
        self._outgoing: Dict[str, List[Edge]] = {}   # source -> edges
        self._incoming: Dict[str, List[Edge]] = {}   # target -> edges

    # ── Mutation ─────────────────────────────────────────────────

    def add_node(self, node: Node) -> None:
        """Insert or update a node (keyed by ``node.id``)."""
        self._nodes[node.id] = node
        self._outgoing.setdefault(node.id, [])
        self._incoming.setdefault(node.id, [])

    def add_edge(self, edge: Edge) -> None:
        """Append a directed edge and update adjacency indexes."""
        self._edges.append(edge)
        self._outgoing.setdefault(edge.source_id, []).append(edge)
        self._incoming.setdefault(edge.target_id, []).append(edge)

    # ── Read helpers ─────────────────────────────────────────────

    @property
    def nodes(self) -> Dict[str, Node]:
        """All nodes keyed by id (read-only view)."""
        return dict(self._nodes)

    @property
    def edges(self) -> List[Edge]:
        """All edges (read-only copy)."""
        return list(self._edges)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    # ── Traversal ────────────────────────────────────────────────

    def get_dependencies(self, node_id: str) -> List[Node]:
        """Nodes that *node_id* depends on (outgoing edges)."""
        return [
            self._nodes[e.target_id]
            for e in self._outgoing.get(node_id, [])
            if e.target_id in self._nodes
        ]

    def get_callers(self, node_id: str) -> List[Node]:
        """Functions / methods that call *node_id*."""
        return [
            self._nodes[e.source_id]
            for e in self._incoming.get(node_id, [])
            if e.edge_type == EdgeType.CALLS and e.source_id in self._nodes
        ]

    def get_callees(self, node_id: str) -> List[Node]:
        """Functions / methods called by *node_id*."""
        return [
            self._nodes[e.target_id]
            for e in self._outgoing.get(node_id, [])
            if e.edge_type == EdgeType.CALLS and e.target_id in self._nodes
        ]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[Edge]:
        return [e for e in self._edges if e.edge_type == edge_type]

    def get_dependents(self, node_id: str) -> List[Node]:
        """Nodes that depend *on* node_id (incoming edges)."""
        return [
            self._nodes[e.source_id]
            for e in self._incoming.get(node_id, [])
            if e.source_id in self._nodes
        ]

    # ── Impact analysis (future: risk propagation) ───────────────

    def get_impact_set(self, node_id: str, max_depth: int = 3) -> Set[str]:
        """BFS over incoming edges to find all transitively-affected nodes.

        Useful for answering *"if I change function X, what else might break?"*
        """
        visited: Set[str] = set()
        frontier = [node_id]
        depth = 0
        while frontier and depth < max_depth:
            next_frontier: List[str] = []
            for nid in frontier:
                if nid in visited:
                    continue
                visited.add(nid)
                for edge in self._incoming.get(nid, []):
                    if edge.source_id not in visited:
                        next_frontier.append(edge.source_id)
            frontier = next_frontier
            depth += 1
        visited.discard(node_id)  # don't include the seed
        return visited

    # ── Serialisation ────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {nid: asdict(n) for nid, n in self._nodes.items()},
            "edges": [asdict(e) for e in self._edges],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    # ── Summary ──────────────────────────────────────────────────

    def summary(self) -> str:
        type_counts = {}
        for n in self._nodes.values():
            type_counts[n.node_type.value] = type_counts.get(n.node_type.value, 0) + 1
        edge_counts = {}
        for e in self._edges:
            edge_counts[e.edge_type.value] = edge_counts.get(e.edge_type.value, 0) + 1
        return (
            f"CodeGraph: {len(self._nodes)} nodes, {len(self._edges)} edges\n"
            f"  Node types: {type_counts}\n"
            f"  Edge types: {edge_counts}"
        )

    def __repr__(self) -> str:
        return f"<CodeGraph nodes={len(self._nodes)} edges={len(self._edges)}>"
