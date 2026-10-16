"""The light-curve results endpoints (/api/lightcurves/*): grading, summary shape, pagination,
the 400/404 paths and the empty state.

``grade`` is pure and tested on plain dicts. The endpoint tests plant a small slice (one target per
outcome) inside a transaction that is rolled back at teardown, after emptying the Wave 2 tables in
that same transaction, so they run the same on a database with a real run and on one without.
The API's get_db dependency is pointed at that transaction for the duration of a test.

The rebuild test runs identity/build.py's own reset (TRUNCATE of the derived graph, RESTART
IDENTITY CASCADE) inside that transaction and checks that the results survive it and re-resolve
to the re-inserted candidate's new id.
"""

import warnings

warnings.filterwarnings("ignore", message=r"Using `httpx`")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from api.deps import get_db  # noqa: E402
from api.main import app  # noqa: E402
from api.routers.lightcurves import grade  # noqa: E402

pytestmark = pytest.mark.filterwarnings(r"ignore:Using `httpx`")

BTJD = 2457000.0
OK = {"status": "ok", "notes": None}


def _t(cohort="gold_planet", period=10.0, epoch=BTJD + 1000.0, depth=2000.0):
    return {"cohort": cohort, "known_period_days": period, "known_epoch_bjd": epoch,
            "known_depth_ppm": depth}


def _d(method="bls", period=10.0, snr=50.0, epoch=1000.0):
    return {"method": method, "period_days": period, "epoch_bjd": epoch, "depth_ppm": 2000.0,
            "duration_hr": 3.0, "snr": snr, "sde": None, "rank": 1}


# ---- pure grading ------------------------------------------------------------------------------

def test_grade_pending_and_failed_runs():
    assert grade(_t(), None, [])["verdict"] == "pending"
    assert grade(_t(), {"status": "running", "notes": None}, [])["verdict"] == "running"
    g = grade(_t(), {"status": "timeout", "notes": "TLS over 150 s"}, [])
    assert g["verdict"] == "not_processed"
    assert "timeout" in g["reason"] and "150 s" in g["reason"]


def test_grade_gold_planet_exact_harmonic_and_miss():
    g = grade(_t(), OK, [_d(period=10.02)])
    assert g["verdict"] == "recovered" and g["match"] == 1.0
    assert g["best"]["method"] == "bls" and g["phase_offset"] == pytest.approx(0.0)

    g = grade(_t(), OK, [_d(period=20.0)])
    assert g["verdict"] == "recovered_harmonic" and g["match"] == 2.0

    # the right period below SNR 7 is not a recovery
    g = grade(_t(), OK, [_d(period=10.0, snr=5.0)])
    assert g["verdict"] == "missed" and g["reason"]

    # beyond the 50-day periodic cap: the documented blind spot is the reason given
    g = grade(_t(period=260.0), OK, [_d(period=40.0)])
    assert g["verdict"] == "missed" and "50 d" in g["reason"]


def test_grade_false_positive_and_discovery():
    fp = _t(cohort="gold_fp")
    assert grade(fp, OK, [_d(period=10.0)])["verdict"] == "signal_at_catalog_period"
    assert grade(fp, OK, [_d(period=13.7)])["verdict"] == "signal"
    assert grade(fp, OK, [_d(period=13.7, snr=3.0)])["verdict"] == "no_signal"

    disc = _t(cohort="discovery", period=None)
    se = _d(method="single_event", period=None, snr=30.0)
    g = grade(disc, OK, [_d(period=33.0, snr=4.0), se])
    assert g["verdict"] == "signal" and g["single_event"]["snr"] == 30.0
    assert grade(disc, OK, [_d(period=33.0, snr=4.0)])["verdict"] == "below_threshold"


# ---- endpoints over a planted slice ------------------------------------------------------------

def _wipe(cur):
    for table in ("detection", "fp_scenario", "pipeline_run", "target"):
        cur.execute(f"DELETE FROM {table}")


def _toi_link(cur, cand, toi):
    """The crosswalk row identity/build.py writes for a TOI (exofop and nea each assert one)."""
    for source in ("exofop", "nea"):
        cur.execute("INSERT INTO entity_identifier (candidate_id, id_type, id_value, source) "
                    "VALUES (%s, 'toi', %s, %s)", (cand, toi, source))


