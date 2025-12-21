import os
import tempfile
import subprocess
import ast

def generate_patch(file_path, code, message):
    # 🚫 Never auto-fix public API files
    if os.path.basename(file_path) == "__init__.py":
        return None

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    unused_lines = set()

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            unused_lines.add(node.lineno)

        def visit_ImportFrom(self, node):
            unused_lines.add(node.lineno)

    ImportVisitor().visit(tree)

    if not unused_lines:
        return None

    lines = code.splitlines()
    new_lines = [
        line for i, line in enumerate(lines, start=1)
        if i not in unused_lines
    ]

    new_code = "\n".join(new_lines) + "\n"

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8"
    ) as tmp:
        tmp.write(new_code)
        tmp_path = tmp.name

    try:
        diff = subprocess.run(
            ["git", "diff", "--no-index", file_path, tmp_path],
            capture_output=True,
            text=True
        ).stdout

        return diff if diff.strip() else None
    finally:
        os.unlink(tmp_path)
