"""The conflict corpus is one row per planet / per host, even when the graph carries twin rows.

identity.build pass 2 mints a KIC-only star for a Kepler host whose coordinate match to its TIC
star fails (``koi_new_star``); pass 3 then builds KOI-keyed candidate twins of the planets already
under the TIC star, and identity.assertions attaches the Archive's per-name claims to both twins.
Before the dedupe every such planet listed twice on /conflicts (identical spread and range, one
row carrying the KOI claim) and counted twice in the headline. The corpus and its counts now
dedupe on the identity the reader sees — host name + candidate name (host name alone for
star-level axes) — and pool the twins' claims into that one row.

Fixture tests run on an isolated graph (clean_graph: truncated + rolled back); the consistency
tests run against whatever graph DATABASE_URL points at.
"""

import pytest
from psycopg.rows import dict_row

from api import queries


@pytest.fixture
def graph(clean_graph):
    """clean_graph with the dict rows api.queries expects."""
    clean_graph.row_factory = dict_row
    return clean_graph


def _run(cur) -> int:
    cur.execute(
        "INSERT INTO ingest_run (source, endpoint, started_at, status) "
        "VALUES ('t', 't', now(), 'ok') RETURNING ingest_run_id"
    )
    return cur.fetchone()["ingest_run_id"]


def _star(cur, name: str, tic: int | None = None) -> int:
    cur.execute(
        "INSERT INTO star (tic_id, canonical_name) VALUES (%s, %s) RETURNING star_id", (tic, name)
    )
    return cur.fetchone()["star_id"]


def _candidate(cur, star: int, name: str) -> int:
    cur.execute(
        "INSERT INTO candidate (star_id, canonical_name) VALUES (%s, %s) RETURNING candidate_id",
        (star, name),
    )
    return cur.fetchone()["candidate_id"]


def _claim(cur, run: int, col: str, eid: int, attr: str, value: str, source: str, ref=None):
    cur.execute(
        f"INSERT INTO source_assertion ({col}, source_key, attribute, value, source, source_ref, "
        "observed_at, ingest_run_id) VALUES (%s, 'k', %s, %s, %s, %s, now(), %s)",
        (eid, attr, value, source, ref, run),
    )


def _twin_hosts(cur) -> tuple[int, int]:
    """Kepler-444 twice: the TIC star and the KIC-only star the KOI pass minted for it."""
    return _star(cur, "Kepler-444", tic=394172596), _star(cur, "Kepler-444")


def _twin_planet(cur, run: int, tic_star: int, kic_star: int) -> tuple[int, int]:
    """Kepler-444 e under both hosts: the Archive's ps/pscomppars radius claims land on both
    twins, the KOI claim on the KIC twin only."""
    a = _candidate(cur, tic_star, "Kepler-444 e")
    b = _candidate(cur, kic_star, "Kepler-444 e")
    for cand in (a, b):
        _claim(cur, run, "candidate_id", cand, "planet_radius_re", "0.42", "ps", "Campante 2015")
        _claim(cur, run, "candidate_id", cand, "planet_radius_re", "86.5", "ps", "Valizadegan 2023")
        _claim(cur, run, "candidate_id", cand, "planet_radius_re", "0.546", "pscomppars")
    _claim(cur, run, "candidate_id", b, "planet_radius_re", "0.62", "koi")
    return a, b


