"""Deterministic target selection from the Wave 1 identity graph (SPEC Wave 2 §1).

Three cohorts, all chosen by pure SQL against the graph so the slice is reproducible and
documented:

  GOLD PLANETS (~20)  - TOIs with an authoritative TFOPWG disposition of CP (Confirmed Planet) or
                        KP (Known Planet). Stratified across depth x period (deep/shallow,
                        short/long) so the recovery test spans the parameter space; brightest star
                        first within each stratum (best photometry -> a fair test of the pipeline).
  GOLD FALSE POS (~20) - TOIs disposed FP / FA (eclipsing binaries, blends, non-astrophysical).
                        Same depth x period stratification. These have real transit-like signals
                        the pipeline SHOULD recover; the point is that they are not planets.
  DISCOVERY (~15-20)  - the pipelines' documented blind spot (research §4): single-transit TOIs
                        (period unknown / NULL) and long-period (P >= 30 d) PC/APC candidates.
                        No answer key by construction for the single-transit ones — we flag
                        signals worth a dossier, we do not claim planets.

The known catalog ephemeris (period, epoch, depth, duration) is carried onto each `target` row from
the ExoFOP TOI list (the live TFOPWG source) as the recovery answer key. Epoch is stored as the
catalog's full BJD; the pipeline converts to BTJD (BJD - 2457000) when grading against TESS time.

Idempotent: re-running upserts by candidate_id (stable target_id, so downstream pipeline_run rows
survive) and deletes any target no longer selected. The graph is static, so a re-run is a no-op.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn

logger = logging.getLogger(__name__)

# Stratification thresholds (documented, deterministic).
DEEP_PPM = 3000.0        # >= 3000 ppm transit = "deep"
LONG_P_DAYS = 10.0       # >= 10 d = "long" (within the gold set)
DISCOVERY_LONG_P = 30.0  # >= 30 d = long-period discovery target (multi-sector stitch territory)
PER_STRATUM_GOLD = 5     # 4 strata x 5 = ~20 per gold cohort
N_SINGLE_TRANSIT = 8
N_LONG_PERIOD = 10

# One row per TOI candidate that has a TIC (needed for MAST) and its ExoFOP TOI ephemeris.
# DISTINCT ON collapses the two identifier rows (exofop + nea both assert the same TOI number).
_BASE_POOL = """
    WITH pool AS (
        SELECT DISTINCT ON (c.candidate_id)
            c.candidate_id,
            s.tic_id,
            ei.id_value                       AS toi,
            c.disposition                     AS canonical_disp,
            r.tfopwg_disposition              AS tfopwg_disp,
            r.period_days, r.epoch_bjd, r.depth_ppm, r.duration_hr, r.tmag
        FROM candidate c
        JOIN star s              ON s.star_id = c.star_id AND s.tic_id IS NOT NULL
        JOIN entity_identifier ei ON ei.candidate_id = c.candidate_id AND ei.id_type = 'toi'
        JOIN raw_exofop_toi r    ON r.toi = ei.id_value
        ORDER BY c.candidate_id, r.raw_id
    )
"""

# Gold cohorts: stratify depth x period, rank brightest-first within stratum, take N per stratum.
_GOLD_SQL = _BASE_POOL + """
    , stratified AS (
        SELECT *,
            CASE
                WHEN depth_ppm >= %(deep)s AND period_days <  %(longp)s THEN 'deep_short'
                WHEN depth_ppm >= %(deep)s AND period_days >= %(longp)s THEN 'deep_long'
                WHEN period_days <  %(longp)s                           THEN 'shallow_short'
                ELSE 'shallow_long'
            END AS stratum
        FROM pool
        WHERE tfopwg_disp = ANY(%(disps)s)
          AND period_days IS NOT NULL AND period_days > 0
          AND epoch_bjd  IS NOT NULL
          AND depth_ppm  IS NOT NULL
          AND tmag       IS NOT NULL
    ), ranked AS (
        SELECT *, row_number() OVER (
            PARTITION BY stratum ORDER BY tmag ASC, tic_id ASC, toi ASC
        ) AS rn
        FROM stratified
    )
    SELECT candidate_id, tic_id, toi, canonical_disp, tfopwg_disp, stratum,
           period_days, epoch_bjd, depth_ppm, duration_hr, tmag
    FROM ranked WHERE rn <= %(per_stratum)s
    ORDER BY stratum, rn
