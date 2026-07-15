"""Entity resolution for the exoplanet identity graph: deterministic first, probabilistic where it
must be. Rebuilds the derived graph (star, candidate, entity_identifier, source_assertion,
merge_log) from the raw landing tables. No commit — the caller owns the transaction.

Passes
------
1. STARS (deterministic): every distinct TIC across the TESS/Archive sources becomes a `star`,
   keyed by tic_id (`tic_exact`); Gaia DR3 / HD / HIP / host-name identifiers attach from ps/
   pscomppars (`catalog_xref`). Confirmed planets with no TIC get a host `star` keyed by hostname.
2. KOI STARS (probabilistic): each Kepler host (kepid) is coordinate-matched (astropy SkyCoord,
   <2 arcsec) to an existing TIC star and linked via `kic` (`coord_match<2arcsec`, confidence from
   the separation); unmatched Kepler hosts become new KIC-only stars (`koi_new_star`).
3. CANDIDATES: within each star, source designations (TOI/CTOI/KOI/planet-name) seed candidate
   clusters (`candidate_seed`); cross-designation clusters are unified when their periods agree to
   <1% (`period_match<1pct`). A period matching >1 existing cluster is NOT merged — it is flagged
   `period_ambiguous` in merge_log (no silent guesses).

Every link and every flagged non-merge writes merge_log (identity.merge is the sole writer of the
crosswalk + audit log).
"""

from __future__ import annotations

import logging
import re

from psycopg.types.json import Jsonb

from identity import merge
from identity.normalize import canonical_candidate_name, periods_match

logger = logging.getLogger(__name__)

COORD_TOL_ARCSEC = 2.0
_DERIVED_TABLES = "merge_log, source_assertion, entity_identifier, candidate, star"
_PLANET_LETTER = re.compile(r"\s+[a-z]$")


def _latest_run(conn, table: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT max(r.ingest_run_id) FROM {table} r "
            "JOIN ingest_run i ON i.ingest_run_id = r.ingest_run_id WHERE i.status = 'ok'"
        )
        return cur.fetchone()[0]


def _runs(conn) -> dict[str, int | None]:
    return {
        t: _latest_run(conn, t)
        for t in (
            "raw_exofop_toi", "raw_exofop_ctoi", "raw_nea_toi",
            "raw_koi_cumulative", "raw_ps", "raw_pscomppars",
        )
    }


def _reset(conn) -> None:
    """Drop the derived graph so the build is idempotent (raw + ledger + dispo map are kept)."""
    with conn.cursor() as cur:
        cur.execute(f"TRUNCATE {_DERIVED_TABLES} RESTART IDENTITY CASCADE")


# --- pass 1: TIC stars --------------------------------------------------------


def _bulk_link_star(cur, inner_select: str, rule: str, params: dict) -> None:
    """Set-based crosswalk link for stars: insert identifiers, log merge_log for exactly the rows
    actually inserted (ON CONFLICT DO NOTHING + RETURNING), same no-silent-link invariant as
    merge.link but done over a whole snapshot in one statement."""
    cur.execute(
        f"""
        WITH ins AS (
            INSERT INTO entity_identifier (star_id, id_type, id_value, source, confidence)
            {inner_select}
            ON CONFLICT DO NOTHING
            RETURNING star_id, id_type, id_value, source
        )
        INSERT INTO merge_log (entity_type, surviving_id, merged_id, rule_fired, score, details)
        SELECT 'star', star_id, star_id, %(_rule)s, 1.000,
               jsonb_build_object('id_type', id_type, 'id_value', id_value, 'source', source)
        FROM ins
        """,
        {**params, "_rule": rule},
    )


