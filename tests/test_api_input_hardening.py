"""Inputs that used to reach SQL or the calendar unchecked and surface as 500s.

Pure: these exercise the helpers the routes call, with no database.
"""

import datetime as dt
import html

import pytest
from fastapi import HTTPException

from api import queries
from api.routers import twoskies
from api.seo import render_head

SHELL = """<!doctype html><html><head><title>x</title>
<meta name="description" content="d" />
<link rel="canonical" href="https://exo.vibcreates.com/" />
<meta property="og:title" content="t" /><meta property="og:description" content="d" />
<meta property="og:url" content="https://exo.vibcreates.com/" />
<meta name="twitter:title" content="t" /><meta name="twitter:description" content="d" />
</head><body></body></html>"""


def test_ascii_int_rejects_unicode_digits():
    """str.isdigit() is true for "²" and "①", which int() rejects: a 500 on /api/target/²."""
    assert queries.ascii_int("10589") == 10589
    assert queries.ascii_int("²") is None
    assert queries.ascii_int("①") is None
    assert queries.ascii_int("١٢") is None
    assert queries.ascii_int("12a") is None
    assert queries.ascii_int("") is None


def test_catalog_prefix_is_stripped_before_matching():
    """Identifiers are stored bare, so the site's own example "TIC 278892590" found nothing."""
    assert queries.strip_catalog_prefix("TIC 278892590") == "278892590"
    assert queries.strip_catalog_prefix("tic-278892590") == "278892590"
    assert queries.strip_catalog_prefix("Gaia DR3 2635476908753563008") == "2635476908753563008"
    assert queries.strip_catalog_prefix("TOI-1836") == "TOI-1836"  # TOI numbers are stored as TOI
    assert queries.strip_catalog_prefix("TRAPPIST-1") == "TRAPPIST-1"


def test_like_metacharacters_are_literal():
    assert queries.like_escape("100%") == "100\\%"
    assert queries.like_escape("a_b") == "a\\_b"
    assert queries.like_escape("back\\slash") == "back\\\\slash"


def test_datetime_overflow_is_a_422_not_a_500():
    with pytest.raises(HTTPException) as e:
        twoskies._parse_datetime("0001-01-01T00:00:00+01:00")
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        twoskies._parse_datetime("9999-12-31T23:30:00Z")
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e:
        twoskies._parse_datetime("not a date")
    assert e.value.status_code == 422


def test_datetime_near_now_parses_to_utc():
    parsed = twoskies._parse_datetime("2026-11-04T05:00:00+02:00")
    assert parsed == dt.datetime(2026, 11, 4, 3, 0, tzinfo=dt.UTC)
    assert twoskies._parse_datetime(None).tzinfo is dt.UTC


def test_time_grid_is_capped_by_coarsening_the_step():
    steps, step = twoskies._time_grid(60, 30)
    assert (steps, step) == (121, 30)
    steps, step = twoskies._time_grid(180, 15)  # 721 points before; the step coarsens
    assert steps <= twoskies.MAX_STEPS
    assert step >= 45


def test_canonical_percent_encodes_a_param_with_a_space():
    out, status = render_head(SHELL, "/target/TOI-1836 b")  # the ASGI path is decoded
    assert status == 200
    assert 'href="https://exo.vibcreates.com/target/TOI-1836%20b"' in out


def test_canonical_encodes_like_encode_uri_component():
    # the client builds its canonical with encodeURIComponent, which keeps ! * ' ( ) bare and
    # encodes + and ,: the server-rendered head must agree character for character
    out, status = render_head(SHELL, "/target/Teegarden's Star b (c), d+e")
    assert status == 200
    expected = "https://exo.vibcreates.com/target/Teegarden's%20Star%20b%20(c)%2C%20d%2Be"
    assert f'href="{html.escape(expected)}"' in out  # the apostrophe is attribute-escaped
