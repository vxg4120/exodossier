"""GET /api/lightcurves/* -- the Wave 2 light-curve pipeline's transit-recovery results, read-only.

The pipeline (``pipeline/``: select_targets -> fetch_lightcurves -> process) runs offline. It picks
a deterministic slice of TOIs from the identity graph (gold planets, gold false positives and a
discovery slice of long-period / single-transit candidates), downloads their TESS light curves
from MAST, and searches each one for a periodic transit with BLS over the stitched baseline, with
TLS as a cross-check on the longest single segment, plus a single-event lens for the discovery
slice. It writes ``target``, ``pipeline_run`` and ``detection``. This router only reads them.

Every row is graded with the SAME rules as the committed recovery report
(``quality/recovery_report.py``): a recovery is a BLS/TLS period within 1% of the catalog period
or one of its harmonics at SNR >= 7. The grading is a measurement against the TFOPWG answer key;
nothing here confirms or rejects a planet.

The slice is small (tens of targets, a few detections each), so both endpoints read the latest
run per target and grade it in Python on every request; no cache is needed.

The tables can be empty: the nightly graph rebuild truncates ``candidate`` with CASCADE, which
empties ``target`` and, through it, ``pipeline_run``, ``detection`` and ``fp_scenario``. The
endpoints then answer with zero counts and ``state: "empty"`` rather than an error.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_db
from quality.recovery_report import (
    PERIOD_TOL,
    SNR_MIN,
    _analyze_miss,
    _best_recovery,
    epoch_phase_offset,
    match_period,
)

router = APIRouter(tags=["lightcurves"])

COHORTS: dict[str, dict[str, str]] = {
    "gold_planet": {
        "label": "Known planets",
        "description": "TOIs that TFOPWG lists as confirmed (CP) or known (KP) planets: the answer "
        "key the recovery is graded against.",
    },
    "gold_fp": {
        "label": "Known false positives",
        "description": "TOIs that TFOPWG lists as false positives (FP) or false alarms (FA). "
        "Finding a transit-like signal here is expected; recovery is not what rejects them.",
    },
    "discovery": {
        "label": "Discovery slice",
        "description": "Long-period (P >= 30 d) and single-transit planet candidates, the periodic "
        "search's blind spot. A signal here is worth a closer look, not a planet.",
    },
}

VERDICTS: dict[str, str] = {
    "recovered": "Recovered at the catalog period",
    "recovered_harmonic": "Recovered at a harmonic of the catalog period",
    "missed": "Not recovered",
    "signal_at_catalog_period": "Signal at the catalog period",
    "signal": "Signal, other period",
    "no_signal": "No signal above SNR 7",
    "below_threshold": "Below threshold",
    "not_processed": "Run did not finish",
    "running": "Run started, no result yet",
    "pending": "Not run yet",
}

SORTS = ("cohort", "toi", "snr", "period")


def _f(v: Any) -> float | None:
    return float(v) if v is not None else None


def _toi_key(toi: str | None) -> tuple:
    try:
        major, _, minor = (toi or "").partition(".")
        return (0, int(major), int(minor or 0))
    except ValueError:
        return (1, toi or "")


def _det_out(det: dict | None) -> dict[str, Any] | None:
    if det is None:
        return None
    return {
        "method": det["method"],
        "period_days": _f(det["period_days"]),
        "depth_ppm": _f(det["depth_ppm"]),
        "duration_hr": _f(det["duration_hr"]),
        "snr": _f(det["snr"]),
        "sde": _f(det["sde"]),
    }


def grade(target: dict, run: dict | None, dets: list[dict]) -> dict[str, Any]:
    """Grade one target's latest run with the recovery report's rules. Pure: takes the target row
    (answer key), the latest pipeline_run row (or None) and that run's detections."""
    out: dict[str, Any] = {
        "verdict": "pending",
        "match": None,
        "phase_offset": None,
        "reason": None,
        "best": None,
        "single_event": None,
    }
    if run is None:
        out["reason"] = "the pipeline has not processed this target"
        return out
    if run["status"] == "running":
        # process.py inserts the row as 'running' and updates it at the end; a row left that way
        # is either in progress or was interrupted. Either way there is no result to grade yet.
        out["verdict"] = "running"
        out["reason"] = "the run started but has not recorded a result"
        return out
    if run["status"] != "ok":
        out["verdict"] = "not_processed"
        out["reason"] = f"{run['status']}: {run.get('notes') or 'no notes recorded'}"[:300]
        return out

    known = _f(target["known_period_days"])
    periodic = [d for d in dets if d["method"] != "single_event"]
    strongest = max(periodic, key=lambda d: _f(d["snr"]) or 0, default=None)
    se = next((d for d in dets if d["method"] == "single_event"), None)
    out["single_event"] = _det_out(se)
    cohort = target["cohort"]

    if cohort == "gold_planet":
        det, h = _best_recovery(target, dets)
        if det is not None:
            out["verdict"] = "recovered" if abs(h - 1.0) < 1e-6 else "recovered_harmonic"
            out["match"] = h
            out["best"] = _det_out(det)
            out["phase_offset"] = epoch_phase_offset(
                _f(det["epoch_bjd"]), _f(target["known_epoch_bjd"]), known
            )
        else:
            out["verdict"] = "missed"
            out["best"] = _det_out(strongest)
            out["reason"] = _analyze_miss(target, dets)
        return out

    out["best"] = _det_out(strongest)
    strong = strongest is not None and (_f(strongest["snr"]) or 0) >= SNR_MIN
    if cohort == "gold_fp":
        h = match_period(_f(strongest["period_days"]), known) if strongest else None
        out["match"] = h
        out["verdict"] = (
            "signal_at_catalog_period" if h else ("signal" if strong else "no_signal")
        )
        return out

    # discovery: a signal worth a dossier = periodic OR single-event SNR at or above the threshold
    se_strong = se is not None and (_f(se["snr"]) or 0) >= SNR_MIN
    out["verdict"] = "signal" if (strong or se_strong) else "below_threshold"
    return out


