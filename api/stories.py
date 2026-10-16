"""The landing page's stories: what changed in the archives across the retained raw snapshots.

The identity graph is rebuilt nightly with TRUNCATE, so it has no history of its own. The raw
tables do: ``scripts/prune_snapshots.py`` keeps the first OK run of each month plus the newest
three, and those snapshots are the only record of what the archives said before today. Every
change story here is a diff between two of them, looked up by date at request time (run ids are
never hard-coded).

Two snapshot series feed it:
  * ``raw_pscomppars`` (NASA Exoplanet Archive, the confirmed-planet composite table): which
    planets joined or left the confirmed list, what they look like, and who found them.
  * ``raw_exofop_toi`` (ExoFOP, the TESS Objects of Interest list): how TFOPWG verdicts on TESS
    candidates moved, the current verdict mix, and how many TOIs were alerted each month.

The API returns facts (counts, dates, names); the SPA phrases them. Read-only throughout. The
pure helpers below take plain Python values so they are tested without a database.

Both raw tables allow duplicate and NULL keys, so every query keys a run by its non-NULL names
(``pl_name``, ``toi``) and keeps one row per name: the one with the lowest ``raw_id``.

A refresh that finds the newest snapshots empty raises ``SnapshotsUnavailable`` instead of
returning an empty payload. TRUNCATE is not MVCC-safe, so a future TRUNCATE-based compaction that
commits mid-refresh makes the tables look empty to a reader that is already running; raising
keeps the previous payload in ``RefreshingCache``. The REPEATABLE READ snapshot covers the
nightly DELETE, which is MVCC-safe.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

import psycopg

# Sentinels in a verdict transition, next to the TFOPWG codes (PC, APC, CP, KP, FP, FA) and None
# (a TOI on the list with no TFOPWG disposition yet). Codes are two or three letters, so these
# can never collide with one.
NEW = "NEW"  # not on the TOI list at the earlier snapshot
DROPPED = "DROPPED"  # not on the TOI list at the later snapshot

CONFIRMED_CODES = ("CP", "KP")
RULED_OUT_CODES = ("FP", "FA")


class SnapshotsUnavailable(RuntimeError):
    """The retained snapshots look empty, which a real archive never is. Raised so that a refresh
    fails and the cache keeps serving the payload it has."""


NEWEST_SHOWN = 12
ALERT_MONTHS = 15

# (label, lower bound inclusive, upper bound exclusive) in Earth radii; the spec's bins.
RADIUS_BINS: list[tuple[str, float, float]] = [
    ("Earth-size", 0.0, 1.25),
    ("Super-Earth", 1.25, 2.0),
    ("Sub-Neptune", 2.0, 4.0),
    ("Neptune-size", 4.0, 6.0),
    ("Giant", 6.0, float("inf")),
]
UNKNOWN_RADIUS = "Unknown radius"

_SNAPSHOTS = {
    "pscomppars": ("nea", "tap_pscomppars", "raw_pscomppars"),
    "toi": ("exofop", "toi_csv", "raw_exofop_toi"),
}


# ---------------------------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------------------------
def radius_bin(radius_re: float | None) -> str:
    if radius_re is None:
        return UNKNOWN_RADIUS
    for label, lo, hi in RADIUS_BINS:
        if lo <= radius_re < hi:
            return label
    return UNKNOWN_RADIUS  # a negative radius is not a size


def size_bins(radii: list[float | None]) -> list[dict[str, Any]]:
    """Every bin in order, zeros included, so the chart keeps its shape whatever arrived."""
    counts = Counter(radius_bin(r) for r in radii)
    labels = [b[0] for b in RADIUS_BINS] + [UNKNOWN_RADIUS]
    return [{"bin": label, "count": counts.get(label, 0)} for label in labels]


def month_window(as_of: dt.date, n: int = ALERT_MONTHS) -> list[str]:
    """The ``n`` calendar months ending with ``as_of``'s month, oldest first, as YYYY-MM."""
    y, m = as_of.year, as_of.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)
    return out[::-1]


def fill_months(counts: dict[str, int], as_of: dt.date, n: int = ALERT_MONTHS) -> list[dict]:
    """One row per month in the window; months with no alert are 0, never missing. The month
    that contains ``as_of`` is still running, so it is marked partial."""
    months = month_window(as_of, n)
    current = months[-1]
    return [
        {"month": mo, "count": counts.get(mo, 0), "partial": mo == current} for mo in months
    ]