def _build_tic_stars(conn, runs: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE _star_src (tic BIGINT, ra NUMERIC, dec NUMERIC, hostname TEXT) "
            "ON COMMIT DROP"
        )
        # Only ps/pscomppars carry a host name and reliable decimal coordinates for TIC stars.
        for table, run in (
            ("raw_exofop_ctoi", runs["raw_exofop_ctoi"]),
            ("raw_nea_toi", runs["raw_nea_toi"]),
        ):
            if run is not None:
                col = "tid" if table == "raw_nea_toi" else "tic_id"
                cur.execute(
                    f"INSERT INTO _star_src (tic, ra, dec, hostname) "
                    f"SELECT {col}, ra_deg, dec_deg, NULL FROM {table} "
                    f"WHERE ingest_run_id = %s AND {col} IS NOT NULL",
                    (run,),
                )
        if runs["raw_exofop_toi"] is not None:
            # The TOI CSV's RA/Dec are sexagesimal (landed NULL), so it contributes only the TIC.
            cur.execute(
                "INSERT INTO _star_src (tic, ra, dec, hostname) "
                "SELECT tic_id, NULL, NULL, NULL FROM raw_exofop_toi "
                "WHERE ingest_run_id = %s AND tic_id IS NOT NULL",
                (runs["raw_exofop_toi"],),
            )
        for table, run in (("raw_ps", runs["raw_ps"]), ("raw_pscomppars", runs["raw_pscomppars"])):
            if run is not None:
                cur.execute(
                    f"INSERT INTO _star_src (tic, ra, dec, hostname) "
                    f"SELECT tic_id, ra_deg, dec_deg, hostname FROM {table} "
                    f"WHERE ingest_run_id = %s AND tic_id IS NOT NULL",
                    (run,),
                )
        # One star per distinct TIC, preferring a row that carries a host name and coordinates.
        cur.execute(
            """
            INSERT INTO star (tic_id, canonical_name, ra_deg, dec_deg)
            SELECT tic, COALESCE(hostname, 'TIC ' || tic), ra, dec
            FROM (
                SELECT DISTINCT ON (tic) tic, hostname, ra, dec
                FROM _star_src
                ORDER BY tic, (hostname IS NULL), (ra IS NULL), (dec IS NULL)
            ) s
            """
        )
        # tic identifiers, tagged by originating source system.
        for table, col, xsource in (
            ("raw_exofop_toi", "tic_id", "exofop"),
            ("raw_exofop_ctoi", "tic_id", "exofop"),
            ("raw_nea_toi", "tid", "nea"),
            ("raw_ps", "tic_id", "nea"),
            ("raw_pscomppars", "tic_id", "nea"),
        ):
            run = runs[table]
            if run is None:
                continue
            _bulk_link_star(
                cur,
                f"SELECT s.star_id, 'tic', st.tic::text, %(xsource)s, 1.00 "
                f"FROM (SELECT DISTINCT {col} AS tic FROM {table} "
                f"      WHERE ingest_run_id = %(run)s AND {col} IS NOT NULL) st "
                f"JOIN star s ON s.tic_id = st.tic",
                "tic_exact",
                {"run": run, "xsource": xsource},
            )
        # Gaia DR3 / HD / HIP / host-name crosswalk from ps + pscomppars.
        for table in ("raw_ps", "raw_pscomppars"):
            run = runs[table]
            if run is None:
                continue
            for id_type, src_col in (
                ("gaia_dr3", "gaia_id"), ("hd", "hd_name"), ("hip", "hip_name"),
                ("name", "hostname"),
            ):
                _bulk_link_star(
                    cur,
                    f"SELECT s.star_id, %(id_type)s, st.v, 'nea', 1.00 "
                    f"FROM (SELECT DISTINCT tic_id, {src_col} AS v FROM {table} "
                    f"      WHERE ingest_run_id = %(run)s AND tic_id IS NOT NULL "
                    f"        AND {src_col} IS NOT NULL AND {src_col} <> '') st "
                    f"JOIN star s ON s.tic_id = st.tic_id",
                    "catalog_xref",
                    {"run": run, "id_type": id_type},
                )


def _build_hostname_stars(conn, runs: dict) -> None:
    """Confirmed planets whose host has no TIC still deserve a star — keyed by host name."""
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE _host_src (hostname TEXT, ra NUMERIC, dec NUMERIC) ON COMMIT DROP"
        )
        for table in ("raw_ps", "raw_pscomppars"):
            run = runs[table]
            if run is None:
                continue
            cur.execute(
                f"INSERT INTO _host_src (hostname, ra, dec) "
                f"SELECT hostname, ra_deg, dec_deg FROM {table} "
                f"WHERE ingest_run_id = %s AND (tic_id IS NULL) "
                f"  AND hostname IS NOT NULL AND hostname <> ''",
                (run,),
            )
        # Only hostnames with no TIC-backed star anywhere become name-only stars.
        cur.execute(
            """
            INSERT INTO star (canonical_name, ra_deg, dec_deg)
            SELECT hostname, ra, dec
            FROM (
                SELECT DISTINCT ON (hostname) hostname, ra, dec
                FROM _host_src h
                WHERE NOT EXISTS (
                    SELECT 1 FROM entity_identifier ei
                    WHERE ei.id_type = 'name' AND ei.id_value = h.hostname
                      AND ei.star_id IS NOT NULL
                )
                ORDER BY hostname, (ra IS NULL), (dec IS NULL)
            ) s
            RETURNING star_id, canonical_name
            """
        )
        created = cur.fetchall()
    # Link the host-name identifier for each newly created name-only star.
    for star_id, hostname in created:
        merge.link(conn, "star", star_id, "name", hostname, "nea", "hostname_new_star", 1.000)


