"""Contract + sanity tests for the /api/twoskies/* Follow-up bridge (exoplanets x satellites).

Read-only across both databases: ExoDossier's own ``exo`` (the exoplanet targets) and the foreign
satellite ``oei`` (element sets + operator labels). ``/targets`` reads ``exo`` and is gated on the
usual ``db_conn`` fixture; ``/congestion-astronomy`` and ``/passes`` read ``oei`` and are gated on
its reachability, so the suite skips cleanly where only one database is up. The /passes sanity test
asserts the geometry contract (every returned separation is within the threshold; a below-horizon
target yields an empty, crash-free result) rather than an exact count, since propagated positions
drift as the element sets age.
"""

import datetime as dt
import os
import warnings

import psycopg
import pytest
from psycopg.rows import dict_row

from api.deps import OEI_DATABASE_URL_DEFAULT
from api.routers import twoskies

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fastapi.testclient import TestClient

from api.main import app


def _oei_reachable() -> bool:
    url = os.environ.get("OEI_DATABASE_URL", OEI_DATABASE_URL_DEFAULT)
    try:
        psycopg.connect(url).close()
        return True
    except psycopg.OperationalError:
        return False


oei_required = pytest.mark.skipif(
    not _oei_reachable(), reason="oei (satellite) database not reachable"
)

# UTC instants + target/site where geometry is fully determined by Earth rotation (independent of
# element-set freshness): GJ 1214 is well up over Kitt Peak; TRAPPIST-1 is below the observability
# gate at Kitt Peak at 05:00Z on 16 July. The same calendar instant in the current year keeps that
# sky (sidereal time at a fixed date and UTC drifts by minutes a year) and stays inside the
# service's ten-year start bound as the years pass.
_GJ1214 = {"ra": 258.831475, "dec": 4.960211}
_TRAPPIST1 = {"ra": 346.6263919, "dec": -5.0434618}
_WHEN = f"{dt.date.today().year}-07-16T05:00:00Z"

_PASS_KEYS = {"norad", "name", "operator", "alt_km", "closest_sep_deg", "alt_deg", "time_utc"}


@pytest.fixture
def client(db_conn):
    return TestClient(app)


# --------------------------------------------------------------------------- /targets (exo)
@pytest.mark.db
@pytest.mark.graph
def test_targets_shape_and_conflict_flag(client):
    r = client.get("/api/twoskies/targets")
    assert r.status_code == 200
    body = r.json()
    assert 30 <= len(body["targets"]) <= 120
    assert body["n_famous"] > 0 and body["n_conflict"] > 0

    required = {"candidate_id", "host", "ra_deg", "dec_deg", "disposition", "has_conflict"}
    for t in body["targets"]:
        assert required <= set(t)
        assert 0.0 <= t["ra_deg"] <= 360.0
        assert -90.0 <= t["dec_deg"] <= 90.0
        assert isinstance(t["has_conflict"], bool)

    # A famous host with coordinates is present, and at least one conflict-flagged target exists.
    hosts = {t["host"] for t in body["targets"]}
    assert "TRAPPIST-1" in hosts
    conflicted = [t for t in body["targets"] if t["has_conflict"]]
    assert conflicted, "expected at least one conflict-flagged target"
    assert all(t["ra_deg"] is not None and t["dec_deg"] is not None for t in conflicted)
    # every conflict-flagged target deep-links back to its dossier
    assert all(t["candidate_id"] is not None for t in conflicted)


@pytest.mark.db
@pytest.mark.graph
def test_conflict_flag_means_the_sources_disagree_on_disposition(client):
    """The flag says the catalogs disagree on disposition, so every flagged target's dossier has
    to show a disposition conflict, and every row of the conflict slice has to be flagged."""
    body = client.get("/api/twoskies/targets").json()
    assert all(t["has_conflict"] for t in body["targets"] if t["category"] == "conflict")
    for t in (t for t in body["targets"] if t["has_conflict"]):
        dossier = client.get(f"/api/target/{t['candidate_id']}").json()
        assert "disposition" in dossier["conflict_attributes"], t["candidate"]


# ------------------------------------------------------------------ the flag (no database)
_HOST_ROW = {
    "star_id": 1, "host": "Example", "tic_id": 42, "ra_deg": 10.0, "dec_deg": -5.0,
    "n_candidates": 3, "candidate_ids": [11, 12, 13],
    "candidate_names": ["Example b", "Example c", "TOI 9999.01"],
    "dispositions": ["CONFIRMED", "CANDIDATE", "AMBIGUOUS"],
}


