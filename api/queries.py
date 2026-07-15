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
Disagreements are surfaced, never adjudicated.
"""

from __future__ import annotations

from typing import Any

import psycopg

# A source_assertion.value is TEXT; only cast the ones that look numeric. Anchored, allows an
# optional sign, a decimal point and scientific notation ("1e+04") — everything Postgres ::numeric
# accepts and nothing it chokes on.
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
def _num(value: str) -> float | None:
    """Parse an assertion value to float, or None if it is not numeric."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _numeric_conflict_cte(attr_level: str) -> str:
    """CTE ``conflicted(eid, mn, mx, spread, n_sources)`` for a numeric attribute.

    ``attr_level`` is a trusted internal literal ('candidate_id' or 'star_id'), never user input.
    A conflict is a genuine cross-source disagreement: >= 2 distinct values from >= 2 distinct
    sources, relative spread over the caller's threshold.
    """
    return f"""
    WITH vals AS (
        SELECT sa.{attr_level} AS eid, (sa.value)::numeric AS v, sa.source
        FROM source_assertion sa
        WHERE sa.attribute = %(attr)s
          AND sa.{attr_level} IS NOT NULL
          AND sa.value ~ %(numre)s
    ),
    agg AS (
        SELECT eid, min(v) AS mn, max(v) AS mx,
               count(DISTINCT v) AS n_values, count(DISTINCT source) AS n_sources
        FROM vals GROUP BY eid
    ),
    conflicted AS (
        SELECT eid, mn, mx, n_sources, (mx - mn) / mx AS spread
        FROM agg
        WHERE n_values >= 2 AND n_sources >= 2 AND mx > 0 AND (mx - mn) / mx > %(threshold)s
    )
    """


_DISPO_CTE = """
    WITH dispo AS (
        SELECT sa.candidate_id AS eid, dm.canonical_disposition AS canon
        FROM source_assertion sa
        JOIN disposition_mapping dm
          ON dm.source = sa.source AND dm.source_value = sa.value
        WHERE sa.attribute = 'disposition' AND sa.candidate_id IS NOT NULL
    ),
    conflicted AS (
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

        cur.execute(
            """
            SELECT DISTINCT ON (source, endpoint)
                source, endpoint, status, rows_ingested, bytes_downloaded, finished_at
            FROM ingest_run
            ORDER BY source, endpoint, started_at DESC NULLS LAST
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
    that star, so every result deep-links to a target. Exact matches rank first, then prefix, then
    substring; ties break on name.
    """
    q = q.strip()
    if not q:
        return []
    params = {"ex": q, "prefix": q + "%", "like": "%" + q + "%", "limit": limit}
    sql = """
    WITH matches AS (
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
        -- host star name -> all its candidates
        SELECT c.candidate_id AS cid, 2 AS rank
        FROM candidate c JOIN star s ON s.star_id = c.star_id
        WHERE s.canonical_name ILIKE %(like)s
        UNION ALL
        -- star-level identifier (tic / kic / gaia / hd / hip / name) -> all its candidates
        SELECT c.candidate_id AS cid,
               CASE WHEN lower(ei.id_value) = lower(%(ex)s) THEN 0
                    WHEN ei.id_value ILIKE %(prefix)s THEN 1 ELSE 2 END AS rank
        FROM entity_identifier ei JOIN candidate c ON c.star_id = ei.star_id
        WHERE ei.star_id IS NOT NULL AND ei.id_value ILIKE %(like)s
    ),
    best AS (SELECT cid, min(rank) AS rank FROM matches GROUP BY cid)
    SELECT c.candidate_id, c.canonical_name AS target, c.disposition,
           s.canonical_name AS host, s.tic_id, b.rank
    FROM best b
    JOIN candidate c ON c.candidate_id = b.cid
    JOIN star s ON s.star_id = c.star_id
    ORDER BY b.rank, c.canonical_name
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
        # host: star name or star-level identifier -> first candidate of that star
        cur.execute(
            """
            SELECT c.candidate_id
            FROM star s
            JOIN candidate c ON c.star_id = s.star_id
            LEFT JOIN entity_identifier ei
              ON ei.star_id = s.star_id AND lower(ei.id_value) = lower(%(ex)s)
            WHERE lower(s.canonical_name) = lower(%(ex)s) OR ei.star_id IS NOT NULL
            ORDER BY c.candidate_id
            LIMIT 1
            """,
            {"ex": ident},
        )
        row = cur.fetchone()
        return row["candidate_id"] if row else None


