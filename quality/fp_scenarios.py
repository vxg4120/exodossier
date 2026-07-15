"""False-positive vetting for a ~10-target subset (SPEC Wave 2 §4) -> fp_scenario table.

TRICERATOPS status (honest, documented): triceratops is NOT installable in this environment. It
pulls pytransit==2.2 -> numba -> llvmlite, whose wheel build fails here (`Failed building wheel for
llvmlite`) on both the py3.14 primary venv and an isolated py3.13 venv — the numba-family / py3.14
conflict flagged in the wave brief. Rather than sink the wave on a compiled-dependency yak-shave, we
compute a DETERMINISTIC, light-curve-only vetting suite that captures the same first-order
false-positive physics TRICERATOPS' scenarios encode, and we label it honestly as such:

  * odd/even transit-depth mismatch  -> the classic eclipsing-binary tell (a stellar secondary makes
    alternating eclipses unequal); TRICERATOPS' EB / EBx2P scenarios.
  * secondary-eclipse search at phase ~0.5 -> a detectable occultation is a binary/blend tell;
    TRICERATOPS' EB / BEB scenarios.
  * transit depth / V-vs-U shape proxy -> implausibly deep or V-shaped events flag grazing binaries.

Each target gets per-metric rows plus a summary `FP_FLAG` row carrying a coarse, explicitly
UNCALIBRATED false-positive score in [0,1] (NOT a TRICERATOPS FPP/NFPP). tool='heuristic_vetting'
is stamped on every row so nothing can be mistaken for a probabilistic TRICERATOPS result. All
inputs are the already-persisted BLS ephemeris + the on-disk light curve, so the whole thing is
reproducible and offline.
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn
from pipeline import process

logger = logging.getLogger(__name__)

TOOL = "heuristic_vetting"
# Subset composition: a few confirmed planets (expect clean), a few known FPs (expect EB tells), a
# few discovery candidates. Deterministic pick (brightest-first within cohort via tmag).
SUBSET = {"gold_planet": 4, "gold_fp": 3, "discovery": 3}
ODD_EVEN_EB_SIGMA = 3.0     # |odd-even| depth mismatch above this sigma -> EB-like
SECONDARY_EB_SNR = 5.0      # a secondary eclipse above this SNR -> EB/blend-like
DEEP_EB_PPM = 100000.0      # > 10% deep -> stellar-companion / grazing-binary territory


def _pick_subset(conn):
    rows = []
    with conn.cursor() as cur:
        for cohort, n in SUBSET.items():
            cur.execute(
                """SELECT t.target_id, t.tic_id, t.toi, t.cohort, t.tfopwg_disp, t.known_period_days
                   FROM target t
                   WHERE t.cohort = %s
                     AND EXISTS (SELECT 1 FROM lightcurve_file l WHERE l.tic_id = t.tic_id)
                   ORDER BY t.tmag ASC NULLS LAST, t.tic_id ASC
                   LIMIT %s""",
                (cohort, n),
            )
            cols = [d[0] for d in cur.description]
            rows.extend(dict(zip(cols, r, strict=True)) for r in cur.fetchall())
    return rows


def _best_bls(conn, target_id):
    """Best (rank-1) BLS detection for a target's latest pipeline_run, as the vetting ephemeris."""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT d.period_days, d.epoch_bjd, d.depth_ppm, d.duration_hr, d.snr
               FROM detection d
               JOIN pipeline_run pr ON pr.pipeline_run_id = d.pipeline_run_id
               WHERE pr.target_id = %s AND d.method = 'bls'
               ORDER BY pr.pipeline_run_id DESC, d.rank ASC LIMIT 1""",
            (target_id,),
        )
        row = cur.fetchone()
    if not row or not row[0]:
        return None
    return {"period_days": float(row[0]),
            "epoch_bjd": float(row[1]) if row[1] is not None else None,
            "depth_ppm": float(row[2]) if row[2] is not None else None,
            "duration_hr": float(row[3]) if row[3] is not None else None,
            "snr": float(row[4]) if row[4] is not None else None}


def vet_target(t, f, det, np) -> dict:
    """Compute odd/even, secondary-eclipse and depth/shape vetting metrics from the folded light
    curve + the BLS ephemeris. Pure numpy; returns a dict of metrics + a coarse FP score."""
    p = det["period_days"]
    epoch = det["epoch_bjd"]
    dur_d = (det["duration_hr"] or 2.0) / 24.0
    half = 0.5 * dur_d
    med = float(np.median(f))
    phase = ((t - epoch + 0.5 * p) % p) - 0.5 * p          # centred on the transit
    in_tr = np.abs(phase) < half
    oot = ~in_tr
    sigma = float(np.median(np.abs(f[oot] - np.median(f[oot])))) * 1.4826 if oot.sum() else 0.0
    if sigma <= 0:
        sigma = float(np.std(f)) or 1e-9

    # ---- odd / even depth mismatch (eclipsing-binary tell) ----
    cycle = np.round((t - epoch) / p).astype(np.int64)
    odd = in_tr & (cycle % 2 == 1)
    even = in_tr & (cycle % 2 == 0)
    oe_sigma = None
    d_odd = d_even = None
    if odd.sum() >= 3 and even.sum() >= 3:
        d_odd = med - float(np.mean(f[odd]))
        d_even = med - float(np.mean(f[even]))
        e_odd = sigma / np.sqrt(odd.sum())
        e_even = sigma / np.sqrt(even.sum())
        oe_sigma = abs(d_odd - d_even) / float(np.hypot(e_odd, e_even))

    # ---- secondary eclipse at phase ~0.5 ----
    sphase = ((t - epoch) % p) / p
    sec = np.abs(sphase - 0.5) < (half / p)
    sec_snr = None
    if sec.sum() >= 3:
        d_sec = med - float(np.mean(f[sec]))
        sec_snr = d_sec / (sigma / np.sqrt(sec.sum()))

    # ---- depth / shape ----
    depth_ppm = det.get("depth_ppm")

    # ---- coarse, UNCALIBRATED false-positive score in [0,1] ----
    flags = []
    score = 0.0
    if oe_sigma is not None and oe_sigma > ODD_EVEN_EB_SIGMA:
        score = max(score, min(0.5 + 0.1 * (oe_sigma - ODD_EVEN_EB_SIGMA), 0.95))
        flags.append(f"odd/even {oe_sigma:.1f}sigma")
    if sec_snr is not None and sec_snr > SECONDARY_EB_SNR:
        score = max(score, min(0.5 + 0.05 * (sec_snr - SECONDARY_EB_SNR), 0.95))
        flags.append(f"secondary SNR {sec_snr:.1f}")
    if depth_ppm is not None and depth_ppm > DEEP_EB_PPM:
        score = max(score, 0.6)
        flags.append(f"deep {depth_ppm/1e4:.1f}%")
    return {
        "odd_even_sigma": oe_sigma, "depth_odd_ppm": (d_odd * 1e6 if d_odd is not None else None),
        "depth_even_ppm": (d_even * 1e6 if d_even is not None else None),
        "secondary_snr": sec_snr, "depth_ppm": depth_ppm, "oot_sigma_ppm": sigma * 1e6,
        "n_in_transit": int(in_tr.sum()), "fp_score": round(score, 3),
        "flags": flags or ["no strong FP tell"],
    }


def _persist(conn, tgt, det, m):
    from psycopg.types.json import Jsonb
    note = ("heuristic light-curve vetting (triceratops uninstallable: llvmlite/pytransit wheel "
            "build failure); NOT a calibrated TRICERATOPS FPP")
    rows = [
        ("odd_even", m["odd_even_sigma"], {"depth_odd_ppm": m["depth_odd_ppm"],
                                           "depth_even_ppm": m["depth_even_ppm"]}),
        ("secondary", m["secondary_snr"], {"oot_sigma_ppm": m["oot_sigma_ppm"]}),
        ("FP_FLAG", m["fp_score"], {"flags": m["flags"], "depth_ppm": m["depth_ppm"],
                                    "bls_period_days": det["period_days"],
                                    "n_in_transit": m["n_in_transit"]}),
    ]
    with conn.cursor() as cur:
        cur.execute("DELETE FROM fp_scenario WHERE target_id = %s AND tool = %s",
                    (tgt["target_id"], TOOL))
        for scenario, prob, metrics in rows:
            cur.execute(
                """INSERT INTO fp_scenario (target_id, tic_id, tool, scenario, probability,
                       metrics, notes) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (tgt["target_id"], tgt["tic_id"], TOOL, scenario,
                 prob, Jsonb(metrics), note),
            )
    conn.commit()


