"""Standalone Transit Least Squares worker — runs in the isolated .venv-tls interpreter.

WHY a separate process: transitleastsquares pulls numba/llvmlite + a C-compiled batman, which on
this arm64-under-x86_64(Rosetta) laptop only builds cleanly in a dedicated Python 3.13 venv
(.venv-tls) separate from the lightkurve/astropy stack (.venv-lc, which needs a newer numpy than
numba accepts). process.py (in .venv-lc) hands us a detrended light curve as an .npz and reads back
JSON — a clean cross-venv, cross-numpy bridge. This file therefore imports ONLY numpy +
transitleastsquares (no repo modules), so it runs under .venv-tls with no path games.

Contract:  python tls_worker.py <input.npz> <output.json>
  input.npz : time (BTJD), flux (normalised ~1), period_min, period_max, oversampling
  output.json: {ok, period, t0, depth_ppm, duration_hr, sde, snr, odd_even_sigma, n_transits, ...}
              or {ok: false, error: "..."} on failure.
"""

import json
import sys
import warnings


def main() -> int:
    warnings.simplefilter("ignore")
    in_path, out_path = sys.argv[1], sys.argv[2]
    import numpy as np
    from transitleastsquares import transitleastsquares

    data = np.load(in_path)
    time = np.asarray(data["time"], dtype="float64")
    flux = np.asarray(data["flux"], dtype="float64")
    period_min = float(data["period_min"])
    period_max = float(data["period_max"])
    oversampling = int(data["oversampling"]) if "oversampling" in data else 3

    try:
        model = transitleastsquares(time, flux)
        res = model.power(
            period_min=period_min,
            period_max=period_max,
            oversampling_factor=oversampling,
            duration_grid_step=1.1,
            use_threads=2,
            show_progress_bar=False,
        )
        depth_frac = float(1.0 - res.depth)  # TLS reports depth as the in-transit flux LEVEL
        out = {
            "ok": True,
            "period": float(res.period),
            "t0": float(res.T0),
            "depth_ppm": depth_frac * 1e6,
            "duration_hr": float(res.duration) * 24.0,
            "sde": float(res.SDE),
            "snr": float(res.snr) if np.isfinite(res.snr) else None,
            "odd_even_sigma": (float(res.odd_even_mismatch)
                               if np.isfinite(res.odd_even_mismatch) else None),
            "n_transits": int(res.distinct_transit_count),
            "rp_rs": float(res.rp_rs) if np.isfinite(res.rp_rs) else None,
            "chi2red_min": float(np.nanmin(res.chi2red)) if len(res.chi2red) else None,
        }
    except Exception as exc:  # noqa: BLE001 - report the failure as JSON, never crash the bridge
        out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:500]}

    with open(out_path, "w") as fh:
        json.dump(out, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
