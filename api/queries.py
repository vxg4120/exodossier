"""The read-only query layer over the Wave-1 identity graph.

One source of truth for every question the surface asks — the FastAPI routers (``api/routers``)
and the MCP server (``mcp/server.py``) both call these functions, so the web catalog, the JSON API
and the agent tools can never disagree about what the archives say. Every function takes an open
psycopg connection with ``dict_row`` row factory and returns plain JSON-able dicts/lists.

Tables read (identity + conflict graph only): star, candidate, entity_identifier,
source_assertion, merge_log, disposition_mapping, ingest_run. Nothing here writes, and nothing
here touches the Wave-2 light-curve tables.

Conflict semantics (honest + reproducible against docs/reports/conflict_report.md):
  * disposition — a candidate whose per-source dispositions map (via disposition_mapping, exact) to
    >= 2 distinct canonical values. The "dramatic" kind pairs FALSE_POSITIVE with CONFIRMED/KNOWN.
  * numeric (period/radius/teff/rstar/…) — a cross-source disagreement: >= 2 distinct values AND
    >= 2 distinct sources, with relative spread (max-min)/max over the attribute's threshold.
  * one row per planet / per host — the graph can carry twin rows for the same object (see
    ``_identity_cte``); the corpus, counts and dossier share a guarded host/candidate key,
    so a row and the page it links to show the same disagreement.
Disagreements are surfaced, never adjudicated.
"""

from __future__ import annotations

import html
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any

import psycopg

# A source_assertion.value is TEXT; only cast the ones that look numeric. Anchored, allows an
# optional minus, a decimal point and scientific notation ("1e+04"). The dossier uses
# this same grammar; nonfinite/unsupported forms stay visible as raw claims but do not vote.
NUM_RE = r"^-?[0-9]+\.?[0-9]*([eE][-+]?[0-9]+)?$"

# Canonical disposition taxonomy (mirrors db/migrations 0004/0005 seed).
DISPOSITIONS = ["CONFIRMED", "KNOWN_PLANET", "CANDIDATE", "AMBIGUOUS", "FALSE_POSITIVE"]

# Per-attribute metadata: the star- vs candidate-level split, display unit, and the relative-spread
# threshold above which a cross-source numeric disagreement counts as a conflict. ``None`` threshold
# = shown in the who-says-what table but never flagged (e.g. epoch, where differing references are
# expected). Thresholds for period/radius/teff/rstar track the conflict report's headline counts.
ATTRIBUTES: dict[str, dict[str, Any]] = {
    # candidate-level
    "disposition": {"level": "candidate", "unit": None, "kind": "disposition"},
    "period_days": {"level": "candidate", "unit": "days", "kind": "numeric", "threshold": 0.01},
    "planet_radius_re": {"level": "candidate", "unit": "R_earth", "kind": "numeric",
                         "threshold": 0.10},
    "depth_ppm": {"level": "candidate", "unit": "ppm", "kind": "numeric", "threshold": 0.10},
    "duration_hr": {"level": "candidate", "unit": "hr", "kind": "numeric", "threshold": 0.10},
    "epoch_bjd": {"level": "candidate", "unit": "BJD", "kind": "numeric", "threshold": None},
    # star-level
    "teff_k": {"level": "star", "unit": "K", "kind": "numeric", "threshold": 0.05},
    "rstar_rsun": {"level": "star", "unit": "R_sun", "kind": "numeric", "threshold": 0.10},
    "logg": {"level": "star", "unit": "log10(cm/s^2)", "kind": "numeric", "threshold": 0.10},
    "parallax_mas": {"level": "star", "unit": "mas", "kind": "numeric", "threshold": 0.10},
    "tmag": {"level": "star", "unit": "mag", "kind": "numeric", "threshold": 0.05},
    "vmag": {"level": "star", "unit": "mag", "kind": "numeric", "threshold": 0.05},
}

# The browsable conflict corpus: type -> attribute + how it is counted/listed.
CONFLICT_TYPES: dict[str, dict[str, Any]] = {
    "disposition": {
        "attribute": "disposition",
        "level": "candidate",
        "label": "Disposition — is it even a planet?",
        "description": (
            "Candidates whose canonical disposition disagrees across catalogs. The dramatic kind: "
            "one archive calls it a FALSE POSITIVE while another says CONFIRMED or KNOWN PLANET."
        ),
    },
    "radius": {
        "attribute": "planet_radius_re",
        "level": "candidate",
        "unit": "R_earth",
        "threshold": 0.10,
        "label": "Planet radius (> 10% across sources)",
        "description": (
            "Same candidate, planet radius disagreeing by more than 10% across sources — Gaia "
            "revisions propagate here, and this is where rocky-vs-sub-Neptune classification flips."
        ),
    },
    "teff": {
        "attribute": "teff_k",
        "level": "star",
        "unit": "K",
        "threshold": 0.05,
        "label": "Host Teff (> 5% — can flip the habitable zone)",
        "description": (
            "Host stars whose effective temperature disagrees by more than 5% across catalogs. "
            "Kane 2014: a ~5% Teff error shifts the HZ boundary ~10%, so HZ membership can flip."
        ),
    },
}


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def _num(value: str) -> Decimal | None:
    """Parse the same finite decimal grammar used by the SQL conflict queries."""
    return Decimal(value) if re.fullmatch(NUM_RE, value) else None


