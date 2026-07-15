"""Politeness ledger: polite_get pulls once, records the run, and skips a fresh repeat.

Network mocked via `responses`; db-marked because the freshness gate lives in ingest_run. Uses a
throwaway source token and cleans up its own ledger rows so the real graph is untouched.
"""

import datetime as dt

import pytest
import requests
import responses

from ingest import runlog

_SRC = "test_src"
_EP = "test_ep"
_URL = "https://example.test/data.csv"


@pytest.fixture
def _cleanup(db_conn):
    yield
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM ingest_run WHERE source = %s", (_SRC,))
    db_conn.commit()


@pytest.mark.db
@responses.activate
def test_polite_get_pulls_then_skips_when_fresh(db_conn, _cleanup):
    responses.add(responses.GET, _URL, body="a,b\n1,2\n", status=200)

    resp = runlog.polite_get(db_conn, _SRC, _EP, _URL, dt.timedelta(hours=24))
    assert resp is not None
    assert hasattr(resp, "exo_run_id") and resp.exo_bytes > 0
    runlog.finish_run(db_conn, resp.exo_run_id, rows=1, bytes_dl=resp.exo_bytes, status="ok")

    # A second call within the interval is skipped (no HTTP), logging a skipped_fresh row.
    assert runlog.fresh_within(db_conn, _SRC, _EP, dt.timedelta(hours=24))
    skipped = runlog.polite_get(db_conn, _SRC, _EP, _URL, dt.timedelta(hours=24))
    assert skipped is None
    assert len(responses.calls) == 1

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, count(*) FROM ingest_run WHERE source = %s GROUP BY status", (_SRC,)
        )
        by_status = dict(cur.fetchall())
    assert by_status.get("ok") == 1
    assert by_status.get("skipped_fresh") == 1


@pytest.mark.db
@responses.activate
def test_polite_get_ledgers_http_error(db_conn, _cleanup):
    responses.add(responses.GET, _URL, status=503)
    with pytest.raises(requests.RequestException):
        runlog.polite_get(db_conn, _SRC, _EP, _URL, dt.timedelta(hours=24))
    db_conn.rollback()  # the errored run was committed by finish_run; the raise aborted our txn
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status FROM ingest_run WHERE source = %s ORDER BY ingest_run_id DESC LIMIT 1",
            (_SRC,),
        )
        assert cur.fetchone()[0] == "error"
