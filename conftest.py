import psycopg
import pytest

from common.db import get_conn


def pytest_configure(config):
    config.addinivalue_line("markers", "db: test requires a reachable DATABASE_URL (exo database)")


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
