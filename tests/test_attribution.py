"""The attribution names every source the site serves data from, and the web fixture says the same.

No database: ``attribution()`` is static. The light-curve check serves TESS light curves from
MAST, and the Follow-up tool serves satellite positions and owners that Orbital Economy
Intelligence builds from CelesTrak, Space-Track and GCAT, so each of them is credited. Mock mode
renders ``web/src/api/fixtures/attribution.json``, which has to match what the API serves.
"""

import json
import pathlib

from api.queries import attribution

FIXTURE = pathlib.Path(__file__).resolve().parents[1] / "web/src/api/fixtures/attribution.json"


def _source(name: str) -> dict:
    return next(s for s in attribution()["sources"] if s["name"] == name)


def test_mast_is_credited_with_its_own_tess_acknowledgement():
    mast = _source("MAST")
    assert mast["url"] == "https://archive.stsci.edu/"
    assert "light curves" in mast["used_for"]
    assert mast["citation"].startswith(
        "This paper includes data collected with the TESS mission, obtained from the MAST data "
        "archive at the Space Telescope Science Institute (STScI)."
    )
    assert mast["citation"].endswith("under NASA contract NAS5-26555.")


def test_the_satellite_sources_behind_follow_up_are_credited():
    sats = _source("CelesTrak, Space-Track and GCAT")
    for name in ("CelesTrak", "Space-Track", "GCAT", "Orbital Economy Intelligence"):
        assert name in sats["used_for"]
    # GCAT is CC-BY: its page asks for this citation
    assert "McDowell, J, 2020: General Catalog of Artificial Space Objects" in sats["citation"]


def test_the_notes_do_not_claim_the_live_counts_track_the_v0_report():
    notes = attribution()["notes"]
    assert "track the v0" not in notes
    assert "no longer match the figures in the frozen v0 conflict report" in notes


def test_the_mock_fixture_matches_the_api():
    assert json.loads(FIXTURE.read_text()) == attribution()
