"""The landing page's two expensive responses are computed once, warmed early, and never make a
visitor wait twice.

No database: the query functions are replaced with counters. ``/api/stats`` and the first
disposition page of ``/api/conflicts`` share the stale-while-revalidate memo in ``api.cache``;
every other conflicts page is computed fresh, as before.
"""

import threading
import time

import pytest
from fastapi import HTTPException

from api.cache import RefreshingCache
from api.routers import conflicts, stats

DB = object()  # the request's connection; the fakes never touch it


def _wait_for_refresh(cache, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while cache.refreshing and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not cache.refreshing, "background refresh never finished"


@pytest.fixture(autouse=True)
def _cold_caches():
    stats.stats_cache.reset()
    conflicts.first_disposition_page.reset()
    yield
    _wait_for_refresh(stats.stats_cache)
    _wait_for_refresh(conflicts.first_disposition_page)
    # Reset on teardown too, so a fake value planted here never leaks into a later test file
    # whatever the run order (the old twoskies fixture got this from monkeypatch for free).
    stats.stats_cache.reset()
    conflicts.first_disposition_page.reset()


class _Counter:
    """Stands in for a query function; records every call and answers with ``value``."""

    def __init__(self, value, delay_s=0.0):
        self.value, self.delay_s, self.calls = value, delay_s, []

    def __call__(self, db, *args):
        self.calls.append((db, *args))
        time.sleep(self.delay_s)
        return self.value if not callable(self.value) else self.value()


def _fake_db(conn):
    def get_db():
        yield conn

    return get_db


# ---------------------------------------------------------------------------------------------
# /api/stats
# ---------------------------------------------------------------------------------------------
def test_stats_is_computed_once_and_served_from_memory(monkeypatch):
    compute = _Counter({"stars": 1})
    monkeypatch.setattr(stats, "catalog_stats", compute)
    assert stats.get_stats(DB) == {"stars": 1}
    assert stats.get_stats(DB) == {"stars": 1}
    assert compute.calls == [(DB,)]  # the first request used its own connection; the second none


def test_concurrent_cold_stats_requests_compute_once(monkeypatch):
    compute = _Counter({"stars": 1}, delay_s=0.05)
    monkeypatch.setattr(stats, "catalog_stats", compute)
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(stats.get_stats(DB))) for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(compute.calls) == 1
    assert results == [{"stars": 1}] * 4


def test_stale_stats_are_served_while_one_background_refresh_runs(monkeypatch):
    compute = _Counter({"stars": 1})
    monkeypatch.setattr(stats, "catalog_stats", compute)
    stats.get_stats(DB)

    refresh_conn = object()
    fresh = _Counter({"stars": 2}, delay_s=0.2)
    monkeypatch.setattr(stats, "catalog_stats", fresh)
    monkeypatch.setattr(stats, "get_db", _fake_db(refresh_conn))
    monkeypatch.setattr(stats.stats_cache, "ttl_s", 0.0)
    started = time.monotonic()
    served = [stats.get_stats(DB)["stars"] for _ in range(3)]
    assert served == [1, 1, 1]  # the stale numbers, immediately
    assert time.monotonic() - started < 0.15  # nobody waited on the 0.2 s refresh
    _wait_for_refresh(stats.stats_cache)
    assert fresh.calls == [(refresh_conn,)]  # three stale hits, one refresh, on its own connection
    monkeypatch.setattr(stats.stats_cache, "ttl_s", 3600.0)
    assert stats.get_stats(DB)["stars"] == 2


def test_a_failed_stats_refresh_keeps_the_previous_numbers(monkeypatch):
    monkeypatch.setattr(stats, "catalog_stats", _Counter({"stars": 1}))
    stats.get_stats(DB)

    def broken_db():
        raise OSError("database unreachable")
        yield  # pragma: no cover

    monkeypatch.setattr(stats, "get_db", broken_db)
    monkeypatch.setattr(stats.stats_cache, "ttl_s", 0.0)
    assert stats.get_stats(DB)["stars"] == 1
    _wait_for_refresh(stats.stats_cache)
    assert stats.stats_cache.value == {"stars": 1}


