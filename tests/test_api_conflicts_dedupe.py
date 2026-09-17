"""The conflict corpus is one row per planet / per host, even when the graph carries twin rows.

identity.build pass 2 mints a KIC-only star for a Kepler host whose coordinate match to its TIC
star fails (``koi_new_star``); pass 3 then builds KOI-keyed candidate twins of the planets already
under the TIC star, and identity.assertions attaches the Archive's per-name claims to both twins.
Before the dedupe every such planet listed twice on /conflicts (identical spread and range, one
row carrying the KOI claim) and counted twice in the headline. The corpus and its counts now
pool only within a guarded host group: distinct TICs remain separate; same-name null-TIC
rows join only one unambiguous TIC host. Candidate names are scoped to that group. Unanchored
host rows remain separate even when display names match.

Fixture tests run on an isolated graph (clean_graph: truncated + rolled back); the consistency
tests run against whatever graph DATABASE_URL points at.
"""

import datetime as dt

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


def _twin_system(cur, run: int) -> tuple[int, int, int, int]:
    """Kepler-444 as the graph carries it: twin hosts, twin ``e`` planets conflicting on radius
    and disposition, twin hosts conflicting on Teff. Returns (tic_star, kic_star, a, b)."""
    tic_star, kic_star = _twin_hosts(cur)
    a, b = _twin_planet(cur, run, tic_star, kic_star)
    for cand in (a, b):
        _claim(cur, run, "candidate_id", cand, "disposition", "Published Confirmed", "ps")
    _claim(cur, run, "candidate_id", b, "disposition", "FALSE POSITIVE", "koi")
    for star, other in ((tic_star, "exofop_toi"), (kic_star, "koi")):
        _claim(cur, run, "star_id", star, "teff_k", "5780", other)
        _claim(cur, run, "star_id", star, "teff_k", "5040", "ps", "Campante 2015")
    return tic_star, kic_star, a, b


@pytest.mark.db
def test_every_conflict_row_deep_links_to_a_dossier_showing_that_conflict(graph):
    """The corpus row and the page it links to must agree: whichever twin the row links to, and
    whether the reader arrives by id or by name, the dossier (and the MCP target_conflicts tool)
    pools the same twins' claims the row pooled, so a FALSE POSITIVE vs CONFIRMED row never lands
    on a page that says nobody disagrees."""
    with graph.cursor() as cur:
        _twin_system(cur, _run(cur))

    for ctype in ("radius", "disposition", "teff"):
        (row,) = queries.list_conflicts(graph, ctype, limit=10)["rows"]
        for ident in (row["candidate_id"], row["target"]):
            page = queries.resolve_target(graph, ident)
            assert row["attribute"] in page["conflict_attributes"], (ctype, ident)
            group = next(g for g in page["attributes"] if g["attribute"] == row["attribute"])
            assert {s["source"] for s in row["by_source"]} == {
                a["source"] for a in group["assertions"]
            }, (ctype, ident)
            tool = queries.target_conflicts(graph, ident)
            assert tool["has_conflict"] and row["attribute"] in tool["conflict_attributes"]


@pytest.mark.db
def test_dossier_is_one_page_per_planet(graph):
    """Both twins, the planet name and a twin-only identifier resolve to the same pooled dossier:
    the representative candidate, the union of the crosswalk (once per identifier), each claim
    once per publication, and each sibling planet once."""
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star, a, b = _twin_system(cur, run)
        for star in (tic_star, kic_star):  # a sibling the graph also carries twice
            _candidate(cur, star, "Kepler-444 c")
        cur.execute(
            "INSERT INTO entity_identifier (candidate_id, id_type, id_value, source) VALUES "
            "(%s, 'name', 'Kepler-444 e', 'nea'), (%s, 'name', 'Kepler-444 e', 'nea'), "
            "(%s, 'koi', 'K03158.05', 'nea')",
            (a, b, b),
        )
        cur.execute(
            "INSERT INTO entity_identifier (star_id, id_type, id_value, source) VALUES "
            "(%s, 'tic', '394172596', 'exofop'), (%s, 'kic', '6278762', 'nea')",
            (tic_star, kic_star),
        )

    pages = [queries.resolve_target(graph, i) for i in (a, b, "Kepler-444 e", "K03158.05")]
    assert {p["candidate"]["candidate_id"] for p in pages} == {min(a, b)}
    page = pages[0]
    assert page["star"]["tic_id"] == "394172596"
    ids = [(i["owner"], i["id_type"], i["id_value"]) for i in page["identifiers"]]
    assert sorted(ids) == [
        ("candidate", "koi", "K03158.05"), ("candidate", "name", "Kepler-444 e"),
        ("star", "kic", "6278762"), ("star", "tic", "394172596"),
    ]
    radius = next(g for g in page["attributes"] if g["attribute"] == "planet_radius_re")
    assert sorted((x["source"], x["value"]) for x in radius["assertions"]) == [
        ("koi", "0.62"), ("ps", "0.42"), ("ps", "86.5"), ("pscomppars", "0.546"),
    ]
    assert [s["name"] for s in page["sibling_candidates"]] == ["Kepler-444 c"]