# --- pass 2: KOI stars via coordinate match -----------------------------------


def _kepler_host(planet_name: str | None) -> str | None:
    if not planet_name:
        return None
    return _PLANET_LETTER.sub("", planet_name).strip() or None


def _coord_match_koi(conn, runs: dict, tol_arcsec: float) -> dict:
    """Coordinate-match each Kepler host to a TIC star (<tol) or mint a new KIC-only star."""
    run = runs["raw_koi_cumulative"]
    stats = {"koi_coord_matched": 0, "koi_new_stars": 0}
    if run is None:
        return stats
    from astropy import units as u
    from astropy.coordinates import SkyCoord

    with conn.cursor() as cur:
        cur.execute("SELECT star_id, ra_deg, dec_deg FROM star "
                    "WHERE ra_deg IS NOT NULL AND dec_deg IS NOT NULL")
        tic_rows = cur.fetchall()
        cur.execute(
            "SELECT DISTINCT ON (kepid) kepid, ra_deg, dec_deg, kepler_name "
            "FROM raw_koi_cumulative WHERE ingest_run_id = %s AND kepid IS NOT NULL "
            "ORDER BY kepid, (kepler_name IS NULL)",
            (run,),
        )
        koi_rows = cur.fetchall()
    if not koi_rows:
        return stats

    catalog = None
    if tic_rows:
        catalog = SkyCoord(
            ra=[float(r[1]) for r in tic_rows] * u.deg,
            dec=[float(r[2]) for r in tic_rows] * u.deg,
        )
    koi_with_coords = [r for r in koi_rows if r[1] is not None and r[2] is not None]
    idx_map, seps = {}, {}
    if catalog is not None and koi_with_coords:
        probe = SkyCoord(
            ra=[float(r[1]) for r in koi_with_coords] * u.deg,
            dec=[float(r[2]) for r in koi_with_coords] * u.deg,
        )
        nearest_idx, sep2d, _ = probe.match_to_catalog_sky(catalog)
        for i, row in enumerate(koi_with_coords):
            idx_map[row[0]] = int(nearest_idx[i])
            seps[row[0]] = float(sep2d[i].arcsec)

    for kepid, ra, dec, kepler_name in koi_rows:
        matched_star = None
        if kepid in seps and seps[kepid] < tol_arcsec:
            matched_star = tic_rows[idx_map[kepid]][0]
        if matched_star is not None:
            sep = seps[kepid]
            merge.link(
                conn, "star", matched_star, "kic", str(kepid), "nea",
                "coord_match<2arcsec", round(1.0 - sep / tol_arcsec, 3),
                confidence=round(max(0.80, 1.0 - sep / tol_arcsec), 2),
                details={"sep_arcsec": round(sep, 4), "kepid": kepid},
            )
            stats["koi_coord_matched"] += 1
        else:
            name = _kepler_host(kepler_name) or f"KIC {kepid}"
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO star (canonical_name, ra_deg, dec_deg) VALUES (%s, %s, %s) "
                    "RETURNING star_id",
                    (name, ra, dec),
                )
                star_id = cur.fetchone()[0]
            merge.link(conn, "star", star_id, "kic", str(kepid), "nea", "koi_new_star", 1.000)
            stats["koi_new_stars"] += 1
    return stats


# --- pass 3: candidates -------------------------------------------------------


def _entity_maps(conn) -> tuple[dict, dict, dict]:
    """tic->star_id, kepid->star_id, hostname->star_id (only name-only hosts)."""
    tic_to_star, kic_to_star, host_to_star = {}, {}, {}
    with conn.cursor() as cur:
        cur.execute("SELECT tic_id, star_id FROM star WHERE tic_id IS NOT NULL")
        tic_to_star = {int(t): s for t, s in cur.fetchall()}
        cur.execute("SELECT id_value, star_id FROM entity_identifier "
                    "WHERE id_type = 'kic' AND star_id IS NOT NULL")
        kic_to_star = {int(v): s for v, s in cur.fetchall()}
        cur.execute(
            "SELECT ei.id_value, ei.star_id FROM entity_identifier ei "
            "JOIN star s ON s.star_id = ei.star_id "
            "WHERE ei.id_type = 'name' AND s.tic_id IS NULL AND ei.star_id IS NOT NULL"
        )
        host_to_star = {v: s for v, s in cur.fetchall()}
    return tic_to_star, kic_to_star, host_to_star


