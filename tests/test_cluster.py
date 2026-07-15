"""Candidate clustering ER rules (pure — identity.build._cluster_star operates on plain dicts)."""

from identity.build import _cluster_star


def _obs(id_type, value, xsource, period, planet_name=None):
    return {"id_type": id_type, "value": value, "xsource": xsource,
            "period": period, "planet_name": planet_name}


def test_same_designation_two_sources_one_candidate():
    # The same TOI number seen by ExoFOP and the Archive is one candidate carrying both sources.
    clusters, ambiguous = _cluster_star([
        _obs("toi", "101.01", "exofop", 1.43),
        _obs("toi", "101.01", "nea", 1.43),
    ])
    assert len(clusters) == 1
    assert ambiguous == []
    group = clusters[0]["groups"][("toi", "101.01")]
    assert group["xsources"] == {"exofop", "nea"}


def test_cross_designation_period_unification():
    # A TOI and a confirmed planet (ps name) on the same star with matching period -> one candidate.
    clusters, ambiguous = _cluster_star([
        _obs("toi", "174.01", "exofop", 3.7695),
        _obs("name", "HD 3167 b", "nea", 3.7700, planet_name="HD 3167 b"),
    ])
    assert len(clusters) == 1
    assert ambiguous == []
    cluster = clusters[0]
    assert set(cluster["groups"].keys()) == {("toi", "174.01"), ("name", "HD 3167 b")}
    # 'name' sorts first so it seeds; the TOI joins by period and is audited as such (no silent
    # merge) — exactly one group carries the period-match rule.
    assert cluster["join_rule"][("name", "HD 3167 b")] == "candidate_seed"
    assert cluster["join_rule"][("toi", "174.01")] == "period_match<1pct"


def test_distinct_periods_stay_separate():
    clusters, ambiguous = _cluster_star([
        _obs("name", "K b", "nea", 5.00, planet_name="K b"),
        _obs("name", "K c", "nea", 12.00, planet_name="K c"),
    ])
    assert len(clusters) == 2
    assert ambiguous == []


def test_ambiguous_period_is_flagged_not_merged():
    # A period that matches TWO existing clusters must NOT be silently merged; it is flagged.
    clusters, ambiguous = _cluster_star([
        _obs("name", "A", "nea", 5.00, planet_name="A"),   # seeds cluster @5.00
        _obs("name", "C", "nea", 5.06, planet_name="C"),   # 1.2% from A -> new cluster @5.06
        _obs("toi", "9.01", "exofop", 5.03),               # 0.6% from A, 0.59% from C -> ambiguous
    ])
    assert len(ambiguous) == 1
    flagged_group, competing = ambiguous[0]
    assert flagged_group["id_type"] == "toi"
    assert set(competing) == {("name", "A"), ("name", "C")}


def test_null_period_never_unifies():
    clusters, ambiguous = _cluster_star([
        _obs("koi", "K1.01", "nea", None),
        _obs("toi", "2.01", "exofop", None),
    ])
    assert len(clusters) == 2
    assert ambiguous == []