# Query-time identity guard; no graph rows or claims are rewritten. A unique TIC anchor
# permits the existing same-name TIC/KIC twin presentation. Two known TICs never pool, and a
# null-TIC host cannot bridge them. Without one unambiguous anchor, preserve each host row.
# This is a conservative presentation heuristic, not proof that same-name aliases are the same
# star. Other catalog identifiers/coordinates need an independently validated identity policy.
# Candidate names are scoped to that safe host group. Representatives depend on graph identity,
# not on which twin happens to carry a particular assertion, so every surface links consistently.
def _identity_cte(scope: str | None = None) -> str:
    """Shared identity relation, optionally restricted to a page's host names.

    The scoped form still inspects *every* same-name host when deciding whether a TIC anchor
    is unambiguous. It avoids sorting the entire graph for a single dossier or provenance page.
    ``scope`` is an internal assertion-level literal; IDs remain bound SQL parameters.
    """
    names = {
        "candidate_id": "SELECT lower(s.canonical_name) COLLATE \"C\" FROM star s "
                        "JOIN candidate c ON c.star_id = s.star_id "
                        "WHERE c.candidate_id = ANY(%(ids)s)",
        "star_id": "SELECT lower(canonical_name) COLLATE \"C\" FROM star "
                   "WHERE star_id = ANY(%(ids)s)",
        "search": "SELECT lower(s.canonical_name) COLLATE \"C\" FROM star s "
                  "JOIN host_matches m ON m.star_id = s.star_id",
    }
    where = (f'WHERE lower(canonical_name) COLLATE "C" IN ({names[scope]})'
             if scope is not None else "")
    return f"""
    host_anchors AS (
        SELECT star_id, tic_id,
               count(tic_id) OVER same_name AS n_tics,
               min(star_id) FILTER (WHERE tic_id IS NOT NULL) OVER same_name AS anchor_id
        FROM star
        {where}
        WINDOW same_name AS (PARTITION BY lower(canonical_name) COLLATE "C")
    ),
    host_identity AS (
        SELECT star_id,
               CASE WHEN tic_id IS NULL AND n_tics = 1 THEN anchor_id
                    ELSE star_id END AS host_id
        FROM host_anchors
    ),
    candidate_identity AS (
        SELECT c.candidate_id, h.host_id,
               min(c.candidate_id) OVER (
                   PARTITION BY h.host_id, lower(c.canonical_name) COLLATE "C"
               ) AS eid
        FROM candidate c JOIN host_identity h ON h.star_id = c.star_id
    ),
    host_targets AS (
        SELECT host_id, min(candidate_id) AS eid
        FROM candidate_identity GROUP BY host_id
    )
"""

# Every conflict eid is a stable candidate link, including host-level conflicts. Joining
# host_targets limits the browsable host corpus to groups with a candidate dossier; a star with
# no candidate anywhere in its group has no public target route and cannot produce a list row.
_IDENTITY: dict[str, dict[str, str]] = {
    "candidate_id": {
        "join": "JOIN candidate_identity ci ON ci.candidate_id = sa.candidate_id",
        "eid": "ci.eid",
    },
    "star_id": {
        "join": "JOIN host_identity hi ON hi.star_id = sa.star_id "
                "JOIN host_targets ht ON ht.host_id = hi.host_id",
        "eid": "ht.eid",
    },
}

# A page's twins use the exact identity contract as counts and dossiers. Fetching assertions
# through these IDs retains the existing (id, attribute) index path for per-source details.
_TWINS_CTE: dict[str, str] = {
    "candidate_id": """
    twins AS (
        SELECT r.candidate_id AS eid, t.candidate_id
        FROM candidate r
        JOIN host_identity rh ON rh.star_id = r.star_id
        JOIN host_identity th ON th.host_id = rh.host_id
        JOIN candidate t ON t.star_id = th.star_id
                        AND lower(t.canonical_name) COLLATE "C"
                            = lower(r.canonical_name) COLLATE "C"
        WHERE r.candidate_id = ANY(%(ids)s)
    )""",
    "star_id": """
    twins AS (
        SELECT r.star_id AS eid, t.star_id
        FROM host_identity r JOIN host_identity t ON t.host_id = r.host_id
        WHERE r.star_id = ANY(%(ids)s)
    )""",
}


def _numeric_conflict_cte(attr_level: str) -> str:
    """CTE ``conflicted(eid, mn, mx, spread, n_sources)`` for a numeric attribute.

    ``attr_level`` is a trusted internal literal ('candidate_id' or 'star_id'), never user input.
    Claims group on the guarded identity (see ``_IDENTITY``); ``eid`` is the stable
    candidate link for that planet or host group. A conflict requires >= 2 distinct values from
    >= 2 distinct sources, relative spread over the caller's threshold.
    """
    ident = _IDENTITY[attr_level]
    # Filter attribute before applying numeric regex/casts. This boundary also prevents the
    # planner from evaluating regex across unrelated claims after the computed-identity join.
    return f"""
    WITH {_identity_cte()}, attribute_claims AS MATERIALIZED (
        SELECT {attr_level}, value, source
        FROM source_assertion WHERE attribute = %(attr)s
    ),
    vals AS (
        SELECT {ident['eid']} AS eid, (sa.value)::numeric AS v, sa.source
        FROM attribute_claims sa
        {ident['join']}
        WHERE sa.value ~ %(numre)s
    ),
    agg AS (
        SELECT eid, min(v) AS mn, max(v) AS mx,
               count(DISTINCT v) AS n_values, count(DISTINCT source) AS n_sources
        FROM vals GROUP BY eid
    ),
    conflicted AS MATERIALIZED (
        SELECT eid, mn, mx, n_sources, (mx - mn) / mx AS spread
        FROM agg
        WHERE n_values >= 2 AND n_sources >= 2 AND mx > 0
          AND mx - mn > mx * %(threshold)s::numeric
    )
    """


