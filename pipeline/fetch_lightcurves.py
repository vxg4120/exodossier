"""Download TESS light curves for the selected targets from MAST via lightkurve (SPEC Wave 2 §2).

Per distinct target TIC:
  1. search MAST (`search_lightcurve`) for all TESS products (one ledgered request);
  2. per sector, pick the best product - SPOC 2-min PDCSAP first, then TESS-SPOC (FFI), then QLP
     (FFI-only fallback) - and download ALL sectors (one ledgered request each);
  3. store each as Parquet under data/lightcurves/TIC<tic>/ and index it in `lightcurve_file`.

Politeness (SPEC): every MAST call opens + closes an ingest_run row (source='mast'); downloads are
serial with a small delay; nothing is re-fetched - a sector already present in `lightcurve_file`
is skipped, so the whole run is resumable. bytes_downloaded records the real FITS network volume;
the FITS cache file is deleted after conversion to keep laptop disk bounded (Parquet is the store).

We store raw (un-normalized) flux + flux_err + quality; normalization/detrending is process.py's
job.
Time is TESS BTJD (BJD - 2457000), the native light-curve time system.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import pathlib
import sys
import time
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn
from ingest import runlog

logger = logging.getLogger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LC_DIR = REPO_ROOT / "data" / "lightcurves"
CACHE_DIR = REPO_ROOT / "data" / "mast_cache"
POLITE_DELAY_S = 1.0  # serial downloads, no hammering

# Author preference per sector (best photometry first). SPOC 2-min is the gold standard; QLP is the
# FFI-only fallback for stars SPOC never made a postage stamp for.
AUTHOR_RANK = {"SPOC": 0, "TESS-SPOC": 1, "QLP": 2}
# Cadence preference (SPEC: "prefer SPOC 2-min"). 120 s is ideal for transit search; 20 s gives no
# recovery benefit at 6-9x the volume, so it is deprioritised hard. Lower score = preferred.
CADENCE_SCORE = {120: 0, 200: 1, 600: 2, 1800: 3, 20: 4}
# Preferred flux column per author (transit-safe, detrended flux), with fallbacks.
FLUX_COLS = {
    "SPOC": ["pdcsap_flux", "sap_flux"],
    "TESS-SPOC": ["pdcsap_flux", "sap_flux"],
    "QLP": ["kspsap_flux", "sap_flux", "det_flux"],
}


def _lazy_imports():
    """Import the heavy stack lazily so `--help` and unit tests don't pay for it."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import lightkurve as lk
        import numpy as np
        import pandas as pd
    return lk, np, pd


def _selected_tics(conn) -> list[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT tic_id FROM target ORDER BY tic_id")
        return [row[0] for row in cur.fetchall()]


def _already_have(conn, tic: int) -> set[tuple]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT sector, author, cadence_s FROM lightcurve_file WHERE tic_id = %s", (tic,)
        )
        return {tuple(r) for r in cur.fetchall()}


def _sector_of(row_table) -> int | None:
    for col in ("sequence_number", "sector"):
        if col in row_table.colnames:
            try:
                return int(row_table[col][0])
            except (TypeError, ValueError):
                pass
    mission = str(row_table["mission"][0]) if "mission" in row_table.colnames else ""
    digits = "".join(ch for ch in mission.split("Sector")[-1] if ch.isdigit())
    return int(digits) if digits else None


def _best_per_sector(search) -> dict[int, int]:
    """Map sector -> index into the SearchResult of the best (author, cadence) product."""
    best: dict[int, tuple[int, float, int]] = {}
    tbl = search.table
    for i in range(len(search)):
        author = str(tbl["author"][i])
        if author not in AUTHOR_RANK:
            continue
        sector = _sector_of(search[i].table)
        if sector is None:
            continue
        exptime = float(tbl["exptime"][i]) if "exptime" in tbl.colnames else 9999.0
        cad_score = CADENCE_SCORE.get(int(round(exptime)), 5)
        rank = (AUTHOR_RANK[author], cad_score)  # SPOC first, then 2-min cadence, wins
        if sector not in best or rank < (best[sector][1], best[sector][2]):
            best[sector] = (i, AUTHOR_RANK[author], cad_score)  # type: ignore[assignment]
    return {sector: v[0] for sector, v in best.items()}


def _extract(lc, author, np):
    """Return (time_btjd, flux, flux_err, quality, flux_kind) as finite-flux numpy arrays."""
    cols = lc.colnames
    flux_kind = next((c for c in FLUX_COLS.get(author, ["sap_flux"]) if c in cols), None)
    if flux_kind is None:
        flux_kind = "flux"
        flux = np.asarray(lc.flux.value, dtype="float64")
    else:
        flux = np.asarray(lc[flux_kind].value, dtype="float64")
    t = np.asarray(lc.time.value, dtype="float64")
    err_col = flux_kind + "_err"
    if err_col in cols:
        ferr = np.asarray(lc[err_col].value, dtype="float64")
    elif "flux_err" in cols:
        ferr = np.asarray(lc.flux_err.value, dtype="float64")
    else:
        ferr = np.full_like(flux, np.nan)
    quality = (np.asarray(lc["quality"].value, dtype="int64") if "quality" in cols
               else np.zeros_like(flux, dtype="int64"))
    good = np.isfinite(t) & np.isfinite(flux)
    return t[good], flux[good], ferr[good], quality[good], flux_kind.replace("_flux", "")


