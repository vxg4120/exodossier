"""Link and merge audit — the ONLY writer of entity_identifier + merge_log.

Every crosswalk link and every candidate/star merge writes merge_log: there are no silent writes
anywhere in identity/ (ported discipline from the satellite platform's identity/merge.py). These
functions never commit; the caller owns the transaction boundary.
"""

from __future__ import annotations

from psycopg.types.json import Jsonb

_COL = {"star": "star_id", "candidate": "candidate_id"}


def link(
    conn,
    entity_type: str,
    entity_id: int,
    id_type: str,
    id_value: str,
    source: str,
    rule: str,
    score: float,
    confidence: float = 1.00,
    details: dict | None = None,
) -> bool:
    """Attach one identifier to a star or candidate and log the link.

    entity_type is 'star' or 'candidate' (selects which polymorphic FK column carries the id).
    Idempotent: the identifier insert is ON CONFLICT DO NOTHING against the crosswalk's
    UNIQUE NULLS NOT DISTINCT constraint, and merge_log is written only when a new identifier row
    was actually created (rowcount > 0), so re-running does not spam the audit log. Returns True if
    a new identifier was linked.
    """
    if entity_type not in _COL:
        raise ValueError(f"unknown entity_type: {entity_type!r}")
    col = _COL[entity_type]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO entity_identifier ({col}, id_type, id_value, source, confidence)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (entity_id, id_type, id_value, source, confidence),
        )
        if not cur.rowcount:
            return False
        payload = dict(details or {})
        payload.setdefault("id_type", id_type)
        payload.setdefault("id_value", id_value)
        payload.setdefault("source", source)
        cur.execute(
            """
            INSERT INTO merge_log (entity_type, surviving_id, merged_id, rule_fired, score, details)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (entity_type, entity_id, entity_id, rule, score, Jsonb(payload)),
        )
    return True


def log_ambiguous(
    conn,
    entity_type: str,
    entity_id: int,
    rule: str,
    details: dict,
) -> None:
    """Record a non-merge decision (e.g. a period that matched >1 existing candidate) in merge_log
    without creating any link. surviving_id = merged_id = the entity the ambiguity concerns; score
    is NULL to mark it as a flagged non-merge rather than a confident link."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO merge_log (entity_type, surviving_id, merged_id, rule_fired, score, details)
            VALUES (%s, %s, %s, %s, NULL, %s)
            """,
            (entity_type, entity_id, entity_id, rule, Jsonb(details)),
        )
