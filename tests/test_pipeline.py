"""Pipeline fixture tests (SPEC Wave 2 §6): drive the real load -> normalise -> stitch -> bin ->
detect path over synthetic Parquet light curves written to disk and indexed like the MAST fetch,
and the full process_target persistence into pipeline_run + detection. DB-backed (marked `db`);
every test cleans up its synthetic TIC so the graph is never polluted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline import detect, process

TEST_TIC = 990000001  # synthetic; far outside the real TIC range in the graph


def _write_sector(path, t0, days, period, depth=0.004, dur=0.09, cad_min=10.0, seed=1):
    """Write one synthetic sector of raw (un-normalised ~1.0) flux with a box transit to Parquet,
    in the column layout fetch_lightcurves.py produces (time, flux, flux_err, quality)."""
    rng = np.random.default_rng(seed)
    t = np.arange(t0, t0 + days, cad_min / 1440.0)
    phase = ((t + 0.5 * period) % period) - 0.5 * period
    f = np.ones_like(t)
    f[np.abs(phase) < dur / 2.0] -= depth
    f += rng.normal(0.0, 3e-4, t.size)
    pd.DataFrame({"time": t, "flux": f, "flux_err": np.full_like(f, 3e-4),
                  "quality": np.zeros(t.size, dtype="int64")}).to_parquet(path, index=False)
    return t.min(), t.max(), t.size


def _index_file(conn, path, sector, t_start, t_end, n):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO lightcurve_file (tic_id, sector, author, cadence_s, flux_kind, mission,
                   path, n_points, t_start, t_end)
               VALUES (%s,%s,'SPOC',120,'pdcsap','TESS',%s,%s,%s,%s)""",
            (TEST_TIC, sector, str(path), n, t_start, t_end),
        )


@pytest.fixture
def synthetic_tic(db_conn):
    """Yield the db connection; on teardown delete every row keyed to the synthetic TEST_TIC
    (process_target commits, so a plain rollback is not enough)."""
    yield db_conn
    db_conn.rollback()
    with db_conn.cursor() as cur:
        for sql in (
            "DELETE FROM detection WHERE tic_id=%s",
            "DELETE FROM fp_scenario WHERE tic_id=%s",
            "DELETE FROM pipeline_run WHERE tic_id=%s",
            "DELETE FROM target WHERE tic_id=%s",
            "DELETE FROM lightcurve_file WHERE tic_id=%s",
            "DELETE FROM candidate WHERE star_id IN (SELECT star_id FROM star WHERE tic_id=%s)",
            "DELETE FROM star WHERE tic_id=%s",
        ):
            cur.execute(sql, (TEST_TIC,))
    db_conn.commit()


@pytest.mark.db
def test_load_stitched_bins_and_recovers(synthetic_tic, tmp_path):
    """Two synthetic sectors -> _load_stitched normalises/stitches/flattens/bins, and BLS recovers
    the injected period. Also checks the ~10-min binning actually reduced the point count."""
    conn = synthetic_tic
    lk, np_, pd_ = process._lazy()
    n_raw_total = 0
    for i, t0 in enumerate([1000.0, 1030.0]):  # two adjacent 27-day sectors
        p = tmp_path / f"s{i}.parquet"
        a, b, n = _write_sector(p, t0, 27.0, period=2.3, cad_min=2.0, seed=i + 1)
        n_raw_total += n
        _index_file(conn, p, i + 1, a, b, n)
    conn.commit()

    t, f, meta = process._load_stitched(conn, TEST_TIC, lk, np_, pd_)
    assert t is not None
    assert meta["n_sectors"] == 2
    assert meta["n_points"] < n_raw_total          # binning reduced 2-min -> 10-min
    assert meta["detrend"]["bin_minutes"] == process.BIN_MINUTES
    d = detect.bls_search(t, f, 0.6, 13.0)
    assert abs(d["period_days"] - 2.3) / 2.3 < 0.01
    assert d["snr"] > 7.0


