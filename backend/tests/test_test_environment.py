"""Test-environment reproducibility.

Covers P2 #5 of PRODUCTION_READINESS_AUDIT.md ("Install Test Dependencies").
Two separate problems were found under that heading:

1. Nothing declared pytest. A fresh checkout could not run the suite at all
   without someone knowing to `pip install pytest` by hand.

2. The suite did not collect on pytest 8. `tests/` and `backend/tests/` both
   carried `__init__.py`, and because pytest.ini puts both the repository root
   and `backend/` on the import path, each conftest resolved to the same module
   name `tests.conftest`. pytest 7.x raised ImportPathMismatchError; 8.x aborts
   collection with "Plugin already registered under a different name". So the
   pinned local interpreter passed while a fresh environment could not start.

Both failure modes are silent in the environment that already works, which is
what these tests are for: they fail in the environment where the suite runs, not
only in the fresh one where the breakage shows up.
"""

import configparser
import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def repo_path(*parts):
    return os.path.join(REPO_ROOT, *parts)


def read_text(*parts):
    with open(repo_path(*parts)) as handle:
        return handle.read()


def module_name_for(relative_file):
    """The dotted module name pytest gives `relative_file` under importlib mode.

    Two cases:
      - Inside a package (an unbroken `__init__.py` chain upwards): the name
        starts at the topmost package directory, so `backend/tests/conftest.py`
        with `backend/tests/__init__.py` but no `backend/__init__.py` becomes
        `tests.conftest` — colliding with `tests/conftest.py`.
      - No package markers: the name is the full rootdir-relative path,
        `tests.conftest` versus `backend.tests.conftest`, which is distinct.
    """
    parts = relative_file.split("/")
    directories, filename = parts[:-1], parts[-1]
    stem = filename[: -len(".py")]

    package_start = None
    for index in range(len(directories) - 1, -1, -1):
        if os.path.exists(repo_path(*directories[: index + 1], "__init__.py")):
            package_start = index
        else:
            break

    if package_start is None:
        return ".".join(directories + [stem])
    return ".".join(directories[package_start:] + [stem])


class TestDeclaredDependencies:
    """P2 #5: a fresh environment must be installable from declared files."""

    def test_dev_requirements_file_exists(self):
        assert os.path.exists(repo_path("requirements-dev.txt")), (
            "requirements-dev.txt is how a fresh environment learns it needs pytest"
        )

    def test_pytest_is_declared(self):
        content = read_text("requirements-dev.txt")
        assert re.search(r"^pytest\b", content, re.MULTILINE), (
            "pytest must be declared, not assumed present"
        )

    def test_dev_requirements_include_runtime_requirements(self):
        """Otherwise `pip install -r requirements-dev.txt` yields a broken env."""
        content = read_text("requirements-dev.txt")
        assert "-r requirements.txt" in content

    def test_pytest_floor_is_at_least_7(self):
        """pytest.ini's `pythonpath` option is ignored before 7.0.

        On 6.x that key is silently skipped and every `from app...` import in
        backend/tests fails at collection, so the floor is load-bearing.
        """
        content = read_text("requirements-dev.txt")
        match = re.search(r"^pytest>=(\d+)\.(\d+)", content, re.MULTILINE)
        assert match, "pytest must carry a lower bound"
        major, minor = int(match.group(1)), int(match.group(2))
        assert (major, minor) >= (7, 0)

    def test_running_pytest_satisfies_the_declared_floor(self):
        """The interpreter running these tests must meet what we declare."""
        content = read_text("requirements-dev.txt")
        match = re.search(r"^pytest>=(\d+)\.(\d+)", content, re.MULTILINE)
        declared = (int(match.group(1)), int(match.group(2)))
        actual = tuple(int(part) for part in pytest.__version__.split(".")[:2])
        assert actual >= declared, (
            f"pytest {pytest.__version__} is below the declared floor {declared}"
        )

    def test_pytest_stays_out_of_the_production_image(self):
        """The Dockerfile installs requirements.txt; test tools do not belong there."""
        assert "requirements.txt" in read_text("Dockerfile")
        runtime = read_text("requirements.txt")
        assert not re.search(r"^pytest\b", runtime, re.MULTILINE), (
            "pytest in requirements.txt ships the test framework to production"
        )


class TestImportRootsNeedNoEnvironmentVariables:
    """`pip install` then `pytest` must work with nothing else exported."""

    def test_pytest_ini_declares_import_roots(self):
        parser = configparser.ConfigParser()
        parser.read(repo_path("pytest.ini"))
        roots = parser["pytest"]["pythonpath"].split()
        assert "." in roots and "backend" in roots

    def test_import_mode_is_importlib(self):
        parser = configparser.ConfigParser()
        parser.read(repo_path("pytest.ini"))
        assert "--import-mode=importlib" in parser["pytest"]["addopts"]

    def test_agent_is_not_on_the_import_path(self):
        """Documented in pytest.ini: it would double-import agent submodules.

        With `agent` on sys.path, `intelligence.proposal` and
        `agent.intelligence.proposal` become two distinct module objects holding
        two distinct copies of every class, so isinstance checks across the
        boundary fail.
        """
        parser = configparser.ConfigParser()
        parser.read(repo_path("pytest.ini"))
        assert "agent" not in parser["pytest"]["pythonpath"].split()

    def test_suite_does_not_depend_on_an_exported_pythonpath(self):
        """The conftests must not require PYTHONPATH to already be set.

        This test is running, which means imports resolved — but it would also
        pass if PYTHONPATH happened to be exported in this shell. Asserting that
        pytest.ini carries the roots (above) is the real check; this records that
        the app packages resolve without the developer's environment.
        """
        import app.db.base  # noqa: F401  — resolves via pytest.ini's `backend` root
        import agent.intelligence  # noqa: F401  — resolves via the `.` root


class TestNoAmbiguousTestPackages:
    """Regression guard for the pytest 8 collection failure.

    Re-adding either `__init__.py` restores the duplicate `tests.conftest`
    module name and makes the suite refuse to collect on pytest 8 — while still
    passing on a pinned 7.x. Asserting their absence here means the mistake is
    caught in whichever version is in use.
    """

    @pytest.mark.parametrize("marker", ["tests/__init__.py", "backend/tests/__init__.py"])
    def test_test_directories_have_no_package_marker(self, marker):
        assert not os.path.exists(repo_path(marker)), (
            f"{marker} makes both test trees resolve to the module name "
            "'tests.conftest'; see the comment in pytest.ini"
        )

    def test_the_two_conftests_resolve_to_distinct_module_names(self):
        """The condition the marker removal exists to guarantee.

        Models pytest's own naming rule rather than inspecting sys.modules,
        because which conftests are loaded depends on which subset of the suite
        you run — a check based on that would pass or fail by accident.

        The rule, under --import-mode=importlib:
          - a file inside a package (an unbroken `__init__.py` chain) is named by
            walking up to the topmost package directory, so its name starts at
            that directory;
          - otherwise it is named by its path relative to rootdir.
        """
        names = {
            path: module_name_for(path)
            for path in ("tests/conftest.py", "backend/tests/conftest.py")
        }

        assert len(set(names.values())) == 2, (
            f"both conftests resolve to the same module name: {names}"
        )

    def test_both_test_trees_are_collected(self):
        """A fix that silenced the collision by dropping a tree would be worse."""
        parser = configparser.ConfigParser()
        parser.read(repo_path("pytest.ini"))
        testpaths = parser["pytest"]["testpaths"].split()
        assert "tests" in testpaths
        assert "backend/tests" in testpaths