_DISPO_CTE = f"""
    WITH {_identity_cte()}, dispo AS (
        SELECT {_IDENTITY['candidate_id']['eid']} AS eid,
               dm.canonical_disposition AS canon
        FROM source_assertion sa
        {_IDENTITY['candidate_id']['join']}
        JOIN disposition_mapping dm
          ON dm.source = sa.source AND dm.source_value = sa.value
        WHERE sa.attribute = 'disposition'
    ),
    conflicted AS MATERIALIZED (
        SELECT eid,
               array_agg(DISTINCT canon ORDER BY canon) AS dispositions,
               (bool_or(canon = 'FALSE_POSITIVE')
                AND bool_or(canon IN ('CONFIRMED', 'KNOWN_PLANET'))) AS dramatic
        FROM dispo
        GROUP BY eid
        HAVING count(DISTINCT canon) >= 2
    )
"""


# ---------------------------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------------------------
def catalog_stats(db: psycopg.Connection) -> dict[str, Any]:
    """Graph totals, cross-source conflict counts, and the ingestion ledger."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                (SELECT count(*) FROM star) AS stars,
                (SELECT count(*) FROM candidate) AS candidates,
                (SELECT count(*) FROM entity_identifier) AS identifiers,
                (SELECT count(*) FROM source_assertion) AS source_assertions,
                (SELECT count(*) FROM merge_log) AS merge_events
            """
        )
        totals = cur.fetchone()

        conflicts = {
            "disposition": count_disposition_conflicts(db),
            "disposition_dramatic": count_disposition_conflicts(db, dramatic_only=True),
            "radius": count_numeric_conflicts(db, "radius"),
            "teff": count_numeric_conflicts(db, "teff"),
        }

        # Last run per catalog endpoint, plus the last pull that actually landed rows: the 24h
        # freshness gate ledgers a ``skipped_fresh`` row on every run inside the window, so the
        # latest row alone can hide when the catalog was last pulled. Scope to the catalog sources
        # that populate the identity graph ('exofop', 'nea'); the same ledger also carries the
        # Wave-2 per-target MAST fetches (source 'mast'), which are not part of this surface and
        # would flood the response.
        cur.execute(
            """
            SELECT DISTINCT ON (ir.source, ir.endpoint)
                ir.source, ir.endpoint, ir.status, ir.rows_ingested, ir.bytes_downloaded,
                ir.finished_at,
                ok.finished_at AS last_ok_at, ok.rows_ingested AS last_ok_rows
            FROM ingest_run ir
            LEFT JOIN LATERAL (
                SELECT finished_at, rows_ingested
                FROM ingest_run
                WHERE source = ir.source AND endpoint = ir.endpoint AND status = 'ok'
                ORDER BY started_at DESC NULLS LAST
                LIMIT 1
            ) ok ON true
            WHERE ir.source IN ('exofop', 'nea')
            ORDER BY ir.source, ir.endpoint, ir.started_at DESC NULLS LAST
            """
        )
        ingest_runs = cur.fetchall()

    return {
        "stars": totals["stars"],
        "candidates": totals["candidates"],
        "identifiers": totals["identifiers"],
        "source_assertions": totals["source_assertions"],
        "merge_events": totals["merge_events"],
        "conflicts": conflicts,
        "ingest_runs": [_iso_row(r) for r in ingest_runs],
    }


def count_disposition_conflicts(db: psycopg.Connection, dramatic_only: bool = False) -> int:
    where = "WHERE dramatic" if dramatic_only else ""
    with db.cursor() as cur:
        cur.execute(_DISPO_CTE + f"SELECT count(*) AS n FROM conflicted {where}")
        return cur.fetchone()["n"]


def count_numeric_conflicts(db: psycopg.Connection, ctype: str) -> int:
    spec = CONFLICT_TYPES[ctype]
    level = "candidate_id" if spec["level"] == "candidate" else "star_id"
    with db.cursor() as cur:
        cur.execute(
            _numeric_conflict_cte(level) + "SELECT count(*) AS n FROM conflicted",
            {"attr": spec["attribute"], "numre": NUM_RE, "threshold": spec["threshold"]},
        )
        return cur.fetchone()["n"]


