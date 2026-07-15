"""Precedence resolution + disposition mapping, against an isolated (truncated + rolled back) graph.

disposition_mapping is preserved by clean_graph, so the real per-source vocabulary is exercised.
"""

import pytest

from identity import resolve


def _seed(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO ingest_run (source, endpoint, started_at, status) "
            "VALUES ('t', 't', now(), 'ok') RETURNING ingest_run_id"
        )
        run = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO star (tic_id, canonical_name) VALUES (999001, 'Test Star') "
            "RETURNING star_id"
        )
        star = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO candidate (star_id, canonical_name) VALUES (%s, 'Test b') "
            "RETURNING candidate_id",
            (star,),
        )
        cand = cur.fetchone()[0]

        def sa(entity_col, eid, attr, value, source):
            cur.execute(
                f"INSERT INTO source_assertion ({entity_col}, source_key, attribute, value, "
                "source, observed_at, ingest_run_id) VALUES (%s, 'k', %s, %s, %s, now(), %s)",
                (eid, attr, value, source, run),
            )

        sa("candidate_id", cand, "period_days", "5.5", "exofop_toi")
        sa("candidate_id", cand, "period_days", "5.0", "ps")
        sa("candidate_id", cand, "disposition", "FP", "exofop_toi")
        sa("candidate_id", cand, "disposition", "Published Confirmed", "ps")
        sa("star_id", star, "teff_k", "5780", "exofop_toi")
        sa("star_id", star, "teff_k", "3200", "ps")
    return star, cand


@pytest.mark.db
def test_resolve_applies_precedence_and_disposition_mapping(clean_graph):
    star, cand = _seed(clean_graph)
    stats = resolve.resolve(clean_graph)

    with clean_graph.cursor() as cur:
        cur.execute("SELECT period_days, disposition FROM candidate WHERE candidate_id = %s",
                    (cand,))
        period, dispo = cur.fetchone()
        cur.execute("SELECT teff_k FROM star WHERE star_id = %s", (star,))
        teff = cur.fetchone()[0]

    assert float(period) == 5.0          # ps precedence beats exofop_toi (5.5)
    assert dispo == "CONFIRMED"          # ps 'Published Confirmed' beats exofop 'FP'
    assert float(teff) == 3200           # ps precedence beats the exofop 5780 default
    assert stats["disposition_resolved"] == 1
    assert stats["unmapped_dispositions"] == []