"""

# Discovery — single transit: period unknown (NULL / 0). We still know the epoch (T0) of the one
# observed event, so the single-event lens has something to localize. Brightest-first.
_DISCOVERY_SINGLE_SQL = _BASE_POOL + """
    SELECT candidate_id, tic_id, toi, canonical_disp, tfopwg_disp,
           'single_transit'::text AS stratum,
           period_days, epoch_bjd, depth_ppm, duration_hr, tmag
    FROM pool
    WHERE tfopwg_disp = ANY(%(disps)s)
      AND (period_days IS NULL OR period_days = 0)
      AND epoch_bjd IS NOT NULL AND tmag IS NOT NULL
      AND tic_id <> ALL(%(exclude)s)
    ORDER BY tmag ASC, tic_id ASC, toi ASC
    LIMIT %(limit)s
"""

# Discovery — long period: P >= 30 d PC/APC. The blind spot where multi-sector stitching pays.
_DISCOVERY_LONG_SQL = _BASE_POOL + """
    SELECT candidate_id, tic_id, toi, canonical_disp, tfopwg_disp,
           'long_period'::text AS stratum,
           period_days, epoch_bjd, depth_ppm, duration_hr, tmag
    FROM pool
    WHERE tfopwg_disp = ANY(%(disps)s)
      AND period_days >= %(longp)s
      AND epoch_bjd IS NOT NULL AND tmag IS NOT NULL
      AND tic_id <> ALL(%(exclude)s)
    ORDER BY tmag ASC, tic_id ASC, toi ASC
    LIMIT %(limit)s
