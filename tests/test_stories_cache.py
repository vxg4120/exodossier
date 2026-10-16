"""The landing page's stories: memoised like /api/stats, and the snapshot arithmetic behind them.

No database: the query function is replaced with a counter, and the pure helpers in
``api.stories`` take plain values.
"""

import datetime as dt
import threading
import time

import pytest

from api import stories as st
from api.routers import stories

DB = object()  # the request's connection; the fakes never touch it


def _wait_for_refresh(cache, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while cache.refreshing and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not cache.refreshing, "background refresh never finished"


@pytest.fixture(autouse=True)
def _cold_cache():
    stories.stories_cache.reset()
    yield
    _wait_for_refresh(stories.stories_cache)
    stories.stories_cache.reset()


class _Counter:
    def __init__(self, value, delay_s=0.0):
        self.value, self.delay_s, self.calls = value, delay_s, []

    def __call__(self, db, *args):
        self.calls.append((db, *args))
        time.sleep(self.delay_s)
        return self.value


def _fake_db(conn):
    def get_db():
        yield conn

    return get_db


# ---------------------------------------------------------------------------------------------
# the cache
# ---------------------------------------------------------------------------------------------
def test_stories_are_computed_once_and_served_from_memory(monkeypatch):
    compute = _Counter({"as_of": "2026-10-15"})
    monkeypatch.setattr(stories, "catalog_stories", compute)
    assert stories.get_stories(DB) == {"as_of": "2026-10-15"}
    assert stories.get_stories(DB) == {"as_of": "2026-10-15"}
    assert compute.calls == [(DB,)]


def test_concurrent_cold_stories_requests_compute_once(monkeypatch):
    compute = _Counter({"as_of": "2026-10-15"}, delay_s=0.05)
    monkeypatch.setattr(stories, "catalog_stories", compute)
    results = []
    threads = [
        threading.Thread(target=lambda: results.append(stories.get_stories(DB)))
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(compute.calls) == 1
    assert results == [{"as_of": "2026-10-15"}] * 4


def test_stale_stories_are_served_while_one_background_refresh_runs(monkeypatch):
    monkeypatch.setattr(stories, "catalog_stories", _Counter({"as_of": "2026-10-14"}))
    stories.get_stories(DB)

    refresh_conn = object()
    fresh = _Counter({"as_of": "2026-10-15"}, delay_s=0.2)
    monkeypatch.setattr(stories, "catalog_stories", fresh)
    monkeypatch.setattr(stories, "get_db", _fake_db(refresh_conn))
    monkeypatch.setattr(stories.stories_cache, "ttl_s", 0.0)
    started = time.monotonic()
    served = [stories.get_stories(DB)["as_of"] for _ in range(3)]
    assert served == ["2026-10-14"] * 3
    assert time.monotonic() - started < 0.15
    _wait_for_refresh(stories.stories_cache)
    assert fresh.calls == [(refresh_conn,)]
    monkeypatch.setattr(stories.stories_cache, "ttl_s", 3600.0)
    assert stories.get_stories(DB)["as_of"] == "2026-10-15"


def test_a_failed_stories_refresh_keeps_the_previous_payload(monkeypatch):
    monkeypatch.setattr(stories, "catalog_stories", _Counter({"as_of": "2026-10-14"}))
    stories.get_stories(DB)

    def broken_db():
        raise OSError("database unreachable")
        yield  # pragma: no cover

    monkeypatch.setattr(stories, "get_db", broken_db)
    monkeypatch.setattr(stories.stories_cache, "ttl_s", 0.0)
    assert stories.get_stories(DB)["as_of"] == "2026-10-14"
    _wait_for_refresh(stories.stories_cache)
    assert stories.stories_cache.value == {"as_of": "2026-10-14"}


@pytest.mark.filterwarnings(r"ignore:Using `httpx`")
def test_the_lifespan_warms_the_stories_cache(monkeypatch):
    from fastapi.testclient import TestClient

    from api import main
    from api.routers import conflicts, stats

    warmed = []
    for cache in (stats.stats_cache, conflicts.first_disposition_page, stories.stories_cache):
        monkeypatch.setattr(cache, "warm", lambda keep_warm=False, c=cache: warmed.append(
            (c.name, keep_warm)))
    with TestClient(main.app):
        pass
    assert ("stories", True) in warmed


# ---------------------------------------------------------------------------------------------
# snapshot arithmetic
# ---------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("radius", "label"),
    [
        (None, "Unknown radius"),
        (0.94, "Earth-size"),
        (1.25, "Super-Earth"),
        (1.99, "Super-Earth"),
        (2.0, "Sub-Neptune"),
        (4.0, "Neptune-size"),
        (6.0, "Giant"),
        (13.5, "Giant"),
    ],
)
def test_radius_bins_follow_the_spec_edges(radius, label):
    assert st.radius_bin(radius) == label


def test_size_bins_keep_every_bin_in_order_with_zeros():
    out = st.size_bins([0.9, 2.5, 2.6, None])
    assert [b["bin"] for b in out] == [
        "Earth-size", "Super-Earth", "Sub-Neptune", "Neptune-size", "Giant", "Unknown radius",
    ]
    assert [b["count"] for b in out] == [1, 0, 2, 0, 0, 1]


def test_alert_months_are_fifteen_with_gaps_as_zero_and_the_current_month_partial():
    out = st.fill_months({"2025-08": 10, "2026-10": 3}, dt.date(2026, 10, 15))
    assert len(out) == 15
    assert (out[0]["month"], out[-1]["month"]) == ("2025-08", "2026-10")
    assert out[0]["count"] == 10 and out[1] == {"month": "2025-09", "count": 0, "partial": False}
    assert out[-1] == {"month": "2026-10", "count": 3, "partial": True}
    assert sum(r["partial"] for r in out) == 1


def test_month_window_crosses_the_year():
    assert st.month_window(dt.date(2026, 2, 1), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


SNAPS = [
    {"run": 6, "date": "2026-07-15"},
    {"run": 1111, "date": "2026-08-01"},
    {"run": 1849, "date": "2026-10-01"},
    {"run": 1993, "date": "2026-10-13"},
    {"run": 2017, "date": "2026-10-15"},
]


def test_this_month_is_measured_from_the_first_snapshot_of_the_newest_month():
    assert st.month_baseline(SNAPS)["date"] == "2026-10-01"


def test_on_the_first_of_the_month_this_month_falls_back_to_the_snapshot_before():
    assert st.month_baseline(SNAPS[:3])["date"] == "2026-08-01"


def test_one_snapshot_has_no_month_baseline():
    assert st.month_baseline(SNAPS[:1]) is None


RUNS = [6, 1111, 1849, 2017]
# only the names missing from some snapshot reach Python
PARTIAL = {
    "CD-35 2722 b": [6, 1111],  # renamed on Oct 1
    "CD-35 2722 B b": [1849, 2017],
    "NGTS-39 b": [1111, 1849, 2017],
    "TOI-2158 c": [2017],
}


def test_membership_changes_per_snapshot():
    steps = st.membership_changes(PARTIAL, RUNS)
    assert steps[0] == {"added": [], "removed": []}
    assert steps[1] == {"added": ["NGTS-39 b"], "removed": []}
    assert steps[2] == {"added": ["CD-35 2722 B b"], "removed": ["CD-35 2722 b"]}
    assert steps[3] == {"added": ["TOI-2158 c"], "removed": []}


def test_diff_names_counts_a_departure_as_removed_not_hidden():
    added, removed = st.diff_names(PARTIAL, 6, 2017)
    assert added == ["CD-35 2722 B b", "NGTS-39 b", "TOI-2158 c"]
    assert removed == ["CD-35 2722 b"]


def test_first_seen_is_the_earliest_snapshot_date():
    dates = {6: "2026-07-15", 1111: "2026-08-01", 1849: "2026-10-01", 2017: "2026-10-15"}
    assert st.first_seen([1849, 2017], dates) == "2026-10-01"


ROWS = [
    {"pl_name": "TOI-6662 b", "host": "TOI-6662", "facility": "TESS", "radius_re": 0.94,
     "period_days": 0.29},
    {"pl_name": "TOI-2158 c", "host": "TOI-2158", "facility": "Multiple Facilities",
     "radius_re": 13.5, "period_days": 414.5},
    {"pl_name": "Elias 2-24 b", "host": "Elias 2-24", "facility": None, "radius_re": 13.2,
     "period_days": None},
]


def test_records_skip_unknown_values():
    assert st.record(ROWS, "radius_re", largest=False)["pl_name"] == "TOI-6662 b"
    assert st.record(ROWS, "period_days", largest=False)["value"] == 0.29
    longest = st.record(ROWS, "period_days", largest=True)
    assert (longest["pl_name"], longest["value"]) == ("TOI-2158 c", 414.5)
    assert st.record([], "radius_re", largest=False) is None


def test_facility_counts_rank_by_count_and_name_an_unknown_facility():
    out = st.facility_counts(ROWS + [dict(ROWS[0], pl_name="TOI-1 b")])
    assert out[0] == {"facility": "TESS", "count": 2}
    assert {"facility": "Unknown facility", "count": 1} in out


def test_transitions_sort_by_count_then_codes_with_blank_dispositions_allowed():
    rows = [
        {"from": "PC", "to": "FP", "count": 57},
        {"from": None, "to": "KP", "count": 1},
        {"from": "PC", "to": "CP", "count": 79},
        {"from": "APC", "to": "CP", "count": 1},
    ]
    assert [(t["from"], t["to"]) for t in st.sort_transitions(rows)] == [
        ("PC", "CP"), ("PC", "FP"), (None, "KP"), ("APC", "CP"),
    ]
