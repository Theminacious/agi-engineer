"""AST-based symbol extraction from Python source files.

Parses a single ``.py`` file and returns a structured ``SymbolTable``
containing every top-level function, class (with methods), and import
statement.  Used by the graph builder to populate nodes.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data carriers ───────────────────────────────────────────────────

@dataclass
class ImportInfo:
    """A single import statement."""

    module: str                       # e.g. "os.path"
    names: List[str] = field(default_factory=list)  # e.g. ["join", "exists"]
    is_from: bool = False             # True  → from X import Y
    alias: Optional[str] = None
    line_number: int = 0


@dataclass
class FunctionInfo:
    """A top-level function or standalone method."""

    name: str
    line_number: int
    end_line_number: Optional[int] = None
    args: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)      # names invoked
    is_async: bool = False
    docstring: Optional[str] = None


@dataclass
class ClassInfo:
    """A class definition with its methods."""

    name: str
    line_number: int
    end_line_number: Optional[int] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionInfo] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class SymbolTable:
    """Everything extracted from a single Python file."""

    file_path: str
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)
    imports: List[ImportInfo] = field(default_factory=list)
    module_docstring: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        return asdict(self)


# ── Extractor ───────────────────────────────────────────────────────

class SymbolExtractor:
    """Parse a Python file and return its ``SymbolTable``."""

    def extract(self, file_path: str) -> SymbolTable:
        """Extract symbols from a Python source file.

        Parameters
        ----------
        file_path:
            Absolute or relative path to a ``.py`` file.

        Returns
        -------
        SymbolTable
            Structured representation of every symbol in the file.
        """
        source = Path(file_path).read_text(encoding="utf-8", errors="replace")
        return self.extract_from_source(source, file_path)

    def extract_from_source(self, source: str, file_path: str = "<string>") -> SymbolTable:
        """Extract symbols from raw source text."""
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as exc:
            logger.warning("SyntaxError parsing %s: %s", file_path, exc)
            return SymbolTable(file_path=file_path)

        table = SymbolTable(file_path=file_path)
        table.module_docstring = ast.get_docstring(tree)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                table.functions.append(self._extract_function(node))
            elif isinstance(node, ast.ClassDef):
                table.classes.append(self._extract_class(node))
            elif isinstance(node, ast.Import):
                table.imports.extend(self._extract_import(node))
            elif isinstance(node, ast.ImportFrom):
                table.imports.extend(self._extract_import_from(node))

        return table

    # ── Private helpers ──────────────────────────────────────────

    def _extract_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionInfo:
        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", None),
            args=[a.arg for a in node.args.args],
            decorators=self._decorator_names(node),
            calls=self._collect_calls(node),
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=ast.get_docstring(node),
        )

    def _extract_class(self, node: ast.ClassDef) -> ClassInfo:
        methods: List[FunctionInfo] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(item))

        bases: List[str] = []
        for base in node.bases:
            bases.append(self._node_name(base))

        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            end_line_number=getattr(node, "end_lineno", None),
            bases=bases,
            methods=methods,
            decorators=self._decorator_names(node),
            docstring=ast.get_docstring(node),
        )

    def _extract_import(self, node: ast.Import) -> List[ImportInfo]:
        results: List[ImportInfo] = []
        for alias in node.names:
            results.append(ImportInfo(
                module=alias.name,
                names=[],
                is_from=False,
                alias=alias.asname,
                line_number=node.lineno,
            ))
        return results

    def _extract_import_from(self, node: ast.ImportFrom) -> List[ImportInfo]:
        module = node.module or ""
        names = [alias.name for alias in node.names]
        return [ImportInfo(
            module=module,
            names=names,
            is_from=True,
            line_number=node.lineno,
        )]

    @staticmethod
    def _decorator_names(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
        names: List[str] = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                names.append(dec.id)
            elif isinstance(dec, ast.Attribute):
                names.append(f"{SymbolExtractor._node_name(dec.value)}.{dec.attr}")
            elif isinstance(dec, ast.Call):
                names.append(SymbolExtractor._node_name(dec.func))
            else:
                names.append("<unknown>")
        return names

    @staticmethod
    def _node_name(node: ast.expr) -> str:
        """Best-effort human-readable name for an AST expression."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{SymbolExtractor._node_name(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return SymbolExtractor._node_name(node.value)
        if isinstance(node, ast.Call):
            return SymbolExtractor._node_name(node.func)
        return "<complex>"

    @staticmethod
    def _collect_calls(node: ast.AST) -> List[str]:
        """Walk the subtree and collect every function/method call name."""
        calls: List[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                name = SymbolExtractor._node_name(child.func)
                if name and name != "<complex>":
                    calls.append(name)
        return calls