"""

_COLS = ("candidate_id", "tic_id", "toi", "canonical_disp", "tfopwg_disp", "stratum",
         "period_days", "epoch_bjd", "depth_ppm", "duration_hr", "tmag")


def _rows(cur, sql, params) -> list[dict]:
    cur.execute(sql, params)
    return [dict(zip(_COLS, row, strict=True)) for row in cur.fetchall()]


def select_targets(conn) -> list[dict]:
    """Run the deterministic selection SQL. Returns the ordered target rows (gold first, then
    discovery), each tagged with cohort + stratum + a human-readable select_rule."""
    with conn.cursor() as cur:
        planets = _rows(cur, _GOLD_SQL, {
            "disps": ["CP", "KP"], "deep": DEEP_PPM, "longp": LONG_P_DAYS,
            "per_stratum": PER_STRATUM_GOLD,
        })
        fps = _rows(cur, _GOLD_SQL, {
            "disps": ["FP", "FA"], "deep": DEEP_PPM, "longp": LONG_P_DAYS,
            "per_stratum": PER_STRATUM_GOLD,
        })
        gold_tics = sorted({r["tic_id"] for r in planets} | {r["tic_id"] for r in fps})
        singles = _rows(cur, _DISCOVERY_SINGLE_SQL, {
            "disps": ["PC", "APC"], "exclude": gold_tics, "limit": N_SINGLE_TRANSIT,
        })
        used = gold_tics + sorted({r["tic_id"] for r in singles})
        longs = _rows(cur, _DISCOVERY_LONG_SQL, {
            "disps": ["PC", "APC"], "longp": DISCOVERY_LONG_P, "exclude": used,
            "limit": N_LONG_PERIOD,
        })

    out: list[dict] = []
    for r in planets:
        out.append({**r, "cohort": "gold_planet",
                    "select_rule": f"TFOPWG {r['tfopwg_disp']}; stratum {r['stratum']}; "
                                   "brightest-first"})
    for r in fps:
        out.append({**r, "cohort": "gold_fp",
                    "select_rule": f"TFOPWG {r['tfopwg_disp']}; stratum {r['stratum']}; "
                                   "brightest-first"})
    for r in singles:
        out.append({**r, "cohort": "discovery",
                    "select_rule": f"TFOPWG {r['tfopwg_disp']}; single-transit (period unknown); "
                                   "brightest-first"})
    for r in longs:
        out.append({**r, "cohort": "discovery",
                    "select_rule": f"TFOPWG {r['tfopwg_disp']}; P>={DISCOVERY_LONG_P:g}d; "
                                   "brightest-first"})
    return out


def persist(conn, selection: list[dict]) -> None:
    """Upsert the selection into `target` (stable target_id per candidate) and delete any target no
    longer selected. Committed by the caller / here."""
    with conn.cursor() as cur:
        for r in selection:
            cur.execute(
                """
                INSERT INTO target (candidate_id, tic_id, toi, cohort, stratum, tfopwg_disp,
                    canonical_disp, known_period_days, known_epoch_bjd, known_depth_ppm,
                    known_duration_hr, tmag, select_rule)
                VALUES (%(candidate_id)s, %(tic_id)s, %(toi)s, %(cohort)s, %(stratum)s,
                    %(tfopwg_disp)s, %(canonical_disp)s, %(period_days)s, %(epoch_bjd)s,
                    %(depth_ppm)s, %(duration_hr)s, %(tmag)s, %(select_rule)s)
                ON CONFLICT (candidate_id) DO UPDATE SET
                    tic_id = EXCLUDED.tic_id, toi = EXCLUDED.toi, cohort = EXCLUDED.cohort,
                    stratum = EXCLUDED.stratum, tfopwg_disp = EXCLUDED.tfopwg_disp,
                    canonical_disp = EXCLUDED.canonical_disp,
                    known_period_days = EXCLUDED.known_period_days,
                    known_epoch_bjd = EXCLUDED.known_epoch_bjd,
                    known_depth_ppm = EXCLUDED.known_depth_ppm,
                    known_duration_hr = EXCLUDED.known_duration_hr,
                    tmag = EXCLUDED.tmag, select_rule = EXCLUDED.select_rule
                """,
                r,
            )
        keep = [r["candidate_id"] for r in selection]
        cur.execute("DELETE FROM target WHERE candidate_id <> ALL(%s)", (keep,))
    conn.commit()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Select the Wave 2 target slice (deterministic).")
    parser.add_argument("--dry-run", action="store_true", help="print selection, do not persist")
    args = parser.parse_args()

    conn = get_conn()
    try:
        selection = select_targets(conn)
        if not args.dry_run:
            persist(conn, selection)
    finally:
        conn.close()

    by_cohort: dict[str, int] = {}
    for r in selection:
        by_cohort[r["cohort"]] = by_cohort.get(r["cohort"], 0) + 1
    print(f"\n=== target selection ({'DRY RUN' if args.dry_run else 'persisted'}) ===")
    for cohort, n in sorted(by_cohort.items()):
        print(f"  {cohort:14s} {n}")
    n_tic = len({r["tic_id"] for r in selection})
    print(f"  {'TOTAL':14s} {len(selection)}  (distinct TIC: {n_tic})")
    for r in selection:
        p = r["period_days"]
        pstr = f"{float(p):8.3f}d" if p else "  single "
        print(f"  {r['cohort']:12s} {r['stratum']:14s} TIC {r['tic_id']:<11} TOI {r['toi']:<9} "
              f"{r['tfopwg_disp']:3s} P={pstr} Tmag={float(r['tmag']):.2f}")


if __name__ == "__main__":
    main()
