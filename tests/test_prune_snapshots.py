"""Retention for the raw_* snapshot tables (scripts/prune_snapshots.py).

The policy is a pure function over the runs present in one table, so most of it is pinned here
without a database. The db-marked tests drive the two write paths, the nightly DELETE and the
one-time TRUNCATE-and-reinsert, against scratch tables and a real raw table, and race a
concurrent writer against the rewrite.
"""

import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from common.db import get_autocommit_conn, get_conn
from scripts import prune_snapshots
from scripts.prune_snapshots import (
    KEEP_LATEST,
    SNAPSHOT_TABLES,
    Run,
    compact,
    prune_table,
    runs_in,
    runs_to_drop,
)

MIGRATIONS = Path(__file__).resolve().parent.parent / "db" / "migrations"


def _run(run_id, month, day, status="ok", rows=10):
    return Run(run_id, status, datetime(2026, month, day, 7, 10, tzinfo=UTC), rows)


def _ids(runs):
    return sorted(r.run_id for r in runs)


def test_keeps_the_newest_three_ok_runs_and_each_months_first():
    runs = [_run(1, 7, 8), _run(2, 7, 9), _run(3, 8, 3), _run(4, 8, 4), _run(5, 8, 5),
            _run(6, 9, 1), _run(7, 9, 2), _run(8, 9, 3), _run(9, 9, 4)]
    # 1, 3 and 6 open July, August and September; 7, 8 and 9 are the newest three.
    assert _ids(runs_to_drop(runs)) == [2, 4, 5]


def test_a_month_is_a_utc_month():
    # 23:30 on Aug 31 in Los Angeles is already September in UTC, so this run opens September.
    late = Run(2, "ok", datetime.fromisoformat("2026-08-31T23:30:00-07:00"), 10)
    runs = [_run(1, 8, 1), late] + [_run(i, 9, i) for i in range(3, 7)]
    assert _ids(runs_to_drop(runs)) == [3]


def test_the_first_ok_run_ever_is_always_kept():
    """The monthly rule keeps a table's first OK run forever, even behind an earlier failed run.
    pipeline/select_targets.py reads each TOI's OLDEST raw_exofop_toi row, and for most TOIs that
    is in run 1 (2026-07-15); the TOIs whose oldest row is in a dropped run are measured in
    docs/specs/raw-retention.md."""
    runs = [_run(1, 7, 14, status="error"), _run(2, 7, 15)] + [
        _run(i, 7, i + 13) for i in range(3, 12)
    ]
    assert 2 not in _ids(runs_to_drop(runs))


def test_a_run_newer_than_the_newest_ok_run_is_never_touched():
    # Run 7 is an ingest still in flight: no reader sees it, and it is not ours to judge. Run 2
    # failed long ago, and no reader ever selects a failed run.
    runs = [_run(1, 9, 1), _run(2, 9, 2, status="error"), _run(3, 9, 3), _run(4, 9, 4),
            _run(5, 9, 5), _run(6, 9, 6), _run(7, 9, 7, status=None)]
    assert _ids(runs_to_drop(runs)) == [2, 3]


def test_an_older_run_still_in_flight_is_kept():
    """Two ingests overlap and the newer one finishes first. The older one has committed its rows
    but not yet recorded 'ok', so its id is below the newest OK run. Only a finished run is ours
    to judge (the satellite platform's Codex verify, 2026-09-29)."""
    runs = [_run(1, 9, 1), _run(2, 9, 2), _run(3, 9, 3), _run(4, 9, 4, status=None),
            _run(5, 9, 5)]
    assert 4 not in _ids(runs_to_drop(runs))


def test_only_a_finished_run_is_ever_dropped():
    # A missing ledger row, an empty status or an unknown one: none of them says finished.
    runs = [_run(1, 9, 1), Run(2, None, None, 10), _run(3, 9, 3, status=""),
            _run(4, 9, 4, status="running"), _run(5, 9, 5, status="error"),
            _run(6, 9, 6), _run(7, 9, 7), _run(8, 9, 8)]
    assert _ids(runs_to_drop(runs)) == [5]


