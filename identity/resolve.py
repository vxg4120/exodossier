"""Assertion -> canonical resolver. Precedence is config (precedence.yml), not code.

For each candidate/star and attribute the resolver applies the per-attribute source precedence and
writes the winner to the canonical column; losing assertions stay queryable in source_assertion
("disagreements are data, not errors"). Disposition resolves through the disposition_mapping table
(per-source vocabulary -> canonical taxonomy). No commit — the caller owns the transaction. Ported
in shape from the satellite platform's identity/resolve.py.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

_PRECEDENCE_DEFAULT = Path(__file__).with_name("precedence.yml")

_CANDIDATE_NUM = ["period_days", "planet_radius_re"]
_STAR_NUM = ["teff_k", "logg", "rstar_rsun"]


def load_precedence(path=None) -> dict:
    with open(path or _PRECEDENCE_DEFAULT) as fh:
        return yaml.safe_load(fh)


def _by_source(conn, entity_col: str, attribute: str) -> dict[int, dict[str, str]]:
    """{entity_id: {source: value}} for one attribute (last value per source wins deterministically
    via a stable ORDER BY, matching the satellite resolver's tiebreak discipline)."""
    out: dict[int, dict[str, str]] = defaultdict(dict)
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {entity_col}, source, value FROM source_assertion "
            f"WHERE attribute = %s AND {entity_col} IS NOT NULL "
            "ORDER BY observed_at, ingest_run_id, source_key, assertion_id",
            (attribute,),
        )
        for eid, source, value in cur.fetchall():
            out[eid][source] = value
    return out


def _pick(by_source: dict[str, str], order: list[str]):
    for src in order:
        if src in by_source:
            return src, by_source[src]
    return None


def _resolve_numeric(conn, entity_col, table, id_col, attribute, order) -> int:
    data = _by_source(conn, entity_col, attribute)
    resolved = 0
    with conn.cursor() as cur:
        for eid, by_source in data.items():
            picked = _pick(by_source, order)
            if picked is None:
                continue
            try:
                value = float(picked[1])
            except (TypeError, ValueError):
                continue
            cur.execute(
                f"UPDATE {table} SET {attribute} = %s, updated_at = now() WHERE {id_col} = %s",
                (value, eid),
            )
            resolved += 1
    return resolved


def _disposition_map(conn) -> dict[tuple[str, str], str]:
    with conn.cursor() as cur:
        cur.execute("SELECT source, source_value, canonical_disposition FROM disposition_mapping")
        return {(s, v): c for s, v, c in cur.fetchall()}


def _resolve_disposition(conn, order, stats) -> None:
    """Map each source's raw disposition to the canonical taxonomy, then pick by precedence.
    Unmapped source values are skipped (and counted) rather than guessed."""
    mapping = _disposition_map(conn)
    data = _by_source(conn, "candidate_id", "disposition")
    unmapped: set[tuple[str, str]] = set()
    resolved = 0
    with conn.cursor() as cur:
        for cand_id, by_source in data.items():
            winner = None
            for src in order:
                if src not in by_source:
                    continue
                raw = by_source[src]
                canonical = mapping.get((src, raw))
                if canonical is None:
                    unmapped.add((src, raw))
                    continue
                winner = canonical
                break
            if winner is None:
                continue
            cur.execute(
                "UPDATE candidate SET disposition = %s, updated_at = now() WHERE candidate_id = %s",
                (winner, cand_id),
            )
            resolved += 1
    stats["disposition_resolved"] = resolved
    stats["unmapped_dispositions"] = sorted(unmapped)


def resolve(conn, precedence_path=None) -> dict:
    """Resolve every configured attribute for every candidate + star. Returns coverage stats."""
    prec = load_precedence(precedence_path)
    stats: dict = {}
    for attr in _CANDIDATE_NUM:
        stats[f"candidate_{attr}_resolved"] = _resolve_numeric(
            conn, "candidate_id", "candidate", "candidate_id", attr, prec[attr]
        )
    for attr in _STAR_NUM:
        stats[f"star_{attr}_resolved"] = _resolve_numeric(
            conn, "star_id", "star", "star_id", attr, prec[attr]
        )
    _resolve_disposition(conn, prec["disposition"], stats)
    return stats