def _gather_observations(conn, runs, tic_to_star, kic_to_star, host_to_star) -> dict:
    """star_id -> list of observation dicts {id_type, value, xsource, period, planet_name}."""
    obs: dict[int, list[dict]] = {}

    def add(star_id, id_type, value, xsource, period, planet_name=None):
        if star_id is None or value is None or value == "":
            return
        obs.setdefault(star_id, []).append(
            {"id_type": id_type, "value": str(value), "xsource": xsource,
             "period": period, "planet_name": planet_name}
        )

    with conn.cursor() as cur:
        if runs["raw_exofop_toi"]:
            cur.execute("SELECT toi, tic_id, period_days FROM raw_exofop_toi "
                        "WHERE ingest_run_id = %s AND toi IS NOT NULL", (runs["raw_exofop_toi"],))
            for toi, tic, period in cur.fetchall():
                add(tic_to_star.get(int(tic)) if tic is not None else None,
                    "toi", toi, "exofop", period)
        if runs["raw_nea_toi"]:
            cur.execute("SELECT toi, tid, period_days FROM raw_nea_toi "
                        "WHERE ingest_run_id = %s AND toi IS NOT NULL", (runs["raw_nea_toi"],))
            for toi, tid, period in cur.fetchall():
                add(tic_to_star.get(int(tid)) if tid is not None else None,
                    "toi", toi, "nea", period)
        if runs["raw_exofop_ctoi"]:
            cur.execute("SELECT ctoi, tic_id, period_days FROM raw_exofop_ctoi "
                        "WHERE ingest_run_id = %s AND ctoi IS NOT NULL", (runs["raw_exofop_ctoi"],))
            for ctoi, tic, period in cur.fetchall():
                add(tic_to_star.get(int(tic)) if tic is not None else None,
                    "ctoi", ctoi, "exofop", period)
        if runs["raw_koi_cumulative"]:
            cur.execute("SELECT kepoi_name, kepid, kepler_name, period_days "
                        "FROM raw_koi_cumulative "
                        "WHERE ingest_run_id = %s AND kepoi_name IS NOT NULL",
                        (runs["raw_koi_cumulative"],))
            for kepoi, kepid, kepler_name, period in cur.fetchall():
                add(kic_to_star.get(int(kepid)) if kepid is not None else None,
                    "koi", kepoi, "nea", period, planet_name=kepler_name)
        if runs["raw_ps"]:
            cur.execute(
                "SELECT DISTINCT ON (pl_name) pl_name, tic_id, hostname, period_days "
                "FROM raw_ps WHERE ingest_run_id = %s AND pl_name IS NOT NULL "
                "ORDER BY pl_name, default_flag DESC NULLS LAST, (period_days IS NULL)",
                (runs["raw_ps"],),
            )
            for pl_name, tic, hostname, period in cur.fetchall():
                star = (tic_to_star.get(int(tic)) if tic is not None else None) \
                    or host_to_star.get(hostname)
                add(star, "name", pl_name, "nea", period, planet_name=pl_name)
        if runs["raw_pscomppars"]:
            cur.execute("SELECT pl_name, tic_id, hostname, period_days FROM raw_pscomppars "
                        "WHERE ingest_run_id = %s AND pl_name IS NOT NULL",
                        (runs["raw_pscomppars"],))
            for pl_name, tic, hostname, period in cur.fetchall():
                star = (tic_to_star.get(int(tic)) if tic is not None else None) \
                    or host_to_star.get(hostname)
                add(star, "name", pl_name, "nea", period, planet_name=pl_name)
    return obs


def _cluster_star(observations: list[dict]):
    """Cluster one star's observations into candidates by designation + period.

    Returns (clusters, ambiguous). Each cluster: {"groups": {(id_type,value): group}, "period",
    "join_rule"}. `ambiguous` lists (designation, [competing cluster indices]) — periods that
    matched more than one existing cluster and were therefore NOT merged.
    """
    # Collapse identical designations first (same TOI number seen by ExoFOP and the Archive).
    groups: dict[tuple, dict] = {}
    for o in observations:
        key = (o["id_type"], o["value"])
        g = groups.setdefault(
            key, {"id_type": o["id_type"], "value": o["value"], "period": None,
                  "xsources": set(), "planet_name": None}
        )
        g["xsources"].add(o["xsource"])
        if g["period"] is None and o["period"] is not None:
            g["period"] = o["period"]
        if g["planet_name"] is None and o["planet_name"]:
            g["planet_name"] = o["planet_name"]

    clusters: list[dict] = []
    ambiguous: list[tuple] = []
    for key in sorted(groups, key=lambda k: (k[0], str(k[1]))):
        g = groups[key]
        hits = [i for i, c in enumerate(clusters) if periods_match(c["period"], g["period"])]
        if len(hits) == 1:
            c = clusters[hits[0]]
            c["groups"][key] = g
            c.setdefault("join_rule", {})[key] = "period_match<1pct"
            if c["period"] is None:
                c["period"] = g["period"]
        else:
            if len(hits) > 1:
                ambiguous.append((g, [clusters[i]["seed_key"] for i in hits]))
            clusters.append({
                "groups": {key: g}, "period": g["period"], "seed_key": key,
                "join_rule": {key: "candidate_seed"},
            })
    return clusters, ambiguous