def _load(db: psycopg.Connection, cohort: str | None = None) -> list[dict[str, Any]]:
    """Every selected target joined to its candidate/host, its latest run and that run's
    detections, graded. Ordered by cohort then TOI."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT t.target_id, t.candidate_id, t.tic_id, t.toi, t.cohort, t.stratum,
                   t.tfopwg_disp, t.canonical_disp, t.known_period_days, t.known_epoch_bjd,
                   t.known_depth_ppm, t.known_duration_hr, t.tmag,
                   c.canonical_name AS name, s.canonical_name AS host,
                   r.pipeline_run_id, r.status, r.n_sectors, r.baseline_days, r.runtime_s,
                   r.data_vintage, r.git_sha, r.notes, r.finished_at
            FROM target t
            JOIN candidate c ON c.candidate_id = t.candidate_id
            JOIN star s ON s.star_id = c.star_id
            LEFT JOIN LATERAL (
                SELECT * FROM pipeline_run pr WHERE pr.target_id = t.target_id
                ORDER BY pr.pipeline_run_id DESC LIMIT 1
            ) r ON true
            WHERE %(cohort)s::text IS NULL OR t.cohort = %(cohort)s
            """,
            {"cohort": cohort},
        )
        targets = cur.fetchall()
        run_ids = [t["pipeline_run_id"] for t in targets if t["pipeline_run_id"] is not None]
        dets: dict[int, list[dict]] = {}
        if run_ids:
            cur.execute(
                """SELECT pipeline_run_id, method, rank, period_days, epoch_bjd, depth_ppm,
                          duration_hr, snr, sde
                   FROM detection WHERE pipeline_run_id = ANY(%s)
                   ORDER BY pipeline_run_id, method, rank""",
                (run_ids,),
            )
            for d in cur.fetchall():
                dets.setdefault(d["pipeline_run_id"], []).append(d)

    rows = []
    for t in targets:
        run = None
        if t["pipeline_run_id"] is not None:
            run = {k: t[k] for k in ("status", "notes")}
        g = grade(t, run, dets.get(t["pipeline_run_id"], []))
        rows.append(
            {
                "target_id": t["target_id"],
                "candidate_id": t["candidate_id"],
                "name": t["name"],
                "host": t["host"],
                "tic_id": str(t["tic_id"]),
                "toi": t["toi"],
                "cohort": t["cohort"],
                "stratum": t["stratum"],
                "tfopwg_disp": t["tfopwg_disp"],
                "canonical_disp": t["canonical_disp"],
                "known_period_days": _f(t["known_period_days"]),
                "known_depth_ppm": _f(t["known_depth_ppm"]),
                "tmag": _f(t["tmag"]),
                "run_status": t["status"],
                "n_sectors": t["n_sectors"],
                "baseline_days": _f(t["baseline_days"]),
                "runtime_s": _f(t["runtime_s"]),
                "data_vintage": t["data_vintage"].isoformat() if t["data_vintage"] else None,
                "finished_at": t["finished_at"].isoformat() if t["finished_at"] else None,
                **g,
            }
        )
    rows.sort(key=lambda r: (list(COHORTS).index(r["cohort"]) if r["cohort"] in COHORTS else 99,
                             _toi_key(r["toi"])))
    return rows


