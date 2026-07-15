"""Per-target light-curve processing (SPEC Wave 2 §3): load all sectors -> per-sector normalise ->
stitch -> transit-safe detrend -> BLS + TLS period search (+ a single-event lens for the discovery
slice) -> persist to pipeline_run + detection, provenance-linked to the target and the MAST ledger.

Detrending choice (documented): each sector is normalised (divide by its median) then the stitched
series is flattened with lightkurve's Savitzky-Golay `flatten` at a ~0.75-day window, with a
`break_tolerance` respecting inter-sector gaps. 0.75 d >> any TESS transit (hours), so it removes
stellar/instrumental trends WITHOUT eating transits (transit-safe). Cadences flagged by the
SPOC/QLP quality bitmask are dropped first. The detrended series is then binned to ~10 min —
lossless for hours-long transits — which is what makes the baseline-aware BLS grid affordable.

Runtime discipline (SPEC): period search is bounded to [0.6 d, min(baseline/2, 50 d)] (>=2 transits
needed for a periodic detection anyway). BLS runs on the full stitched baseline with a
baseline-aware LOG period grid (fine enough that a short period does not smear over a multi-year
span — the inherited grid bug). TLS's Ofir-optimal grid instead scales with baseline and is
infeasible over the multi-year stitched span, so it runs as an independent cross-check on the
longest single segment (~27 d) under a 150 s wall-clock timeout in the .venv-tls worker — an
overrun/skip is recorded, never hidden. Every non-ok outcome writes WHY into pipeline_run.notes
(no silent failures).

Honest framing: we recover/flag signals and report metrics; we never assert a planet.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import pathlib
import subprocess
import sys
import time as _time
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn
from pipeline import detect

logger = logging.getLogger(__name__)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

PERIOD_MIN = 0.6
PERIOD_MAX_CAP = 50.0     # bounded periodic search; P>50 d is the pipelines' blind spot (report)
DETREND_WINDOW_DAYS = 0.75
BIN_MINUTES = 10          # bin the detrended series to ~10 min: lossless for hours-long transits,
                          # and what makes a baseline-aware fine period grid affordable (grid fix)
TLS_SEGMENT_GAP_DAYS = 10.0  # split the stitched series at gaps > this to pick TLS's single sector
TLS_TIMEOUT_S = 150       # SPEC: ~5-min cap; a TLS overrun is recorded as status='timeout'
TLS_OVERSAMPLING = 2
DATA_VINTAGE = dt.date.today().isoformat()


def _git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:  # noqa: BLE001
        return None


def _lazy():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import lightkurve as lk
        import numpy as np
        import pandas as pd
    return lk, np, pd


def _targets(conn, only_tic=None, cohort=None):
    q = ("SELECT target_id, candidate_id, tic_id, toi, cohort, known_period_days, known_epoch_bjd "
         "FROM target")
    conds, params = [], []
    if only_tic:
        conds.append("tic_id = %s")
        params.append(only_tic)
    if cohort:
        conds.append("cohort = %s")
        params.append(cohort)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY cohort, tic_id, toi"
    with conn.cursor() as cur:
        cur.execute(q, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _bin_series(t, f, np, bin_minutes=BIN_MINUTES):
    """Bin (time, flux) into fixed bin_minutes bins by unweighted mean, keeping only OCCUPIED bins
    (so multi-year inter-sector gaps cost nothing). Lossless for a transit search — a transit lasts
    hours, so 10-min bins preserve its shape — while cutting 2-min short-cadence ~5x, which is what
    lets the baseline-aware BLS grid (and TLS) run in budget on a stitched multi-sector series."""
    if t.size == 0:
        return t, f
    bs = bin_minutes / 1440.0
    idx = np.floor((t - t.min()) / bs).astype(np.int64)
    order = np.argsort(idx, kind="stable")
    idx, ts, fs = idx[order], t[order], f[order]
    _, start = np.unique(idx, return_index=True)
    counts = np.add.reduceat(np.ones_like(ts), start)
    tb = np.add.reduceat(ts, start) / counts
    fb = np.add.reduceat(fs, start) / counts
    good = np.isfinite(tb) & np.isfinite(fb)
    return tb[good], fb[good]


def _largest_segment(t, f, gap_days=TLS_SEGMENT_GAP_DAYS):
    """Return the longest-baseline contiguous chunk of (t, f), split at time gaps > gap_days. Used
    to hand TLS a single-sector-scale baseline its per-baseline grid can search within budget."""
    import numpy as np
    if t.size == 0:
        return t, f
    order = np.argsort(t, kind="stable")
    t, f = t[order], f[order]
    brk = np.where(np.diff(t) > gap_days)[0] + 1
    segs = np.split(np.arange(t.size), brk)
    best = max(segs, key=lambda s: (t[s[-1]] - t[s[0]]) if s.size else 0.0)
    return t[best], f[best]


def _load_stitched(conn, tic, lk, np, pd):
    """Load every sector Parquet for a TIC, per-sector normalise, stitch, and transit-safe flatten.
    Returns (time, flux, meta) or (None, None, reason)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT path, sector, cadence_s FROM lightcurve_file WHERE tic_id = %s"
            " ORDER BY t_start",
            (tic,),
        )
        rows = cur.fetchall()
    if not rows:
        return None, None, "no light-curve files"

    lcs, cadences = [], []
    for rel, _sector, cadence in rows:
        df = pd.read_parquet(REPO_ROOT / rel)
        q = df["quality"].to_numpy() if "quality" in df else np.zeros(len(df))
        good = (q == 0) & np.isfinite(df["flux"].to_numpy())
        if good.sum() < 50:
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lc = lk.LightCurve(time=df["time"].to_numpy()[good],
                               flux=df["flux"].to_numpy()[good]).normalize()
        lcs.append(lc)
        cadences.append(cadence or 120)
    if not lcs:
        return None, None, "all sectors empty after quality mask"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stitched = lk.LightCurveCollection(lcs).stitch() if len(lcs) > 1 else lcs[0]
        med_cadence_s = float(np.median(cadences))
        window = int(round(DETREND_WINDOW_DAYS * 86400.0 / med_cadence_s))
        window = max(101, window | 1)  # odd, >= 101 cadences
        flat = stitched.flatten(window_length=window, break_tolerance=5, polyorder=2)
        t = np.asarray(flat.time.value, dtype="float64")
        f = np.asarray(flat.flux.value, dtype="float64")
    keep = np.isfinite(t) & np.isfinite(f)
    t, f = t[keep], f[keep]
    n_raw = int(t.size)
    t, f = _bin_series(t, f, np)
    meta = {"n_sectors": len(lcs), "n_points": int(t.size), "n_points_raw": n_raw,
            "baseline_days": float(t.max() - t.min()) if t.size else 0.0,
            "detrend": {"method": "lightkurve.flatten(savgol)",
                        "window_length_cadences": window,
                        "window_days": DETREND_WINDOW_DAYS, "polyorder": 2,
                        "break_tolerance": 5, "per_sector_normalize": True,
                        "bin_minutes": BIN_MINUTES, "n_points_raw": n_raw}}
    return t, f, meta


