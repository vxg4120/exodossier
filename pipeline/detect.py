"""Transit detection primitives (SPEC Wave 2 §3): BLS, TLS (via the isolated worker), and a
single-event / change-point lens for the discovery slice.

Pure functions on numpy arrays (time in BTJD, flux normalised to ~1), so the synthetic-injection
unit tests can drive them directly. The only side effect is `run_tls`, which shells out to the
.venv-tls interpreter (see tls_worker.py for why TLS lives in its own venv).

Honest framing: these routines RECOVER / FLAG signals and report metrics; they never assert a
planet. The single-event lens in particular can localise ONE dip and estimate its
depth/duration/SNR, but it cannot constrain a period from a lone event — it reports exactly that
and no more.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile

import numpy as np

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
TLS_PYTHON = os.environ.get("TLS_PYTHON", str(REPO_ROOT / ".venv-tls" / "bin" / "python"))
TLS_WORKER = str(REPO_ROOT / "pipeline" / "tls_worker.py")

# Trial transit durations (days) for BLS + the single-event scan. Spans TESS-typical 1 h -> 12 h.
DEFAULT_DURATIONS = np.array([0.04, 0.06, 0.08, 0.12, 0.18, 0.25, 0.35, 0.5])


def _sde(power: np.ndarray, peak: float) -> float:
    """Signal Detection Efficiency: peak height in units of the periodogram's own scatter.
    Comparable between BLS and TLS (both report an SDE-like significance)."""
    med = float(np.nanmedian(power))
    std = float(np.nanstd(power))
    return (peak - med) / std if std > 0 else 0.0


def _robust_sigma(flux: np.ndarray) -> float:
    """Robust per-point scatter (1.4826 x MAD). astropy BLS needs a `dy`; without one it silently
    assumes dy=1.0, which makes depth_snr meaningless (~0.1 for a real transit). Feeding this sigma
    is what makes depth-SNR — and hence the report's SNR>=7 gate — mean anything."""
    med = float(np.nanmedian(flux))
    sigma = 1.4826 * float(np.nanmedian(np.abs(flux - med)))
    if not np.isfinite(sigma) or sigma <= 0:
        sigma = float(np.nanstd(flux)) or 1e-9
    return sigma


def bls_period_grid(baseline_days, period_min, period_max, grid_duration=0.05,
                    oversample=2.0, min_periods=3000, max_periods=120000):
    """Baseline-aware LOG period grid. A log grid has a CONSTANT fractional step dP/P; setting that
    step to grid_duration/baseline/oversample guarantees a transit at ANY period is resolved without
    the last cycle smearing across the multi-year baseline (the inherited stitched-6-sector bug: a
    fixed 12k grid gave dP/P~3.7e-4, ~8x too coarse for a 1.48 d period over 1876 d, so BLS locked
    onto the P/2 alias). This is the efficient form of "let the baseline set the resolution": a
    linear-frequency autopower would oversample the short-period end into ~1e8 trials, infeasible on
    a laptop; a log grid needs only ~1e5. Returns (periods, n, capped)."""
    step = grid_duration / max(float(baseline_days), 1.0) / oversample
    n = int(np.ceil(np.log(period_max / period_min) / step)) if step > 0 else min_periods
    capped = n > max_periods
    n = int(min(max(n, min_periods), max_periods))
    return np.geomspace(period_min, period_max, n), n, capped


def bls_search(time, flux, period_min=0.6, period_max=30.0,
               durations=DEFAULT_DURATIONS, flux_err=None, grid_duration=0.05,
               oversample=2.0, max_periods=120000) -> dict:
    """Box Least Squares (astropy) on a baseline-aware LOG period grid.

    The grid density is derived from the actual baseline (see bls_period_grid) so a short period is
    resolved over a multi-year stitched series without smearing, while a log grid keeps the trial
    count ~1e5 (not the ~1e8 a linear-frequency autopower would demand). A robust `dy` is always
    supplied so depth_snr is physically meaningful. Returns best period/epoch/depth/duration + SNR,
    power, SDE."""
    from astropy.timeseries import BoxLeastSquares

    time = np.asarray(time, dtype="float64")
    flux = np.asarray(flux, dtype="float64")
    durations = np.asarray([d for d in durations if d < period_max], dtype="float64")
    dy = (np.full_like(flux, _robust_sigma(flux)) if flux_err is None
          else np.asarray(flux_err, dtype="float64"))
    baseline = float(time.max() - time.min()) if time.size else 1.0
    periods, n_periods, capped = bls_period_grid(
        baseline, period_min, period_max, grid_duration=grid_duration,
        oversample=oversample, max_periods=max_periods)
    model = BoxLeastSquares(time, flux, dy)
    periodogram = model.power(periods, durations, objective="snr")
    power = np.asarray(periodogram.power, dtype="float64")
    i = int(np.nanargmax(power))
    period = float(periodogram.period[i])
    t0 = float(periodogram.transit_time[i])
    duration = float(periodogram.duration[i])
    depth = float(periodogram.depth[i])
    snr = float(periodogram.depth_snr[i])
    return {
        "method": "bls",
        "period_days": period,
        "epoch_bjd": t0,
        "depth_ppm": depth * 1e6,
        "duration_hr": duration * 24.0,
        "snr": snr,
        "power": float(power[i]),
        "sde": _sde(power, float(power[i])),
        "metrics": {"n_periods": int(power.size), "objective": "snr",
                    "dP_over_P": float(np.log(period_max / period_min) / n_periods),
                    "grid_capped": bool(capped), "baseline_days": baseline,
                    "period_min": period_min, "period_max": period_max},
    }