def month_baseline(snapshots: list[dict]) -> dict | None:
    """The snapshot "this month" is measured from: the first retained snapshot in the newest
    snapshot's month. When the newest IS that first snapshot (the morning of the 1st), measure
    from the snapshot before it instead, so the window is never empty by construction. None when
    there is only one snapshot. ``snapshots`` is oldest first, each with a ``date``."""
    if len(snapshots) < 2:
        return None
    newest = snapshots[-1]
    in_month = [s for s in snapshots if s["date"][:7] == newest["date"][:7]]
    first = in_month[0]
    return first if first is not newest else snapshots[-2]


def one_per_date(snapshots: list[dict]) -> list[dict]:
    """Keep the newest snapshot of each UTC date, so the series never repeats a date (two OK
    pulls on one day would otherwise draw two points at one x and give React duplicate keys).
    ``snapshots`` is oldest first; so is the result."""
    newest: dict[str, dict] = {}
    for s in snapshots:
        newest[s["date"]] = s  # a later run of the same date replaces the earlier one
    return list(newest.values())


def membership_changes(
    partial_members: dict[str, list[int]], run_ids: list[int]
) -> list[dict[str, list[str]]]:
    """Given, for every name absent from at least one snapshot, the runs it appears in, return
    per snapshot (oldest first) the names that arrived and left versus the snapshot before. The
    first snapshot has nothing to compare with, so both lists are empty."""
    steps: list[dict[str, list[str]]] = [{"added": [], "removed": []}]
    for prev, cur in zip(run_ids, run_ids[1:], strict=False):
        added = sorted(n for n, runs in partial_members.items() if cur in runs and prev not in runs)
        removed = sorted(
            n for n, runs in partial_members.items() if prev in runs and cur not in runs
        )
        steps.append({"added": added, "removed": removed})
    return steps


def diff_names(
    partial_members: dict[str, list[int]], before: int, after: int
) -> tuple[list[str], list[str]]:
    """Names on the list at ``after`` but not ``before``, and the reverse."""
    added = sorted(n for n, r in partial_members.items() if after in r and before not in r)
    removed = sorted(n for n, r in partial_members.items() if before in r and after not in r)
    return added, removed


def first_seen(runs: list[int], run_dates: dict[int, str]) -> str:
    return min(run_dates[r] for r in runs if r in run_dates)


def record(rows: list[dict], key: str, largest: bool) -> dict | None:
    """The row with the smallest (or largest) non-null ``key``, ties broken by name."""
    have = [r for r in rows if r[key] is not None]
    if not have:
        return None
    pick = sorted(have, key=lambda r: ((-r[key]) if largest else r[key], r["pl_name"]))[0]
    return {
        "pl_name": pick["pl_name"],
        "host": pick["host"],
        "facility": pick["facility"],
        "value": pick[key],
    }


def facility_counts(rows: list[dict]) -> list[dict[str, Any]]:
    counts = Counter(r["facility"] or "Unknown facility" for r in rows)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"facility": f, "count": n} for f, n in ranked]


def sort_transitions(rows: list[dict]) -> list[dict]:
    """Largest movement first; ties in a fixed order so the payload is stable."""
    return sorted(rows, key=lambda t: (-t["count"], t["from"] or "", t["to"] or ""))


# ---------------------------------------------------------------------------------------------
# queries
# ---------------------------------------------------------------------------------------------
def _f(value: Any) -> float | None:
    return float(value) if value is not None else None


def _snapshots(cur: psycopg.Cursor) -> dict[str, list[dict]]:
    """OK runs of each snapshot endpoint that still have rows in their raw table, oldest first.
    The prune keeps a handful, so the ledger's other runs (pruned, skipped, failed) drop out."""
    parts, params = [], []
    for key, (source, endpoint, table) in _SNAPSHOTS.items():
        parts.append(
            f"""
            SELECT %s AS key, r.ingest_run_id, r.finished_at
            FROM ingest_run r
            WHERE r.source = %s AND r.endpoint = %s AND r.status = 'ok'
              AND EXISTS (SELECT 1 FROM {table} t WHERE t.ingest_run_id = r.ingest_run_id)
            """
        )
        params += [key, source, endpoint]
    cur.execute(" UNION ALL ".join(parts) + " ORDER BY finished_at, ingest_run_id", params)
    out: dict[str, list[dict]] = {key: [] for key in _SNAPSHOTS}
    for row in cur.fetchall():
        out[row["key"]].append(
            {
                "run": row["ingest_run_id"],
                "date": row["finished_at"].astimezone(dt.UTC).date().isoformat(),
            }
        )
    return {key: one_per_date(snaps) for key, snaps in out.items()}


