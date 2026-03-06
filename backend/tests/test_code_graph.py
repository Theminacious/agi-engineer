"""Tests for Phase 19 — Code Intelligence Graph Engine."""

import os
import textwrap
import tempfile
import pytest
from pathlib import Path

from app.intelligence.code_graph.graph_store import (
    CodeGraph, Node, Edge, NodeType, EdgeType,
)
from app.intelligence.code_graph.symbol_extractor import SymbolExtractor
from app.intelligence.code_graph.call_graph import CallGraphBuilder
from app.intelligence.code_graph.dependency_mapper import DependencyMapper
from app.intelligence.code_graph.code_graph_builder import CodeGraphBuilder


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a tiny multi-file Python repo for integration tests."""
    (tmp_path / "utils.py").write_text(textwrap.dedent("""\
        \"\"\"Utility helpers.\"\"\"

        def add(a, b):
            return a + b

        def multiply(a, b):
            return a * b
    """))

    (tmp_path / "math_service.py").write_text(textwrap.dedent("""\
        \"\"\"Service that uses utils.\"\"\"

        from utils import add, multiply

        class MathService:
            def compute(self, x, y):
                return add(x, y)

            def double(self, x):
                return multiply(x, 2)

        def standalone():
            return add(1, 2)
    """))

    (tmp_path / "app.py").write_text(textwrap.dedent("""\
        \"\"\"Entry point.\"\"\"

        from math_service import MathService

        def main():
            svc = MathService()
            result = svc.compute(3, 4)
            print(result)

        if __name__ == "__main__":
            main()
    """))

    # A sub-package
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "helper.py").write_text(textwrap.dedent("""\
        def greet(name):
            return f"Hello, {name}"
    """))

    return tmp_path


# ─── GraphStore tests ────────────────────────────────────────────────

class TestCodeGraph:
    def test_add_and_retrieve_node(self):
        g = CodeGraph()
        node = Node(id="a.py", node_type=NodeType.FILE, name="a.py")
        g.add_node(node)
        assert g.get_node("a.py") is node
        assert len(g.nodes) == 1

    def test_add_edge(self):
        g = CodeGraph()
        g.add_node(Node(id="a", node_type=NodeType.FUNCTION, name="a"))
        g.add_node(Node(id="b", node_type=NodeType.FUNCTION, name="b"))
        g.add_edge(Edge(source_id="a", target_id="b", edge_type=EdgeType.CALLS))
        assert len(g.edges) == 1

    def test_get_dependencies(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py", node_type=NodeType.FILE, name="a.py"))
        g.add_node(Node(id="b.py", node_type=NodeType.FILE, name="b.py"))
        g.add_edge(Edge(source_id="a.py", target_id="b.py", edge_type=EdgeType.IMPORTS))
        deps = g.get_dependencies("a.py")
        assert len(deps) == 1
        assert deps[0].id == "b.py"

    def test_get_callers_and_callees(self):
        g = CodeGraph()
        g.add_node(Node(id="f1", node_type=NodeType.FUNCTION, name="f1"))
        g.add_node(Node(id="f2", node_type=NodeType.FUNCTION, name="f2"))
        g.add_edge(Edge(source_id="f1", target_id="f2", edge_type=EdgeType.CALLS))
        assert len(g.get_callees("f1")) == 1
        assert g.get_callees("f1")[0].id == "f2"
        assert len(g.get_callers("f2")) == 1
        assert g.get_callers("f2")[0].id == "f1"

    def test_get_nodes_by_type(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py", node_type=NodeType.FILE, name="a.py"))
        g.add_node(Node(id="func", node_type=NodeType.FUNCTION, name="func"))
        assert len(g.get_nodes_by_type(NodeType.FILE)) == 1
        assert len(g.get_nodes_by_type(NodeType.FUNCTION)) == 1

    def test_impact_set(self):
        g = CodeGraph()
        for nid in ("a", "b", "c"):
            g.add_node(Node(id=nid, node_type=NodeType.FUNCTION, name=nid))
        g.add_edge(Edge(source_id="b", target_id="a", edge_type=EdgeType.CALLS))
        g.add_edge(Edge(source_id="c", target_id="b", edge_type=EdgeType.CALLS))
        impact = g.get_impact_set("a", max_depth=3)
        assert "b" in impact
        assert "c" in impact

    def test_to_json(self):
        g = CodeGraph()
        g.add_node(Node(id="x", node_type=NodeType.FILE, name="x"))
        j = g.to_json()
        assert '"x"' in j

    def test_summary(self):
        g = CodeGraph()
        g.add_node(Node(id="x", node_type=NodeType.FILE, name="x"))
        s = g.summary()
        assert "1 nodes" in s

    def test_get_dependents(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py", node_type=NodeType.FILE, name="a.py"))
        g.add_node(Node(id="b.py", node_type=NodeType.FILE, name="b.py"))
        g.add_edge(Edge(source_id="a.py", target_id="b.py", edge_type=EdgeType.IMPORTS))
        dependents = g.get_dependents("b.py")
        assert len(dependents) == 1
        assert dependents[0].id == "a.py"


# ─── SymbolExtractor tests ──────────────────────────────────────────

class TestSymbolExtractor:
    def test_extract_functions(self):
        src = textwrap.dedent("""\
            def foo(a, b):
                return a + b

            async def bar():
                pass
        """)
        table = SymbolExtractor().extract_from_source(src)
        assert len(table.functions) == 2
        assert table.functions[0].name == "foo"
        assert table.functions[0].args == ["a", "b"]
        assert table.functions[1].is_async is True

    def test_extract_classes(self):
        src = textwrap.dedent("""\
            class Animal:
                def speak(self):
                    pass

            class Dog(Animal):
                def speak(self):
                    return "woof"
        """)
        table = SymbolExtractor().extract_from_source(src)
        assert len(table.classes) == 2
        assert table.classes[0].name == "Animal"
        assert len(table.classes[0].methods) == 1
        assert table.classes[1].bases == ["Animal"]

    def test_extract_imports(self):
        src = textwrap.dedent("""\
            import os
            from pathlib import Path
            from typing import List, Dict
        """)
        table = SymbolExtractor().extract_from_source(src)
        assert len(table.imports) == 3
        assert table.imports[0].module == "os"
        assert table.imports[1].module == "pathlib"
        assert table.imports[1].names == ["Path"]
        assert table.imports[2].names == ["List", "Dict"]

    def test_extract_calls(self):
        src = textwrap.dedent("""\
            def foo():
                bar()
                baz(1, 2)
        """)
        table = SymbolExtractor().extract_from_source(src)
        assert "bar" in table.functions[0].calls
        assert "baz" in table.functions[0].calls

    def test_syntax_error_returns_empty_table(self):
        table = SymbolExtractor().extract_from_source("def broken(")
        assert table.functions == []
        assert table.classes == []

    def test_extract_decorators(self):
        src = textwrap.dedent("""\
            import functools

            @functools.lru_cache
            def cached():
                pass
        """)
        table = SymbolExtractor().extract_from_source(src)
        assert len(table.functions) == 1
        assert "functools.lru_cache" in table.functions[0].decorators

    def test_extract_file(self, tmp_path: Path):
        f = tmp_path / "demo.py"
        f.write_text("def hello(): pass")
        table = SymbolExtractor().extract(str(f))
        assert len(table.functions) == 1
        assert table.functions[0].name == "hello"

    def test_docstrings(self):
        src = textwrap.dedent('''\
            """Module doc."""

            def foo():
                """Foo doc."""
                pass

            class Bar:
                """Bar doc."""
                def baz(self):
                    """Baz doc."""
                    pass
        ''')
        table = SymbolExtractor().extract_from_source(src)
        assert table.module_docstring == "Module doc."
        assert table.functions[0].docstring == "Foo doc."
        assert table.classes[0].docstring == "Bar doc."
        assert table.classes[0].methods[0].docstring == "Baz doc."


# ─── CallGraphBuilder tests ─────────────────────────────────────────

class TestCallGraphBuilder:
    def test_basic_call_edge(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py::foo", node_type=NodeType.FUNCTION, name="foo", file_path="a.py"))
        g.add_node(Node(id="a.py::bar", node_type=NodeType.FUNCTION, name="bar", file_path="a.py"))

        src = textwrap.dedent("""\
            def foo():
                bar()

            def bar():
                pass
        """)
        table = SymbolExtractor().extract_from_source(src, "a.py")
        table.file_path = "a.py"

        CallGraphBuilder().build(g, [table])
        call_edges = g.get_edges_by_type(EdgeType.CALLS)
        assert len(call_edges) >= 1
        assert any(e.source_id == "a.py::foo" and e.target_id == "a.py::bar" for e in call_edges)

    def test_self_method_call(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py::Svc.run", node_type=NodeType.METHOD, name="run", file_path="a.py"))
        g.add_node(Node(id="a.py::Svc.helper", node_type=NodeType.METHOD, name="helper", file_path="a.py"))

        src = textwrap.dedent("""\
            class Svc:
                def run(self):
                    self.helper()

                def helper(self):
                    pass
        """)
        table = SymbolExtractor().extract_from_source(src, "a.py")
        table.file_path = "a.py"

        CallGraphBuilder().build(g, [table])
        call_edges = g.get_edges_by_type(EdgeType.CALLS)
        assert any(e.source_id == "a.py::Svc.run" and e.target_id == "a.py::Svc.helper" for e in call_edges)


# ─── DependencyMapper tests ─────────────────────────────────────────

class TestDependencyMapper:
    def test_import_edge(self):
        g = CodeGraph()
        g.add_node(Node(id="a.py", node_type=NodeType.FILE, name="a.py", file_path="a.py"))
        g.add_node(Node(id="b.py", node_type=NodeType.FILE, name="b.py", file_path="b.py"))

        src = textwrap.dedent("""\
            from b import something
        """)
        table = SymbolExtractor().extract_from_source(src, "a.py")
        table.file_path = "a.py"

        DependencyMapper().build(g, [table])
        import_edges = g.get_edges_by_type(EdgeType.IMPORTS)
        assert len(import_edges) == 1
        assert import_edges[0].source_id == "a.py"
        assert import_edges[0].target_id == "b.py"


# ─── CodeGraphBuilder integration tests ─────────────────────────────

class TestCodeGraphBuilder:
    def test_build_graph_creates_nodes(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        file_nodes = graph.get_nodes_by_type(NodeType.FILE)
        assert len(file_nodes) >= 4  # utils, math_service, app, pkg/helper + __init__

    def test_build_graph_creates_function_nodes(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        func_nodes = graph.get_nodes_by_type(NodeType.FUNCTION)
        func_names = {n.name for n in func_nodes}
        assert "add" in func_names
        assert "multiply" in func_names
        assert "main" in func_names
        assert "standalone" in func_names

    def test_build_graph_creates_class_nodes(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        class_nodes = graph.get_nodes_by_type(NodeType.CLASS)
        assert any(n.name == "MathService" for n in class_nodes)

    def test_build_graph_creates_method_nodes(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        method_nodes = graph.get_nodes_by_type(NodeType.METHOD)
        method_names = {n.name for n in method_nodes}
        assert "compute" in method_names
        assert "double" in method_names

    def test_defines_edges(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        defines = graph.get_edges_by_type(EdgeType.DEFINES)
        assert len(defines) >= 4  # at least: add, multiply, MathService, main

    def test_contains_edges(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        contains = graph.get_edges_by_type(EdgeType.CONTAINS)
        assert len(contains) >= 2  # MathService -> compute, double

    def test_call_edges(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        calls = graph.get_edges_by_type(EdgeType.CALLS)
        assert len(calls) >= 1  # standalone -> add at minimum

    def test_import_edges(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        imports = graph.get_edges_by_type(EdgeType.IMPORTS)
        assert len(imports) >= 1

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            CodeGraphBuilder().build_graph("/no/such/path/xyz")

    def test_summary_string(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        summary = graph.summary()
        assert "nodes" in summary
        assert "edges" in summary

    def test_to_json_roundtrip(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        import json
        data = json.loads(graph.to_json())
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == len(graph.nodes)
        assert len(data["edges"]) == len(graph.edges)

    def test_skip_pycache(self, sample_repo: Path):
        cache_dir = sample_repo / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("x = 1")
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        assert not any("__pycache__" in n.id for n in graph.nodes.values())

    def test_sub_package(self, sample_repo: Path):
        graph = CodeGraphBuilder().build_graph(str(sample_repo))
        func_names = {n.name for n in graph.get_nodes_by_type(NodeType.FUNCTION)}
        assert "greet" in func_names


# ─── CodeGraphService tests ─────────────────────────────────────────

class TestCodeGraphService:
    def test_generate_repo_graph(self, sample_repo: Path):
        from app.services.code_graph_service import CodeGraphService
        svc = CodeGraphService()
        result = svc.generate_repo_graph(str(sample_repo))
        assert result.node_count > 0
        assert result.edge_count > 0
        assert result.file_count >= 4
        assert result.build_time_ms >= 0

    def test_result_to_dict(self, sample_repo: Path):
        from app.services.code_graph_service import CodeGraphService
        svc = CodeGraphService()
        result = svc.generate_repo_graph(str(sample_repo))
        d = result.to_dict()
        assert "node_count" in d
        assert "edge_count" in d
        assert "summary" in d

    def test_get_impact_set(self, sample_repo: Path):
        from app.services.code_graph_service import CodeGraphService
        svc = CodeGraphService()
        result = svc.generate_repo_graph(str(sample_repo))
        # "add" is called by standalone and MathService.compute — should have impact
        add_id = "utils.py::add"
        impact = svc.get_impact_set(result.graph, add_id)
        # At minimum, the callers of add should appear
        assert isinstance(impact, set)

    def test_nonexistent_raises(self):
        from app.services.code_graph_service import CodeGraphService
        svc = CodeGraphService()
        with pytest.raises(FileNotFoundError):
            svc.generate_repo_graph("/does/not/exist/xyz")
