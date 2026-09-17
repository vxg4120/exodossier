"""Conflict-corpus tests + known-data spot checks.

Pins the headline conflict findings the whole product is built to surface:
  * TRAPPIST-1 shows a cross-source Teff conflict (solar-default 5780 K vs measured ~2560 K).
  * A known disposition-conflict target (Kepler-1517 b) shows FALSE_POSITIVE vs CONFIRMED.
Read-only; requires a reachable ``exo`` database.
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


def _conflict_counts() -> dict:
    return client.get("/api/stats").json()["conflicts"]


def test_stats_conflict_counts_are_the_list_totals():
    """The headline counts and the corpus they link to are the same query, so they agree — on
    whatever graph the nightly rebuild produced (the numbers drift as the catalogs refresh)."""
    counts = _conflict_counts()
    for ctype in ("disposition", "radius", "teff"):
        total = client.get("/api/conflicts", params={"type": ctype, "limit": 1}).json()["total"]
        assert counts[ctype] == total > 0, ctype
    assert 0 < counts["disposition_dramatic"] <= counts["disposition"]


def test_disposition_list_puts_dramatic_first():
    counts = _conflict_counts()
    n_dramatic = counts["disposition_dramatic"]
    r = client.get("/api/conflicts", params={"type": "disposition", "limit": n_dramatic + 2})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == counts["disposition"]
    flags = [row["dramatic"] for row in body["rows"]]
    assert flags == [True] * n_dramatic + [False] * (len(flags) - n_dramatic)
    # the flagship FALSE POSITIVE vs CONFIRMED cases the product was built around
    dramatic = {row["target"] for row in body["rows"][:n_dramatic]}
    assert {"Kepler-1517 b", "Kepler-404 b", "TOI-1836 c"} <= dramatic


def test_known_disposition_conflict_fp_vs_confirmed():
    """Kepler-1517 b: one catalog says FALSE_POSITIVE, another CONFIRMED — the headline case."""
    t = client.get("/api/target/Kepler-1517 b").json()
    disp = next(a for a in t["attributes"] if a["attribute"] == "disposition")
    assert disp["conflict"] is True
    canon = {a["source"]: a["canonical_disposition"] for a in disp["assertions"]
             if a["canonical_disposition"]}
    assert canon.get("exofop_toi") == "FALSE_POSITIVE"
    assert canon.get("nea_toi") == "FALSE_POSITIVE"
    assert canon.get("pscomppars") == "CONFIRMED"
    assert canon.get("koi") == "CONFIRMED"


def test_trappist1_shows_teff_conflict():
    """TRAPPIST-1: TOI catalogs list the solar-default 5780 K, ps/pscomppars ~2560 K."""
    t = client.get("/api/target/TRAPPIST-1 b").json()
    teff = next(a for a in t["attributes"] if a["attribute"] == "teff_k")
    assert teff["conflict"] is True
    assert teff["level"] == "star"
    values = {float(a["value"]) for a in teff["assertions"]}
    assert max(values) >= 5780  # solar-default placeholder from the TOI catalogs
    assert min(values) <= 2600  # measured cool-dwarf temperature
    assert "teff_k" in t["conflict_attributes"]


def test_teff_conflict_list_includes_trappist1_and_links_to_target():
    r = client.get("/api/conflicts", params={"type": "teff", "limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == _conflict_counts()["teff"]
    rows = {row["host"]: row for row in body["rows"]}
    assert "TRAPPIST-1" in rows  # the flagship Teff conflict is on page 1 (sorted by spread)
    trappist = rows["TRAPPIST-1"]
    assert trappist["candidate_id"] is not None  # deep-links to a target
    assert trappist["spread_pct"] > 5
    assert any(bs["source"] == "ps" for bs in trappist["by_source"])


def test_radius_list_sorted_by_spread_desc_with_provenance():
    r = client.get("/api/conflicts", params={"type": "radius", "limit": 10})
    body = r.json()
    assert body["total"] == _conflict_counts()["radius"]
    spreads = [row["spread_pct"] for row in body["rows"]]
    assert spreads == sorted(spreads, reverse=True)
    first = body["rows"][0]
    assert first["attribute"] == "planet_radius_re"
    assert first["by_source"]  # per-source ranges present


def test_conflicts_pagination():
    p1 = client.get("/api/conflicts", params={"type": "radius", "limit": 5, "offset": 0}).json()
    p2 = client.get("/api/conflicts", params={"type": "radius", "limit": 5, "offset": 5}).json()
    assert p1["total"] == p2["total"] == _conflict_counts()["radius"]
    ids1 = {r["candidate_id"] for r in p1["rows"]}
    ids2 = {r["candidate_id"] for r in p2["rows"]}
    assert ids1.isdisjoint(ids2)  # no overlap across pages


def test_bad_conflict_type_is_400():
    r = client.get("/api/conflicts", params={"type": "banana"})
    assert r.status_code == 400


def test_conflict_types_endpoint():
    r = client.get("/api/conflicts/types")
    assert r.status_code == 200
    types = {t["type"] for t in r.json()["types"]}
    assert types == {"disposition", "radius", "teff"}
