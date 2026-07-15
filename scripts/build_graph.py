"""Wave 1 identity pipeline CLI: build the graph, extract assertions, resolve winners, summarize.

Every phase is idempotent (the build truncates and rebuilds the derived graph from the raw landing
tables), so the whole thing is safe to re-run. One transaction: commit only if all phases succeed.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from common.db import get_conn
from identity import assertions, build, resolve


def run_pipeline(conn) -> dict:
    """build -> assertions -> resolve, without committing. Returns a merged summary dict."""
    build_stats = build.build(conn)
    assertions.extract(conn)
    resolve_stats = resolve.resolve(conn)
    return summarize(conn, build_stats, resolve_stats)


def summarize(conn, build_stats, resolve_stats) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM star")
        stars = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM candidate")
        candidates = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM entity_identifier")
        crosswalk = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM source_assertion")
        asserts = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM merge_log")
        merges = cur.fetchone()[0]
        cur.execute("SELECT rule_fired, count(*) FROM merge_log GROUP BY rule_fired ORDER BY 1")
        by_rule = dict(cur.fetchall())
    return {
        "stars": stars, "candidates": candidates, "crosswalk_rows": crosswalk,
        "source_assertions": asserts, "merge_log_rows": merges, "merge_log_by_rule": by_rule,
        **build_stats, **resolve_stats,
    }


def main() -> None:
    conn = get_conn()
    try:
        summary = run_pipeline(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("=== identity build summary ===")
    for key, value in summary.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