def test_an_ambiguous_candidate_alone_is_not_a_conflict():
    # a resolved AMBIGUOUS disposition is one winning claim, not a disagreement between sources
    t = twoskies._reduce_target(_HOST_ROW, "famous", frozenset())
    assert t["has_conflict"] is False
    assert (t["candidate_id"], t["disposition"]) == (11, "CONFIRMED")


def test_a_flagged_host_is_represented_by_its_conflicted_candidate():
    t = twoskies._reduce_target(_HOST_ROW, "conflict", {12: False})
    assert t["has_conflict"] is True
    # the dossier link opens the candidate whose sources disagree, not the best-known planet
    assert (t["candidate_id"], t["candidate"], t["disposition"]) == (12, "Example c", "CANDIDATE")


class _FakeTargetsDb:
    """Answers the three /targets queries: the conflict corpus, the famous hosts, the slice."""

    def __init__(self, conflicted, famous, slice_rows):
        self.answers = {"corpus": conflicted, "famous": famous, "slice": slice_rows}
        self.params = {}

    def cursor(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        if sql is twoskies._CONFLICTED_CANDIDATES_SQL:
            self.last = "corpus"
        elif "ANY(%(names)s)" in sql:
            self.last = "famous"
        else:
            self.last = "slice"
        self.params[self.last] = params

    def fetchall(self):
        return self.answers[self.last]


def _host(star_id, host, ids, names, disps):
    return {"star_id": star_id, "host": host, "tic_id": None, "ra_deg": 1.0, "dec_deg": 2.0,
            "n_candidates": len(ids), "candidate_ids": ids, "candidate_names": names,
            "dispositions": disps}


def test_the_flag_and_the_slice_come_from_the_disposition_conflict_corpus():
    # the same CTE /conflicts and /api/stats count, expanded to every twin candidate row
    assert twoskies._CONFLICTED_CANDIDATES_SQL.startswith(twoskies._DISPO_CTE)
    corpus = [{"candidate_id": 2, "dramatic": False}, {"candidate_id": 5, "dramatic": True},
              {"candidate_id": 7, "dramatic": False}]
    famous = [_host(1, "TRAPPIST-1", [1, 2], ["TRAPPIST-1 b", "TRAPPIST-1 c"],
                    ["CONFIRMED", "CONFIRMED"]),
              _host(2, "GJ 1214", [3], ["GJ 1214 b"], ["AMBIGUOUS"])]
    slice_rows = [_host(3, "Alpha", [7], ["Alpha b"], ["CONFIRMED"]),
                  _host(4, "Zeta", [5], ["TOI 1.01"], ["FALSE_POSITIVE"])]
    db = _FakeTargetsDb(corpus, famous, slice_rows)
    body = twoskies.targets(db, conflict_limit=24)
    assert sorted(db.params["slice"]["conflicted"]) == [2, 5, 7]
    flags = {t["host"]: (t["has_conflict"], t["candidate"]) for t in body["targets"]}
    assert flags["TRAPPIST-1"] == (True, "TRAPPIST-1 c")  # famous hosts are flagged the same way
    assert flags["GJ 1214"] == (False, "GJ 1214 b")  # AMBIGUOUS alone is not a conflict
    # the dramatic kind leads the slice, then the rest by host name
    assert [t["host"] for t in body["targets"] if t["category"] == "conflict"] == ["Zeta", "Alpha"]
    assert "AMBIGUOUS" not in body["note"] and "/conflicts" in body["note"]


def test_decayed_objects_are_left_out_of_the_sky_and_the_counts():
    assert "s.decay_date IS NULL" in twoskies._FETCH_LEO_SQL
    for sql in (twoskies._CONGESTION_SQL, twoskies._TRACKED_SQL):
        assert sql.startswith(twoskies._LIVE_ELEMENTS_CTE)
    assert "s.decay_date IS NOT NULL" in twoskies._LIVE_ELEMENTS_CTE
    # the staleness window is measured against the data, so an old database copy still answers
    assert "now()" not in twoskies._LIVE_ELEMENTS_CTE


def test_the_caveat_dates_the_element_sets_by_their_refresh():
    caveat = twoskies.CAVEATS[1]
    assert "week old" not in caveat
    assert "CelesTrak twice a day" in caveat and "Space-Track once a day" in caveat


# ---------------------------------------------------------------- /congestion-astronomy (oei)
@oei_required
@pytest.mark.db
def test_congestion_astronomy_shape(client):
    r = client.get("/api/twoskies/congestion-astronomy")
    assert r.status_code == 200
    body = r.json()
    assert body["catalog_objects"] > 1000
    assert body["tracked_with_elements"] > 1000
    assert body["leo_objects"] > 0
    assert body["bins"] and body["shells"]
    assert body["top_operators"][0]["payloads"] > 0
    # bins carry the heatmap triple; caveats are present (the honest framing is mandatory).
    for b in body["bins"]:
        assert set(b) == {"alt_bin_km", "inc_bin_deg", "object_count"}
    assert len(body["caveats"]) >= 2


# --------------------------------------------------------------------------- /passes (oei)
@oei_required
@pytest.mark.db
def test_passes_geometry_contract(client):
    # GJ 1214 is well up over Kitt Peak at this instant (pure Earth-rotation geometry -- stable).
    r = client.get(
        "/api/twoskies/passes",
        params={**_GJ1214, "datetime": _WHEN, "site": "kitt_peak", "window_min": 60, "sep_deg": 5},
    )
    assert r.status_code == 200
    body = r.json()

    assert body["target_visible"] is True
    assert body["target_max_alt_deg"] > 20.0
    assert body["n_considered"] > 100
    assert body["n_found"] >= 0
    assert isinstance(body["passes"], list)

    # The geometry contract: every returned pass is within the threshold and above the horizon.
    for p in body["passes"]:
        assert set(p) == _PASS_KEYS
        assert p["closest_sep_deg"] <= 5.0
        assert p["alt_deg"] >= 0.0
        assert p["time_utc"].endswith("Z")
    # sorted ascending by closest separation.
    seps = [p["closest_sep_deg"] for p in body["passes"]]
    assert seps == sorted(seps)


@oei_required
@pytest.mark.db
def test_passes_below_horizon_target_is_empty(client):
    # TRAPPIST-1 is below the observability gate at Kitt Peak at this instant -> empty, no crash.
    r = client.get("/api/twoskies/passes", params={**_TRAPPIST1, "datetime": _WHEN,
                                                    "site": "kitt_peak"})
    assert r.status_code == 200
    body = r.json()
    assert body["target_visible"] is False
    assert body["n_found"] == 0
    assert body["passes"] == []


@oei_required
@pytest.mark.db
def test_passes_default_datetime_runs(client):
    # No datetime => "now"; must run cleanly whatever the current sky looks like.
    r = client.get("/api/twoskies/passes", params={**_GJ1214, "site": "generic_north"})
    assert r.status_code == 200
    body = r.json()
    assert body["elapsed_ms"] > 0
    assert all(p["closest_sep_deg"] <= body["sep_deg"] for p in body["passes"])


@oei_required
@pytest.mark.db
def test_passes_custom_latlon(client):
    r = client.get("/api/twoskies/passes", params={**_GJ1214, "datetime": _WHEN,
                                                    "lat": 31.96, "lon": -111.6, "elev_km": 2.1})
    assert r.status_code == 200
    assert r.json()["site"]["key"] is None  # custom site, no preset key


def _oei_conn():
    url = os.environ.get("OEI_DATABASE_URL", OEI_DATABASE_URL_DEFAULT)
    return psycopg.connect(url, row_factory=dict_row)


@oei_required
@pytest.mark.db
def test_no_decayed_payload_is_propagated_or_counted():
    """A re-entered payload's last element set can still propagate without an SGP4 error, so the
    catalog query has to leave it out; the congestion panel's live set has to as well."""
    with _oei_conn() as conn:
        conn.read_only = True
        leo = [r["norad_id"] for r in conn.execute(twoskies._FETCH_LEO_SQL, {"maxalt": 2000})]
        live = [r["norad_id"] for r in conn.execute(
            twoskies._LIVE_ELEMENTS_CTE + "SELECT norad_id FROM latest_elements")]
        for norads in (leo, live):
            n = conn.execute(
                "SELECT count(*) AS n FROM satellite "
                "WHERE decay_date IS NOT NULL AND norad_id = ANY(%s)", (norads,),
            ).fetchone()["n"]
            assert n == 0
        tracked = conn.execute(twoskies._TRACKED_SQL).fetchone()["tracked_with_elements"]
        assert tracked == len(live)


@oei_required
@pytest.mark.db
def test_passes_unknown_site_is_422(client):
    r = client.get("/api/twoskies/passes", params={**_GJ1214, "site": "atlantis"})
    assert r.status_code == 422


def test_the_mock_fixture_serves_the_api_caveats():
    import json
    import pathlib

    fixture = pathlib.Path(__file__).resolve().parents[1] / "web/src/api/fixtures/twoskies.json"
    mock = json.loads(fixture.read_text())
    assert mock["congestion"]["caveats"] == twoskies.CAVEATS
    assert mock["passes"]["caveats"] == twoskies.CAVEATS