def _plant(cur, n, cohort, toi, period, dets, status="ok"):
    tic = 990100000 + n
    cur.execute("INSERT INTO star (tic_id, canonical_name) VALUES (%s, %s) RETURNING star_id",
                (tic, f"LC-TEST-{n}"))
    star = cur.fetchone()["star_id"]
    cur.execute("INSERT INTO candidate (star_id, canonical_name) VALUES (%s, %s) "
                "RETURNING candidate_id", (star, f"LC-TEST-{n} b"))
    cand = cur.fetchone()["candidate_id"]
    _toi_link(cur, cand, toi)
    cur.execute(
        """INSERT INTO target (candidate_id, tic_id, toi, cohort, stratum, tfopwg_disp,
               known_period_days, known_epoch_bjd, known_depth_ppm, select_rule)
           VALUES (%s,%s,%s,%s,'test','CP',%s,%s,2000,'test') RETURNING target_id""",
        (cand, tic, toi, cohort, period, BTJD + 1000.0),
    )
    target = cur.fetchone()["target_id"]
    if status is None:
        return cand
    cur.execute(
        """INSERT INTO pipeline_run (target_id, tic_id, status, runtime_s, data_vintage,
               finished_at) VALUES (%s,%s,%s,42,'2026-07-15','2026-07-15 21:30+00')
           RETURNING pipeline_run_id""",
        (target, tic, status),
    )
    run = cur.fetchone()["pipeline_run_id"]
    for d in dets:
        cur.execute(
            """INSERT INTO detection (pipeline_run_id, tic_id, method, rank, period_days,
                   epoch_bjd, depth_ppm, duration_hr, snr) VALUES (%s,%s,%s,1,%s,%s,2000,3,%s)""",
            (run, tic, d["method"], d["period_days"], d["epoch_bjd"], d["snr"]),
        )
    return cand


@pytest.fixture
def lc_db(db_conn):
    db_conn.row_factory = dict_row
    with db_conn.cursor() as cur:
        _wipe(cur)

    def _override():
        yield db_conn

    app.dependency_overrides[get_db] = _override
    try:
        yield db_conn
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def planted(lc_db):
    with lc_db.cursor() as cur:
        ids = {
            "hit": _plant(cur, 1, "gold_planet", "9001.01", 10.0, [_d(period=10.01, snr=80.0)]),
            "miss": _plant(cur, 2, "gold_planet", "9002.01", 260.0, [_d(period=40.0)]),
            "fp": _plant(cur, 3, "gold_fp", "9003.01", 5.0, [_d(period=5.0, snr=300.0)]),
            "disc": _plant(cur, 4, "discovery", "9004.01", None,
                           [_d(period=33.0, snr=4.0),
                            _d(method="single_event", period=None, snr=25.0)]),
            "error": _plant(cur, 5, "discovery", "9005.01", 40.0, [], status="error"),
            "pending": _plant(cur, 6, "discovery", "9006.01", 45.0, [], status=None),
        }
    return ids


client = TestClient(app)


@pytest.mark.db
def test_summary_shape_and_counts(planted):
    s = client.get("/api/lightcurves/summary").json()
    assert s["state"] == "ready"
    assert (s["targets"], s["processed"], s["not_processed"], s["pending"]) == (6, 4, 1, 1)
    assert s["gold_planets"] == {"targets": 2, "recovered": 1, "recovered_exact": 1}
    assert s["gold_false_positives"] == {"targets": 1, "with_signal": 1}
    assert s["discovery"] == {"targets": 3, "with_signal": 1}
    assert set(s["by_cohort"]) == {"gold_planet", "gold_fp", "discovery"}
    assert s["by_cohort"]["gold_planet"]["by_verdict"] == {"recovered": 1, "missed": 1}
    assert s["last_run_at"].startswith("2026-07-15")
    assert s["data_vintage"] == "2026-07-15"
    assert s["rules"]["snr_min"] == 7.0
    for key in ("lightcurve_files", "lightcurve_stars", "last_fetch_at", "median_runtime_s"):
        assert key in s


@pytest.mark.db
def test_results_pagination_sort_and_links(planted):
    r = client.get("/api/lightcurves/results", params={"limit": 4, "offset": 0}).json()
    assert r["total"] == 6 and len(r["rows"]) == 4
    # cohort order: gold planets, then false positives, then discovery
    assert [row["cohort"] for row in r["rows"]] == ["gold_planet", "gold_planet", "gold_fp",
                                                    "discovery"]
    rest = client.get("/api/lightcurves/results", params={"limit": 4, "offset": 4}).json()
    assert len(rest["rows"]) == 2
    seen = {row["candidate_id"] for row in r["rows"] + rest["rows"]}
    assert seen == set(planted.values())

    first = r["rows"][0]
    assert first["toi"] == "9001.01" and first["verdict"] == "recovered"
    assert first["name"] == "LC-TEST-1 b" and first["tic_id"] == "990100001"
    # the row links to the target page by candidate_id, which the target endpoint resolves
    assert client.get(f"/api/target/{first['candidate_id']}").status_code == 200

    by_snr = client.get("/api/lightcurves/results", params={"sort": "snr"}).json()["rows"]
    assert by_snr[0]["candidate_id"] == planted["fp"]
    only = client.get("/api/lightcurves/results", params={"cohort": "discovery"}).json()
    assert only["total"] == 3 and {row["cohort"] for row in only["rows"]} == {"discovery"}


