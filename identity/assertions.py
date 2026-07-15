"""Extract per-attribute source claims into source_assertion (provenance before resolution).

One assertion per (attribute, source row), attached to the star/candidate through the crosswalk
(id_type + originating source + id_value). ps carries per-publication refs (pl_refname/st_refname)
so its competing rows stay distinguishable — this is the exoplanet analog of "SATCAT says X, GCAT
says Y", except ps disagrees with *itself* across publications. Idempotent within a rebuild; no
commit (the caller owns the transaction). Ported in shape from the satellite platform's
identity/assertions.py.
"""

from __future__ import annotations

# Each spec: (attribute, value_sql, unit, ref_sql). value_sql/ref_sql are expressions over the
# aliased raw row `r`. A NULL value_sql yields no assertion for that row.
# ps.pl_trandep / pscomppars.pl_trandep are PERCENT -> convert to ppm (*10000) for a like-for-like
# depth comparison against the ppm sources.
_CANDIDATE_ATTRS = {
    "exofop_toi": [
        ("period_days", "r.period_days", "days", "NULL"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "NULL"),
        ("depth_ppm", "r.depth_ppm", "ppm", "NULL"),
        ("duration_hr", "r.duration_hr", "hr", "NULL"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "NULL"),
        ("disposition", "r.tfopwg_disposition", None, "NULL"),
    ],
    "nea_toi": [
        ("period_days", "r.period_days", "days", "NULL"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "NULL"),
        ("depth_ppm", "r.depth_ppm", "ppm", "NULL"),
        ("duration_hr", "r.duration_hr", "hr", "NULL"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "NULL"),
        ("disposition", "r.tfopwg_disp", None, "NULL"),
    ],
    "exofop_ctoi": [
        ("period_days", "r.period_days", "days", "NULL"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "NULL"),
        ("depth_ppm", "r.depth_ppm", "ppm", "NULL"),
        ("duration_hr", "r.duration_hr", "hr", "NULL"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "NULL"),
        ("disposition", "r.user_disposition", None, "NULL"),
    ],
    "koi": [
        ("period_days", "r.period_days", "days", "NULL"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "NULL"),
        ("depth_ppm", "r.depth_ppm", "ppm", "NULL"),
        ("duration_hr", "r.duration_hr", "hr", "NULL"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "NULL"),
        ("disposition", "r.koi_disposition", None, "NULL"),
    ],
    "ps": [
        ("period_days", "r.period_days", "days", "r.pl_refname"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "r.pl_refname"),
        ("depth_ppm", "r.depth_pct * 10000", "ppm", "r.pl_refname"),
        ("duration_hr", "r.duration_hr", "hr", "r.pl_refname"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "r.pl_refname"),
        ("disposition",
         "CASE WHEN r.pl_controv_flag = 1 THEN 'CONTROVERSIAL' ELSE r.soltype END",
         None, "r.pl_refname"),
    ],
    "pscomppars": [
        ("period_days", "r.period_days", "days", "NULL"),
        ("planet_radius_re", "r.planet_radius_re", "R_earth", "NULL"),
        ("depth_ppm", "r.depth_pct * 10000", "ppm", "NULL"),
        ("duration_hr", "r.duration_hr", "hr", "NULL"),
        ("epoch_bjd", "r.epoch_bjd", "bjd", "NULL"),
        ("disposition", "'CONFIRMED'", None, "NULL"),
    ],
}
_STAR_ATTRS = {
    "exofop_toi": [
        ("teff_k", "r.teff_k", "K", "NULL"),
        ("logg", "r.logg", "log_cgs", "NULL"),
        ("rstar_rsun", "r.rstar_rsun", "R_sun", "NULL"),
        ("tmag", "r.tmag", "mag", "NULL"),
    ],
    "nea_toi": [
        ("teff_k", "r.teff_k", "K", "NULL"),
        ("logg", "r.logg", "log_cgs", "NULL"),
        ("rstar_rsun", "r.rstar_rsun", "R_sun", "NULL"),
        ("tmag", "r.tmag", "mag", "NULL"),
    ],
    "koi": [
        ("teff_k", "r.teff_k", "K", "NULL"),
        ("logg", "r.logg", "log_cgs", "NULL"),
        ("rstar_rsun", "r.rstar_rsun", "R_sun", "NULL"),
    ],
    "ps": [
        ("teff_k", "r.teff_k", "K", "r.st_refname"),
        ("logg", "r.logg", "log_cgs", "r.st_refname"),
        ("rstar_rsun", "r.rstar_rsun", "R_sun", "r.st_refname"),
        ("vmag", "r.vmag", "mag", "r.st_refname"),
        ("tmag", "r.tmag", "mag", "r.st_refname"),
    ],
    "pscomppars": [
        ("teff_k", "r.teff_k", "K", "NULL"),
        ("logg", "r.logg", "log_cgs", "NULL"),
        ("rstar_rsun", "r.rstar_rsun", "R_sun", "NULL"),
        ("vmag", "r.vmag", "mag", "NULL"),
        ("tmag", "r.tmag", "mag", "NULL"),
    ],
}