def _insert_detection(cur, run_id, tic, det, rank):
    cur.execute(
        """INSERT INTO detection (pipeline_run_id, tic_id, method, rank, period_days, epoch_bjd,
               depth_ppm, duration_hr, snr, sde, power, metrics)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (run_id, tic, det["method"], rank, det.get("period_days"), det.get("epoch_bjd"),
         det.get("depth_ppm"), det.get("duration_hr"), det.get("snr"), det.get("sde"),
         det.get("power"), _Json(det.get("metrics", {}))),
    )


def process_target(conn, tgt, lk, np, pd) -> dict:
    tic = tgt["tic_id"]
    started = _time.time()
    t0 = dt.datetime.now(dt.UTC)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_run (target_id, tic_id, status, data_vintage, git_sha,"
            " started_at) VALUES (%s,%s,'running',%s,%s,%s) RETURNING pipeline_run_id",
            (tgt["target_id"], tic, DATA_VINTAGE, _git_sha(), t0),
        )
        run_id = cur.fetchone()[0]
    conn.commit()

    try:
        t, f, meta = _load_stitched(conn, tic, lk, np, pd)
        if t is None:
            _finish(conn, run_id, "no_data", None, _time.time() - started, notes=meta)
            return {"tic": tic, "status": "no_data"}

        period_max = min(max(meta["baseline_days"] / 2.0, 1.0), PERIOD_MAX_CAP)
        detections: list[tuple[dict, int]] = []

        bls1 = detect.bls_search(t, f, PERIOD_MIN, period_max)
        detections.append((bls1, 1))
        # Second BLS pass (mask the first signal) — recovers the 2nd planet in multi-planet systems.
        # Skipped when the grid hit its cap (extreme baseline): a 2nd full pass there would blow the
        # per-target budget for a marginal multi-planet nicety.
        keep = detect.mask_transits(
            t, f, bls1["period_days"], bls1["epoch_bjd"], bls1["duration_hr"])
        if keep.sum() > 100 and not bls1["metrics"].get("grid_capped"):
            bls2 = detect.bls_search(t[keep], f[keep], PERIOD_MIN, period_max)
            detections.append((bls2, 2))

        # TLS cross-check on the BEST SINGLE SECTOR. TLS's Ofir-optimal period grid scales with the
        # baseline; over the multi-year stitched span that dominates this TESS cohort it needs
        # ~1e6+ trial periods and cannot finish in the per-target budget on a laptop (verified:
        # >200 s even binned). Run on the longest contiguous segment instead — a bounded ~27 d
        # baseline where TLS's limb-darkened template is a genuine, fast (~30 s) independent check
        # of BLS. Documented as such in the recovery report; BLS carries the full-baseline recovery.
        ts, fs = _largest_segment(t, f)
        seg_base = float(ts.max() - ts.min()) if ts.size else 0.0
        if ts.size >= 200 and seg_base >= 2.0:
            tls_pmax = min(max(seg_base / 2.0, 1.0), PERIOD_MAX_CAP)
            tls = detect.run_tls(ts, fs, PERIOD_MIN, tls_pmax, oversampling=TLS_OVERSAMPLING,
                                 timeout_s=TLS_TIMEOUT_S)
            if isinstance(tls.get("metrics"), dict):
                tls["metrics"].update({"scope": "best_single_segment",
                                       "segment_baseline_days": seg_base,
                                       "segment_points": ts.size})
        else:
            tls = {"status": "skipped",
                   "reason": f"best segment too short ({ts.size} pts, {seg_base:.1f} d)"}
        tls_note = None
        if tls.get("status") == "ok":
            detections.append((tls, 1))
        else:
            tls_note = f"TLS {tls.get('status')}: {tls.get('reason')}"

        if tgt["cohort"] == "discovery":
            se = detect.single_event_scan(t, f)
            if se.get("status") in ("ok", "no_event"):
                detections.append((se, 1))

        with conn.cursor() as cur:
            for det, rank in detections:
                _insert_detection(cur, run_id, tic, det, rank)
        notes = meta["detrend"].copy()
        if tls_note:
            notes["tls"] = tls_note
        _finish(conn, run_id, "ok", meta, _time.time() - started, notes=notes)
        logger.info("TIC %s (%s): ok  BLS P=%.4f SNR=%.1f | TLS %s  [%.0fs]",
                    tic, tgt["toi"], bls1["period_days"], bls1["snr"],
                    tls.get("status"), _time.time() - started)
        return {"tic": tic, "status": "ok", "runtime_s": _time.time() - started}
    except Exception as exc:  # noqa: BLE001 - a target that fails records WHY, never aborts the run
        conn.rollback()
        _finish(conn, run_id, "error", None, _time.time() - started,
                notes={"error": f"{type(exc).__name__}: {exc}"[:1500]})
        logger.warning("TIC %s failed: %s", tic, exc)
        return {"tic": tic, "status": "error", "error": str(exc)}


def _finish(conn, run_id, status, meta, runtime_s, notes):
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE pipeline_run SET status=%s, n_sectors=%s, n_points=%s, baseline_days=%s,
                   detrend=%s, runtime_s=%s, notes=%s, finished_at=now()
               WHERE pipeline_run_id=%s""",
            (status, (meta or {}).get("n_sectors"), (meta or {}).get("n_points"),
             (meta or {}).get("baseline_days"), _Json((meta or {}).get("detrend")), runtime_s,
             _json_or_text(notes), run_id),
        )
    conn.commit()


def _Json(obj):
    from psycopg.types.json import Jsonb
    return Jsonb(obj) if obj is not None else None


def _json_or_text(notes):
    if notes is None or isinstance(notes, str):
        return notes
    import json
    return json.dumps(notes)[:4000]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Process the selected targets (BLS + TLS + lens).")
    parser.add_argument("--tic", type=int, default=None, help="process a single TIC")
    parser.add_argument("--cohort", default=None, help="restrict to one cohort")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    lk, np, pd = _lazy()
    conn = get_conn()
    try:
        targets = _targets(conn, only_tic=args.tic, cohort=args.cohort)
        if args.limit:
            targets = targets[: args.limit]
        results = [process_target(conn, tgt, lk, np, pd) for tgt in targets]
    finally:
        conn.close()

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n=== processed {len(results)} targets: {ok} ok, "
          f"{sum(1 for r in results if r['status'] != 'ok')} non-ok ===")
    for r in results:
        if r["status"] != "ok":
            print(f"  {r['status']:8s} TIC {r['tic']}: {r.get('error', '')}")


if __name__ == "__main__":
    main()