def _confirmed(cur: psycopg.Cursor, snaps: list[dict]) -> dict[str, Any]:
    run_ids = [s["run"] for s in snaps]
    run_dates = {s["run"]: s["date"] for s in snaps}
    empty = {
        "series": [], "baseline_date": None, "added_since_baseline": 0,
        "removed_since_baseline": 0, "removed": [], "month_baseline_date": None,
        "added_since_month": 0, "newest": [], "sizes": size_bins([]), "facilities": [],
        "records": {"smallest": None, "shortest_period": None, "longest_period": None},
    }
    if not snaps:
        return empty

    cur.execute(
        """
        SELECT ingest_run_id, count(DISTINCT pl_name) AS n FROM raw_pscomppars
        WHERE ingest_run_id = ANY(%(runs)s) AND pl_name IS NOT NULL GROUP BY ingest_run_id
        """,
        {"runs": run_ids},
    )
    counts = {r["ingest_run_id"]: r["n"] for r in cur.fetchall()}
    if any(counts.get(run, 0) == 0 for run in run_ids):
        raise SnapshotsUnavailable("a retained pscomppars snapshot has no planets")

    # Only the names missing from some snapshot can have moved; everything else is on every list.
    cur.execute(
        """
        SELECT pl_name, array_agg(DISTINCT ingest_run_id ORDER BY ingest_run_id) AS runs
        FROM raw_pscomppars
        WHERE ingest_run_id = ANY(%(runs)s) AND pl_name IS NOT NULL
        GROUP BY pl_name
        HAVING count(DISTINCT ingest_run_id) < %(n)s
        """,
        {"runs": run_ids, "n": len(run_ids)},
    )
    partial = {r["pl_name"]: list(r["runs"]) for r in cur.fetchall()}

    steps = membership_changes(partial, run_ids)
    series = [
        {
            "date": s["date"],
            "count": counts.get(s["run"], 0),
            "added": len(step["added"]) if i else None,
            "removed": len(step["removed"]) if i else None,
        }
        for i, (s, step) in enumerate(zip(snaps, steps, strict=True))
    ]

    baseline, newest = snaps[0], snaps[-1]
    added, removed = diff_names(partial, baseline["run"], newest["run"])
    mbase = month_baseline(snaps)
    added_month = diff_names(partial, mbase["run"], newest["run"])[0] if mbase else []

    rows: list[dict] = []
    if added:
        cur.execute(
            """
            SELECT DISTINCT ON (pl_name)
                   pl_name, hostname, disc_facility, planet_radius_re, period_days
            FROM raw_pscomppars
            WHERE ingest_run_id = %(run)s AND pl_name = ANY(%(names)s)
            ORDER BY pl_name, raw_id
            """,
            {"run": newest["run"], "names": added},
        )
        rows = [
            {
                "pl_name": r["pl_name"],
                "host": r["hostname"],
                "facility": r["disc_facility"],
                "radius_re": _f(r["planet_radius_re"]),
                "period_days": _f(r["period_days"]),
                "first_seen": first_seen(partial[r["pl_name"]], run_dates),
            }
            for r in cur.fetchall()
        ]
    # newest first; inside one snapshot there is no finer arrival order, so by name
    rows.sort(key=lambda r: r["pl_name"])
    rows.sort(key=lambda r: r["first_seen"], reverse=True)

    return {
        "series": series,
        "baseline_date": baseline["date"],
        "added_since_baseline": len(added),
        "removed_since_baseline": len(removed),
        "removed": [
            {"pl_name": n, "last_seen": max(run_dates[r] for r in partial[n])} for n in removed
        ],
        "month_baseline_date": mbase["date"] if mbase else None,
        "added_since_month": len(added_month),
        "newest": rows[:NEWEST_SHOWN],
        "sizes": size_bins([r["radius_re"] for r in rows]),
        "facilities": facility_counts(rows),
        "records": {
            "smallest": record(rows, "radius_re", largest=False),
            "shortest_period": record(rows, "period_days", largest=False),
            "longest_period": record(rows, "period_days", largest=True),
        },
    }


# One row per TOI in one run: NULL TOIs dropped, duplicates resolved to the lowest raw_id.
_TOI_RUN = """
SELECT DISTINCT ON (toi) toi, tic_id, tfopwg_disposition AS d, extra
FROM raw_exofop_toi
WHERE ingest_run_id = %({run})s AND toi IS NOT NULL
ORDER BY toi, raw_id
"""

_TRANSITIONS_SQL = f"""
WITH b AS ({_TOI_RUN.format(run="before")}),
     a AS ({_TOI_RUN.format(run="after")})
SELECT CASE WHEN b.toi IS NULL THEN %(new)s ELSE b.d END AS from_code,
       CASE WHEN a.toi IS NULL THEN %(dropped)s ELSE a.d END AS to_code,
       count(*) AS n
FROM b FULL JOIN a USING (toi)
WHERE b.toi IS NULL OR a.toi IS NULL OR b.d IS DISTINCT FROM a.d
GROUP BY 1, 2
"""