@pytest.mark.db
def test_bad_params_and_404(planted):
    assert client.get("/api/lightcurves/results", params={"cohort": "nope"}).status_code == 400
    assert client.get("/api/lightcurves/results", params={"sort": "nope"}).status_code == 422
    assert client.get("/api/lightcurves/results", params={"limit": 0}).status_code == 422
    one = client.get(f"/api/lightcurves/target/{planted['miss']}")
    assert one.status_code == 200 and one.json()["verdict"] == "missed"
    assert client.get("/api/lightcurves/target/-1").status_code == 404


@pytest.mark.db
def test_empty_state(lc_db):
    """No targets (what every graph rebuild leaves behind): zero counts, not an error."""
    s = client.get("/api/lightcurves/summary").json()
    assert s["state"] == "empty"
    assert (s["targets"], s["processed"], s["gold_planets"]["recovered"]) == (0, 0, 0)
    assert s["last_run_at"] is None
    r = client.get("/api/lightcurves/results").json()
    assert r["rows"] == [] and r["total"] == 0


def test_build_truncate_list_spares_the_result_tables():
    """The rebuild's TRUNCATE names only the derived graph, never a Wave 2 table."""
    from identity.build import _DERIVED_TABLES

    named = {t.strip() for t in _DERIVED_TABLES.split(",")}
    assert named.isdisjoint({"target", "pipeline_run", "detection", "fp_scenario",
                             "lightcurve_file"})


@pytest.mark.db
def test_results_survive_the_graph_rebuild(planted, lc_db):
    """The nightly rebuild truncates the graph with CASCADE and renumbers candidates. The results
    must survive it, and once the planet is back under a NEW candidate_id the row links there."""
    from identity.build import _reset

    before = client.get("/api/lightcurves/results", params={"limit": 200}).json()
    old_id = planted["hit"]
    assert any(r["candidate_id"] == old_id for r in before["rows"])

    with lc_db.cursor() as cur:
        cur.execute("SELECT max(candidate_id) AS m FROM candidate")
        high = cur.fetchone()["m"]
    _reset(lc_db)  # exactly the build's TRUNCATE ... RESTART IDENTITY CASCADE

    # The graph is gone, the results are not; with no crosswalk nothing links.
    s = client.get("/api/lightcurves/summary").json()
    assert (s["targets"], s["processed"]) == (6, 4)
    assert s["gold_planets"]["recovered"] == 1
    gone = client.get("/api/lightcurves/results", params={"limit": 200}).json()["rows"]
    assert len(gone) == 6 and all(r["candidate_id"] is None for r in gone)
    assert {r["name"] for r in gone} >= {"TOI-9001.01"}  # renders without a link

    # The rebuild re-inserts the planet; push the identity past the old ids so it gets a new one.
    with lc_db.cursor() as cur:
        cur.execute("SELECT setval(pg_get_serial_sequence('candidate', 'candidate_id'), %s)",
                    (high + 1000,))
        cur.execute("INSERT INTO star (tic_id, canonical_name) VALUES (990100001, 'LC-TEST-1') "
                    "RETURNING star_id")
        star = cur.fetchone()["star_id"]
        cur.execute("INSERT INTO candidate (star_id, canonical_name) VALUES (%s, 'LC-TEST-1 b') "
                    "RETURNING candidate_id", (star,))
        new_id = cur.fetchone()["candidate_id"]
        _toi_link(cur, new_id, "9001.01")
    assert new_id != old_id

    row = next(r for r in client.get("/api/lightcurves/results", params={"limit": 200}).json()
               ["rows"] if r["toi"] == "9001.01")
    assert row["candidate_id"] == new_id and row["name"] == "LC-TEST-1 b"
    assert row["verdict"] == "recovered"
    assert client.get(f"/api/lightcurves/target/{new_id}").json()["toi"] == "9001.01"
    assert client.get(f"/api/target/{new_id}").status_code == 200
    # the other five still have no candidate in the rebuilt graph and stay unlinked
    others = [r for r in client.get("/api/lightcurves/results", params={"limit": 200}).json()
              ["rows"] if r["toi"] != "9001.01"]
    assert all(r["candidate_id"] is None for r in others)
