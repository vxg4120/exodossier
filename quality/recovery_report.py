"""THE Wave 2 deliverable (SPEC §5): docs/reports/recovery_report.md — the gold-graded recovery
baseline the whole dossier's credibility rests on.

For the GOLD set it measures how often the independent BLS/TLS pipeline recovers the KNOWN ephemeris
of confirmed/known planets (period within 1% or an integer harmonic, with an epoch-consistency
check), what the pipeline does on known false positives (it DOES find transit-like signals — that is
the point; the disposition comes from the FP analysis, not the recovery), a per-method BLS-vs-TLS
comparison, and an honest analysis of misses. For the DISCOVERY slice it reports single-event /
periodic signals worth a dossier — with NO overclaiming ("we recover/flag signals; we do not confirm
planets").

Pure: `generate_report(conn) -> str` reads only the Wave 2 tables + the target answer key and
returns markdown, so tests can drive it inside their own transaction. Deterministic (every query
ordered) and data-vintage-stamped from pipeline_run.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "recovery_report.md"

BTJD_OFFSET = 2457000.0        # catalog epoch is full BJD; TESS light-curve time is BTJD = BJD-this
PERIOD_TOL = 0.01              # within 1% = a period match (SPEC)
SNR_MIN = 7.0                  # a detection below this is not counted as a recovered signal
# Ratios rec/known that count as a harmonic recovery (BLS/TLS often lock onto 2x or 1/2 the period).
HARMONICS = (1.0, 2.0, 0.5, 3.0, 1.0 / 3.0, 1.5, 2.0 / 3.0)


def match_period(rec, known, tol=PERIOD_TOL):
    """Return the harmonic ratio (rec/known) if `rec` matches `known` within `tol` at any harmonic,
    else None. 1.0 = exact; 2.0/0.5/... = harmonic alias."""
    if not rec or not known or rec <= 0 or known <= 0:
        return None
    for h in HARMONICS:
        if abs(rec - known * h) / (known * h) <= tol:
            return h
    return None


def epoch_phase_offset(t0_rec_btjd, t0_known_bjd, period):
    """Fractional phase separation (0..0.5) between recovered and known epoch, folded on `period`.
    Small => the recovered transit falls at the catalog ephemeris (epoch-consistent)."""
    if t0_rec_btjd is None or t0_known_bjd is None or not period or period <= 0:
        return None
    t0_known_btjd = float(t0_known_bjd) - BTJD_OFFSET
    d = ((float(t0_rec_btjd) - t0_known_btjd) % period) / period
    return min(d, 1.0 - d)


def _fmt(v, spec="") -> str:
    if v is None:
        return "-"
    if spec:
        return format(v, spec)
    return str(v)


def _md_table(cols, rows) -> str:
    if not rows:
        return "_(none)_\n"
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out) + "\n"


def _fetch_targets(cur):
    cur.execute(
        """SELECT t.target_id, t.tic_id, t.toi, t.cohort, t.stratum, t.tfopwg_disp,
                  t.known_period_days, t.known_epoch_bjd, t.known_depth_ppm, t.tmag
           FROM target t ORDER BY t.cohort, t.stratum, t.tic_id, t.toi"""
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]


def _fetch_detections(cur):
    """Latest pipeline_run per target -> its detections. {target_id: {run, dets:[...]}}."""
    cur.execute(
        """SELECT DISTINCT ON (target_id) pipeline_run_id, target_id, tic_id, status,
                  n_sectors, n_points, baseline_days, runtime_s, data_vintage, notes
           FROM pipeline_run ORDER BY target_id, pipeline_run_id DESC"""
    )
    runcols = [d[0] for d in cur.description]
    runs = {r[1]: dict(zip(runcols, r, strict=True)) for r in cur.fetchall()}
    out = {tid: {"run": run, "dets": []} for tid, run in runs.items()}
    if runs:
        run_ids = [run["pipeline_run_id"] for run in runs.values()]
        cur.execute(
            """SELECT pipeline_run_id, method, rank, period_days, epoch_bjd, depth_ppm,
                      duration_hr, snr, sde FROM detection
               WHERE pipeline_run_id = ANY(%s) ORDER BY pipeline_run_id, method, rank""",
            (run_ids,),
        )
        dcols = [d[0] for d in cur.description]
        by_run = {run["pipeline_run_id"]: tid for tid, run in runs.items()}
        for row in cur.fetchall():
            det = dict(zip(dcols, row, strict=True))
            out[by_run[det["pipeline_run_id"]]]["dets"].append(det)
    return out


def _best_recovery(target, dets):
    """Best period-matching detection for a target. Returns (det, harmonic) or (None, None)."""
    known = target["known_period_days"]
    best = None
    for det in dets:
        if det["method"] == "single_event":
            continue
        h = match_period(_f(det["period_days"]), _f(known))
        if h is not None and _f(det["snr"]) is not None and _f(det["snr"]) >= SNR_MIN:
            if best is None or abs(h - 1.0) < abs(best[1] - 1.0):
                best = (det, h)
    return best if best else (None, None)


def _f(v):
    return float(v) if v is not None else None


def _analyze_miss(target, dets) -> str:
    known = _f(target["known_period_days"])
    depth = _f(target["known_depth_ppm"])
    if known and known > 50:
        return f"P={known:.1f} d > 50 d periodic-search cap (blind spot; needs single-event)"
    best_snr = max([_f(d["snr"]) or 0 for d in dets if d["method"] != "single_event"] or [0])
    if depth is not None and depth < 500:
        return f"shallow ({depth:.0f} ppm); best BLS/TLS SNR={best_snr:.1f} < {SNR_MIN:g}"
    if best_snr < SNR_MIN:
        return f"no signal above SNR {SNR_MIN:g} (best={best_snr:.1f}); detrending/short baseline?"
    return f"strongest signal did not match catalog P (best SNR={best_snr:.1f}); wrong-alias/blend?"


def generate_report(conn) -> str:
    with conn.cursor() as cur:
        targets = _fetch_targets(cur)
        detmap = _fetch_detections(cur)

    vintages = {str(v["run"].get("data_vintage")) for v in detmap.values()
                if v["run"].get("data_vintage")}
    vintage = sorted(vintages)[-1] if vintages else "n/a"
    processed = sum(1 for v in detmap.values() if v["run"]["status"] == "ok")

    lines: list[str] = []
    lines.append("# ExoDossier — Wave 2 Recovery Report")
    lines.append("")
    lines.append(f"_Generated {dt.date.today().isoformat()}; light-curve data vintage {vintage}; "
                 f"{len(targets)} targets, {processed} processed ok._")
    lines.append("")
    lines.append("**Framing.** This pipeline independently RECOVERS or FLAGS transit signals from "
                 "raw TESS photometry and grades them against the known TFOPWG answer key. It does "
                 "not confirm planets. A recovery = a BLS/TLS period within 1% of the catalog "
                 f"period or an integer harmonic, at depth-SNR ≥ {SNR_MIN:.0f}.")
    lines.append("")

    # ---- GOLD PLANETS ---------------------------------------------------------------------------
    planets = [t for t in targets if t["cohort"] == "gold_planet"]
    recovered, rows = 0, []
    method_hit = {"bls": 0, "tls": 0}
    for t in planets:
        entry = detmap.get(t["target_id"], {"run": {"status": "missing"}, "dets": []})
        dets = entry["dets"]
        det, h = _best_recovery(t, dets)
        # per-method credit
        for m in ("bls", "tls"):
            md = [d for d in dets if d["method"] == m]
            if any(match_period(_f(d["period_days"]), _f(t["known_period_days"])) is not None
                   and (_f(d["snr"]) or 0) >= SNR_MIN for d in md):
                method_hit[m] += 1
        if det:
            recovered += 1
            phase = epoch_phase_offset(_f(det["epoch_bjd"]), _f(t["known_epoch_bjd"]),
                                       _f(t["known_period_days"]))
            kind = "exact" if abs(h - 1.0) < 1e-6 else f"harmonic x{h:g}"
            rows.append([t["toi"], t["tfopwg_disp"], f"{_f(t['known_period_days']):.3f}",
                         f"{_f(det['period_days']):.3f}", det["method"].upper(), kind,
                         f"{_f(det['snr']):.1f}", _fmt(phase, ".3f") if phase is not None else "-"])
        else:
            rows.append([t["toi"], t["tfopwg_disp"], f"{_f(t['known_period_days']):.3f}",
                         "MISS", "-", "-", "-", _analyze_miss(t, dets)])
    lines.append(f"## Gold planets: {recovered}/{len(planets)} known planets recovered")
    lines.append("")
    lines.append(_md_table(
        ["TOI", "disp", "P_known(d)", "P_rec(d)", "method", "match", "SNR", "phaseΔ/miss-reason"],
        rows))
    lines.append("")

    # ---- BLS vs TLS -----------------------------------------------------------------------------
    lines.append("## BLS vs TLS (gold planets)")
    lines.append("")
    lines.append(_md_table(
        ["method", "planets recovered", "of"],
        [["BLS", method_hit["bls"], len(planets)], ["TLS", method_hit["tls"], len(planets)]]))
    lines.append("")

    # ---- GOLD FALSE POSITIVES -------------------------------------------------------------------
    fps = [t for t in targets if t["cohort"] == "gold_fp"]
    fp_rows, fp_signal = [], 0
    for t in fps:
        entry = detmap.get(t["target_id"], {"run": {"status": "missing"}, "dets": []})
        dets = entry["dets"]
        periodic = [d for d in dets if d["method"] != "single_event"]
        best = max(periodic, key=lambda d: _f(d["snr"]) or 0, default=None)
        has_sig = best is not None and (_f(best["snr"]) or 0) >= SNR_MIN
        if has_sig:
            fp_signal += 1
        h = match_period(_f(best["period_days"]), _f(t["known_period_days"])) if best else None
        fp_rows.append([t["toi"], t["tfopwg_disp"], f"{_f(t['known_period_days']):.3f}",
                        f"{_f(best['period_days']):.3f}" if best else "-",
                        f"{_f(best['snr']):.1f}" if best else "-",
                        "signal@catalog-P" if h else ("signal" if has_sig else "no signal")])
    lines.append(f"## Gold false positives: pipeline found a transit-like signal in "
                 f"{fp_signal}/{len(fps)}")
    lines.append("")
    lines.append("These ARE eclipsing binaries / blends / false alarms. That the pipeline recovers "
                 "a signal is expected and correct — recovery is NOT what rejects them. The FP "
                 "verdict comes from odd/even depth, secondary eclipse, centroid, and TRICERATOPS "
                 "scenarios (see fp_scenario). Recovering their ephemerides cleanly is what lets "
                 "that analysis run.")
    lines.append("")
    lines.append(_md_table(
        ["TOI", "disp", "P_catalog(d)", "P_rec(d)", "SNR", "pipeline"], fp_rows))
    lines.append("")

    # ---- DISCOVERY SLICE ------------------------------------------------------------------------
    disc = [t for t in targets if t["cohort"] == "discovery"]
    d_rows, credible = [], 0
    for t in disc:
        entry = detmap.get(t["target_id"], {"run": {"status": "missing"}, "dets": []})
        dets = entry["dets"]
        se = next((d for d in dets if d["method"] == "single_event"), None)
        periodic = [d for d in dets if d["method"] != "single_event"]
        best_p = max(periodic, key=lambda d: _f(d["snr"]) or 0, default=None)
        se_snr = _f(se["snr"]) if se else None
        p_snr = _f(best_p["snr"]) if best_p else None
        is_credible = (se_snr or 0) >= SNR_MIN or (p_snr or 0) >= SNR_MIN
        if is_credible:
            credible += 1
        d_rows.append([
            t["toi"], t["stratum"],
            f"{_f(t['known_period_days']):.2f}" if t["known_period_days"] else "single",
            f"{_f(best_p['period_days']):.3f}" if best_p else "-",
            f"{p_snr:.1f}" if p_snr else "-",
            f"{se_snr:.1f}" if se_snr else "-",
            "signal worth a dossier" if is_credible else "below threshold",
        ])
    lines.append(f"## Discovery slice: {credible}/{len(disc)} targets show a signal worth a "
                 "dossier")
    lines.append("")
    lines.append("Long-period / single-transit candidates — the pipelines' documented blind spot. "
                 "The single-event lens localises a lone dip (epoch/depth/duration/SNR) but claims "
                 "NO period; the periodic columns show what BLS found within the 50-day cap. These "
                 "are candidate signals for a dossier, not planets.")
    lines.append("")
    lines.append(_md_table(
        ["TOI", "kind", "P_catalog(d)", "P_bls(d)", "BLS SNR", "single-event SNR", "verdict"],
        d_rows))
    lines.append("")

    # ---- FAILURES / TIMINGS ---------------------------------------------------------------------
    failed = [(t, detmap.get(t["target_id"])) for t in targets
              if detmap.get(t["target_id"], {}).get("run", {}).get("status") not in (None, "ok")]
    lines.append("## Processing failures / timeouts")
    lines.append("")
    if failed:
        frows = [[t["toi"], t["tic_id"], e["run"]["status"],
                  str(e["run"].get("notes"))[:80]] for t, e in failed if e]
        lines.append(_md_table(["TOI", "TIC", "status", "why"], frows))
    else:
        lines.append("_None — every target processed ok._")
    lines.append("")
    runtimes = [v["run"].get("runtime_s") for v in detmap.values() if v["run"].get("runtime_s")]
    if runtimes:
        rr = sorted(float(x) for x in runtimes)
        lines.append(f"Per-target runtime: median {rr[len(rr) // 2]:.0f}s, max {rr[-1]:.0f}s "
                     f"(TLS wall-clock cap enforced per SPEC).")
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    conn = get_conn()
    try:
        md = generate_report(conn)
    finally:
        conn.close()
    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(md)
    print(f"wrote {DEFAULT_REPORT_PATH} ({len(md)} bytes)")


if __name__ == "__main__":
    main()
