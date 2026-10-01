"""Deterministic package re-export test selection (AST-only, no execution)."""

from pathlib import Path

from app.models.change_impact import ChangedSymbol
from app.services.verification_execution import _select_tests, _test_targets


def _flask_repo(tmp_path, init_body, submodules, test_body, test_path="tests/test_app.py"):
    pkg = tmp_path / "src" / "flask"
    pkg.mkdir(parents=True)
    if init_body is not None:
        (pkg / "__init__.py").write_text(init_body)
    for name, body in submodules.items():
        target = pkg / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)
    test_file = tmp_path / test_path
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(test_body)
    return tmp_path


def _symbol(name, file_path):
    return ChangedSymbol(
        node_id=f"flask.{file_path}.{name}",
        node_type="class",
        file_path=file_path,
        name=name,
        change_kind="modified",
    )


def test_reexport_import_selects_test(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\nfrom .config import Config as Config\n",
        {"app.py": "class Flask:\n    pass\n", "config.py": "class Config:\n    pass\n"},
        "from flask import Flask\n",
    )
    records = _select_tests(repo, ["src/flask/app.py"])
    assert len(records) == 1
    assert records[0].test_file == "tests/test_app.py"
    assert records[0].evidence == "REEXPORT_IMPORT"
    assert records[0].changed_module == "flask.app"
    assert records[0].symbols == ()


def test_reexport_import_and_symbol_upgrades_tier(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import Flask\n",
    )
    records = _select_tests(
        repo, ["src/flask/app.py"], [_symbol("Flask", "src/flask/app.py")]
    )
    assert len(records) == 1
    assert records[0].evidence == "REEXPORT_IMPORT_AND_SYMBOL"
    assert records[0].symbols == ("Flask",)


def test_reexport_of_other_name_does_not_select(tmp_path):
    """`from flask import Config` is not evidence for a change in flask/app.py."""
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\nfrom .config import Config as Config\n",
        {"app.py": "class Flask:\n    pass\n", "config.py": "class Config:\n    pass\n"},
        "from flask import Config\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_reexport_alias_binds_exported_name_only(tmp_path):
    """Only the aliased export name is evidence; the original name is not."""
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as App\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import App\n",
    )
    records = _select_tests(repo, ["src/flask/app.py"])
    assert len(records) == 1
    assert records[0].evidence == "REEXPORT_IMPORT"


def test_reexport_alias_original_name_is_not_evidence(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as App\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import Flask\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_missing_init_yields_no_reexport_evidence(tmp_path):
    repo = _flask_repo(
        tmp_path,
        None,
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import Flask\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_ancestor_only_import_is_not_reexport_evidence(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\n",
        {"app.py": "class Flask:\n    pass\n"},
        "import flask\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_relative_import_in_test_is_not_reexport_evidence(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from . import Flask\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_from_dot_import_submodule_reexport_selects(tmp_path):
    """`from . import blueprints as bp` in __init__ makes `from flask import bp` evidence.

    The alias is required: a bare `from flask import blueprints` names the
    submodule directly and is DIRECT_IMPORT, not a re-export.
    """
    repo = _flask_repo(
        tmp_path,
        "from . import blueprints as bp\n",
        {"blueprints.py": "BP = 1\n"},
        "from flask import bp\n",
    )
    records = _select_tests(repo, ["src/flask/blueprints.py"])
    assert len(records) == 1
    assert records[0].evidence == "REEXPORT_IMPORT"
    assert records[0].changed_module == "flask.blueprints"


def test_from_dot_import_submodule_bare_name_is_direct_import(tmp_path):
    repo = _flask_repo(
        tmp_path,
        "from . import blueprints\n",
        {"blueprints.py": "BP = 1\n"},
        "from flask import blueprints\n",
    )
    records = _select_tests(repo, ["src/flask/blueprints.py"])
    assert len(records) == 1
    assert records[0].evidence == "DIRECT_IMPORT"
    assert records[0].changed_module == "flask.blueprints"


def test_all_declaration_without_reexport_is_not_evidence(tmp_path):
    """A name in __all__ that is not actually re-exported from the changed submodule
    does not fabricate selection."""
    repo = _flask_repo(
        tmp_path,
        "__all__ = ['Flask', 'Missing']\nfrom .app import Flask as Flask\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import Missing\n",
    )
    assert _test_targets(repo, ["src/flask/app.py"]) == []


def test_nested_package_reexport_selects(tmp_path):
    pkg = tmp_path / "src" / "flask" / "sansio"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .app import App as App\n")
    (pkg / "app.py").write_text("class App:\n    pass\n")
    test_file = tmp_path / "tests" / "test_sansio.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("from flask.sansio import App\n")
    records = _select_tests(tmp_path, ["src/flask/sansio/app.py"])
    assert len(records) == 1
    assert records[0].evidence == "REEXPORT_IMPORT"
    assert records[0].changed_module == "flask.sansio.app"


def test_ancestor_package_reexport_selects(tmp_path):
    """A top-level __init__ re-export of a deeper submodule is evidence for that submodule."""
    pkg = tmp_path / "src" / "flask"
    (pkg / "json").mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .json.provider import JSONProvider as JSONProvider\n")
    (pkg / "json" / "__init__.py").write_text("")
    (pkg / "json" / "provider.py").write_text("class JSONProvider:\n    pass\n")
    test_file = tmp_path / "tests" / "test_provider.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("from flask import JSONProvider\n")
    records = _select_tests(tmp_path, ["src/flask/json/provider.py"])
    assert len(records) == 1
    assert records[0].evidence == "REEXPORT_IMPORT"
    assert records[0].changed_module == "flask.json.provider"


def test_changed_init_has_direct_module_identity(tmp_path):
    """A changed package __init__.py resolves to the package dotted path and is
    matched by a direct `from flask import X` import, not the re-export path."""
    repo = _flask_repo(
        tmp_path,
        "from .app import Flask as Flask\n",
        {"app.py": "class Flask:\n    pass\n"},
        "from flask import Flask\n",
    )
    records = _select_tests(repo, ["src/flask/__init__.py"])
    assert len(records) == 1
    assert records[0].changed_module == "flask"
    assert records[0].evidence == "DIRECT_IMPORT"