def lightcurve_summary(db: psycopg.Connection) -> dict[str, Any]:
    rows = _load(db)
    with db.cursor() as cur:
        cur.execute(
            """SELECT count(*) AS files, count(DISTINCT tic_id) AS stars,
                      max(created_at) AS last_fetch
               FROM lightcurve_file"""
        )
        lc = cur.fetchone()
        cur.execute(
            """SELECT max(finished_at) AS last_run, max(data_vintage) AS vintage,
                      count(*) AS attempts
               FROM pipeline_run"""
        )
        runs = cur.fetchone()

    def count(cohort: str, *verdicts: str) -> int:
        return sum(1 for r in rows if r["cohort"] == cohort and r["verdict"] in verdicts)

    by_cohort = {}
    for key, meta in COHORTS.items():
        sel = [r for r in rows if r["cohort"] == key]
        by_cohort[key] = {
            **meta,
            "targets": len(sel),
            "processed": sum(1 for r in sel if r["run_status"] == "ok"),
            "by_verdict": {
                v: n for v in VERDICTS if (n := sum(1 for r in sel if r["verdict"] == v))
            },
        }
    runtimes = sorted(r["runtime_s"] for r in rows if r["runtime_s"] is not None)
    processed = sum(1 for r in rows if r["run_status"] == "ok")
    return {
        "state": "ready" if processed else "empty",
        "targets": len(rows),
        "processed": processed,
        "not_processed": sum(1 for r in rows if r["verdict"] == "not_processed"),
        "pending": sum(1 for r in rows if r["verdict"] in ("pending", "running")),
        "gold_planets": {
            "targets": by_cohort["gold_planet"]["targets"],
            "recovered": count("gold_planet", "recovered", "recovered_harmonic"),
            "recovered_exact": count("gold_planet", "recovered"),
        },
        "gold_false_positives": {
            "targets": by_cohort["gold_fp"]["targets"],
            "with_signal": count("gold_fp", "signal", "signal_at_catalog_period"),
        },
        "discovery": {
            "targets": by_cohort["discovery"]["targets"],
            "with_signal": count("discovery", "signal"),
        },
        "by_cohort": by_cohort,
        "last_run_at": runs["last_run"].isoformat() if runs["last_run"] else None,
        "data_vintage": runs["vintage"].isoformat() if runs["vintage"] else None,
        "run_attempts": runs["attempts"],
        "median_runtime_s": runtimes[len(runtimes) // 2] if runtimes else None,
        "lightcurve_files": lc["files"],
        "lightcurve_stars": lc["stars"],
        "last_fetch_at": lc["last_fetch"].isoformat() if lc["last_fetch"] else None,
        "rules": {
            "period_tolerance": PERIOD_TOL,
            "snr_min": SNR_MIN,
            "statement": (
                f"A recovery is a BLS or TLS period within {PERIOD_TOL:.0%} of the catalog "
                f"period, or a harmonic of it, at SNR >= {SNR_MIN:g}."
            ),
        },
        "verdicts": VERDICTS,
    }


def _sort_rows(rows: list[dict], sort: str) -> list[dict]:
    if sort == "toi":
        return sorted(rows, key=lambda r: _toi_key(r["toi"]))
    if sort == "snr":
        return sorted(rows, key=lambda r: -((r["best"] or {}).get("snr") or 0))
    if sort == "period":
        return sorted(rows, key=lambda r: (r["known_period_days"] is None,
                                           r["known_period_days"] or 0))
    return rows  # cohort order, as loaded


@router.get("/lightcurves/summary")
def get_summary(db: Annotated[psycopg.Connection, Depends(get_db)]):
    """Counts for the light-curve pipeline: targets selected and processed, recoveries by cohort
    and verdict, the last run and the last MAST fetch."""
    return lightcurve_summary(db)


@router.get("/lightcurves/results")
def get_results(
    db: Annotated[psycopg.Connection, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[Literal["cohort", "toi", "snr", "period"], Query()] = "cohort",
    cohort: Annotated[str | None, Query(description="gold_planet | gold_fp | discovery")] = None,
):
    """One graded row per selected target, each deep-linking to /target/{candidate_id}."""
    if cohort is not None and cohort not in COHORTS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown cohort {cohort!r}; expected one of {list(COHORTS)}",
        )
    rows = _sort_rows(_load(db, cohort), sort)
    return {
        "rows": rows[offset : offset + limit],
        "total": len(rows),
        "limit": limit,
        "offset": offset,
        "sort": sort,
        "cohort": cohort,
    }


@router.get("/lightcurves/target/{candidate_id}")
def get_target_result(candidate_id: int, db: Annotated[psycopg.Connection, Depends(get_db)]):
    """The graded row for one candidate, or 404 when the pipeline's slice does not include it."""
    row = next((r for r in _load(db) if r["candidate_id"] == candidate_id), None)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"candidate {candidate_id} is not in the light-curve pipeline's target slice",
        )
    return row
