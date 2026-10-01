"""The congestion panel caches only its ingest-driven half, and never makes a visitor wait twice.

No database: a fake connection answers the four queries and records what ran. The scan-heavy half
(bins, tracked count, top operators) is cached and refreshed in the background once stale; the
launch windows roll over at midnight, so they are read fresh on every request.
"""

import threading
import time

import pytest

from api.routers import twoskies

BINS_A = [
    {"alt_bin_km": 550, "inc_bin_deg": 50, "object_count": 7},
    {"alt_bin_km": 1200, "inc_bin_deg": 85, "object_count": 3},
]
BINS_B = [{"alt_bin_km": 500, "inc_bin_deg": 95, "object_count": 11}]


class _FakeConn:
    """Answers each query by identity with the module's SQL constants; records every execution."""

    def __init__(self, bins=BINS_A, windows=(12, 2), delay_s=0.0):
        self.bins, self.windows, self.delay_s = bins, windows, delay_s
        self.executed = []

    def cursor(self):
        return _FakeCursor(self)


class _FakeCursor:
    def __init__(self, conn):
        self.conn, self.last = conn, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append(sql)
        self.last = sql
        if sql is twoskies._CONGESTION_SQL:
            time.sleep(self.conn.delay_s)

    def fetchall(self):
        if self.last is twoskies._CONGESTION_SQL:
            return self.conn.bins
        return [{"operator": "Example Orbital", "payloads": 10}]

    def fetchone(self):
        if self.last is twoskies._TRACKED_SQL:
            return {"tracked_with_elements": 90}
        one_y, thirty_d = self.conn.windows
        return {
            "catalog_objects": 100,
            "payloads_launched_1y": one_y,
            "payloads_launched_30d": thirty_d,
        }


def _scans(*conns):
    return sum(c.executed.count(twoskies._CONGESTION_SQL) for c in conns)


def _wait_for_refresh(timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while twoskies._heavy_refreshing and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not twoskies._heavy_refreshing, "background refresh never finished"


@pytest.fixture(autouse=True)
def _cold_cache(monkeypatch):
    monkeypatch.setattr(twoskies, "_heavy_cached", None)
    monkeypatch.setattr(twoskies, "_heavy_refreshing", False)
    yield
    _wait_for_refresh()


def test_a_warm_hit_skips_the_scan_but_reads_the_launch_windows_fresh():
    first = twoskies.congestion_astronomy(_FakeConn(windows=(12, 2)))
    later = _FakeConn(windows=(13, 3))
    second = twoskies.congestion_astronomy(later)
    assert _scans(later) == 0
    assert later.executed == [twoskies._LAUNCH_WINDOWS_SQL]
    assert (first["payloads_launched_1y"], first["payloads_launched_30d"]) == (12, 2)
    assert (second["payloads_launched_1y"], second["payloads_launched_30d"]) == (13, 3)
    assert second["leo_objects"] == 10
    assert second["shells"] == [
        {"alt_lo_km": 400, "alt_hi_km": 600, "objects": 7},
        {"alt_lo_km": 1200, "alt_hi_km": 1400, "objects": 3},
    ]


def test_a_stale_entry_is_served_while_one_background_refresh_runs(monkeypatch):
    twoskies.congestion_astronomy(_FakeConn(bins=BINS_A))
    refresh_conn = _FakeConn(bins=BINS_B, delay_s=0.2)

    def fake_oei_db():
        yield refresh_conn

    monkeypatch.setattr(twoskies, "get_oei_db", fake_oei_db)
    monkeypatch.setattr(twoskies, "CONGESTION_TTL_S", 0.0)
    served = []
    started = time.monotonic()
    for _ in range(3):
        served.append(twoskies.congestion_astronomy(_FakeConn())["leo_objects"])
    elapsed = time.monotonic() - started
    assert served == [10, 10, 10]  # the stale numbers, immediately
    assert elapsed < 0.15  # nobody waited on the 0.2 s refresh
    _wait_for_refresh()
    assert _scans(refresh_conn) == 1  # three stale hits, one refresh
    monkeypatch.setattr(twoskies, "CONGESTION_TTL_S", 3600.0)
    assert twoskies.congestion_astronomy(_FakeConn())["leo_objects"] == 11


def test_a_failed_refresh_keeps_the_previous_numbers_in_service(monkeypatch):
    twoskies.congestion_astronomy(_FakeConn(bins=BINS_A))

    def broken_oei_db():
        raise OSError("database unreachable")
        yield  # pragma: no cover

    monkeypatch.setattr(twoskies, "get_oei_db", broken_oei_db)
    monkeypatch.setattr(twoskies, "CONGESTION_TTL_S", 0.0)
    assert twoskies.congestion_astronomy(_FakeConn())["leo_objects"] == 10
    _wait_for_refresh()
    assert twoskies._heavy_cached is not None
    assert twoskies._heavy_cached[1]["leo_objects"] == 10


def test_concurrent_cold_requests_run_the_scan_once():
    conns = [_FakeConn(delay_s=0.05) for _ in range(4)]
    results = []
    threads = [
        threading.Thread(target=lambda c=c: results.append(twoskies.congestion_astronomy(c)))
        for c in conns
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert _scans(*conns) == 1
    assert [r["leo_objects"] for r in results] == [10, 10, 10, 10]


def test_a_refresh_thread_that_fails_to_start_does_not_disable_refreshes(monkeypatch):
    import types

    twoskies.congestion_astronomy(_FakeConn(bins=BINS_A))

    class _Unstartable:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            raise RuntimeError("can't start new thread")

    real_threading = twoskies.threading
    monkeypatch.setattr(twoskies, "CONGESTION_TTL_S", 0.0)
    monkeypatch.setattr(twoskies, "threading", types.SimpleNamespace(Thread=_Unstartable))
    assert twoskies.congestion_astronomy(_FakeConn())["leo_objects"] == 10  # stale, no error
    assert twoskies._heavy_refreshing is False

    refresh_conn = _FakeConn(bins=BINS_B)

    def fake_oei_db():
        yield refresh_conn

    monkeypatch.setattr(twoskies, "threading", real_threading)
    monkeypatch.setattr(twoskies, "get_oei_db", fake_oei_db)
    twoskies.congestion_astronomy(_FakeConn())  # a later request retries the refresh
    _wait_for_refresh()
    assert _scans(refresh_conn) == 1
