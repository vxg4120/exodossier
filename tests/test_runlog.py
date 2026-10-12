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


@pytest.mark.db
def test_a_daily_feed_pulled_at_yesterdays_slot_is_due_again_today(db_conn, _cleanup):
    # The nightly's two slots are 12 hours apart and fresh_within counts from finished_at, so a
    # full day's interval left yesterday's slot "fresh" whenever tonight's exo ingest started a
    # few minutes earlier than yesterday's finished. The daily interval has to call that pull
    # stale, and a pull from the other slot today fresh.
    run_id = runlog.start_run(db_conn, _SRC, "daily")
    runlog.finish_run(db_conn, run_id, rows=1, bytes_dl=1, status="ok")
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE ingest_run SET started_at = now() - interval '24 hours', "
            "finished_at = now() - interval '23 hours 55 minutes' WHERE ingest_run_id = %s",
            (run_id,),
        )
    assert runlog.fresh_within(db_conn, _SRC, "daily", runlog.DAILY) is False
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE ingest_run SET started_at = now() - interval '12 hours', "
            "finished_at = now() - interval '11 hours 55 minutes' WHERE ingest_run_id = %s",
            (run_id,),
        )
    assert runlog.fresh_within(db_conn, _SRC, "daily", runlog.DAILY) is True


@pytest.mark.db
def test_a_failed_morning_pull_is_retried_in_the_evening(db_conn, _cleanup):
    # Only an 'ok' run makes a feed fresh, so a pull that failed at this morning's slot leaves
    # the feed due at the evening slot, 12 hours later.
    run_id = runlog.start_run(db_conn, _SRC, "daily_retry")
    runlog.finish_run(db_conn, run_id, rows=0, bytes_dl=0, status="error")
    with db_conn.cursor() as cur:
        cur.execute(
            "UPDATE ingest_run SET started_at = now() - interval '12 hours', "
            "finished_at = now() - interval '11 hours 55 minutes' WHERE ingest_run_id = %s",
            (run_id,),
        )
    assert runlog.fresh_within(db_conn, _SRC, "daily_retry", runlog.DAILY) is False


def test_every_daily_feed_fits_between_one_nightly_slot_and_a_day():
    from ingest import loaders

    assert loaders.MIN_INTERVAL is runlog.DAILY
    assert dt.timedelta(hours=12) < runlog.DAILY < dt.timedelta(hours=24)
