"""Citation text served from the ps source_ref: tags stripped, entities decoded."""

from api.queries import _clean_ref


def test_strips_the_anchor_and_decodes_named_entities():
    ref = (
        "<a refstr=GAJDOS_ET_AL__2019 href=https://ui.adsabs.harvard.edu/abs/x>"
        "Gajdo&scaron; et al. 2019</a>"
    )
    assert _clean_ref(ref) == "Gajdoš et al. 2019"


def test_decodes_an_escaped_ampersand_once():
    assert _clean_ref("<a href=x>Fulton &amp; Petigura 2018</a>") == "Fulton & Petigura 2018"


def test_a_decoded_angle_bracket_is_text_not_a_tag():
    assert _clean_ref("<a href=x>R &lt; 2 R&oplus; sample</a>") == "R < 2 R⊕ sample"


def test_empty_and_missing_refs_pass_through():
    assert _clean_ref(None) is None
    assert _clean_ref("") == ""
    assert _clean_ref("<a href=x></a>") is None
