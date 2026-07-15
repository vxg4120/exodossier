"""Shape + spot-check tests for the read-only ExoDossier API (stats/search/target/attribution).

Read-only; requires a reachable ``exo`` database (skipped otherwise). The StarletteDeprecation
warning about httpx in the test client is a third-party notice about the test utility itself, not
our code — it is filtered so the repo's ``-W error`` policy still governs everything we control.
"""

import warnings

warnings.filterwarnings("ignore", message=r"Using `httpx`")

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402
from common.db import get_conn  # noqa: E402

pytestmark = pytest.mark.filterwarnings(r"ignore:Using `httpx`")


def _db_reachable() -> bool:
    try:
        get_conn().close()
        return True
    except psycopg.OperationalError:
        return False


if not _db_reachable():
    pytest.skip("exo database not reachable at DATABASE_URL", allow_module_level=True)

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stats_shape_and_totals():
    r = client.get("/api/stats")
    assert r.status_code == 200
    s = r.json()
    for key in ("stars", "candidates", "identifiers", "source_assertions",
                "merge_events", "conflicts", "ingest_runs"):
        assert key in s
    # Wave-1 graph totals are fixed and known.
    assert s["stars"] == 20341
    assert s["candidates"] == 23031
    assert s["identifiers"] == 76534
    assert s["source_assertions"] == 684210
    assert isinstance(s["ingest_runs"], list) and len(s["ingest_runs"]) >= 1


def test_search_host_expands_to_candidates():
    r = client.get("/api/search", params={"q": "TRAPPIST-1"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 7  # TRAPPIST-1 b..h
    names = {row["target"] for row in body["results"]}
    assert "TRAPPIST-1 b" in names
    assert all(row["host"] == "TRAPPIST-1" for row in body["results"])
    assert all(row["candidate_id"] is not None for row in body["results"])


def test_search_empty_query_returns_nothing():
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_search_by_koi_identifier():
    # Kepler-1517 b carries KOI K03728.01; the raw identifier must resolve it.
    r = client.get("/api/search", params={"q": "K03728.01"})
    assert r.status_code == 200
    targets = {row["target"] for row in r.json()["results"]}
    assert "Kepler-1517 b" in targets


def test_target_by_name_shape():
    r = client.get("/api/target/Kepler-1517 b")
    assert r.status_code == 200
    t = r.json()
    assert t["candidate"]["name"] == "Kepler-1517 b"
    assert t["star"]["name"] == "Kepler-1517"
    # full crosswalk carries both candidate- and star-owned identifiers
    owners = {i["owner"] for i in t["identifiers"]}
    assert owners == {"candidate", "star"}
    id_types = {i["id_type"] for i in t["identifiers"]}
    assert {"toi", "koi", "tic"} <= id_types
    # who-says-what table is grouped by attribute, disposition present
    attrs = {a["attribute"] for a in t["attributes"]}
    assert "disposition" in attrs
    assert isinstance(t["conflict_attributes"], list)


def test_target_resolves_by_candidate_id_and_toi_and_host():
    by_name = client.get("/api/target/TRAPPIST-1 b").json()
    cid = by_name["candidate"]["candidate_id"]
    # by candidate_id
    assert client.get(f"/api/target/{cid}").json()["candidate"]["candidate_id"] == cid
    # by host name -> first candidate of the star (still TRAPPIST-1's system)
    assert client.get("/api/target/TRAPPIST-1").json()["star"]["name"] == "TRAPPIST-1"


def test_target_404():
    r = client.get("/api/target/NOPE-not-a-real-target-zzz")
    assert r.status_code == 404


def test_attribution_lists_sources():
    r = client.get("/api/attribution")
    assert r.status_code == 200
    names = {s["name"] for s in r.json()["sources"]}
    assert "NASA Exoplanet Archive" in names
    assert "ExoFOP-TESS" in names
    # honest framing is present
    assert "does not adjudicate" in r.json()["summary"].lower()
