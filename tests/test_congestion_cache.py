"""The congestion panel is memoized whole: warm hits run no SQL, and cold requests compute once.

No database: a fake connection answers the three queries and counts them.
"""

import threading
import time

import pytest

from api.routers import twoskies


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.last = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.conn.executed.append(sql)
        self.last = sql
        time.sleep(self.conn.delay_s)

    def fetchall(self):
        if self.last is twoskies._CONGESTION_SQL:
            return [
                {"alt_bin_km": 550, "inc_bin_deg": 50, "object_count": 7},
                {"alt_bin_km": 1200, "inc_bin_deg": 85, "object_count": 3},
            ]
        return [{"operator": "Example Orbital", "payloads": 10}]

    def fetchone(self):
        return {
            "catalog_objects": 100,
            "tracked_with_elements": 90,
            "payloads_launched_1y": 12,
            "payloads_launched_30d": 2,
        }


class _FakeConn:
    def __init__(self, delay_s=0.0):
        self.executed = []
        self.delay_s = delay_s

    def cursor(self):
        return _FakeCursor(self)


@pytest.fixture(autouse=True)
def _cold_cache(monkeypatch):
    monkeypatch.setattr(twoskies, "_congestion_cached", None)


def test_a_warm_hit_runs_no_sql_and_returns_the_same_payload():
    conn = _FakeConn()
    first = twoskies.congestion_astronomy(conn)
    queries_after_first = len(conn.executed)
    second = twoskies.congestion_astronomy(conn)
    assert queries_after_first == 3
    assert len(conn.executed) == 3
    assert second is first
    assert first["leo_objects"] == 10
    assert first["shells"] == [
        {"alt_lo_km": 400, "alt_hi_km": 600, "objects": 7},
        {"alt_lo_km": 1200, "alt_hi_km": 1400, "objects": 3},
    ]


def test_an_expired_entry_is_recomputed(monkeypatch):
    conn = _FakeConn()
    twoskies.congestion_astronomy(conn)
    monkeypatch.setattr(twoskies, "CONGESTION_TTL_S", 0.0)
    twoskies.congestion_astronomy(conn)
    assert len(conn.executed) == 6


def test_concurrent_cold_requests_compute_once():
    conn = _FakeConn(delay_s=0.05)
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(twoskies.congestion_astronomy(conn)))
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(conn.executed) == 3
    assert all(r is results[0] for r in results)
