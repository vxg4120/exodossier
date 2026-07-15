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
