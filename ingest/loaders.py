"""Catalog loaders: land each source's raw CSV verbatim, once, politely, ledgered.

Six one-time bulk pulls feed Wave 1:
  - ExoFOP TESS TOI list  (download_toi.php CSV)
  - ExoFOP TESS CTOI list (download_ctoi.php CSV)
  - NASA Exoplanet Archive TAP `toi`, `cumulative` (KOI), `ps`, `pscomppars` (ADQL, format=csv)

Every pull goes through ingest.runlog.polite_get (24h freshness gate, User-Agent, ledger row).
Each source's typed identity/attribute columns are projected out of the CSV by header name; the
ENTIRE raw row is also kept verbatim in the `extra` JSONB column (provenance discipline). A single
malformed numeric/date cell degrades to NULL (logged) rather than aborting a ~7k/40k-row load.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import urllib.parse

from psycopg.types.json import Jsonb

from ingest import runlog

logger = logging.getLogger(__name__)

MIN_INTERVAL = dt.timedelta(hours=24)

EXOFOP_TOI_URL = "https://exofop.ipac.caltech.edu/tess/download_toi.php?sort=toi&output=csv"
EXOFOP_CTOI_URL = "https://exofop.ipac.caltech.edu/tess/download_ctoi.php?sort=ctoi&output=csv"
NEA_TAP_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

# ADQL for each Archive table (explicit column lists keep the CSV narrow and stable).
NEA_QUERIES = {
    "toi": (
        "select toi,toipfx,tid,ctoi_alias,tfopwg_disp,pl_orbper,pl_trandurh,pl_trandep,"
        "pl_rade,pl_tranmid,st_teff,st_logg,st_rad,st_tmag,ra,dec,rowupdate from toi"
    ),
    "cumulative": (
        "select kepid,kepoi_name,kepler_name,koi_disposition,koi_pdisposition,koi_period,"
        "koi_duration,koi_depth,koi_prad,koi_time0bk,koi_steff,koi_slogg,koi_srad,koi_kepmag,"
        "ra,dec from cumulative"
    ),
    "ps": (
        "select pl_name,hostname,tic_id,gaia_dr3_id,hd_name,hip_name,default_flag,soltype,"
        "pl_controv_flag,pl_orbper,pl_rade,pl_trandep,pl_trandur,pl_tranmid,st_teff,st_logg,"
        "st_rad,sy_vmag,sy_tmag,ra,dec,disc_facility,pl_refname,st_refname,pl_pubdate from ps"
    ),
    "pscomppars": (
        "select pl_name,hostname,tic_id,gaia_dr3_id,hd_name,hip_name,pl_orbper,pl_rade,pl_trandep,"
        "pl_trandur,pl_tranmid,st_teff,st_logg,st_rad,sy_vmag,sy_tmag,ra,dec,disc_facility "
        "from pscomppars"
    ),
}

# Column maps: (typed_column, csv_header, kind). kind in {int, num, text}. The header is matched
# case-insensitively; unmatched headers still land verbatim in `extra`.
_EXOFOP_TOI_COLS = [
    ("toi", "TOI", "text"),
    ("tic_id", "TIC ID", "int"),
    ("tfopwg_disposition", "TFOPWG Disposition", "text"),
    ("tess_disposition", "TESS Disposition", "text"),
    ("period_days", "Period (days)", "num"),
    ("duration_hr", "Duration (hours)", "num"),
    ("depth_ppm", "Depth (ppm)", "num"),
    ("planet_radius_re", "Planet Radius (R_Earth)", "num"),
    ("epoch_bjd", "Epoch (BJD)", "num"),
    ("teff_k", "Stellar Eff Temp (K)", "num"),
    ("logg", "Stellar log(g) (cm/s^2)", "num"),
    ("rstar_rsun", "Stellar Radius (R_Sun)", "num"),
    ("tmag", "TESS Mag", "num"),
    ("ra_deg", "RA", "num"),         # sexagesimal in the TOI CSV -> NULL (TOI joins by TIC)
    ("dec_deg", "Dec", "num"),
]
_EXOFOP_CTOI_COLS = [
    ("ctoi", "CTOI", "text"),
    ("tic_id", "TIC ID", "int"),
    ("promoted_to_toi", "Promoted to TOI", "text"),
    ("user_disposition", "User Disposition", "text"),
    ("period_days", "Period (days)", "num"),
    ("duration_hr", "Duration (hrs)", "num"),
    ("depth_ppm", "Depth ppm", "num"),
    ("planet_radius_re", "Planet Radius (R_Earth)", "num"),
    ("epoch_bjd", "Transit Epoch (BJD)", "num"),
    ("tmag", "TESS Mag", "num"),
    ("ra_deg", "RA", "num"),
    ("dec_deg", "Dec", "num"),
]
_NEA_TOI_COLS = [
    ("toi", "toi", "text"),
    ("tid", "tid", "int"),
    ("tfopwg_disp", "tfopwg_disp", "text"),
    ("period_days", "pl_orbper", "num"),
    ("duration_hr", "pl_trandurh", "num"),
    ("depth_ppm", "pl_trandep", "num"),
    ("planet_radius_re", "pl_rade", "num"),
    ("epoch_bjd", "pl_tranmid", "num"),
    ("teff_k", "st_teff", "num"),
    ("logg", "st_logg", "num"),
    ("rstar_rsun", "st_rad", "num"),
    ("tmag", "st_tmag", "num"),
    ("ra_deg", "ra", "num"),
    ("dec_deg", "dec", "num"),
]
_KOI_COLS = [
    ("kepid", "kepid", "int"),
    ("kepoi_name", "kepoi_name", "text"),
    ("kepler_name", "kepler_name", "text"),
    ("koi_disposition", "koi_disposition", "text"),
    ("koi_pdisposition", "koi_pdisposition", "text"),
    ("period_days", "koi_period", "num"),
    ("duration_hr", "koi_duration", "num"),
    ("depth_ppm", "koi_depth", "num"),
    ("planet_radius_re", "koi_prad", "num"),
    ("epoch_bjd", "koi_time0bk", "num"),
    ("teff_k", "koi_steff", "num"),
    ("logg", "koi_slogg", "num"),
    ("rstar_rsun", "koi_srad", "num"),
    ("kepmag", "koi_kepmag", "num"),
    ("ra_deg", "ra", "num"),
    ("dec_deg", "dec", "num"),
]
_PS_COLS = [
    ("pl_name", "pl_name", "text"),
    ("hostname", "hostname", "text"),
    ("tic_id", "tic_id", "tic"),
    ("gaia_id", "gaia_dr3_id", "text"),
    ("hd_name", "hd_name", "text"),
    ("hip_name", "hip_name", "text"),
    ("default_flag", "default_flag", "int"),
    ("soltype", "soltype", "text"),
    ("pl_controv_flag", "pl_controv_flag", "int"),
    ("period_days", "pl_orbper", "num"),
    ("planet_radius_re", "pl_rade", "num"),
    ("depth_pct", "pl_trandep", "num"),
    ("duration_hr", "pl_trandur", "num"),
    ("epoch_bjd", "pl_tranmid", "num"),
    ("teff_k", "st_teff", "num"),
    ("logg", "st_logg", "num"),
    ("rstar_rsun", "st_rad", "num"),
    ("vmag", "sy_vmag", "num"),
    ("tmag", "sy_tmag", "num"),
    ("ra_deg", "ra", "num"),
    ("dec_deg", "dec", "num"),
    ("disc_facility", "disc_facility", "text"),
    ("pl_refname", "pl_refname", "text"),
    ("st_refname", "st_refname", "text"),
    ("pl_pubdate", "pl_pubdate", "text"),
]
_PSCOMPPARS_COLS = [
    ("pl_name", "pl_name", "text"),
    ("hostname", "hostname", "text"),
    ("tic_id", "tic_id", "tic"),
    ("gaia_id", "gaia_dr3_id", "text"),
    ("hd_name", "hd_name", "text"),
    ("hip_name", "hip_name", "text"),
    ("period_days", "pl_orbper", "num"),
    ("planet_radius_re", "pl_rade", "num"),
    ("depth_pct", "pl_trandep", "num"),
    ("duration_hr", "pl_trandur", "num"),
    ("epoch_bjd", "pl_tranmid", "num"),
    ("teff_k", "st_teff", "num"),
    ("logg", "st_logg", "num"),
    ("rstar_rsun", "st_rad", "num"),
    ("vmag", "sy_vmag", "num"),
    ("tmag", "sy_tmag", "num"),
    ("ra_deg", "ra", "num"),
    ("dec_deg", "dec", "num"),
    ("disc_facility", "disc_facility", "text"),
]


def _coerce(kind: str, value: str | None):
    """Coerce one CSV cell to its column type. Un-coercible typed values degrade to NULL (logged)
    so a single bad cell never aborts a bulk load.

    kind 'tic' strips the Archive's "TIC " prefix (the ps/pscomppars tic_id column ships as
    "TIC 158722002", not a bare integer) before parsing the digits.
    """
    value = (value or "").strip()
    if value == "":
        return None
    try:
        if kind == "tic":
            digits = value.upper().removeprefix("TIC").strip()
            return int(digits) if digits.isdigit() else None
        if kind == "int":
            return int(float(value))  # tolerate '12345.0'
        if kind == "num":
            return float(value)
    except ValueError:
        logger.warning("dropping unparseable %s cell %r -> NULL", kind, value)
        return None
    return value


def parse_rows(text: str, colmap: list[tuple[str, str, str]]) -> list[dict]:
    """Parse CSV text into landing dicts: one per row, with typed columns projected out of the CSV
    by (case-insensitive) header name plus an `extra` dict holding the entire raw row verbatim.

    NASA TAP comment/error responses (which begin with 'ERROR' rather than a CSV header) raise so
    the caller can ledger the failure instead of silently landing zero rows.
    """
    head = text.lstrip()[:200].upper()
    if head.startswith("ERROR") or "<VOTABLE" in head:
        raise ValueError(f"source returned a non-CSV error payload: {text[:300]!r}")
    reader = csv.DictReader(io.StringIO(text))
    header_lookup = {h.strip().lower(): h for h in (reader.fieldnames or [])}
    plan = [
        (typed, header_lookup[header.lower()], kind)
        for typed, header, kind in colmap
        if header.lower() in header_lookup
    ]
    rows = []
    for raw_row in reader:
        typed = {typed_col: _coerce(kind, raw_row.get(src)) for typed_col, src, kind in plan}
        typed["extra"] = {k: v for k, v in raw_row.items() if k is not None}
        rows.append(typed)
    return rows


def _land(conn, table: str, rows: list[dict], colmap, run_id: int) -> int:
    typed_cols = [c[0] for c in colmap]
    all_cols = [*typed_cols, "extra", "ingest_run_id"]
    placeholders = ", ".join(["%s"] * len(all_cols))
    sql = f"INSERT INTO {table} ({', '.join(all_cols)}) VALUES ({placeholders})"
    with conn.cursor() as cur:
        for row in rows:
            values = [row.get(c) for c in typed_cols]
            values.append(Jsonb(row.get("extra", {})))
            values.append(run_id)
            cur.execute(sql, values)
    conn.commit()
    return len(rows)


def _run(conn, source, endpoint, url, table, colmap) -> int:
    """Pull one source, land it verbatim, and close the ledger row. Returns rows landed (0 if the
    pull was skipped as fresh)."""
    resp = runlog.polite_get(conn, source, endpoint, url, MIN_INTERVAL)
    if resp is None:
        logger.info("%s/%s: skipped, fresh run within %s", source, endpoint, MIN_INTERVAL)
        return 0
    try:
        rows = parse_rows(resp.text, colmap)
        n = _land(conn, table, rows, colmap, resp.exo_run_id)
    except Exception as exc:
        conn.rollback()
        runlog.finish_run(
            conn, resp.exo_run_id, rows=0, bytes_dl=resp.exo_bytes, status="error",
            notes=str(exc)[:2000],
        )
        raise
    runlog.finish_run(conn, resp.exo_run_id, rows=n, bytes_dl=resp.exo_bytes, status="ok")
    logger.info("%s/%s: landed %d rows into %s", source, endpoint, n, table)
    return n


def _tap_url(table: str) -> str:
    q = urllib.parse.urlencode({"query": NEA_QUERIES[table], "format": "csv"})
    return f"{NEA_TAP_URL}?{q}"


def run_exofop_toi(conn) -> int:
    return _run(conn, "exofop", "toi_csv", EXOFOP_TOI_URL, "raw_exofop_toi", _EXOFOP_TOI_COLS)


def run_exofop_ctoi(conn) -> int:
    return _run(conn, "exofop", "ctoi_csv", EXOFOP_CTOI_URL, "raw_exofop_ctoi", _EXOFOP_CTOI_COLS)


def run_nea_toi(conn) -> int:
    return _run(conn, "nea", "tap_toi", _tap_url("toi"), "raw_nea_toi", _NEA_TOI_COLS)


def run_koi_cumulative(conn) -> int:
    return _run(
        conn, "nea", "tap_cumulative", _tap_url("cumulative"), "raw_koi_cumulative", _KOI_COLS
    )


def run_ps(conn) -> int:
    return _run(conn, "nea", "tap_ps", _tap_url("ps"), "raw_ps", _PS_COLS)


def run_pscomppars(conn) -> int:
    return _run(conn, "nea", "tap_pscomppars", _tap_url("pscomppars"), "raw_pscomppars",
                _PSCOMPPARS_COLS)


ALL_LOADERS = [
    run_exofop_toi,
    run_exofop_ctoi,
    run_nea_toi,
    run_koi_cumulative,
    run_ps,
    run_pscomppars,
]
