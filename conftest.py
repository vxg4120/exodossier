import psycopg
import pytest

from common.db import get_conn


def pytest_configure(config):
    config.addinivalue_line("markers", "db: test requires a reachable DATABASE_URL (exo database)")
    config.addinivalue_line(
        "markers",
        "graph: test asserts on the populated identity graph; skipped when the database is empty",
    )


@pytest.fixture(scope="session")
def _database_reachable():
    """One connection attempt per session, closed immediately."""
    try:
        conn = get_conn()
    except psycopg.Error:
        return False
    conn.close()
    return True


@pytest.fixture(scope="session")
def _graph_populated(_database_reachable):
    """Whether the identity graph holds any candidate, probed once and let go.

    The spot-check tests assert on what the real graph contains (TRAPPIST-1's Teff conflict, the
    dramatic disposition corpus). On a migrated but empty database, which is what CI has, they
    could only fail, so they skip there and run wherever a built graph is reachable."""
    if not _database_reachable:
        return False
    conn = get_conn()
    try:
        return conn.execute("SELECT EXISTS (SELECT 1 FROM candidate)").fetchone()[0]
    except psycopg.errors.UndefinedTable:
        return False  # not migrated: no graph either. Any other error is a real failure.
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def _skip_db_marked_without_a_database(request):
    """A db-marked test skips when there is no database, whether or not it takes db_conn.

    Without this the marker only means "deselected by the fast job": a db-marked test that reaches
    the database some other way (a TestClient, the MCP server subprocess) still ran in the full
    job and failed on connection refused, which reads as a broken test rather than a missing
    database. The marker is the declaration; this makes it the guarantee."""
    # The probe is resolved INSIDE the marker check, never as a parameter: an autouse fixture that
    # took _database_reachable would make every unmarked test open a connection, which is exactly
    # what the fast job exists to avoid.
    if not request.node.get_closest_marker("db"):
        return
    if not request.getfixturevalue("_database_reachable"):
        pytest.skip("database not reachable at DATABASE_URL")
    if request.node.get_closest_marker("graph") and not request.getfixturevalue("_graph_populated"):
        pytest.skip("the identity graph at DATABASE_URL is empty")


@pytest.fixture
def db_conn():
    """A connection to exo, rolled back at teardown so tests never pollute the graph."""
    try:
        conn = get_conn()
    except psycopg.OperationalError:
        pytest.skip("database not reachable at DATABASE_URL")
        return
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()


@pytest.fixture
def clean_graph(db_conn):
    """Isolate a test on an empty derived graph: TRUNCATE the derived tables inside the
    transaction, then rely on db_conn's rollback to restore the real graph afterward. Raw landing,
    the ingest ledger and disposition_mapping are preserved."""
    with db_conn.cursor() as cur:
        cur.execute(
            "TRUNCATE merge_log, source_assertion, entity_identifier, candidate, star CASCADE"
        )
    return db_conn