def _build_candidates(conn, runs: dict) -> dict:
    tic_to_star, kic_to_star, host_to_star = _entity_maps(conn)
    obs = _gather_observations(conn, runs, tic_to_star, kic_to_star, host_to_star)
    stats = {"candidates": 0, "ambiguous_period_candidates": 0}
    links: dict[tuple, tuple] = {}  # (candidate_id,id_type,id_value,source) -> (conf, rule)

    with conn.cursor() as cur:
        for star_id in sorted(obs):
            clusters, ambiguous = _cluster_star(obs[star_id])
            for c in clusters:
                names = {"fallback": f"star {star_id}"}
                for (id_type, value), g in c["groups"].items():
                    if id_type == "name":
                        names["planet"] = value
                    else:
                        names[id_type] = value
                    if g["planet_name"]:
                        names["planet"] = g["planet_name"]
                cur.execute(
                    "INSERT INTO candidate (star_id, canonical_name) VALUES (%s, %s) "
                    "RETURNING candidate_id",
                    (star_id, canonical_candidate_name(names)),
                )
                cand_id = cur.fetchone()[0]
                stats["candidates"] += 1
                for key, g in c["groups"].items():
                    rule = c["join_rule"][key]
                    for xsource in sorted(g["xsources"]):
                        links[(cand_id, g["id_type"], g["value"], xsource)] = (1.00, rule)
                    if g["planet_name"] and g["id_type"] != "name":
                        links[(cand_id, "name", g["planet_name"], "nea")] = (1.00, rule)
            for g, competing in ambiguous:
                stats["ambiguous_period_candidates"] += 1
                merge.log_ambiguous(
                    conn, "candidate", star_id, "period_ambiguous",
                    {"designation": f"{g['id_type']}:{g['value']}", "period_days": g["period"],
                     "competing_seed_designations": [f"{t}:{v}" for t, v in competing]},
                )
    _flush_candidate_links(conn, links)
    return stats


def _flush_candidate_links(conn, links: dict) -> None:
    if not links:
        return
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TEMP TABLE _cand_links (candidate_id BIGINT, id_type TEXT, id_value TEXT, "
            "source TEXT, confidence NUMERIC, rule TEXT) ON COMMIT DROP"
        )
        with cur.copy(
            "COPY _cand_links (candidate_id, id_type, id_value, source, confidence, rule) "
            "FROM STDIN"
        ) as cp:
            for (cand_id, id_type, id_value, source), (conf, rule) in links.items():
                cp.write_row((cand_id, id_type, id_value, source, conf, rule))
        cur.execute(
            """
            WITH ins AS (
                INSERT INTO entity_identifier (candidate_id, id_type, id_value, source, confidence)
                SELECT candidate_id, id_type, id_value, source, confidence FROM _cand_links
                ON CONFLICT DO NOTHING
                RETURNING candidate_id, id_type, id_value, source
            )
            INSERT INTO merge_log (entity_type, surviving_id, merged_id, rule_fired, score, details)
            SELECT 'candidate', l.candidate_id, l.candidate_id, l.rule, 1.000,
                   jsonb_build_object('id_type', l.id_type, 'id_value', l.id_value,
                                      'source', l.source)
            FROM _cand_links l
            JOIN ins ON ins.candidate_id = l.candidate_id AND ins.id_type = l.id_type
                    AND ins.id_value = l.id_value AND ins.source = l.source
            """
        )
        cur.execute("DROP TABLE _cand_links")


def build(conn, tol_arcsec: float = COORD_TOL_ARCSEC) -> dict:
    """Full ER build (stars -> KOI coord match -> candidates). Returns pass stats. No commit."""
    runs = _runs(conn)
    _reset(conn)
    _build_tic_stars(conn, runs)
    _build_hostname_stars(conn, runs)
    koi_stats = _coord_match_koi(conn, runs, tol_arcsec)
    cand_stats = _build_candidates(conn, runs)
    return {**koi_stats, **cand_stats}


# Jsonb re-exported for callers/tests that build detail payloads.
__all__ = ["build", "Jsonb"]