# ---------------------------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------------------------
def search_targets(db: psycopg.Connection, q: str, limit: int = 50) -> list[dict[str, Any]]:
    """Resolve any TIC / TOI / CTOI / KOI / planet-name / host to candidate targets.

    A host match (star name or a star-level identifier like a TIC) expands to every candidate of
    its guarded host group, so every result deep-links to a target. Exact matches rank first, then
    prefix, then substring; ties break on name.
    """
    q = q.strip()
    if not q:
        return []
    params = {"ex": q, "prefix": q + "%", "like": "%" + q + "%", "limit": limit}
    sql = f"""
    WITH host_matches AS (
        SELECT star_id, 2 AS rank FROM star WHERE canonical_name ILIKE %(like)s
        UNION ALL
        SELECT star_id,
               CASE WHEN lower(id_value) = lower(%(ex)s) THEN 0
                    WHEN id_value ILIKE %(prefix)s THEN 1 ELSE 2 END AS rank
        FROM entity_identifier
        WHERE star_id IS NOT NULL AND id_value ILIKE %(like)s
    ),
    {_identity_cte('search')},
    matches AS (
        -- candidate canonical name
        SELECT c.candidate_id AS cid,
               CASE WHEN lower(c.canonical_name) = lower(%(ex)s) THEN 0
                    WHEN c.canonical_name ILIKE %(prefix)s THEN 1 ELSE 2 END AS rank
        FROM candidate c
        WHERE c.canonical_name ILIKE %(like)s
        UNION ALL
        -- candidate-level identifier (toi / ctoi / koi / name)
        SELECT ei.candidate_id AS cid,
               CASE WHEN lower(ei.id_value) = lower(%(ex)s) THEN 0
                    WHEN ei.id_value ILIKE %(prefix)s THEN 1 ELSE 2 END AS rank
        FROM entity_identifier ei
        WHERE ei.candidate_id IS NOT NULL AND ei.id_value ILIKE %(like)s
        UNION ALL
        -- Host matches expand through the same guard as exact lookup, including aliases
        -- without candidates; an ambiguous null-TIC alias cannot borrow foreign candidates.
        SELECT c.candidate_id AS cid, m.rank
        FROM host_matches m
        JOIN host_identity r ON r.star_id = m.star_id
        JOIN host_identity t ON t.host_id = r.host_id
        JOIN candidate c ON c.star_id = t.star_id
    ),
    best AS (SELECT cid, min(rank) AS rank FROM matches GROUP BY cid)
    SELECT c.candidate_id, c.canonical_name AS target, c.disposition,
           s.canonical_name AS host, s.tic_id, b.rank
    FROM best b
    JOIN candidate c ON c.candidate_id = b.cid
    JOIN star s ON s.star_id = c.star_id
    ORDER BY b.rank, c.canonical_name, c.candidate_id
    LIMIT %(limit)s
    """
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [
        {
            "candidate_id": r["candidate_id"],
            "target": r["target"],
            "host": r["host"],
            "tic_id": str(r["tic_id"]) if r["tic_id"] is not None else None,
            "disposition": r["disposition"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------------------------
# target (the money endpoint) — identity + full crosswalk + who-says-what + conflict flags
# ---------------------------------------------------------------------------------------------
def _resolve_candidate_id(db: psycopg.Connection, ident: str) -> int | None:
    """Resolve a path token to a candidate_id.

    Order: exact candidate_id (integer) -> candidate-level identifier / candidate name -> host
    (star name or star-level identifier), returning that star's first candidate as the target.
    """
    ident = ident.strip()
    with db.cursor() as cur:
        if ident.isdigit():
            cur.execute("SELECT candidate_id FROM candidate WHERE candidate_id = %s", (int(ident),))
            row = cur.fetchone()
            if row:
                return row["candidate_id"]
        # candidate-level identifier or candidate name (exact, case-insensitive)
        cur.execute(
            """
            SELECT c.candidate_id
            FROM candidate c
            LEFT JOIN entity_identifier ei
              ON ei.candidate_id = c.candidate_id AND lower(ei.id_value) = lower(%(ex)s)
            WHERE ei.candidate_id IS NOT NULL OR lower(c.canonical_name) = lower(%(ex)s)
            ORDER BY c.candidate_id
            LIMIT 1
            """,
            {"ex": ident},
        )
        row = cur.fetchone()
        if row:
            return row["candidate_id"]
        # Match hosts before looking for a candidate: an identifier can belong to a pooled
        # alias with no candidates of its own. Expansion must use the same guarded host group.
        cur.execute(
            """
            SELECT DISTINCT s.star_id
            FROM star s
            LEFT JOIN entity_identifier ei
              ON ei.star_id = s.star_id AND lower(ei.id_value) = lower(%(ex)s)
            WHERE lower(s.canonical_name) = lower(%(ex)s) OR ei.star_id IS NOT NULL
            """,
            {"ex": ident},
        )
        sids = [r["star_id"] for r in cur.fetchall()]
        if not sids:
            return None
        cur.execute(
            f"""
            WITH {_identity_cte('star_id')}
            SELECT c.candidate_id
            FROM host_identity r
            JOIN host_identity t ON t.host_id = r.host_id
            JOIN candidate c ON c.star_id = t.star_id
            WHERE r.star_id = ANY(%(ids)s)
            ORDER BY c.candidate_id LIMIT 1
            """,
            {"ids": sids},
        )
        row = cur.fetchone()
        return row["candidate_id"] if row else None


def _identity_group(cur: psycopg.Cursor, cid: int) -> tuple[list[int], list[int]]:
    """Candidate and host twins under the shared guard, ordered by stable graph ID."""
    cur.execute(
        f"""
        WITH {_identity_cte('candidate_id')}
        SELECT ARRAY(
                   SELECT t.candidate_id FROM candidate_identity t
                   WHERE t.eid = r.eid ORDER BY t.candidate_id
               ) AS cids,
               ARRAY(
                   SELECT h.star_id FROM host_identity h
                   WHERE h.host_id = r.host_id ORDER BY h.star_id
               ) AS sids
        FROM candidate_identity r WHERE r.candidate_id = %(cid)s
        """,
        {"cid": cid, "ids": [cid]},
    )
    group = cur.fetchone()
    return group["cids"], group["sids"]


def resolve_target(db: psycopg.Connection, ident: str | int) -> dict[str, Any] | None:
    """Full target dossier: canonical identity, complete crosswalk, the who-says-what table
    (every source_assertion grouped by attribute) with per-attribute conflict flags, and the
    resolved/canonical value where the graph has one. Returns None when nothing resolves.

    One dossier per planet: whichever twin ``ident`` lands on, the canonical row is the
    representative's and the crosswalk, claims and siblings pool over the whole identity group —
    exactly what the conflict corpus pooled into the row that links here."""
    cid = _resolve_candidate_id(db, str(ident))
    if cid is None:
        return None

    with db.cursor() as cur:
        cids, sids = _identity_group(cur, cid)
        cur.execute(
            """
            SELECT c.candidate_id, c.canonical_name, c.disposition, c.period_days,
                   c.planet_radius_re, c.star_id,
                   s.canonical_name AS host, s.tic_id, s.ra_deg, s.dec_deg,
                   s.teff_k, s.logg, s.rstar_rsun
            FROM candidate c JOIN star s ON s.star_id = c.star_id
            WHERE c.candidate_id = %s
            """,
            (cids[0],),
        )
        c = cur.fetchone()

        # full crosswalk: candidate-owned + star-owned identifiers, once per identifier
        cur.execute(
            """
            SELECT id_type, id_value, source, max(confidence) AS confidence,
                   CASE WHEN candidate_id IS NOT NULL THEN 'candidate' ELSE 'star' END AS owner
            FROM entity_identifier
            WHERE candidate_id = ANY(%(cids)s) OR star_id = ANY(%(sids)s)
            GROUP BY 1, 2, 3, 5
            ORDER BY owner, id_type, source, id_value
            """,
            {"cids": cids, "sids": sids},
        )
        identifiers = [
            {
                "id_type": r["id_type"],
                "id_value": r["id_value"],
                "source": r["source"],
                "confidence": float(r["confidence"]) if r["confidence"] is not None else None,
                "owner": r["owner"],
            }
            for r in cur.fetchall()
        ]

        # every assertion for the planet AND its host, with canonical disposition mapped; the same
        # Archive row attached to two twins is one claim (value + citation), as in the corpus
        cur.execute(
            """
            SELECT sa.attribute, sa.source, sa.value, sa.unit, sa.source_ref,
                   max(sa.observed_at) AS observed_at, dm.canonical_disposition,
                   CASE WHEN sa.candidate_id IS NOT NULL THEN 'candidate' ELSE 'star' END AS level
            FROM source_assertion sa
            LEFT JOIN disposition_mapping dm
              ON sa.attribute = 'disposition'
             AND dm.source = sa.source AND dm.source_value = sa.value
            WHERE sa.candidate_id = ANY(%(cids)s) OR sa.star_id = ANY(%(sids)s)
            GROUP BY 1, 2, 3, 4, 5, 7, 8
            ORDER BY sa.attribute, sa.source, observed_at DESC
            """,
            {"cids": cids, "sids": sids},
        )
        raw_assertions = cur.fetchall()

        # sibling planets of the host (its twins included), one per planet, linking to each
        # planet's own representative
        cur.execute(
            """
            SELECT DISTINCT ON (lower(canonical_name) COLLATE "C")
                   candidate_id, canonical_name, disposition
            FROM candidate
            WHERE star_id = ANY(%(sids)s) AND candidate_id <> ALL(%(cids)s)
            ORDER BY lower(canonical_name) COLLATE "C", candidate_id
            """,
            {"cids": cids, "sids": sids},
        )
        siblings = cur.fetchall()

    attributes = _group_assertions(raw_assertions, c)
    conflict_attributes = [a["attribute"] for a in attributes if a["conflict"]]

    return {
        "candidate": {
            "candidate_id": c["candidate_id"],
            "name": c["canonical_name"],
            "disposition": c["disposition"],
            "period_days": _f(c["period_days"]),
            "planet_radius_re": _f(c["planet_radius_re"]),
        },
        "star": {
            "star_id": c["star_id"],
            "name": c["host"],
            "tic_id": str(c["tic_id"]) if c["tic_id"] is not None else None,
            "ra_deg": _f(c["ra_deg"]),
            "dec_deg": _f(c["dec_deg"]),
            "teff_k": _f(c["teff_k"]),
            "logg": _f(c["logg"]),
            "rstar_rsun": _f(c["rstar_rsun"]),
        },
        "identifiers": identifiers,
        "attributes": attributes,
        "conflict_attributes": conflict_attributes,
        "sibling_candidates": [
            {"candidate_id": s["candidate_id"], "name": s["canonical_name"],
             "disposition": s["disposition"]}
            for s in siblings
        ],
    }


def _group_assertions(rows: list[dict], canon_row: dict) -> list[dict[str, Any]]:
    """Group raw assertions by attribute into the who-says-what table, computing the per-attribute
    conflict flag and attaching the graph's resolved/canonical value where one exists."""
    # resolved winners the graph already picked, keyed by attribute
    resolved = {
        "disposition": canon_row["disposition"],
        "period_days": _f(canon_row["period_days"]),
        "planet_radius_re": _f(canon_row["planet_radius_re"]),
        "teff_k": _f(canon_row["teff_k"]),
        "logg": _f(canon_row["logg"]),
        "rstar_rsun": _f(canon_row["rstar_rsun"]),
    }

    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["attribute"], []).append(r)

    out: list[dict[str, Any]] = []
    for attr, items in grouped.items():
        meta = ATTRIBUTES.get(attr, {"level": items[0]["level"], "unit": None, "kind": "numeric",
                                     "threshold": 0.10})
        conflict = _attribute_conflict(attr, meta, items)
        out.append({
            "attribute": attr,
            "level": meta["level"],
            "unit": meta.get("unit"),
            "kind": meta["kind"],
            "conflict": conflict,
            "resolved": resolved.get(attr),
            "assertions": [
                {
                    "source": it["source"],
                    "value": it["value"],
                    "canonical_disposition": it["canonical_disposition"],
                    "source_ref": _clean_ref(it["source_ref"]),
                    "observed_at": it["observed_at"].isoformat() if it["observed_at"] else None,
                }
                for it in items
            ],
        })

    # stable, meaningful order: conflicts first, then the primary axes, then the rest
    axis_order = list(ATTRIBUTES.keys())

    def _order(a: dict) -> tuple:
        idx = axis_order.index(a["attribute"]) if a["attribute"] in axis_order else 99
        return (not a["conflict"], idx)

    out.sort(key=_order)
    return out


def _attribute_conflict(attr: str, meta: dict, items: list[dict]) -> bool:
    """True when the sources genuinely disagree on this attribute."""
    if meta["kind"] == "disposition":
        canon = {it["canonical_disposition"] for it in items if it["canonical_disposition"]}
        return len(canon) >= 2
    threshold = meta.get("threshold")
    if threshold is None:
        return False
    by_source: dict[str, set[Decimal]] = {}
    for it in items:
        v = _num(it["value"])
        if v is not None:
            by_source.setdefault(it["source"], set()).add(v)
    values = {v for vs in by_source.values() for v in vs}
    if len(by_source) < 2 or len(values) < 2:
        return False
    mx = max(values)
    # Cross-multiply exactly, matching SQL numeric arithmetic. Fraction avoids both binary
    # float rounding and Decimal's default context rounding at a strict threshold boundary.
    return mx > 0 and Fraction(mx) - Fraction(min(values)) > Fraction(mx) * Fraction(str(threshold))


# ---------------------------------------------------------------------------------------------
# conflict corpus (browsable, paginated)
# ---------------------------------------------------------------------------------------------
def list_conflicts(
    db: psycopg.Connection, ctype: str, limit: int = 50, offset: int = 0
) -> dict[str, Any]:
    """A page of the ``ctype`` conflict corpus (disposition | radius | teff), each row deep-linking
    to a target. Returns ``{"type", "rows", "total", "limit", "offset"}``."""
    if ctype not in CONFLICT_TYPES:
        raise ValueError(f"unknown conflict type: {ctype!r}")
    if ctype == "disposition":
        rows, total = _list_disposition(db, limit, offset)
    else:
        rows, total = _list_numeric(db, ctype, limit, offset)
    return {"type": ctype, "rows": rows, "total": total, "limit": limit, "offset": offset}


def _list_disposition(db: psycopg.Connection, limit: int, offset: int) -> tuple[list[dict], int]:
    with db.cursor() as cur:
        cur.execute(_DISPO_CTE + "SELECT count(*) AS n FROM conflicted")
        total = cur.fetchone()["n"]
        cur.execute(
            _DISPO_CTE
            + """
            SELECT c.candidate_id, c.canonical_name AS target, c.disposition,
                   s.canonical_name AS host, s.tic_id,
                   x.dispositions, x.dramatic
            FROM conflicted x
            JOIN candidate c ON c.candidate_id = x.eid
            JOIN star s ON s.star_id = c.star_id
            ORDER BY x.dramatic DESC, c.canonical_name, c.candidate_id
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            {"limit": limit, "offset": offset},
        )
        page = cur.fetchall()
        ids = [r["candidate_id"] for r in page]
        who = _dispo_by_source(db, ids)

    return [
        {
            "candidate_id": r["candidate_id"],
            "target": r["target"],
            "host": r["host"],
            "tic_id": str(r["tic_id"]) if r["tic_id"] is not None else None,
            "attribute": "disposition",
            "resolved": r["disposition"],
            "dispositions": r["dispositions"],
            "dramatic": r["dramatic"],
            "by_source": who.get(r["candidate_id"], []),
        }
        for r in page
    ], total


def _dispo_by_source(db: psycopg.Connection, candidate_ids: list[int]) -> dict[int, list[dict]]:
    """Per-source canonical dispositions for the page's rows, keyed by the row's candidate_id
    (twin candidates pool; see ``_TWINS_CTE``)."""
    if not candidate_ids:
        return {}
    with db.cursor() as cur:
        cur.execute(
            f"""
            WITH {_identity_cte('candidate_id')}, {_TWINS_CTE['candidate_id']}
            SELECT DISTINCT t.eid AS candidate_id, sa.source, dm.canonical_disposition AS canon
            FROM twins t
            JOIN source_assertion sa
              ON sa.candidate_id = t.candidate_id AND sa.attribute = 'disposition'
            JOIN disposition_mapping dm
              ON dm.source = sa.source AND dm.source_value = sa.value
            ORDER BY 1, 2
            """,
            {"ids": candidate_ids},
        )
        out: dict[int, list[dict]] = {}
        for r in cur.fetchall():
            out.setdefault(r["candidate_id"], []).append(
                {"source": r["source"], "disposition": r["canon"]}
            )
    return out


def _list_numeric(
    db: psycopg.Connection, ctype: str, limit: int, offset: int
) -> tuple[list[dict], int]:
    spec = CONFLICT_TYPES[ctype]
    attr = spec["attribute"]
    level = "candidate_id" if spec["level"] == "candidate" else "star_id"
    params = {"attr": attr, "numre": NUM_RE, "threshold": spec["threshold"],
              "limit": limit, "offset": offset}
    cte = _numeric_conflict_cte(level)

    with db.cursor() as cur:
        cur.execute(cte + "SELECT count(*) AS n FROM conflicted", params)
        total = cur.fetchone()["n"]

        join = """
            SELECT c.candidate_id, c.canonical_name AS target, c.disposition,
                   s.canonical_name AS host, s.tic_id,
                   x.mn, x.mx, x.spread, x.n_sources
            FROM conflicted x
            JOIN candidate c ON c.candidate_id = x.eid
            JOIN star s ON s.star_id = c.star_id
            ORDER BY x.spread DESC, c.canonical_name, c.candidate_id
            LIMIT %(limit)s OFFSET %(offset)s
            """
        cur.execute(cte + join, params)
        page = cur.fetchall()

    # per-source ranges for just this page, keyed by the row's candidate_id
    by_source = _numeric_by_source(db, attr, page, spec["level"])

    rows = [
        {
            "candidate_id": r["candidate_id"],
            "target": r["target"],
            "host": r["host"],
            "tic_id": str(r["tic_id"]) if r["tic_id"] is not None else None,
            "attribute": attr,
            "unit": spec.get("unit"),
            "resolved": r["disposition"],
            "min": _f(r["mn"]),
            "max": _f(r["mx"]),
            "spread_pct": round(float(r["spread"]) * 100, 1),
            "n_sources": r["n_sources"],
            "by_source": by_source.get(r["candidate_id"], []),
        }
        for r in page
    ]
    return rows, total


def _numeric_by_source(
    db: psycopg.Connection, attr: str, page: list[dict], level_name: str
) -> dict[int, list[dict]]:
    """Per-source min/max/claim-count for the page's targets, keyed by candidate_id (the row key
    the web table renders). Twin rows pool (see ``_TWINS_CTE``), so ``n`` counts distinct claims
    (value + citation) rather than rows — the same Archive row attached to two twins is one
    claim."""
    if not page:
        return {}
    # For candidate-level, group over the planet's row candidate_id; for star-level, group over
    # the host's row star_id then map to the candidate_id in the page.
    if level_name == "candidate":
        ids = [r["candidate_id"] for r in page]
        with db.cursor() as cur:
            cur.execute(
                f"""
                WITH {_identity_cte('candidate_id')}, {_TWINS_CTE['candidate_id']}
                SELECT t.eid, sa.source, min((sa.value)::numeric) AS mn,
                       max((sa.value)::numeric) AS mx,
                       count(DISTINCT (sa.value, sa.source_ref)) AS n
                FROM twins t
                JOIN source_assertion sa
                  ON sa.candidate_id = t.candidate_id AND sa.attribute = %(attr)s
                WHERE sa.value ~ %(numre)s
                GROUP BY t.eid, sa.source ORDER BY t.eid, sa.source
                """,
                {"attr": attr, "ids": ids, "numre": NUM_RE},
            )
            per_eid: dict[int, list[dict]] = {}
            for r in cur.fetchall():
                per_eid.setdefault(r["eid"], []).append(
                    {"source": r["source"], "min": _f(r["mn"]), "max": _f(r["mx"]), "n": r["n"]}
                )
        return per_eid
    # star-level: the page's candidate_id is the first candidate of the row's star.
    cand_ids = [r["candidate_id"] for r in page]
    with db.cursor() as cur:
        cur.execute(
            "SELECT candidate_id, star_id FROM candidate WHERE candidate_id = ANY(%s)", (cand_ids,)
        )
        star_of = {r["candidate_id"]: r["star_id"] for r in cur.fetchall()}
        star_ids = list(set(star_of.values()))
        cur.execute(
            f"""
            WITH {_identity_cte('star_id')}, {_TWINS_CTE['star_id']}
            SELECT t.eid, sa.source, min((sa.value)::numeric) AS mn,
                   max((sa.value)::numeric) AS mx,
                   count(DISTINCT (sa.value, sa.source_ref)) AS n
            FROM twins t
            JOIN source_assertion sa ON sa.star_id = t.star_id AND sa.attribute = %(attr)s
            WHERE sa.value ~ %(numre)s
            GROUP BY t.eid, sa.source ORDER BY t.eid, sa.source
            """,
            {"attr": attr, "ids": star_ids, "numre": NUM_RE},
        )
        per_star: dict[int, list[dict]] = {}
        for r in cur.fetchall():
            per_star.setdefault(r["eid"], []).append(
                {"source": r["source"], "min": _f(r["mn"]), "max": _f(r["mx"]), "n": r["n"]}
            )
    return {cid: per_star.get(sid, []) for cid, sid in star_of.items()}


# ---------------------------------------------------------------------------------------------
# target_conflicts — compact "does anyone disagree?" answer for one target (MCP-friendly)
# ---------------------------------------------------------------------------------------------
def target_conflicts(db: psycopg.Connection, ident: str | int) -> dict[str, Any] | None:
    """Just the conflicting attributes for one target: attribute, whether it is a headline conflict
    axis, and the per-source claims. Returns None if the target does not resolve."""
    target = resolve_target(db, ident)
    if target is None:
        return None
    conflicts = [
        {
            "attribute": a["attribute"],
            "level": a["level"],
            "unit": a["unit"],
            "resolved": a["resolved"],
            "assertions": a["assertions"],
        }
        for a in target["attributes"]
        if a["conflict"]
    ]
    return {
        "candidate_id": target["candidate"]["candidate_id"],
        "target": target["candidate"]["name"],
        "host": target["star"]["name"],
        "has_conflict": len(conflicts) > 0,
        "conflict_attributes": target["conflict_attributes"],
        "conflicts": conflicts,
    }


# ---------------------------------------------------------------------------------------------
# attribution
# ---------------------------------------------------------------------------------------------
def attribution() -> dict[str, Any]:
    """Data provenance + citations. Static; no DB access."""
    return {
        "summary": (
            "ExoDossier surfaces where the exoplanet archives disagree, with full provenance. It "
            "does not adjudicate or confirm. All catalog data is the property of its sources, "
            "retrieved under their public-use terms; please cite them, not this tool."
        ),
        "sources": [
            {
                "name": "NASA Exoplanet Archive",
                "operator": "NASA Exoplanet Science Institute / IPAC / Caltech",
                "used_for": "TOI table, KOI cumulative, Planetary Systems (ps) per-publication "
                            "rows, and the Composite (pscomppars) table, via the TAP service.",
                "url": "https://exoplanetarchive.ipac.caltech.edu/",
                "citation": (
                    "This research has made use of the NASA Exoplanet Archive, operated by "
                    "the California Institute of Technology, under contract with the National "
                    "Aeronautics and Space Administration under the Exoplanet Exploration Program."
                ),
            },
            {
                "name": "ExoFOP-TESS",
                "operator": "Exoplanet Follow-up Observing Program / IPAC / Caltech",
                "used_for": "TESS Objects of Interest (TOI) and Community TOI (CTOI) lists.",
                "url": "https://exofop.ipac.caltech.edu/tess/",
                "citation": (
                    "This paper includes data collected by the ExoFOP-TESS website, operated by "
                    "IPAC/Caltech under contract with NASA."
                ),
            },
            {
                "name": "TESS Mission",
                "operator": "NASA / MIT",
                "used_for": "TESS produced the TOI/CTOI candidates this catalog reconciles.",
                "url": "https://tess.mit.edu/",
                "citation": (
                    "Funding for TESS is provided by NASA's Science Mission Directorate."
                ),
            },
        ],
        "notes": (
            "Disposition vocabularies are mapped to a canonical taxonomy (CONFIRMED, KNOWN_PLANET, "
            "CANDIDATE, AMBIGUOUS, FALSE_POSITIVE) per db/migrations disposition_mapping. Conflict "
            "counts are recomputed live from the identity graph and track the v0 conflict report."
        ),
    }


# ---------------------------------------------------------------------------------------------
# tiny helpers
# ---------------------------------------------------------------------------------------------
def _f(value: Any) -> float | None:
    """Decimal/None -> float/None for clean JSON."""
    return float(value) if value is not None else None


def _iso_row(row: dict) -> dict:
    """Copy a ledger row with any datetime rendered ISO for JSON."""
    out = dict(row)
    for k, v in out.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


def _clean_ref(ref: str | None) -> str | None:
    """The ps ``source_ref`` ships an HTML <a> tag; pull out the human citation text.

    The text inside the tag is HTML too, so entities come through as written: "Gajdo&scaron;
    et al. 2019", "Fulton &amp;amp; Petigura 2018". Decode them after the tags are gone, so a
    decoded "&lt;" can never be mistaken for a tag."""
    if not ref:
        return ref
    import re

    text = html.unescape(re.sub(r"<[^>]+>", "", ref)).strip()
    return text or None
