"""Generates docs/reports/conflict_report.md — the "nobody agrees on a planet" artifact (SPEC
Wave 1 §6).

Pure SQL against the identity graph + string formatting (no plotting deps). It reads only the
tables the identity engine populated; it never invokes the engine. "Disagreements are data, not
errors": every number is a live query, every example is a real, citable object.

Two entry points:
  - generate_report(conn) -> str: pure, returns markdown; tests call it against their own
    (uncommitted) transaction so seeded fixtures are visible without a commit.
  - main(): the `make report` entry point — opens a connection, writes the file.

Determinism: every query has an explicit ORDER BY so the committed report is byte-stable except
for the generated-at timestamp.
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "conflict_report.md"

EXAMPLE_LIMIT = 12
# A value that parses as a plain/scientific decimal (guards value::numeric against junk).
_NUMERIC_RE = r"^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$"

# Conflict thresholds (relative unless noted).
PERIOD_TOL = 0.01     # >1% period spread across sources = a conflict (SPEC candidate tolerance)
RADIUS_TOL = 0.10     # >10% radius spread = a conflict (Gaia radius revisions live here)
TEFF_FRAC = 0.05      # >5% Teff spread => ~10% HZ-boundary shift (Kane 2014) => HZ-membership risk
RSTAR_TOL = 0.10      # >10% stellar-radius spread


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def _md_table(cols, rows) -> str:
    if not rows:
        return "_(none)_\n"
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(_fmt(v) for v in row) + " |")
    return "\n".join(out) + "\n"


def _per_source_aggregates(cur, attribute: str, entity_col: str) -> dict:
    """{entity_id: {source: (count, min, max)}} for a numeric attribute, junk values filtered."""
    cur.execute(
        f"""
        SELECT {entity_col}, source, count(*), min(value::numeric), max(value::numeric)
        FROM source_assertion
        WHERE attribute = %s AND {entity_col} IS NOT NULL AND value ~ %s
        GROUP BY {entity_col}, source
        ORDER BY {entity_col}, source
        """,
        (attribute, _NUMERIC_RE),
    )
    out: dict = {}
    for eid, source, cnt, vmin, vmax in cur.fetchall():
        out.setdefault(eid, {})[source] = (cnt, float(vmin), float(vmax))
    return out


def _numeric_conflicts(cur, attribute: str, entity_col: str, tol: float):
    """Return conflict dicts: entities where the per-source values span > tol (relative).

    Sorted by spread desc, then entity id (deterministic). Each carries a per-source detail string
    (single value, or 'min–max (n pubs)' for multi-valued sources like ps).
    """
    aggs = _per_source_aggregates(cur, attribute, entity_col)
    conflicts = []
    for eid, by_source in aggs.items():
        if len(by_source) < 2:
            continue
        gmin = min(v[1] for v in by_source.values())
        gmax = max(v[2] for v in by_source.values())
        if gmax <= 0:
            continue
        spread = (gmax - gmin) / gmax
        if spread <= tol:
            continue
        parts = []
        for src in sorted(by_source):
            cnt, mn, mx = by_source[src]
            parts.append(f"{src}: {mn:.4g}" if mn == mx else f"{src}: {mn:.4g}–{mx:.4g} ({cnt})")
        conflicts.append({
            "eid": eid, "n_src": len(by_source), "min": gmin, "max": gmax,
            "spread": spread, "detail": "; ".join(parts),
        })
    conflicts.sort(key=lambda c: (-c["spread"], c["eid"]))
    return conflicts


def _candidate_labels(cur) -> dict:
    cur.execute(
        "SELECT c.candidate_id, c.canonical_name, c.disposition, s.canonical_name "
        "FROM candidate c JOIN star s ON s.star_id = c.star_id"
    )
    return {cid: (name, dispo, host) for cid, name, dispo, host in cur.fetchall()}


def _star_labels(cur) -> dict:
    cur.execute("SELECT star_id, canonical_name, tic_id FROM star")
    return {sid: (name, tic) for sid, name, tic in cur.fetchall()}


# --- disposition fights -------------------------------------------------------


def _disposition_fights(cur):
    """Candidates carrying >= 2 distinct canonical dispositions across sources. Returns
    (all_fights, fp_vs_confirmed) where the latter is the subset with a FALSE_POSITIVE on one
    source and a CONFIRMED/KNOWN_PLANET on another — the dramatic ones."""
    cur.execute(
        """
        WITH dispo AS (
            SELECT sa.candidate_id, sa.source, dm.canonical_disposition AS cd
            FROM source_assertion sa
            JOIN disposition_mapping dm
              ON dm.source = sa.source AND dm.source_value = sa.value
            WHERE sa.attribute = 'disposition' AND sa.candidate_id IS NOT NULL
            GROUP BY sa.candidate_id, sa.source, dm.canonical_disposition
        )
        SELECT candidate_id,
               count(DISTINCT cd) AS n_dispo,
               bool_or(cd = 'FALSE_POSITIVE') AS has_fp,
               bool_or(cd IN ('CONFIRMED', 'KNOWN_PLANET')) AS has_confirmed,
               string_agg(DISTINCT source || '=' || cd, '; ' ORDER BY source || '=' || cd) AS detail
        FROM dispo
        GROUP BY candidate_id
        HAVING count(DISTINCT cd) >= 2
        ORDER BY count(DISTINCT cd) DESC, candidate_id
        """
    )
    all_fights, fp_vs_conf = [], []
    for cid, n, has_fp, has_conf, detail in cur.fetchall():
        row = {"eid": cid, "n_dispo": n, "detail": detail}
        all_fights.append(row)
        if has_fp and has_conf:
            fp_vs_conf.append(row)
    return all_fights, fp_vs_conf


# --- crosswalk stats ----------------------------------------------------------


def _crosswalk_stats(cur):
    cur.execute(
        "SELECT id_type, count(*) FROM entity_identifier GROUP BY id_type ORDER BY id_type"
    )
    by_id_type = cur.fetchall()
    cur.execute(
        """
        SELECT n_types, count(*) AS stars
        FROM (
            SELECT star_id, count(DISTINCT id_type) AS n_types
            FROM entity_identifier WHERE star_id IS NOT NULL GROUP BY star_id
        ) t
        GROUP BY n_types ORDER BY n_types
        """
    )
    id_type_hist = cur.fetchall()
    cur.execute(
        "SELECT rule_fired, count(*) FROM merge_log GROUP BY rule_fired ORDER BY rule_fired"
    )
    by_rule = cur.fetchall()
    return by_id_type, id_type_hist, by_rule


def _ingest_ledger(cur):
    cur.execute(
        """
        SELECT source, endpoint, status, rows_ingested, bytes_downloaded, finished_at
        FROM (
            SELECT DISTINCT ON (source, endpoint) source, endpoint, status, rows_ingested,
                   bytes_downloaded, finished_at
            FROM ingest_run
            ORDER BY source, endpoint, finished_at DESC NULLS LAST
        ) last_per_endpoint
        ORDER BY source, endpoint
        """
    )
    return [d.name for d in cur.description], cur.fetchall()


def _counts(cur) -> dict:
    out = {}
    for label, sql in (
        ("stars", "SELECT count(*) FROM star"),
        ("candidates", "SELECT count(*) FROM candidate"),
        ("crosswalk", "SELECT count(*) FROM entity_identifier"),
        ("assertions", "SELECT count(*) FROM source_assertion"),
        ("merges", "SELECT count(*) FROM merge_log"),
    ):
        cur.execute(sql)
        out[label] = cur.fetchone()[0]
    return out


# --- assembly -----------------------------------------------------------------


def generate_report(conn) -> str:
    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    out: list[str] = []
    with conn.cursor() as cur:
        counts = _counts(cur)
        ledger_cols, ledger_rows = _ingest_ledger(cur)
        cand_labels = _candidate_labels(cur)
        star_labels = _star_labels(cur)
        period_conf = _numeric_conflicts(cur, "period_days", "candidate_id", PERIOD_TOL)
        radius_conf = _numeric_conflicts(cur, "planet_radius_re", "candidate_id", RADIUS_TOL)
        teff_conf = _numeric_conflicts(cur, "teff_k", "star_id", TEFF_FRAC)
        rstar_conf = _numeric_conflicts(cur, "rstar_rsun", "star_id", RSTAR_TOL)
        all_fights, fp_vs_conf = _disposition_fights(cur)
        by_id_type, id_type_hist, by_rule = _crosswalk_stats(cur)

    def cand_name(cid):
        name, dispo, host = cand_labels.get(cid, ("?", None, "?"))
        return name, host, (dispo or "")

    def star_name(sid):
        name, tic = star_labels.get(sid, ("?", None))
        return name, (f"TIC {tic}" if tic else "(no TIC)")

    out.append("# ExoDossier Conflict Report v0\n")
    out.append(f"\nGenerated at: {now}\n")
    out.append(
        "\nNobody agrees on a planet. Every row below is a live query against the identity graph: "
        "the same star or candidate, described differently by TOI vs CTOI vs the NASA Archive's "
        "per-publication `ps` rows vs the `pscomppars` composite vs the Kepler KOI table. "
        "Disagreements are data, not errors.\n"
    )

    out.append("\n## Graph at a glance\n\n")
    out.append(
        f"- Stars: **{counts['stars']:,}**  |  Candidates: **{counts['candidates']:,}**\n"
        f"- Crosswalk identifiers: **{counts['crosswalk']:,}**  |  "
        f"Source assertions: **{counts['assertions']:,}**  |  "
        f"merge_log rows: **{counts['merges']:,}**\n"
    )

    out.append("\n## Ingestion ledger (last run per endpoint)\n\n")
    out.append(_md_table(ledger_cols, ledger_rows))

    # 1. Disposition fights (the headline).
    out.append("\n## 1. Disposition fights: is it even a planet?\n\n")
    out.append(
        f"Candidates with >= 2 conflicting canonical dispositions across sources: "
        f"**{len(all_fights):,}**. Of those, **{len(fp_vs_conf):,}** are the dramatic kind — one "
        "catalog calls it a FALSE POSITIVE while another calls it CONFIRMED or a KNOWN PLANET.\n\n"
    )
    rows = []
    for f in fp_vs_conf[:EXAMPLE_LIMIT]:
        name, host, _ = cand_name(f["eid"])
        rows.append((name, host, f["detail"]))
    out.append("**FALSE POSITIVE vs CONFIRMED/KNOWN — named examples:**\n\n")
    out.append(_md_table(["candidate", "host", "who says what"], rows))
    if len(fp_vs_conf) < 3:
        rows = []
        for f in all_fights[:EXAMPLE_LIMIT]:
            name, host, _ = cand_name(f["eid"])
            rows.append((name, host, f["detail"]))
        out.append("\n**All disposition disagreements — named examples:**\n\n")
        out.append(_md_table(["candidate", "host", "who says what"], rows))

    # 2. Radius conflicts.
    out.append("\n## 2. Same candidate, conflicting planet radius (> 10% across sources)\n\n")
    out.append(
        f"Count: **{len(radius_conf):,}** candidates. Gaia parallax revisions to stellar radii "
        "propagate straight into planet radii — this is where rocky-vs-sub-Neptune classification "
        "flips.\n\n"
    )
    rows = []
    for c in radius_conf[:EXAMPLE_LIMIT]:
        name, host, dispo = cand_name(c["eid"])
        rows.append((name, host, dispo, f"{c['spread'] * 100:.0f}%", c["detail"]))
    out.append(_md_table(["candidate", "host", "disposition", "spread", "R_Earth by source"], rows))

    # 3. Period conflicts.
    out.append("\n## 3. Same candidate, conflicting orbital period (> 1% across sources)\n\n")
    out.append(
        f"Count: **{len(period_conf):,}** candidates. Large spreads are usually period aliases "
        "(2x/3x) — themselves a real cross-catalog disagreement about the true period.\n\n"
    )
    rows = []
    for c in period_conf[:EXAMPLE_LIMIT]:
        name, host, dispo = cand_name(c["eid"])
        rows.append((name, host, dispo, f"{c['spread'] * 100:.0f}%", c["detail"]))
    out.append(_md_table(["candidate", "host", "disposition", "spread", "period_days by source"],
                         rows))

    # 4. Stellar-parameter conflicts (HZ-moving).
    out.append("\n## 4. Host stellar-parameter conflicts (would move HZ membership)\n\n")
    out.append(
        f"Hosts whose effective temperature disagrees by > 5% across sources: "
        f"**{len(teff_conf):,}** — Kane 2014: a ~5% Teff error shifts the habitable-zone boundary "
        "by ~10%, so these are stars whose HZ membership depends on which catalog you trust. "
        f"Stellar-radius disagreements > 10%: **{len(rstar_conf):,}**.\n\n"
    )
    rows = []
    for c in teff_conf[:EXAMPLE_LIMIT]:
        name, tic = star_name(c["eid"])
        rows.append((name, tic, f"{c['max'] - c['min']:.0f} K", f"{c['spread'] * 100:.0f}%",
                     c["detail"]))
    out.append("**Biggest Teff disagreements:**\n\n")
    out.append(_md_table(["host", "tic", "delta", "spread", "Teff (K) by source"], rows))
    rows = []
    for c in rstar_conf[:EXAMPLE_LIMIT]:
        name, tic = star_name(c["eid"])
        rows.append((name, tic, f"{c['spread'] * 100:.0f}%", c["detail"]))
    out.append("\n**Biggest stellar-radius disagreements:**\n\n")
    out.append(_md_table(["host", "tic", "spread", "R_sun by source"], rows))

    # 5. Crosswalk stats.
    out.append("\n## 5. Crosswalk statistics\n\n")
    out.append("**Identifiers by type:**\n\n")
    out.append(_md_table(["id_type", "count"], by_id_type))
    out.append("\n**Distinct identifier-types per star (breadth of the graph):**\n\n")
    out.append(_md_table(["distinct_id_types", "stars"], id_type_hist))
    out.append("\n**merge_log by rule (every link + flagged non-merge is audited):**\n\n")
    out.append(_md_table(["rule_fired", "count"], by_rule))

    return "".join(out)


def write_report(conn, path: pathlib.Path = DEFAULT_REPORT_PATH) -> pathlib.Path:
    content = generate_report(conn)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def main() -> None:
    conn = get_conn()
    try:
        path = write_report(conn)
        print(f"wrote {path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