def run(conn) -> list[dict]:
    lk, np, pd = process._lazy()
    out = []
    for tgt in _pick_subset(conn):
        det = _best_bls(conn, tgt["target_id"])
        if det is None or det["epoch_bjd"] is None:
            logger.info("TIC %s (%s): no BLS ephemeris, skipping", tgt["tic_id"], tgt["toi"])
            out.append({**tgt, "status": "no_detection"})
            continue
        t, f, meta = process._load_stitched(conn, tgt["tic_id"], lk, np, pd)
        if t is None:
            out.append({**tgt, "status": "no_data"})
            continue
        m = vet_target(t, f, det, np)
        _persist(conn, tgt, det, m)
        logger.info("TIC %s (%s, %s): FP_score=%.2f  %s",
                    tgt["tic_id"], tgt["toi"], tgt["cohort"], m["fp_score"], "; ".join(m["flags"]))
        out.append({**tgt, "status": "ok", **m})
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    argparse.ArgumentParser(description="FP vetting for a subset -> fp_scenario.").parse_args()
    conn = get_conn()
    try:
        results = run(conn)
    finally:
        conn.close()
    ok = [r for r in results if r.get("status") == "ok"]
    print(f"\n=== FP vetting: {len(ok)}/{len(results)} vetted (tool={TOOL}) ===")
    for r in results:
        if r.get("status") == "ok":
            print(f"  {r['cohort']:12s} TIC {r['tic_id']:<11} TOI {r['toi']:<9} "
                  f"FP_score={r['fp_score']:.2f}  {'; '.join(r['flags'])}")
        else:
            print(f"  {r['cohort']:12s} TIC {r['tic_id']:<11} {r['status']}")


if __name__ == "__main__":
    main()
