# Spec: snapshot retention for the exo raw_* tables

**Status:** active (approved by Vib on 2026-10-09: "you can build and deploy")
**Owner:** Vib
**Repos touched:** exodossier (the script), space (the nightly step and runbook)
**Last updated:** 2026-10-09

## Goal
Every exo ingest pull lands a full copy of its source in the six `raw_*` tables, and nothing ever
deleted a copy. On 2026-10-09 the `exo` database was 6.4 GB, and about 6.2 GB of that was 61
copies per table going back to 2026-07-15. Each real pull adds about 105 MB, and a pull happens
about five times a week, so the box (CX23, 81% disk) was losing about 0.5 GB a week to history
that no nightly reader reads. This applies the policy that has bounded the satellite platform's
`oei` raw tables since 2026-10-01 (space `docs/specs/raw-retention.md`) to `exo`.

## Architecture decisions
- 2026-10-09: **Port space's `scripts/prune_snapshots.py` verbatim in shape.** It has the same
  policy (per table, keep the newest 3 OK runs plus the first OK run of each UTC month, and drop
  only other runs that finished before the newest OK run), the same three modes (dry run,
  nightly `--apply`, one-time `--compact`) and the same lock-before-read compaction. Rejected:
  a shared package. Because: the two repos already port `common/db.py` and `ingest/runlog.py`
  this way, and the copy has been in production for nine days.
- 2026-10-09: **`KEEP_LATEST` may go as low as 1.** Exo has no reader that compares two runs
  (space keeps at least 2 for `identity/churn.py`). It stays at 3 for slack.
- 2026-10-09: **Do not change `pipeline/select_targets.py`.** It reads each TOI's oldest
  `raw_exofop_toi` row, and it looked like a bug. On inspection: run 1 (2026-07-15) is the Wave 2
  cohort's answer key, the monthly rule keeps it forever, `persist()` deletes targets that are
  no longer selected, and `pipeline_run.target_id` references `target` with no cascade. Pointing
  it at the newest run would reshuffle the cohort and fail on that foreign key. Rejected: "fix"
  it to the newest run. Because: that is a research-design change for Vib, not retention.
- 2026-10-09: **The backlog goes through `--compact` before the nightly step goes live**, the
  lesson from space's 2026-10-01 rollout, where the nightly met the backlog first and took
  64 minutes.

## Constraints
- Deleting production rows needs Vib's approval. He gave it on 2026-10-09 for this backlog and
  for the nightly step.
- A laptop backup of every row to be deleted exists, and `pg_restore --list` reads it, before
  `--compact` runs.
- Never run `--compact` inside the 07:10 or 19:10 UTC nightly windows. One-offs on the box run
  under `nohup` with a log file, never tied to a live SSH session.
- Never drop a run that has not finished ('ok' or 'error'), whatever its id.
- A new `raw_*` table must be added to `SNAPSHOT_TABLES`. The test suite fails until it is.
- This touches only the `exo` database's `raw_*` tables. Never the `oei` database, and never
  `ingest_run` (the ledger, 320 kB, which `fresh_within` reads).

## Interfaces & dependencies
- `scripts/prune_snapshots.py`: a dry run by default. `--apply` runs the nightly DELETE and
  VACUUM. `--compact` runs the one-time rewrite. It prints a final `prune_snapshots:` line.
- Readers of the raw tables: `identity/build.py` and `identity/assertions.py` take
  `max(ingest_run_id)` among OK runs, and `ingest/loaders.py` only writes. The API, the web app
  and `mcp/` read none of them. No view and no foreign key depends on a raw table.
- space `deploy/nightly-refresh.sh`: `exo_prune_snapshots` runs
  `python scripts/prune_snapshots.py --apply` in the `exo-api` container, as the last exo
  step, after every reader of tonight's runs. `scripts/` is baked into the image, so the image
  is rebuilt before the nightly line goes live, or the step soft-fails with
  "!! exo prune_snapshots failed" until it is.

## Edge cases
- **`select_targets.py` (manual, not in the image).** It reads the oldest raw row per TOI. For
  the Wave 2 cohort that is run 1, which is kept. For a TOI that first appeared in a dropped run,
  its oldest row becomes its oldest kept row, so a re-run could carry a slightly newer ephemeris
  for a TOI that joined the pool after July 15. A re-run already differs from July 15 anyway,
  because the pool has grown since then.
- **The ledger keeps every row.** A dropped run's `ingest_run` row stays, with status 'ok' and
  no raw rows. Every reader joins from the raw table, so it never selects a run with no rows.
- **Runs with a NULL status** (three on 2026-10-09) are MAST light-curve pulls with no raw rows,
  so the policy never sees them.
- **The monthly sample grows**, by about 105 MB a month in all, which is 1.2 GB a year. It's the
  same trade-off as space, and it's open below.
- **TRUNCATE is not MVCC-safe**, but no API path reads a raw table, so only the nightly could
  notice, and the compaction runs outside it.

## Acceptance criteria
- [x] `DATABASE_URL=<scratch> pytest -q -W error tests/test_prune_snapshots.py` passes on a
  freshly migrated `timescale/timescaledb:latest-pg17`: 15 tests, 5 of them database-backed
  (the two-connection race, a compaction of the real `raw_exofop_toi`, and a dry run of
  `main()`). Mutating the code to drop unfinished runs, to read before locking, or to skip the
  monthly keepers fails the suite.
- [x] On the same scratch database, the full suite's failure set is identical to `main`'s
  (18 data-dependent tests on an empty graph), with 94 passed against 79.
- [ ] Production: the backup is on the laptop and `pg_restore --list` shows all six tables. The
  dry run's plan keeps each table's newest 3 OK runs and its July, August, September and October
  firsts. After `--compact`, a dry run reports "would drop 0 runs", the `exo` database is under
  1.5 GB, each table's newest OK run id and row count are unchanged, `raw_exofop_toi` still holds
  run 1, and the landing page, exo and `exo.vibcreates.com/api/` return 200.
- [ ] After the next two nightlies, `grep -c "step exo_prune_snapshots: .*exit 0" refresh.log`
  is 2, `grep -c "!! exo prune_snapshots failed" refresh.log` is 0, and `exo_build_graph`
  exits 0.

## Open questions
- (Vib) Is a monthly sample of raw history worth about 1.2 GB a year across both apps, or
  should the keepers become quarterly? It's the same answer for `oei` and `exo`.
- (Vib) `select_targets.py` treats July 15 as a frozen cohort while the graph keeps moving. If
  the cohort should follow the live TFOPWG list, that's a deliberate re-selection, and it means
  handling the `pipeline_run` foreign key.

## Decision log & lessons learned
- 2026-10-09 (Claude): the space retention spec listed only `oei` tables, and nothing flagged
  that `exo` lands copies the same way, so it grew for nine more days. Lesson: when a policy is
  ported between sibling apps, check every database on the box, not only the one being fixed.
