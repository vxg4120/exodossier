"""Loader parsing: typed projection, verbatim `extra`, the TIC-prefix quirk, TAP error guard."""

import pytest

from ingest import loaders

_TOI_CSV = (
    "TIC ID,TOI,TFOPWG Disposition,Period (days),Planet Radius (R_Earth),Stellar Eff Temp (K)\n"
    "231663901,101.01,KP,1.4303699,13.187,5600\n"
    "12345,900.01,PC,,2.1,\n"
)

_PS_CSV = (
    "pl_name,hostname,tic_id,gaia_dr3_id,pl_orbper,pl_rade,pl_trandep\n"
    "Kepler-227 b,Kepler-227,TIC 158722002,Gaia DR3 123,9.488,2.26,0.05\n"
)


def test_parse_toi_typed_projection_and_extra():
    rows = loaders.parse_rows(_TOI_CSV, loaders._EXOFOP_TOI_COLS)
    assert len(rows) == 2
    r0 = rows[0]
    assert r0["tic_id"] == 231663901
    assert r0["toi"] == "101.01"
    assert r0["tfopwg_disposition"] == "KP"
    assert abs(r0["period_days"] - 1.4303699) < 1e-6
    assert r0["teff_k"] == 5600.0
    # The full raw row is preserved verbatim in extra.
    assert r0["extra"]["TIC ID"] == "231663901"
    # Empty typed cells coerce to None.
    assert rows[1]["period_days"] is None
    assert rows[1]["teff_k"] is None


def test_parse_ps_strips_tic_prefix():
    rows = loaders.parse_rows(_PS_CSV, loaders._PS_COLS)
    assert rows[0]["tic_id"] == 158722002        # "TIC 158722002" -> 158722002
    assert rows[0]["gaia_id"] == "Gaia DR3 123"
    assert rows[0]["pl_name"] == "Kepler-227 b"


def test_tic_coercion_direct():
    assert loaders._coerce("tic", "TIC 158722002") == 158722002
    assert loaders._coerce("tic", "158722002") == 158722002
    assert loaders._coerce("tic", "") is None
    assert loaders._coerce("tic", "not a tic") is None


def test_tap_error_payload_raises():
    with pytest.raises(ValueError, match="non-CSV error"):
        loaders.parse_rows("ERROR\nORA-00904: invalid identifier\n", loaders._PS_COLS)


_TOI_SEXAGESIMAL_CSV = (
    "TIC ID,TOI,RA,Dec\n"
    "231663901,101.01,21:14:56.88,-55:52:18.71\n"
    "12345,900.01,05:48:33.56,+12:01:02.3\n"
    "67890,901.01,,\n"
)


def test_unparseable_cells_log_once_per_column_not_once_per_cell(caplog):
    """The TOI list ships RA/Dec as sexagesimal strings, which stay NULL by design (a TOI joins
    its star by TIC). One warning per cell wrote 16,296 lines into every nightly log, so its
    10 MB rotation kept only about ten days of the nightly's failure record."""
    with caplog.at_level("WARNING", logger="ingest.loaders"):
        rows = loaders.parse_rows(_TOI_SEXAGESIMAL_CSV, loaders._EXOFOP_TOI_COLS)
    assert [(r["ra_deg"], r["dec_deg"]) for r in rows] == [(None, None)] * 3
    warnings = [r.getMessage() for r in caplog.records]
    assert warnings == [
        "dropping 2 unparseable num cells in RA -> NULL (e.g. '21:14:56.88')",
        "dropping 2 unparseable num cells in Dec -> NULL (e.g. '-55:52:18.71')",
    ]