# (raw_table, source_token, key_expr, crosswalk id_type, crosswalk origin-source). key_expr is the
# source-native object key AND the crosswalk id_value that joins the row back to its entity.
_CANDIDATE_SOURCES = [
    ("raw_exofop_toi", "exofop_toi", "r.toi", "toi", "exofop"),
    ("raw_nea_toi", "nea_toi", "r.toi", "toi", "nea"),
    ("raw_exofop_ctoi", "exofop_ctoi", "r.ctoi", "ctoi", "exofop"),
    ("raw_koi_cumulative", "koi", "r.kepoi_name", "koi", "nea"),
    ("raw_ps", "ps", "r.pl_name", "name", "nea"),
    ("raw_pscomppars", "pscomppars", "r.pl_name", "name", "nea"),
]
_STAR_SOURCES = [
    ("raw_exofop_toi", "exofop_toi", "r.tic_id::text", "tic", "exofop"),
    ("raw_nea_toi", "nea_toi", "r.tid::text", "tic", "nea"),
    ("raw_ps", "ps", "r.tic_id::text", "tic", "nea"),
    ("raw_pscomppars", "pscomppars", "r.tic_id::text", "tic", "nea"),
    ("raw_koi_cumulative", "koi", "r.kepid::text", "kic", "nea"),
]


def _latest_run(conn, table: str) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT max(r.ingest_run_id) FROM {table} r "
            "JOIN ingest_run i ON i.ingest_run_id = r.ingest_run_id WHERE i.status = 'ok'"
        )
        return cur.fetchone()[0]


def _extract_one(conn, table, source, key_expr, id_type, xsource, entity_col, attrs, run) -> None:
    with conn.cursor() as cur:
        for attribute, value_sql, unit, ref_sql in attrs:
            cur.execute(
                f"""
                INSERT INTO source_assertion
                    ({entity_col}, source_key, attribute, value, unit, source, source_ref,
                     observed_at, ingest_run_id)
                SELECT ei.{entity_col}, ({key_expr})::text, %(attr)s, ({value_sql})::text,
                       %(unit)s, %(src)s, ({ref_sql}), r.loaded_at, r.ingest_run_id
                FROM {table} r
                JOIN entity_identifier ei
                  ON ei.id_type = %(id_type)s AND ei.source = %(xsource)s
                 AND ei.id_value = ({key_expr})::text AND ei.{entity_col} IS NOT NULL
                WHERE r.ingest_run_id = %(run)s AND ({value_sql}) IS NOT NULL
                """,
                {"attr": attribute, "unit": unit, "src": source, "id_type": id_type,
                 "xsource": xsource, "run": run},
            )


def extract(conn) -> None:
    """Extract candidate + star assertions from every source's latest snapshot."""
    for table, source, key_expr, id_type, xsource in _CANDIDATE_SOURCES:
        run = _latest_run(conn, table)
        if run is None:
            continue
        _extract_one(conn, table, source, key_expr, id_type, xsource, "candidate_id",
                     _CANDIDATE_ATTRS[source], run)
    for table, source, key_expr, id_type, xsource in _STAR_SOURCES:
        run = _latest_run(conn, table)
        if run is None or source not in _STAR_ATTRS:
            continue
        _extract_one(conn, table, source, key_expr, id_type, xsource, "star_id",
                     _STAR_ATTRS[source], run)