@pytest.mark.db
def test_radius_twins_are_one_row_and_one_count(graph):
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star = _twin_hosts(cur)
        a, b = _twin_planet(cur, run, tic_star, kic_star)
        # control: a different planet of the same host is its own row
        c = _candidate(cur, tic_star, "Kepler-444 c")
        _claim(cur, run, "candidate_id", c, "planet_radius_re", "0.39", "ps", "Campante 2015")
        _claim(cur, run, "candidate_id", c, "planet_radius_re", "0.497", "pscomppars")

    page = queries.list_conflicts(graph, "radius", limit=10)
    assert sorted(r["target"] for r in page["rows"]) == ["Kepler-444 c", "Kepler-444 e"]
    assert page["total"] == 2
    assert queries.count_numeric_conflicts(graph, "radius") == page["total"]

    e = next(r for r in page["rows"] if r["target"] == "Kepler-444 e")
    assert e["candidate_id"] == min(a, b)  # deterministic representative
    assert (e["min"], e["max"], e["n_sources"]) == (0.42, 86.5, 3)
    # the twins' claims pool into one provenance line: KOI shows, ps counted once per publication
    by_source = {s["source"]: s for s in e["by_source"]}
    assert set(by_source) == {"koi", "ps", "pscomppars"}
    assert by_source["ps"]["n"] == 2
    assert (by_source["ps"]["min"], by_source["ps"]["max"]) == (0.42, 86.5)
    assert by_source["koi"]["n"] == 1


@pytest.mark.db
def test_disposition_twins_are_one_row_and_one_count(graph):
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star = _twin_hosts(cur)
        a = _candidate(cur, tic_star, "Kepler-444 e")
        b = _candidate(cur, kic_star, "Kepler-444 e")
        for cand in (a, b):  # each twin conflicts on its own -> two rows before the dedupe
            _claim(cur, run, "candidate_id", cand, "disposition", "Published Confirmed", "ps")
            _claim(cur, run, "candidate_id", cand, "disposition", "FP", "exofop_toi")
        _claim(cur, run, "candidate_id", b, "disposition", "FALSE POSITIVE", "koi")

    page = queries.list_conflicts(graph, "disposition", limit=10)
    assert page["total"] == 1
    assert queries.count_disposition_conflicts(graph) == 1
    assert queries.count_disposition_conflicts(graph, dramatic_only=True) == 1
    (row,) = page["rows"]
    assert row["candidate_id"] == min(a, b)
    assert row["dramatic"] is True
    assert row["dispositions"] == ["CONFIRMED", "FALSE_POSITIVE"]
    assert {(s["source"], s["disposition"]) for s in row["by_source"]} == {
        ("ps", "CONFIRMED"), ("exofop_toi", "FALSE_POSITIVE"), ("koi", "FALSE_POSITIVE"),
    }


@pytest.mark.db
def test_teff_twin_hosts_are_one_row_and_one_count(graph):
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star = _twin_hosts(cur)
        first = _candidate(cur, tic_star, "Kepler-444 b")
        _candidate(cur, kic_star, "Kepler-444 b")
        for star, other in ((tic_star, "exofop_toi"), (kic_star, "koi")):
            _claim(cur, run, "star_id", star, "teff_k", "5780", other)  # solar default
            _claim(cur, run, "star_id", star, "teff_k", "5040", "ps", "Campante 2015")

    page = queries.list_conflicts(graph, "teff", limit=10)
    assert page["total"] == 1
    assert queries.count_numeric_conflicts(graph, "teff") == 1
    (row,) = page["rows"]
    assert row["host"] == "Kepler-444"
    assert row["candidate_id"] == first  # links to a planet of the representative host row
    assert {s["source"] for s in row["by_source"]} == {"exofop_toi", "koi", "ps"}
    assert row["n_sources"] == 3


# --- consistency on whatever graph is present ---------------------------------------------------


def _identity(ctype: str, row: dict) -> tuple:
    return (row["host"].lower(),) if ctype == "teff" else (
        row["host"].lower(), row["target"].lower(),
    )


@pytest.mark.db
@pytest.mark.parametrize("ctype", ["disposition", "radius", "teff"])
def test_headline_count_is_the_list_total_and_pages_carry_no_twins(db_conn, ctype):
    db_conn.row_factory = dict_row
    page = queries.list_conflicts(db_conn, ctype, limit=200)
    assert queries.catalog_stats(db_conn)["conflicts"][ctype] == page["total"]
    keys = [_identity(ctype, r) for r in page["rows"]]
    assert len(keys) == len(set(keys))