def run_tls(time, flux, period_min=0.6, period_max=30.0, oversampling=3,
            timeout_s=300) -> dict:
    """Run TLS in the isolated .venv-tls worker. Returns a detection dict, or a dict with
    status='timeout'/'error' and a reason (no silent failure). Never raises for a TLS problem."""
    time = np.asarray(time, dtype="float64")
    flux = np.asarray(flux, dtype="float64")
    with tempfile.TemporaryDirectory() as td:
        inp = pathlib.Path(td) / "in.npz"
        out = pathlib.Path(td) / "out.json"
        np.savez(inp, time=time, flux=flux, period_min=period_min,
                 period_max=period_max, oversampling=oversampling)
        try:
            proc = subprocess.run(
                [TLS_PYTHON, TLS_WORKER, str(inp), str(out)],
                capture_output=True, text=True, timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return {"method": "tls", "status": "timeout",
                    "reason": f"TLS exceeded {timeout_s}s wall clock"}
        if not out.exists():
            return {"method": "tls", "status": "error",
                    "reason": f"worker rc={proc.returncode}: {proc.stderr[-400:]}"}
        res = json.loads(out.read_text())
    if not res.get("ok"):
        return {"method": "tls", "status": "error", "reason": res.get("error", "unknown")}
    return {
        "method": "tls",
        "status": "ok",
        "period_days": res["period"],
        "epoch_bjd": res["t0"],
        "depth_ppm": res["depth_ppm"],
        "duration_hr": res["duration_hr"],
        "snr": res.get("snr"),
        "sde": res["sde"],
        "power": res["sde"],
        "metrics": {"n_transits": res.get("n_transits"), "rp_rs": res.get("rp_rs"),
                    "odd_even_sigma": res.get("odd_even_sigma"),
                    "chi2red_min": res.get("chi2red_min"),
                    "period_min": period_min, "period_max": period_max},
    }


def mask_transits(time, flux, period_days, epoch_bjd, duration_hr) -> np.ndarray:
    """Return a boolean keep-mask that removes the in-transit cadences of a known signal, so a
    second BLS pass can find the next-strongest transit (multi-planet systems)."""
    time = np.asarray(time, dtype="float64")
    if not period_days or period_days <= 0:
        return np.ones(time.size, dtype=bool)
    half = (duration_hr / 24.0) / 2.0 * 1.1  # 10% guard band
    phase = np.abs(((time - epoch_bjd + 0.5 * period_days) % period_days) - 0.5 * period_days)
    return phase > half


def single_event_scan(time, flux, durations=DEFAULT_DURATIONS) -> dict:
    """Change-point / matched-filter lens for the discovery slice.

    Slides a box of each trial duration across the light curve and finds the single most
    significant dip. SNR = dip_depth / (out-of-transit MAD-scatter / sqrt(N_in)). Reports the ONE
    event's epoch/depth/duration/SNR. It deliberately makes NO period claim — a lone transit does
    not constrain a period. This is the honest tool for single-transit / long-period candidates.
    """
    time = np.asarray(time, dtype="float64")
    flux = np.asarray(flux, dtype="float64")
    order = np.argsort(time)
    time, flux = time[order], flux[order]
    med = float(np.median(flux))
    mad = float(np.median(np.abs(flux - med))) * 1.4826  # robust sigma
    if mad <= 0:
        mad = float(np.std(flux)) or 1e-9

    best = {"snr": 0.0}
    for dur in durations:
        half = dur / 2.0
        # Evaluate a box centred at each cadence (subsample to keep it cheap on long baselines).
        step = max(1, time.size // 20000)
        for c in range(0, time.size, step):
            t_c = time[c]
            in_tr = (time >= t_c - half) & (time <= t_c + half)
            n_in = int(in_tr.sum())
            if n_in < 5:
                continue
            depth = med - float(np.mean(flux[in_tr]))
            if depth <= 0:
                continue
            snr = depth / (mad / np.sqrt(n_in))
            if snr > best["snr"]:
                best = {"snr": snr, "epoch_bjd": float(t_c), "depth_ppm": depth * 1e6,
                        "duration_hr": float(dur) * 24.0, "n_in_transit": n_in}
    if best["snr"] == 0.0:
        return {"method": "single_event", "status": "no_event", "snr": 0.0,
                "metrics": {"note": "no positive dip found"}}
    return {
        "method": "single_event",
        "status": "ok",
        "period_days": None,   # a lone event constrains no period, by construction
        "epoch_bjd": best["epoch_bjd"],
        "depth_ppm": best["depth_ppm"],
        "duration_hr": best["duration_hr"],
        "snr": best["snr"],
        "sde": None,
        "power": best["snr"],
        "metrics": {"n_in_transit": best["n_in_transit"], "mad_sigma": mad,
                    "claim": "single dip localised; no period inferred"},
    }
