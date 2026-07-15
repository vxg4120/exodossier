"""Conflict-report sections detect planted conflicts, against an isolated graph (exact counts)."""

import pytest

from quality import report

_CAND_NAME = "PLANTED-ZZZ b"
_HOST_NAME = "PLANTED-ZZZ"


def _seed(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ingest_run (source, endpoint, started_at, status) "
            "VALUES ('t', 't', now(), 'ok') RETURNING ingest_run_id"
        )
        run = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO star (tic_id, canonical_name) VALUES (999002, %s) RETURNING star_id",
            (_HOST_NAME,),
        )
        star = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO candidate (star_id, canonical_name, disposition) "
            "VALUES (%s, %s, 'CONFIRMED') RETURNING candidate_id",
            (star, _CAND_NAME),
        )
        cand = cur.fetchone()[0]
        # A crosswalk link + audit row so the stats sections render.
        cur.execute(
            "INSERT INTO entity_identifier (star_id, id_type, id_value, source) "
            "VALUES (%s, 'tic', '999002', 'nea')",
            (star,),
        )
        cur.execute(
            "INSERT INTO merge_log (entity_type, surviving_id, merged_id, rule_fired, score) "
            "VALUES ('star', %s, %s, 'tic_exact', 1.0)",
            (star, star),
        )

        def sa(entity_col, eid, attr, value, source):
            cur.execute(
                f"INSERT INTO source_assertion ({entity_col}, source_key, attribute, value, "
                "source, observed_at, ingest_run_id) VALUES (%s, 'k', %s, %s, %s, now(), %s)",
                (eid, attr, value, source, run),
            )

        # Radius conflict: 2.0 vs 4.0 R_Earth = 50% spread (> 10% threshold).
        sa("candidate_id", cand, "planet_radius_re", "2.0", "koi")
        sa("candidate_id", cand, "planet_radius_re", "4.0", "ps")
        # Disposition fight: FALSE POSITIVE vs CONFIRMED.
        sa("candidate_id", cand, "disposition", "FP", "exofop_toi")
        sa("candidate_id", cand, "disposition", "CONFIRMED", "pscomppars")
        # Teff conflict on the host: 5780 vs 3000 K (HZ-moving).
        sa("star_id", star, "teff_k", "5780", "exofop_toi")
        sa("star_id", star, "teff_k", "3000", "ps")
    return star, cand


@pytest.mark.db
def test_report_detects_planted_conflicts(clean_graph):
    _seed(clean_graph)
    md = report.generate_report(clean_graph)

    # The planted object surfaces by name in the report.
    assert _CAND_NAME in md
    assert _HOST_NAME in md
    # Radius section: exactly one conflicting candidate.
    assert "conflicting planet radius" in md
    assert "Count: **1** candidates" in md
    # Disposition fight: the FP-vs-CONFIRMED subset caught it.
    assert "koi: 2; ps: 4" in md
    assert "exofop_toi=FALSE_POSITIVE" in md and "pscomppars=CONFIRMED" in md
    # Stellar-parameter (HZ) section rendered the Teff disagreement.
    assert "would move HZ membership" in md


@pytest.mark.db
def test_report_is_deterministic(clean_graph):
    _seed(clean_graph)
    first = report.generate_report(clean_graph)
    second = report.generate_report(clean_graph)
    # Byte-identical except for the generated-at timestamp line.
    drop_ts = lambda s: "\n".join(  # noqa: E731
        line for line in s.splitlines() if not line.startswith("Generated at:")
    )
    assert drop_ts(first) == drop_ts(second)