def _transitions(cur: psycopg.Cursor, before: dict, after: dict) -> list[dict]:
    cur.execute(
        _TRANSITIONS_SQL,
        {"before": before["run"], "after": after["run"], "new": NEW, "dropped": DROPPED},
    )
    return sort_transitions(
        [{"from": r["from_code"], "to": r["to_code"], "count": r["n"]} for r in cur.fetchall()]
    )


def _toi(cur: psycopg.Cursor, snaps: list[dict]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "toi_verdicts": {"from_date": None, "to_date": None, "transitions": [], "demoted": []},
        "toi_verdicts_month": {"from_date": None, "to_date": None, "transitions": []},
        "toi_mix": [],
        "toi_alerts_monthly": [],
    }
    if not snaps:
        return out
    baseline, newest = snaps[0], snaps[-1]

    if len(snaps) >= 2:
        demoted_sql = f"""
            WITH b AS ({_TOI_RUN.format(run="before")}),
                 a AS ({_TOI_RUN.format(run="after")})
            SELECT a.toi, a.tic_id, b.d AS from_code, a.d AS to_code
            FROM b JOIN a USING (toi)
            WHERE b.d = ANY(%(was)s) AND a.d = ANY(%(now)s)
            ORDER BY a.toi
        """
        cur.execute(
            demoted_sql,
            {"before": baseline["run"], "after": newest["run"],
             "was": list(CONFIRMED_CODES), "now": list(RULED_OUT_CODES)},
        )
        demoted = [
            {"toi": r["toi"], "tic_id": r["tic_id"], "from": r["from_code"], "to": r["to_code"]}
            for r in cur.fetchall()
        ]
        # TOI numbers sort as numbers ("999.01" before "1000.01")
        demoted.sort(key=lambda d: [int(p) if p.isdigit() else p for p in d["toi"].split(".")])
        out["toi_verdicts"] = {
            "from_date": baseline["date"],
            "to_date": newest["date"],
            "transitions": _transitions(cur, baseline, newest),
            "demoted": demoted,
        }
        mbase = month_baseline(snaps)
        if mbase is not None:  # always, with two or more snapshots
            out["toi_verdicts_month"] = {
                "from_date": mbase["date"],
                "to_date": newest["date"],
                "transitions": _transitions(cur, mbase, newest),
            }

    cur.execute(
        f"""
        SELECT d, count(*) AS n FROM ({_TOI_RUN.format(run="run")}) t
        GROUP BY 1 ORDER BY 2 DESC, 1
        """,
        {"run": newest["run"]},
    )
    out["toi_mix"] = [{"disposition": r["d"], "count": r["n"]} for r in cur.fetchall()]
    if not out["toi_mix"]:
        raise SnapshotsUnavailable("the newest TOI snapshot has no TOIs")

    as_of = dt.date.fromisoformat(newest["date"])
    first_month = month_window(as_of)[0]
    cur.execute(
        f"""
        SELECT left(extra->>'Date TOI Alerted (UTC)', 7) AS month, count(*) AS n
        FROM ({_TOI_RUN.format(run="run")}) t
        WHERE extra->>'Date TOI Alerted (UTC)' >= %(start)s
        GROUP BY 1
        """,
        {"run": newest["run"], "start": first_month},
    )
    out["toi_alerts_monthly"] = fill_months(
        {r["month"]: r["n"] for r in cur.fetchall()}, as_of
    )
    return out


def empty_stories() -> dict[str, Any]:
    """The payload with no snapshot at all: every block present and empty, which the SPA hides.
    Served only on a cold start whose compute raised ``SnapshotsUnavailable``."""
    # both helpers return their empty blocks before they touch the cursor
    return {"as_of": None, "confirmed": _confirmed(None, []), **_toi(None, [])}


def catalog_stories(db: psycopg.Connection) -> dict[str, Any]:
    """Everything the landing's story panels need, in one payload (see docs/specs/
    landing-stories.md for the shape). Raises ``SnapshotsUnavailable`` when either source has no
    retained snapshot or its newest one reads as empty.

    ``db`` must not have run a query in its current transaction: the first statement makes the
    transaction REPEATABLE READ, so that every query sees the same snapshots even while the
    nightly prune deletes an old run."""
    with db.cursor() as cur:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        snaps = _snapshots(cur)
        if not snaps["pscomppars"] or not snaps["toi"]:
            raise SnapshotsUnavailable(
                "no retained snapshot of "
                + " or ".join(k for k in ("pscomppars", "toi") if not snaps[k])
            )
        confirmed = _confirmed(cur, snaps["pscomppars"])
        toi = _toi(cur, snaps["toi"])
    return {
        "as_of": max(s[-1]["date"] for s in snaps.values()),
        "confirmed": confirmed,
        **toi,
    }