def test_a_table_with_no_ok_run_keeps_everything():
    runs = [_run(1, 9, 1, status="error"), _run(2, 9, 2, status=None)]
    assert runs_to_drop(runs) == []


def test_keeping_no_run_is_refused():
    # identity/build.py and identity/assertions.py read the newest OK run.
    assert KEEP_LATEST >= 1
    with pytest.raises(ValueError, match="newest OK run"):
        runs_to_drop([_run(1, 9, 1)], keep_latest=0)


def test_every_raw_table_in_the_migrations_is_pruned():
    """A raw_* table left off SNAPSHOT_TABLES grows by a full copy of its source every pull,
    which is how the exo database reached 6.4 GB by 2026-10-09."""
    created = set()
    for sql in MIGRATIONS.glob("*.sql"):
        created |= set(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(raw_\w+)", sql.read_text()))
    assert created, "no raw_* tables found; did the migrations move?"
    assert created <= set(SNAPSHOT_TABLES), f"not pruned: {sorted(created - set(SNAPSHOT_TABLES))}"


def test_only_raw_landing_tables_are_pruned():
    """source_assertion and the rest of the graph are derived: identity/build.py truncates and
    rebuilds them from the newest runs every night, so they never accumulate copies."""
    assert all(t.startswith("raw_") for t in SNAPSHOT_TABLES)


LABELS = [("aug1", "2026-08-01", "ok"), ("aug2", "2026-08-02", "ok"),
          ("sep1", "2026-09-01", "ok"), ("sep2", "2026-09-02", "ok"),
          ("sep3", "2026-09-03", "ok"), ("flight", "2026-09-04", None)]


def _ledger(cur, source, endpoint="scratch"):
    """One ledger row per label. Returns {label: ingest_run_id}."""
    ids = {}
    for label, started, status in LABELS:
        cur.execute(
            "INSERT INTO ingest_run (source, endpoint, started_at, status) "
            "VALUES (%s, %s, %s, %s) RETURNING ingest_run_id",
            (source, endpoint, started, status),
        )
        ids[label] = cur.fetchone()[0]
    return ids


def _seed(cur, table, source):
    """Five OK runs across two months and one in flight, three rows each, in a table with a
    GENERATED ALWAYS identity and a generated column. Returns {label: ingest_run_id}."""
    cur.execute(
        f"CREATE {'TEMP ' if table.startswith('raw_prune_scratch') else ''}TABLE {table} ("
        " row_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,"
        " ingest_run_id BIGINT NOT NULL, payload TEXT,"
        " payload_len INT GENERATED ALWAYS AS (length(payload)) STORED)"
    )
    ids = _ledger(cur, source)
    for label, run_id in ids.items():
        cur.execute(
            f"INSERT INTO {table} (ingest_run_id, payload) "
            "SELECT %s, %s || '-' || g FROM generate_series(1, 3) g",
            (run_id, label),
        )
    return ids


def _rows(conn, table="raw_prune_scratch"):
    with conn.cursor() as cur:
        cur.execute(f"SELECT row_id, ingest_run_id, payload, payload_len FROM {table} "
                    "ORDER BY row_id")
        return cur.fetchall()


@pytest.mark.db
def test_compact_keeps_exactly_the_kept_rows_with_their_ids(db_conn):
    with db_conn.cursor() as cur:
        ids = _seed(cur, "raw_prune_scratch", "prune_test")
    before = _rows(db_conn)
    runs = runs_in(db_conn, "raw_prune_scratch")
    assert [r.rows for r in runs] == [3] * 6
    drop = runs_to_drop(runs)
    assert [r.run_id for r in drop] == [ids["aug2"]]

    assert compact(db_conn, "raw_prune_scratch", runs, drop) == 15
    # Byte-identical rows, identities and generated values included, minus the dropped run.
    assert _rows(db_conn) == [row for row in before if row[1] != ids["aug2"]]
    # The identity sequence was not reset, so a new row cannot collide with a kept one.
    with db_conn.cursor() as cur:
        cur.execute("INSERT INTO raw_prune_scratch (ingest_run_id, payload) "
                    "VALUES (%s, 'new') RETURNING row_id", (ids["sep3"],))
        assert cur.fetchone()[0] > max(row[0] for row in before)
    db_conn.rollback()


@pytest.mark.db
def test_delete_drops_exactly_the_dropped_runs(db_conn):
    with db_conn.cursor() as cur:
        ids = _seed(cur, "raw_prune_scratch", "prune_test")
    before = _rows(db_conn)
    runs, drop = prune_table(db_conn, "raw_prune_scratch", "delete")
    assert [r.run_id for r in drop] == [ids["aug2"]]
    assert _rows(db_conn) == [row for row in before if row[1] != ids["aug2"]]
    db_conn.rollback()


@pytest.mark.db
def test_compact_on_a_real_raw_table(db_conn):
    """The production shape: raw_exofop_toi's raw_id is GENERATED ALWAYS, its ingest_run_id is a
    foreign key, and its extra column is JSONB with a default. Every kept row comes back
    unchanged, raw_id included."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM raw_exofop_toi)")
        if cur.fetchone()[0]:
            pytest.skip("needs an empty raw_exofop_toi (run against a scratch database)")
        ids = _ledger(cur, "exofop", endpoint="prune_test")
        for label, run_id in ids.items():
            cur.execute(
                "INSERT INTO raw_exofop_toi (toi, tic_id, period_days, epoch_bjd, extra, "
                "ingest_run_id) SELECT g || '.01', g, 1.5 * g, 2459000.25 + g, "
                "jsonb_build_object('label', %s::text), %s FROM generate_series(1, 3) g",
                (label, run_id),
            )
        cur.execute("SELECT * FROM raw_exofop_toi ORDER BY raw_id")
        before = cur.fetchall()
    runs, drop = prune_table(db_conn, "raw_exofop_toi", "compact")
    assert [r.run_id for r in drop] == [ids["aug2"]]
    with db_conn.cursor() as cur:
        cur.execute("SELECT * FROM raw_exofop_toi ORDER BY raw_id")
        after = cur.fetchall()
        run_col = [d.name for d in cur.description].index("ingest_run_id")
    assert after == [row for row in before if row[run_col] != ids["aug2"]]
    db_conn.rollback()


@pytest.mark.db
def test_compaction_never_loses_a_row_committed_while_it_waits(db_conn):
    """A writer holds an uncommitted insert into the newest run when the compaction starts. The
    compaction must wait for it and keep its row. Reading the runs before locking would copy the
    kept rows without it, wait at the TRUNCATE, and then truncate it away."""
    table = f"raw_prune_race_{uuid.uuid4().hex[:8]}"
    source = f"prune_race_{uuid.uuid4().hex[:8]}"
    setup = get_autocommit_conn()
    writer = get_conn()
    try:
        with setup.cursor() as cur:
            ids = _seed(cur, table, source)
        with writer.cursor() as cur:
            cur.execute(f"INSERT INTO {table} (ingest_run_id, payload) VALUES (%s, 'late')",
                        (ids["sep3"],))
        threading.Timer(0.5, writer.commit).start()

        runs, drop = prune_table(db_conn, table, "compact")
        db_conn.commit()

        payloads = [row[2] for row in _rows(db_conn, table)]
        assert "late" in payloads
        assert not any(p.startswith("aug2") for p in payloads)
        assert len(payloads) == 16  # 18 seeded + the late row - aug2's three
    finally:
        writer.close()
        db_conn.rollback()
        with setup.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table}")
            cur.execute("DELETE FROM ingest_run WHERE source = %s", (source,))
        setup.close()


@pytest.mark.db
def test_a_dry_run_changes_nothing_and_names_itself(monkeypatch, capsys):
    """The default is a dry run, safe against any database. Its last line carries the script's
    name, which is what makes a successful night greppable in the nightly's refresh.log."""
    monkeypatch.setattr("sys.argv", ["prune_snapshots.py"])
    assert prune_snapshots.main() == 0
    out = capsys.readouterr().out.splitlines()
    assert out[-1].startswith("prune_snapshots: would drop ")
    assert not any("deleted" in line or "compacted" in line for line in out)