# ---------------------------------------------------------------------------------------------
# /api/conflicts: only the first disposition page is memoised
# ---------------------------------------------------------------------------------------------
def _page(ctype, limit, offset, total=321):
    return {
        "type": ctype,
        "rows": [{"candidate_id": offset + i} for i in range(min(limit, total - offset))],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _fake_list(counter):
    def list_conflicts(db, ctype, limit, offset):
        counter.append((db, ctype, limit, offset))
        return _page(ctype, limit, offset)

    return list_conflicts


def test_first_disposition_page_is_fetched_once_at_full_size_and_sliced_per_request(monkeypatch):
    calls = []
    monkeypatch.setattr(conflicts, "list_conflicts", _fake_list(calls))
    overview = conflicts.get_conflicts(DB, type="disposition", limit=3, offset=0)
    listing = conflicts.get_conflicts(DB, type="disposition", limit=40, offset=0)
    assert calls == [(DB, "disposition", conflicts.FIRST_PAGE_ROWS, 0)]
    assert [r["candidate_id"] for r in overview["rows"]] == [0, 1, 2]
    assert (overview["limit"], overview["offset"], overview["total"]) == (3, 0, 321)
    assert len(listing["rows"]) == 40
    assert (listing["limit"], listing["offset"], listing["total"]) == (40, 0, 321)
    assert listing["type"] == "disposition"


def test_the_cached_page_is_not_mutated_by_slicing(monkeypatch):
    monkeypatch.setattr(conflicts, "list_conflicts", _fake_list([]))
    conflicts.get_conflicts(DB, type="disposition", limit=3, offset=0)
    assert len(conflicts.first_disposition_page.value["rows"]) == conflicts.FIRST_PAGE_ROWS
    assert conflicts.first_disposition_page.value["limit"] == conflicts.FIRST_PAGE_ROWS


def test_other_pages_and_types_are_computed_fresh(monkeypatch):
    calls = []
    monkeypatch.setattr(conflicts, "list_conflicts", _fake_list(calls))
    conflicts.get_conflicts(DB, type="disposition", limit=40, offset=40)
    conflicts.get_conflicts(DB, type="disposition", limit=40, offset=40)
    conflicts.get_conflicts(DB, type="radius", limit=40, offset=0)
    conflicts.get_conflicts(DB, type="teff", limit=3, offset=0)
    assert calls == [
        (DB, "disposition", 40, 40),
        (DB, "disposition", 40, 40),
        (DB, "radius", 40, 0),
        (DB, "teff", 3, 0),
    ]
    assert conflicts.first_disposition_page.value is None


def test_an_unknown_type_is_still_a_400_before_any_query(monkeypatch):
    calls = []
    monkeypatch.setattr(conflicts, "list_conflicts", _fake_list(calls))
    with pytest.raises(HTTPException) as exc:
        conflicts.get_conflicts(DB, type="mass", limit=3, offset=0)
    assert exc.value.status_code == 400
    assert calls == []


# ---------------------------------------------------------------------------------------------
# warm-up (what the FastAPI lifespan runs at start)
# ---------------------------------------------------------------------------------------------
def test_warm_computes_on_a_thread_and_a_request_arriving_meanwhile_waits_for_it():
    refreshes, requests = [], []

    def refresh():
        refreshes.append(1)
        time.sleep(0.1)
        return "warm"

    cache = RefreshingCache("t", 3600.0, refresh)
    warming = cache.warm()
    time.sleep(0.02)  # the warm-up is now mid-computation
    assert cache.get(lambda: requests.append(1) or "cold") == "warm"
    warming.join()
    assert (refreshes, requests) == ([1], [])


def test_a_failed_warm_up_leaves_the_first_request_to_compute_cold():
    def refresh():
        raise OSError("database unreachable")

    cache = RefreshingCache("t", 3600.0, refresh)
    cache.warm().join()
    assert cache.value is None
    assert cache.get(lambda: "cold") == "cold"


def test_keep_warm_recomputes_on_the_ttl_without_any_request():
    """A quiet site must not serve last night's counts to the first visitor of the day: with
    keep_warm the warm-up thread recomputes every TTL on its own, no request needed."""
    refreshes = []

    def refresh():
        refreshes.append(time.monotonic())
        return len(refreshes)

    cache = RefreshingCache("t", 0.05, refresh)
    cache.warm(keep_warm=True)
    deadline = time.monotonic() + 2.0
    while len(refreshes) < 3 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(refreshes) >= 3, "the keep-warm loop did not recompute on the TTL"
    # The served value is the latest completed refresh, or the one before it if a refresh is
    # mid-flight at the moment of reading.
    assert cache.value in (len(refreshes), len(refreshes) - 1)
