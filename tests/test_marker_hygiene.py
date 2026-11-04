"""Meta-test: every test that needs a database declares it (ported from orbital's tripwire).

CI runs two Python jobs. The fast one is `pytest -m "not db"` with no database anywhere, and it
exists so that a broken import or a logic error is caught in seconds rather than after a
container spins up. That job is only honest if the db marker is actually applied, and the failure
mode when it is not is nasty in a specific way: the test passes on every developer machine (where
a database happens to be running) and fails only in CI, which is precisely the signal developers
learn to distrust.

The rule enforced here: a test function that consumes a database fixture, or that lives in a
module which imports the FastAPI app (every router reads the database), must carry
@pytest.mark.db, either itself or through a module-level `pytestmark`. It is a static check over
the test sources, so it costs nothing and needs no database.
"""

import ast
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# Fixtures that open a connection, directly or through one that does.
_DB_FIXTURES = {"db_conn", "clean_graph", "client", "planted", "lc_db", "synthetic_tic"}
# Calls that reach the database through the API layer: building a TestClient inside the test, or
# a request on the module-level `client = TestClient(app)` the API test modules share. A module
# that merely imports the app for its pure helpers (the stories cache tests) is not evidence.
_CLIENT_NAMES = {"client", "TestClient"}
# Tests that build the app client on purpose without a database: the shell-head test serves a
# static file, and the lifespan test monkeypatches every cache warmer before the app starts.
# Listing them here is the declaration; a new entry needs the same kind of justification.
_DB_FREE_API_TESTS = {
    "test_seo_head.py::test_served_shell_heads",
    "test_stories_cache.py::test_the_lifespan_warms_the_stories_cache",
}


def _has_marker(node: ast.FunctionDef, name: str) -> bool:
    for dec in node.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr == name:
            return True
    return False


def _module_marks(tree: ast.Module) -> set[str]:
    """Marker names applied to the whole file through `pytestmark = ...` (one mark or a list)."""
    marks: set[str] = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "pytestmark" for t in node.targets):
            continue
        values = node.value.elts if isinstance(node.value, ast.List | ast.Tuple) else [node.value]
        for v in values:
            target = v.func if isinstance(v, ast.Call) else v
            if isinstance(target, ast.Attribute):
                marks.add(target.attr)
    return marks


def _calls_db_touching(node: ast.FunctionDef) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        fn = sub.func
        if isinstance(fn, ast.Name) and fn.id == "TestClient":
            return True
        if isinstance(fn, ast.Attribute) and getattr(fn.value, "id", None) in _CLIENT_NAMES:
            return True
    return False


def _test_functions(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
            "test_"
        ):
            yield node


def _offenders() -> list[str]:
    found = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if "db" in _module_marks(tree):
            continue
        for node in _test_functions(tree):
            if _has_marker(node, "db"):
                continue
            params = {a.arg for a in node.args.args}
            uses_fixture = bool(params & _DB_FIXTURES)
            if f"{path.name}::{node.name}" in _DB_FREE_API_TESTS and not uses_fixture:
                continue
            if uses_fixture or _calls_db_touching(node):
                reason = "uses a db fixture" if uses_fixture else "calls the API"
                found.append(f"{path.name}::{node.name} ({reason})")
    return found


def test_db_touching_tests_carry_the_db_marker():
    offenders = _offenders()
    assert not offenders, (
        "these tests reach the database but are not marked @pytest.mark.db, so they will run "
        "in CI's network-free job and fail there while passing locally:\n  "
        + "\n  ".join(offenders)
    )


def test_graph_tests_are_db_tests():
    """A graph test asserts on what the real identity graph holds, so it needs a database, and
    conftest's skip for an empty graph is only reached through the db marker."""
    offenders = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        marks = _module_marks(tree)
        if "graph" in marks and "db" not in marks:
            offenders.append(f"{path.name} (module-level graph without db)")
        if "db" in marks:
            continue
        offenders += [
            f"{path.name}::{node.name}"
            for node in _test_functions(tree)
            if _has_marker(node, "graph") and not _has_marker(node, "db")
        ]
    assert not offenders, "marked graph but not db:\n  " + "\n  ".join(offenders)


def _probes_at_import(tree: ast.Module) -> bool:
    """True when the module body skips itself with `pytest.skip(..., allow_module_level=True)`
    after a connection attempt: a probe that runs in the network-free job as well."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "skip"):
            continue
        if any(k.arg == "allow_module_level" for k in node.keywords):
            return True
    return False


def test_no_module_level_database_probe():
    """A connection attempt at import time runs in the network-free job too, where it either
    fails the collection or skips the module for the wrong reason. The markers are the gate."""
    offenders = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        if _probes_at_import(tree) and "get_conn" in source:
            offenders.append(path.name)
    assert not offenders, "module-level database probes:\n  " + "\n  ".join(offenders)


def test_the_hygiene_check_can_actually_detect_an_offender(tmp_path):
    """Anti-vacuity: prove the detector fires on a known-bad shape."""
    bad = tmp_path / "test_sample.py"
    bad.write_text(
        "import pytest\n"
        "def test_unmarked(db_conn):\n"
        "    assert db_conn\n"
        "@pytest.mark.db\n"
        "def test_marked(db_conn):\n"
        "    assert db_conn\n",
        encoding="utf-8",
    )
    tree = ast.parse(bad.read_text(encoding="utf-8"))
    fns = {n.name: n for n in _test_functions(tree)}
    assert not _has_marker(fns["test_unmarked"], "db")
    assert _has_marker(fns["test_marked"], "db")


def test_markers_are_registered():
    """Both markers must exist in pyproject's marker list, or -W error turns every use into a
    PytestUnknownMarkWarning and the whole suite fails on a typo."""
    pyproject = (TESTS_DIR.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert '"db:' in pyproject
    assert '"graph:' in pyproject