@pytest.mark.db
def test_process_target_persists_recovery(synthetic_tic, tmp_path, monkeypatch):
    """Full process_target on a single synthetic sector: writes an 'ok' pipeline_run and a BLS
    detection matching the injected period. TLS is stubbed (its subprocess/venv is validated
    separately) to keep the test hermetic and fast."""
    conn = synthetic_tic
    lk, np_, pd_ = process._lazy()

    # star -> candidate -> target (the FK chain the real selection builds)
    with conn.cursor() as cur:
        cur.execute("INSERT INTO star (tic_id, canonical_name) VALUES (%s,%s) RETURNING star_id",
                    (TEST_TIC, f"TIC {TEST_TIC}"))
        star_id = cur.fetchone()[0]
        cur.execute("INSERT INTO candidate (star_id, canonical_name, period_days) "
                    "VALUES (%s,%s,%s) RETURNING candidate_id", (star_id, "TEST.01", 2.3))
        cand_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO target (candidate_id, tic_id, toi, cohort, stratum,
                           known_period_days, select_rule)
                       VALUES (%s,%s,'9999.01','gold_planet','deep_short',2.3,'test')""",
                    (cand_id, TEST_TIC))
    p = tmp_path / "s1.parquet"
    a, b, n = _write_sector(p, 1000.0, 27.0, period=2.3, cad_min=2.0)
    _index_file(conn, p, 1, a, b, n)
    conn.commit()

    def _stub_tls(time, flux, period_min, period_max, oversampling=2, timeout_s=150):
        return {"method": "tls", "status": "ok", "period_days": 2.3, "epoch_bjd": float(time[0]),
                "depth_ppm": 4000.0, "duration_hr": 2.2, "snr": 50.0, "sde": 20.0, "power": 20.0,
                "metrics": {}}
    monkeypatch.setattr(detect, "run_tls", _stub_tls)

    tgt = process._targets(conn, only_tic=TEST_TIC)[0]
    result = process.process_target(conn, tgt, lk, np_, pd_)
    assert result["status"] == "ok"

    with conn.cursor() as cur:
        cur.execute("SELECT status, n_sectors, runtime_s FROM pipeline_run WHERE tic_id=%s "
                    "ORDER BY pipeline_run_id DESC LIMIT 1", (TEST_TIC,))
        status, n_sectors, runtime_s = cur.fetchone()
        assert status == "ok"
        assert runtime_s is not None
        cur.execute("SELECT period_days, snr FROM detection WHERE tic_id=%s AND method='bls' "
                    "ORDER BY rank LIMIT 1", (TEST_TIC,))
        period, snr = cur.fetchone()
        assert abs(float(period) - 2.3) / 2.3 < 0.01
        assert float(snr) > 7.0


@pytest.mark.db
def test_process_target_no_data_is_honest(synthetic_tic):
    """A target with no light-curve files records status='no_data', never a silent skip."""
    conn = synthetic_tic
    lk, np_, pd_ = process._lazy()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO star (tic_id, canonical_name) VALUES (%s,%s) RETURNING star_id",
                    (TEST_TIC, f"TIC {TEST_TIC}"))
        star_id = cur.fetchone()[0]
        cur.execute("INSERT INTO candidate (star_id, canonical_name) VALUES (%s,%s) "
                    "RETURNING candidate_id", (star_id, "TEST.01"))
        cand_id = cur.fetchone()[0]
        cur.execute("""INSERT INTO target (candidate_id, tic_id, toi, cohort, select_rule)
                       VALUES (%s,%s,'9999.01','gold_planet','test')""", (cand_id, TEST_TIC))
    conn.commit()

    tgt = process._targets(conn, only_tic=TEST_TIC)[0]
    result = process.process_target(conn, tgt, lk, np_, pd_)
    assert result["status"] == "no_data"
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM pipeline_run WHERE tic_id=%s ORDER BY pipeline_run_id DESC "
                    "LIMIT 1", (TEST_TIC,))
        assert cur.fetchone()[0] == "no_data"
