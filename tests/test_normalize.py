"""Pure normalization + matching primitives."""

from identity.normalize import (
    canonical_candidate_name,
    norm_name,
    period_rel_diff,
    periods_match,
    rel_diff,
)


def test_norm_name_unifies_forms():
    assert norm_name("Kepler-227 b") == "kepler 227 b"
    assert norm_name("KEPLER 227 B") == "kepler 227 b"
    assert norm_name(None) == ""
    assert norm_name("  TOI-1836  ") == "toi 1836"


def test_period_rel_diff():
    assert period_rel_diff(5.0, 5.0) == 0.0
    assert period_rel_diff(5.0, None) is None
    assert period_rel_diff(5.0, 0) is None
    assert abs(period_rel_diff(5.0, 5.05) - 0.05 / 5.05) < 1e-9


def test_periods_match_one_percent_tolerance():
    assert periods_match(5.0, 5.03)        # 0.6% -> same candidate
    assert not periods_match(5.0, 5.06)    # 1.2% -> different candidate
    assert not periods_match(5.0, None)    # missing period never matches
    assert not periods_match(5.0, 10.0)    # 2x alias is not a 1% match


def test_rel_diff_symmetric():
    assert rel_diff(2.0, 4.0) == 0.5
    assert rel_diff(4.0, 2.0) == 0.5
    assert rel_diff(None, 4.0) is None


def test_canonical_candidate_name_priority():
    assert canonical_candidate_name({"planet": "Kepler-227 b", "toi": "1"}) == "Kepler-227 b"
    assert canonical_candidate_name({"toi": "1836.01"}) == "TOI 1836.01"
    assert canonical_candidate_name({"koi": "K00752.01"}) == "KOI K00752.01"
    assert canonical_candidate_name({"ctoi": "17361.01"}) == "CTOI 17361.01"
    assert canonical_candidate_name({"fallback": "star 5"}) == "star 5"
