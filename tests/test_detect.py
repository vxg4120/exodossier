"""Transit-detection unit tests (SPEC Wave 2 §6): synthetic-injection recovery, the long-baseline
stitched regression that pins the inherited grid bug, no-signal -> no detection, and the honest
single-event lens. Pure numpy in/out — no DB, no network.

The regression (`test_bls_recovers_long_baseline_stitched`) is the load-bearing one: a 1.48 d period
injected across a 6-sector series spanning ~1900 d. The pre-fix FIXED 12k-period grid was ~8x too
coarse for that baseline and locked onto the P/2 alias; the baseline-aware LOG grid recovers it. The
test asserts BOTH that the coarse grid misses AND that bls_search now recovers, so the bug cannot
silently return.
"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline import detect
from pipeline.process import _bin_series


def _inject(sectors, span_days, period, depth=0.004, dur=0.09, cad_min=10.0, seed=1):
    """Synthetic multi-sector TESS-like series: `sectors` 27-day windows spread across span_days,
    a box transit of the given period/depth/duration, white noise, then 10-min binned like the
    pipeline. Returns (time_btjd, flux)."""
    rng = np.random.default_rng(seed)
    seclen = 27.0
    starts = [0.0] if sectors == 1 else np.linspace(0.0, span_days - seclen, sectors)
    t = np.concatenate([np.arange(s, s + seclen, cad_min / 1440.0) for s in starts])
    phase = ((t + 0.5 * period) % period) - 0.5 * period
    f = np.ones_like(t)
    f[np.abs(phase) < dur / 2.0] -= depth
    f += rng.normal(0.0, 3e-4, t.size)
    return _bin_series(t, f, np)


def _pct_err(rec, known):
    return abs(rec - known) / known * 100.0


def test_bls_period_grid_scales_with_baseline():
    """The fix: a longer baseline yields a finer (more periods, smaller dP/P) grid."""
    _, n_short, _ = detect.bls_period_grid(27.0, 0.6, 50.0)
    _, n_long, capped = detect.bls_period_grid(1876.0, 0.6, 50.0)
    assert n_long > n_short
    # A 1876 d baseline needs dP/P < ~5e-5 to phase-connect a ~0.1 d transit; the grid must deliver.
    dp_over_p = np.log(50.0 / 0.6) / n_long
    assert dp_over_p < 5e-5
    assert capped is True  # 1876 d exceeds the cap; recorded honestly


def test_bls_recovers_single_sector():
    t, f = _inject(1, 27.0, period=2.30)
    d = detect.bls_search(t, f, 0.6, 13.0)
    assert _pct_err(d["period_days"], 2.30) < 1.0
    assert d["snr"] > 7.0
    assert d["depth_ppm"] > 1000.0  # injected 4000 ppm; box depth is in the right ballpark


def test_bls_recovers_long_baseline_stitched():
    """REGRESSION for the inherited stitched-series failure (P=1.48 d over ~1900 d, 6 sectors →
    3-sector 30-min proxy here to stay fast). The pre-fix bls_search had two coupled defects that
    both bit on long baselines: a FIXED 12k-period grid AND no per-point `dy` (so astropy's
    depth_snr collapsed to ~0.1 and nothing cleared the report's SNR>=7 gate). This test replays
    that exact pre-fix path and asserts it CANNOT produce a usable recovery, while the fixed
    bls_search recovers the period within 1% at high SNR."""
    from astropy.timeseries import BoxLeastSquares

    durs = np.array([0.06, 0.09, 0.14])
    t, f = _inject(3, 1876.0, period=1.48, cad_min=30.0)

    # Pre-fix path: fixed 12k-period grid, NO dy (exactly the inherited implementation).
    pg = BoxLeastSquares(t, f).power(np.geomspace(0.6, 50.0, 12000), durs, objective="snr")
    i = int(np.nanargmax(pg.power))
    old_ok = _pct_err(float(pg.period[i]), 1.48) < 1.0 and float(pg.depth_snr[i]) >= 7.0
    assert not old_ok  # the inherited code could not recover this stitched signal

    # Fixed bls_search: baseline-aware grid + robust dy -> clean recovery.
    d = detect.bls_search(t, f, 0.6, 50.0, durations=durs)
    assert _pct_err(d["period_days"], 1.48) < 1.0
    assert d["snr"] > 7.0
    assert d["metrics"]["dP_over_P"] < 5e-5
    assert d["metrics"]["grid_capped"] is True


def test_bls_no_signal_stays_below_threshold():
    """Pure noise must not masquerade as a recovered transit (SNR under the report's gate)."""
    rng = np.random.default_rng(7)
    t = np.arange(0.0, 27.0, 10.0 / 1440.0)
    f = 1.0 + rng.normal(0.0, 3e-4, t.size)
    d = detect.bls_search(t, f, 0.6, 13.0)
    assert d["snr"] < 7.0


def test_single_event_localizes_and_claims_no_period():
    """The lens finds ONE dip near its true epoch and, by construction, infers NO period."""
    rng = np.random.default_rng(3)
    t = np.arange(0.0, 27.0, 10.0 / 1440.0)
    f = 1.0 + rng.normal(0.0, 3e-4, t.size)
    t0 = 12.5
    f[np.abs(t - t0) < 0.1] -= 0.01  # a single deep dip
    se = detect.single_event_scan(t, f)
    assert se["status"] == "ok"
    assert se["period_days"] is None
    assert abs(se["epoch_bjd"] - t0) < 0.3
    assert se["snr"] > 7.0


def test_single_event_no_event_on_flat_curve():
    rng = np.random.default_rng(5)
    t = np.arange(0.0, 27.0, 10.0 / 1440.0)
    f = 1.0 + rng.normal(0.0, 1e-4, t.size)
    se = detect.single_event_scan(t, f)
    assert se["snr"] < 7.0  # no credible dip


def test_mask_transits_removes_in_transit_cadences():
    t = np.linspace(0.0, 10.0, 1000)
    f = np.ones_like(t)
    keep = detect.mask_transits(t, f, period_days=2.0, epoch_bjd=1.0, duration_hr=2.4)
    assert keep.sum() < t.size          # something was masked
    # a point exactly at an expected transit centre (epoch + k*period) is dropped
    idx = int(np.argmin(np.abs(t - 3.0)))
    assert not keep[idx]


@pytest.mark.parametrize("period", [1.23, 3.45, 6.78])
def test_bls_recovers_various_periods(period):
    t, f = _inject(1, 27.0, period=period)
    d = detect.bls_search(t, f, 0.6, 13.0)
    assert _pct_err(d["period_days"], period) < 1.0