def _download_sector(conn, tic, sector, author, search_row, np, pd) -> dict | None:
    run_id = runlog.start_run(conn, "mast", f"download:TIC{tic}:s{sector}:{author}")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lc = search_row.download(download_dir=str(CACHE_DIR))
        if lc is None:
            runlog.finish_run(conn, run_id, 0, 0, "error", "download returned None")
            return None
        cadence = None
        if "exptime" in search_row.table.colnames:
            cadence = int(round(float(search_row.table["exptime"][0])))
        t, flux, ferr, quality, flux_kind = _extract(lc, author, np)
        if len(t) == 0:
            runlog.finish_run(conn, run_id, 0, 0, "error", "no finite cadences")
            return None
        fits_bytes = 0
        tic_dir = LC_DIR / f"TIC{tic}"
        tic_dir.mkdir(parents=True, exist_ok=True)
        out = tic_dir / f"s{sector:04d}_{author}_{cadence or 0}.parquet"
        pd.DataFrame({"time": t, "flux": flux, "flux_err": ferr, "quality": quality}).to_parquet(
            out, index=False
        )
        # Record real network volume, then drop the FITS cache (Parquet is the canonical store).
        try:
            cached = list(CACHE_DIR.rglob("*.fits")) + list(CACHE_DIR.rglob("*.fits.gz"))
            for f in cached:
                fits_bytes += f.stat().st_size
                f.unlink()
        except OSError:
            pass
        rel = str(out.relative_to(REPO_ROOT))
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO lightcurve_file (tic_id, sector, author, cadence_s, flux_kind,
                       mission, path, n_points, t_start, t_end, ingest_run_id)
                   VALUES (%s,%s,%s,%s,%s,'TESS',%s,%s,%s,%s,%s)
                   ON CONFLICT (tic_id, sector, author, cadence_s) DO NOTHING""",
                (tic, sector, author, cadence, flux_kind, rel, len(t),
                 float(t.min()), float(t.max()), run_id),
            )
        conn.commit()
        runlog.finish_run(conn, run_id, len(t), fits_bytes, "ok",
                          f"{author} {flux_kind} {len(t)}pts")
        return {"sector": sector, "author": author, "n": len(t), "bytes": fits_bytes}
    except Exception as exc:  # noqa: BLE001 - one bad sector must not abort the target
        conn.rollback()
        runlog.finish_run(conn, run_id, 0, 0, "error", str(exc)[:2000])
        logger.warning("TIC %s sector %s download failed: %s", tic, sector, exc)
        return None


def fetch_tic(conn, tic: int, lk, np, pd) -> dict:
    have = _already_have(conn, tic)
    run_id = runlog.start_run(conn, "mast", f"search:TIC{tic}")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            search = lk.search_lightcurve(f"TIC {tic}", mission="TESS")
        runlog.finish_run(conn, run_id, len(search), 0, "ok", f"{len(search)} products")
    except Exception as exc:  # noqa: BLE001
        runlog.finish_run(conn, run_id, 0, 0, "error", str(exc)[:2000])
        logger.warning("TIC %s search failed: %s", tic, exc)
        return {"tic": tic, "sectors": 0, "bytes": 0, "error": str(exc)}

    picks = _best_per_sector(search)
    downloaded, total_bytes, skipped = 0, 0, 0
    for sector in sorted(picks):
        idx = picks[sector]
        author = str(search.table["author"][idx])
        cadence = (int(round(float(search.table["exptime"][idx])))
                   if "exptime" in search.table.colnames else None)
        if (sector, author, cadence) in have:
            skipped += 1
            continue
        res = _download_sector(conn, tic, sector, author, search[idx], np, pd)
        if res:
            downloaded += 1
            total_bytes += res["bytes"]
        time.sleep(POLITE_DELAY_S)
    logger.info("TIC %s: %d sectors downloaded, %d already present, %.1f MB",
                tic, downloaded, skipped, total_bytes / 1e6)
    return {"tic": tic, "sectors": downloaded, "skipped": skipped, "bytes": total_bytes}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Download TESS light curves for the target slice.")
    parser.add_argument("--limit", type=int, default=None, help="cap number of TICs (smoke test)")
    parser.add_argument("--tic", type=int, default=None, help="fetch a single TIC")
    args = parser.parse_args()

    lk, np, pd = _lazy_imports()
    LC_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    try:
        tics = [args.tic] if args.tic else _selected_tics(conn)
        if args.limit:
            tics = tics[: args.limit]
        started = dt.datetime.now()
        results = [fetch_tic(conn, tic, lk, np, pd) for tic in tics]
    finally:
        conn.close()

    tot_sectors = sum(r.get("sectors", 0) for r in results)
    tot_bytes = sum(r.get("bytes", 0) for r in results)
    errors = [r for r in results if r.get("error")]
    print(f"\n=== fetch complete in {(dt.datetime.now() - started).total_seconds():.0f}s ===")
    print(f"  TICs: {len(results)}  new sectors: {tot_sectors}  volume: {tot_bytes / 1e6:.1f} MB")
    if errors:
        print(f"  search errors: {len(errors)} -> {[e['tic'] for e in errors]}")


if __name__ == "__main__":
    main()