def resolve_target(db: psycopg.Connection, ident: str | int) -> dict[str, Any] | None:
    """Full target dossier: canonical identity, complete crosswalk, the who-says-what table
    (every source_assertion grouped by attribute) with per-attribute conflict flags, and the
    resolved/canonical value where the graph has one. Returns None when nothing resolves."""
    cid = _resolve_candidate_id(db, str(ident))
    if cid is None:
        return None

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT c.candidate_id, c.canonical_name, c.disposition, c.period_days,
                   c.planet_radius_re, c.star_id,
                   s.canonical_name AS host, s.tic_id, s.ra_deg, s.dec_deg,
                   s.teff_k, s.logg, s.rstar_rsun
            FROM candidate c JOIN star s ON s.star_id = c.star_id
            WHERE c.candidate_id = %s
            """,
            (cid,),
        )
        c = cur.fetchone()
        star_id = c["star_id"]

        # full crosswalk: candidate-owned + star-owned identifiers
        cur.execute(
            """
            SELECT id_type, id_value, source, confidence,
                   CASE WHEN candidate_id IS NOT NULL THEN 'candidate' ELSE 'star' END AS owner
            FROM entity_identifier
            WHERE candidate_id = %(cid)s OR star_id = %(sid)s
            ORDER BY owner, id_type, source
            """,
            {"cid": cid, "sid": star_id},
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

        # every assertion for the candidate AND its host star, with canonical disposition mapped
        cur.execute(
            """
            SELECT sa.attribute, sa.source, sa.value, sa.unit, sa.source_ref, sa.observed_at,
                   dm.canonical_disposition,
                   CASE WHEN sa.candidate_id IS NOT NULL THEN 'candidate' ELSE 'star' END AS level
            FROM source_assertion sa
            LEFT JOIN disposition_mapping dm
              ON sa.attribute = 'disposition'
             AND dm.source = sa.source AND dm.source_value = sa.value
            WHERE sa.candidate_id = %(cid)s OR sa.star_id = %(sid)s
            ORDER BY sa.attribute, sa.source, sa.observed_at DESC
            """,
            {"cid": cid, "sid": star_id},
        )
        raw_assertions = cur.fetchall()

        # sibling candidates on the same star (other planets in the system)
        cur.execute(
            """
            SELECT candidate_id, canonical_name, disposition
            FROM candidate WHERE star_id = %s AND candidate_id <> %s
            ORDER BY canonical_name
            """,
            (star_id, cid),
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
    by_source: dict[str, set[float]] = {}
    for it in items:
        v = _num(it["value"])
        if v is not None:
            by_source.setdefault(it["source"], set()).add(v)
    values = {v for vs in by_source.values() for v in vs}
    if len(by_source) < 2 or len(values) < 2:
        return False
    mx = max(values)
    return mx > 0 and (mx - min(values)) / mx > threshold


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
            ORDER BY x.dramatic DESC, c.canonical_name
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
    if not candidate_ids:
        return {}
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT sa.candidate_id, sa.source, dm.canonical_disposition AS canon
            FROM source_assertion sa
            JOIN disposition_mapping dm
              ON dm.source = sa.source AND dm.source_value = sa.value
            WHERE sa.attribute = 'disposition' AND sa.candidate_id = ANY(%s)
            ORDER BY sa.candidate_id, sa.source
            """,
            (candidate_ids,),
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

        if spec["level"] == "candidate":
            join = """
            SELECT c.candidate_id, c.canonical_name AS target, c.disposition,
                   s.canonical_name AS host, s.tic_id,
                   x.mn, x.mx, x.spread, x.n_sources
            FROM conflicted x
            JOIN candidate c ON c.candidate_id = x.eid
            JOIN star s ON s.star_id = c.star_id
            ORDER BY x.spread DESC, c.canonical_name
            LIMIT %(limit)s OFFSET %(offset)s
            """
        else:
            # star-level attribute: link to the star's first candidate as the target
            join = """
            SELECT rep.candidate_id, rep.canonical_name AS target, rep.disposition,
                   s.canonical_name AS host, s.tic_id,
                   x.mn, x.mx, x.spread, x.n_sources
            FROM conflicted x
            JOIN star s ON s.star_id = x.eid
            JOIN LATERAL (
                SELECT candidate_id, canonical_name, disposition
                FROM candidate WHERE star_id = s.star_id
                ORDER BY candidate_id LIMIT 1
            ) rep ON true
            ORDER BY x.spread DESC, s.canonical_name
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
    """Per-source min/max/count for the page's targets, keyed by candidate_id (the row key the web
    table renders)."""
    if not page:
        return {}
    # For candidate-level, group over candidate_id; for star-level, group over the star then map to
    # the representative candidate_id in the page.
    if level_name == "candidate":
        ids = [r["candidate_id"] for r in page]
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT candidate_id AS eid, source, min((value)::numeric) AS mn,
                       max((value)::numeric) AS mx, count(*) AS n
                FROM source_assertion
                WHERE attribute = %s AND candidate_id = ANY(%s) AND value ~ %s
                GROUP BY candidate_id, source ORDER BY candidate_id, source
                """,
                (attr, ids, NUM_RE),
            )
            per_eid: dict[int, list[dict]] = {}
            for r in cur.fetchall():
                per_eid.setdefault(r["eid"], []).append(
                    {"source": r["source"], "min": _f(r["mn"]), "max": _f(r["mx"]), "n": r["n"]}
                )
        return per_eid
    # star-level: build star_id -> candidate_id map from the page (via a lookup)
    cand_ids = [r["candidate_id"] for r in page]
    with db.cursor() as cur:
        cur.execute(
            "SELECT candidate_id, star_id FROM candidate WHERE candidate_id = ANY(%s)", (cand_ids,)
        )
        star_of = {r["candidate_id"]: r["star_id"] for r in cur.fetchall()}
        star_ids = list(set(star_of.values()))
        cur.execute(
            """
            SELECT star_id AS eid, source, min((value)::numeric) AS mn,
                   max((value)::numeric) AS mx, count(*) AS n
            FROM source_assertion
            WHERE attribute = %s AND star_id = ANY(%s) AND value ~ %s
            GROUP BY star_id, source ORDER BY star_id, source
            """,
            (attr, star_ids, NUM_RE),
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
    """The ps ``source_ref`` ships an HTML <a> tag; pull out the human citation text."""
    if not ref:
        return ref
    import re

    text = re.sub(r"<[^>]+>", "", ref).strip()
    return text or None
