# Spec: snapshot retention for the exo raw_* tables

**Status:** shipped 2026-10-09 (approved by Vib: "you can build and deploy"); the
nightly criterion is still open
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
- 2026-10-09: **Do not change `pipeline/select_targets.py`.** Per candidate, it reads the
  `raw_exofop_toi` row with the lowest `raw_id`, across every run and whatever the run's status,
  and it looked like a bug. The cohort it selects is meant to be a fixed, reproducible slice,
  `persist()` deletes targets that are no longer selected, and `pipeline_run.target_id`
  references `target` with no cascade. Pointing it at the newest run would reshuffle the cohort
  and could fail on that foreign key. Rejected: "fix" it to the newest run. Because: that is a
  research-design change for Vib, not retention. The prune's own effect on it is measured under
  Edge cases.
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
- **`select_targets.py` (manual, and not in the image).** It reads the lowest-`raw_id` row
  per TOI across all runs, so for a TOI whose oldest row is in a dropped run, its oldest *kept*
  row takes over. Measured on production on 2026-10-09, before compaction, with the policy
  reimplemented in SQL (`raw_exofop_toi`: 61 runs, all OK; kept runs 1, 1106, 1484, 1844, 1898,
  1916 and 1934): of 8,151 TOIs, 84 have their oldest row in a dropped run, none vanishes, and
  23 would show a different disposition, period, epoch, depth, duration or Tmag. Any of those
  can move a TOI between strata or change the brightest-first ranking on a re-run. Production's
  `target` table is empty, so no persisted target and no `pipeline_run` is affected. Run 1 holds
  8,064 TOIs and the newest run holds 8,151, so the 84 are almost all TOIs that joined after
  July 15, which a re-run would already add to the pool for the first time.
- **The ledger keeps every row.** A dropped run's `ingest_run` row stays, with status 'ok' and
  no raw rows. Every reader joins from the raw table, so it never selects a run with no rows.
- **Runs with a NULL status** (three on 2026-10-09) are MAST light-curve pulls with no raw rows,
  so the policy never sees them.
- **The monthly sample grows**, by about 105 MB a month in all, which is 1.2 GB a year. It's the
  same trade-off as space, and it's open below.
- **TRUNCATE is not MVCC-safe**, but no API path reads a raw table, so only the nightly could
  notice, and the compaction runs outside it.

## Rollout (one time, in this order)
1. Outside the nightly windows, dump the six tables on the box under `nohup`
   (`pg_dump -Fc -t raw_ps -t raw_exofop_toi ...` to `/root/backups/`), copy the dump to
   `~/Backups/vibcreates/`, compare checksums, and check that `pg_restore --list` shows all
   six tables' data. Then delete the box copy.
2. Merge to `main`, push, `git pull` on the box, and rebuild the image with
   `docker compose up -d --build exo-api`, so that `scripts/prune_snapshots.py` is in it.
3. Run the dry run in the container, and check that its plan matches the measurement above.
4. Run `--compact` under `nohup` with a log file in `/root/backups/`.
5. Verify the production acceptance criterion below.
6. Only then merge and pull space's nightly change, which puts `exo_prune_snapshots` live.

## Acceptance criteria
- [x] `DATABASE_URL=<scratch> pytest -q -W error tests/test_prune_snapshots.py` passes on a
  freshly migrated `timescale/timescaledb:latest-pg17`: 15 tests, 5 of them database-backed
  (the two-connection race, a compaction of the real `raw_exofop_toi`, and a dry run of
  `main()`). Mutating the code to drop unfinished runs, to read before locking, or to skip the
  monthly keepers fails the suite.
- [x] On the same scratch database, the full suite's failure set is identical to `main`'s
  (18 data-dependent tests on an empty graph), with 94 passed against 79.
- [x] Production: the backup is on the laptop and `pg_restore --list` shows all six tables. The
  dry run's plan keeps each table's newest 3 OK runs and its July, August, September and October
  firsts. After `--compact`, a dry run reports "would drop 0 runs", the `exo` database is under
  1.5 GB, each table's newest OK run id and row count are unchanged, `raw_exofop_toi` still holds
  run 1, and the landing page, `exo.vibcreates.com` and `exo.vibcreates.com/api/stats` return 200.
  Done on 2026-10-09 (21:17 to 21:18 UTC). The backup is
  `~/Backups/vibcreates/exo-raw-snapshots-20261009.dump` (759 MB, with a matching sha256 on
  both ends; it restores 583,404 `raw_koi_cumulative` rows, the live count). `--compact`
  dropped 54 of 61 runs per table, 324 runs and 4,151,312 rows in all, in about 40 s, and
  `raw_ps` went from 3,817 MB to 443 MB. `exo` went from 6,403 MB to 949 MB, and the box
  from 7.1 GB free (81%) to 12 GB free (67%). Each table's newest OK run (1934 to 1939) kept
  its row count, run 1 kept its 8,064 TOIs, and a dry run and the nightly's own `--apply`
  command both drop 0 runs.
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
- 2026-10-09 (Codex verify on c07051b, confirmed by Claude): no compaction defect, and the port
  matches the original. The six raw tables have outgoing foreign keys to `ingest_run` only, with
  no incoming foreign key, view or trigger, and `raw_id` is a GENERATED ALWAYS identity, which
  the reinsert preserves. Recheck this whenever a migration touches a raw table. Two findings
  were fixed. (1) The first draft claimed the prune left `select_targets.py` unchanged, which
  code alone could not show, so it was replaced with the production measurement under Edge
  cases. (2) The space runbook sent exo operators to foreground commands without the backup,
  so it now points at the Rollout above.