@pytest.mark.db
def test_ledger_reports_last_landed_pull_beside_latest_check(graph):
    """A skipped_fresh check must not hide the last pull that landed rows."""
    with graph.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingest_run
                (source, endpoint, started_at, finished_at, rows_ingested, bytes_downloaded, status)
            VALUES
                ('exofop', 'audit_ep', now() - interval '2 days', now() - interval '2 days',
                 8064, 3735481, 'ok'),
                ('exofop', 'audit_ep', now(), now(), 0, 0, 'skipped_fresh')
            """
        )
    runs = {(r["source"], r["endpoint"]): r for r in queries.catalog_stats(graph)["ingest_runs"]}
    row = runs[("exofop", "audit_ep")]
    assert (row["status"], row["rows_ingested"]) == ("skipped_fresh", 0)
    assert row["last_ok_rows"] == 8064
    assert dt.datetime.fromisoformat(row["last_ok_at"]) < dt.datetime.fromisoformat(
        row["finished_at"]
    )


# --- consistency on whatever graph is present ---------------------------------------------------


@pytest.mark.db
@pytest.mark.parametrize("ctype", ["disposition", "radius", "teff"])
def test_headline_count_is_the_list_total_and_pages_carry_no_twins(db_conn, ctype):
    db_conn.row_factory = dict_row
    page = queries.list_conflicts(db_conn, ctype, limit=200)
    assert queries.catalog_stats(db_conn)["conflicts"][ctype] == page["total"]
    keys = [r["candidate_id"] for r in page["rows"]]
    assert len(keys) == len(set(keys))


@pytest.mark.db
@pytest.mark.parametrize("tics", [(111, 222), (111, None, 222), (None, None)])
def test_same_name_different_hosts_do_not_pool_claims_crosswalks_or_siblings(graph, tics):
    """Display names cannot merge distinct TICs, ambiguous aliases, or unanchored hosts."""
    systems = []
    sources = ("ps", "koi", "exofop_toi")
    dispositions = ("Published Confirmed", "FALSE POSITIVE", "PC")
    with graph.cursor() as cur:
        run = _run(cur)
        for i, tic in enumerate(tics):
            sid = _star(cur, "Collision" if i % 2 == 0 else "COLLISION", tic)
            cid = _candidate(cur, sid, "Collision b")
            sibling = _candidate(cur, sid, f"Own sibling {i}")
            cur.execute(
                "INSERT INTO entity_identifier (star_id, id_type, id_value, source) "
                "VALUES (%s, 'kic', %s, 'test')", (sid, f"host-{i}"),
            )
            cur.execute(
                "INSERT INTO entity_identifier (candidate_id, id_type, id_value, source) "
                "VALUES (%s, 'koi', %s, 'test')", (cid, f"planet-{i}"),
            )
            _claim(cur, run, "star_id", sid, "teff_k", str(3000 + i * 1500), sources[i])
            _claim(cur, run, "candidate_id", cid, "planet_radius_re", str(i + 1), sources[i])
            _claim(cur, run, "candidate_id", cid, "disposition", dispositions[i], sources[i])
            systems.append((sid, cid, sibling, i))

    for ctype in ("radius", "teff", "disposition"):
        page = queries.list_conflicts(graph, ctype)
        assert page["total"] == len(page["rows"]) == 0, ctype
    for sid, cid, sibling, i in systems:
        for ident in (cid, f"planet-{i}", f"host-{i}"):
            target = queries.resolve_target(graph, ident)
            assert target["candidate"]["candidate_id"] == cid
            assert target["star"]["star_id"] == sid
            assert {x["id_value"] for x in target["identifiers"]} == {
                f"planet-{i}", f"host-{i}",
            }
            assert {a["source"] for g in target["attributes"] for a in g["assertions"]} == {
                sources[i],
            }
            assert [s["candidate_id"] for s in target["sibling_candidates"]] == [sibling]
            assert queries.target_conflicts(graph, ident)["has_conflict"] is False


@pytest.mark.db
def test_same_name_hosts_keep_their_real_conflicts_and_list_dossier_mcp_agree(graph):
    """No source or range from an unrelated identified/null-TIC host may leak into a row."""
    cids = []
    with graph.cursor() as cur:
        run = _run(cur)
        for i, tic in enumerate((111, 222, None)):
            sid = _star(cur, "Collision", tic)
            cid = _candidate(cur, sid, "Collision b")
            cids.append(cid)
            for source, value in (("ps", 1 + i * 10), ("koi", 2 + i * 20)):
                _claim(cur, run, "candidate_id", cid, "planet_radius_re", str(value), source)
                _claim(cur, run, "star_id", sid, "teff_k", str(value * 1000), source)
            _claim(cur, run, "candidate_id", cid, "disposition", "Published Confirmed", "ps")
            _claim(cur, run, "candidate_id", cid, "disposition", "FALSE POSITIVE", "koi")

    for ctype in ("radius", "teff", "disposition"):
        page = queries.list_conflicts(graph, ctype, limit=100)
        assert page["total"] == len(page["rows"]) == 3
        count = (queries.count_disposition_conflicts(graph) if ctype == "disposition"
                 else queries.count_numeric_conflicts(graph, ctype))
        assert count == page["total"]
        assert {r["candidate_id"] for r in page["rows"]} == set(cids)
        # Same display names and equal spreads still have a stable ID tie-break across pages.
        paged = [queries.list_conflicts(graph, ctype, limit=1, offset=i)["rows"][0]
                 for i in range(3)]
        assert [r["candidate_id"] for r in paged] == [r["candidate_id"] for r in page["rows"]]
        for row in page["rows"]:
            dossier = queries.resolve_target(graph, row["candidate_id"])
            group = next(g for g in dossier["attributes"] if g["attribute"] == row["attribute"])
            assert group["conflict"] is True
            assert {s["source"] for s in row["by_source"]} == {
                a["source"] for a in group["assertions"]
            }
            if ctype != "disposition":
                vals = [float(a["value"]) for a in group["assertions"]]
                assert (row["min"], row["max"]) == (min(vals), max(vals))
            tool = queries.target_conflicts(graph, row["candidate_id"])
            assert row["attribute"] in tool["conflict_attributes"]


@pytest.mark.db
def test_conflict_link_is_stable_when_only_later_twin_has_claims(graph):
    """The representative is a property of the identity group, not of who has this attribute."""
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star = _twin_hosts(cur)
        first = _candidate(cur, tic_star, "Kepler-444 e")
        later = _candidate(cur, kic_star, "KEPLER-444 E")
        for source, value in (("ps", "1"), ("koi", "2")):
            _claim(cur, run, "candidate_id", later, "planet_radius_re", value, source)
            _claim(cur, run, "star_id", kic_star, "teff_k", str(int(value) * 3000), source)
        _claim(cur, run, "candidate_id", later, "disposition", "Published Confirmed", "ps")
        _claim(cur, run, "candidate_id", later, "disposition", "FALSE POSITIVE", "koi")

    for ctype in ("radius", "teff", "disposition"):
        page = queries.list_conflicts(graph, ctype)
        assert page["total"] == len(page["rows"]) == 1
        (row,) = page["rows"]
        assert row["candidate_id"] == first
        dossier = queries.resolve_target(graph, row["candidate_id"])
        assert row["candidate_id"] == dossier["candidate"]["candidate_id"]
        assert row["attribute"] in dossier["conflict_attributes"]


@pytest.mark.db
def test_star_claims_on_candidate_less_twin_still_link_to_group_target(graph):
    with graph.cursor() as cur:
        run = _run(cur)
        tic_star, kic_star = _twin_hosts(cur)
        first = _candidate(cur, tic_star, "Kepler-444 e")
        cur.execute(
            "INSERT INTO entity_identifier (star_id, id_type, id_value, source) "
            "VALUES (%s, 'kic', 'alias-without-candidate', 'test')", (kic_star,),
        )
        _claim(cur, run, "star_id", kic_star, "teff_k", "3000", "ps")
        _claim(cur, run, "star_id", kic_star, "teff_k", "6000", "koi")

    page = queries.list_conflicts(graph, "teff")
    assert page["total"] == len(page["rows"]) == 1
    assert page["rows"][0]["candidate_id"] == first
    assert "teff_k" in queries.resolve_target(graph, first)["conflict_attributes"]

    by_alias = queries.resolve_target(graph, "alias-without-candidate")
    assert by_alias is not None
    assert by_alias["candidate"]["candidate_id"] == first
    assert "teff_k" in queries.target_conflicts(graph, "alias-without-candidate")[
        "conflict_attributes"
    ]


@pytest.mark.db
def test_null_tic_first_and_case_variant_preserve_unambiguous_anchor(graph):
    with graph.cursor() as cur:
        run = _run(cur)
        null_star = _star(cur, "kEpLeR-444")
        tic_star = _star(cur, "Kepler-444", 394172596)
        first = _candidate(cur, null_star, "Kepler-444 e")
        later = _candidate(cur, tic_star, "KEPLER-444 E")
        _claim(cur, run, "candidate_id", first, "planet_radius_re", "1", "koi")
        _claim(cur, run, "candidate_id", later, "planet_radius_re", "2", "ps")

    page = queries.list_conflicts(graph, "radius")
    assert page["total"] == len(page["rows"]) == 1
    assert page["rows"][0]["candidate_id"] == first
    for cid in (first, later):
        dossier = queries.resolve_target(graph, cid)
        assert dossier["candidate"]["candidate_id"] == first
        assert "planet_radius_re" in dossier["conflict_attributes"]


@pytest.mark.db
def test_empty_and_candidate_less_host_groups_do_not_create_unlinkable_rows(graph):
    for ctype in ("radius", "teff", "disposition"):
        page = queries.list_conflicts(graph, ctype)
        assert page["total"] == len(page["rows"]) == 0
    assert queries.resolve_target(graph, "missing") is None
    assert queries.target_conflicts(graph, "missing") is None
    with graph.cursor() as cur:
        run = _run(cur)
        sid = _star(cur, "No planets yet", 987654)
        _claim(cur, run, "star_id", sid, "teff_k", "3000", "ps")
        _claim(cur, run, "star_id", sid, "teff_k", "6000", "koi")
    page = queries.list_conflicts(graph, "teff")
    assert queries.count_numeric_conflicts(graph, "teff") == page["total"] == len(page["rows"]) == 0
    with graph.cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM source_assertion WHERE star_id = %s", (sid,))
        # Claims remain intact, outside the candidate-linked corpus.
        assert cur.fetchone()["n"] == 2


@pytest.mark.db
def test_ambiguous_candidate_less_alias_identifier_does_not_resolve_foreign_target(graph):
    with graph.cursor() as cur:
        for tic in (111, 222):
            sid = _star(cur, "Collision", tic)
            _candidate(cur, sid, "Collision b")
        alias = _star(cur, "Collision")
        cur.execute(
            "INSERT INTO entity_identifier (star_id, id_type, id_value, source) "
            "VALUES (%s, 'kic', 'ambiguous-alias', 'test')", (alias,),
        )
    assert queries.resolve_target(graph, "ambiguous-alias") is None
    assert queries.target_conflicts(graph, "ambiguous-alias") is None
