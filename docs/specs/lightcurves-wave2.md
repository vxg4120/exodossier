# Spec: the light-curve results page (Wave 2 on the live site)

**Status:** active (spec drafted 2026-10-16, proceeding; Vib: yes to Wave 2)
**Owner:** Vib
**Repos touched:** exodossier (api, web, docs); space `deploy/` only for the open questions below
**Last updated:** 2026-10-16

## Goal
The Wave 2 light-curve pipeline (`pipeline/`) has produced a graded recovery baseline once, on
2026-07-15, and the only place anyone can read it is the committed
`docs/reports/recovery_report.md`. Nothing on the live site reads the pipeline's tables, and the
Docker image does not even contain `pipeline/`. This adds a `/lightcurves` page and three read-only
endpoints that show the pipeline's results straight from the `target`, `pipeline_run` and
`detection` tables, graded with the same rules as the report, with an honest empty state when the
tables hold nothing.

## Architecture decisions
- 2026-10-16 (Claude): **Grade in the API with the report's own functions.** The router imports
  `match_period`, `epoch_phase_offset`, `SNR_MIN`, `PERIOD_TOL`, `_best_recovery` and
  `_analyze_miss` from `quality/recovery_report.py` (which the image already ships). Rejected:
  re-implementing the rules, or storing a verdict column. Because: two copies of the rules would
  drift, and the schema's own comment says it stores measurements, never a verdict.
- 2026-10-16 (Claude): **No cache.** The slice is 58 targets with about four detections each; both
  endpoints load it and grade it per request (two small queries). Rejected: `RefreshingCache` as in
  `stats.py`. Because: the module docstring reserves it for responses that scan a lot, and this
  one scans less than a few hundred rows.
- 2026-10-16 (Claude): **Rows link to `/target/<candidate_id>`.** `target.candidate_id` references
  `candidate`, so whenever a row exists its candidate_id is current. Rejected: linking by TOI.
  Because: every other view links by candidate_id, and the target page resolves it directly.
- 2026-10-16 (Claude): **Verdict badges reuse the disposition badge tones** (confirmed for a match,
  known for a harmonic or an off-period signal, unknown for a non-result, the conflict chip for a
  failed run). No new colours and no font rules (another branch owns heading fonts).

## Constraints
- The API stays read-only (`get_db` marks the transaction READ ONLY). Nothing in this workstream
  writes to production, migrates it, or runs the pipeline there without Vib's explicit OK.
- No `font-family` rules; do not edit `web/src/views/Overview.tsx` (the landing route is owned by
  another branch).
- The page never says a planet was confirmed or rejected. It says recovered, flagged or missed.
- Read-only production queries stay outside 07:10-07:25 and 19:10-19:25 UTC (the nightly refresh).

## Interfaces & dependencies
- `GET /api/lightcurves/summary`: `state` (`ready` | `empty`), `targets`, `processed`,
  `not_processed`, `pending`, `gold_planets{targets,recovered,recovered_exact}`,
  `gold_false_positives{targets,with_signal}`, `discovery{targets,with_signal}`,
  `by_cohort{<cohort>:{label,description,targets,processed,by_verdict}}`, `last_run_at`,
  `data_vintage`, `run_attempts`, `median_runtime_s`, `lightcurve_files`, `lightcurve_stars`,
  `last_fetch_at`, `rules{period_tolerance,snr_min,statement}`, `verdicts{code:label}`.
- `GET /api/lightcurves/results?limit=1..200&offset>=0&sort=cohort|toi|snr|period&cohort=`:
  `{rows,total,limit,offset,sort,cohort}`; an unknown cohort is a 400, an unknown sort a 422.
  Each row: candidate_id, name, host, tic_id, toi, cohort, stratum, tfopwg_disp, the catalog
  period/depth, the latest run's status and timing, `verdict`, `match` (period ratio), 
  `phase_offset`, `reason`, `best` (the matching or strongest BLS/TLS detection) and
  `single_event`.
- `GET /api/lightcurves/target/{candidate_id}`: one row, or 404 when the candidate is not in the
  slice.
- Verdicts: gold planets `recovered` | `recovered_harmonic` | `missed`; gold false positives
  `signal_at_catalog_period` | `signal` | `no_signal`; discovery `signal` | `below_threshold`; any
  cohort `pending` (no run), `running` (row still marked running) or `not_processed`
  (no_data / timeout / error).
- Upstream: `pipeline/select_targets.py` fills `target`; `pipeline/process.py` fills
  `pipeline_run` + `detection` from the Parquet files under `data/lightcurves/` (on the laptop
  only: 211 MB, 749 files, 56 stars).

## Edge cases
- **Empty tables (the production state on 2026-10-16).** `identity/build.py` runs
  `TRUNCATE <derived graph> RESTART IDENTITY CASCADE` every night (space
  `deploy/nightly-refresh.sh`, step `exo_build_graph`, 07:10 and 19:10 UTC). `target` references
  `candidate`, and `pipeline_run` / `fp_scenario` reference `target`, so the CASCADE empties all
  four Wave 2 result tables on every rebuild. `lightcurve_file` has no such reference and
  survives. The endpoints answer `state: "empty"` with zero counts; the page says no results are
  on this server yet and names the indexed light curves.
- A run row left in `running` (a crashed process) grades as `running`, not as a failure.
- Discovery single-transit targets have no catalog period; the period columns show a dash and
  the note shows the single-dip SNR.
- Several runs for one target: only the latest (`max(pipeline_run_id)`) is graded, as in the
  report.

## Acceptance criteria
- [x] `DATABASE_URL=<any exo db> python -m pytest -q tests/test_api_lightcurves.py` passes
      (7 tests: grading, summary shape, pagination/sort/cohort, 400/422/404, empty state).
- [x] `python -m pytest -q tests` shows no new failures against the same database.
- [x] `cd web && pnpm run build` exits 0.
- [x] `curl -s localhost:8700/api/lightcurves/summary | jq -r .state` prints `empty` against a
      database whose `target` table is empty, and `ready` once one run is graded.
- [x] `curl -s 'localhost:8700/api/lightcurves/results?cohort=nope' -o /dev/null -w '%{http_code}'`
      prints `400`; `/api/lightcurves/target/-1` prints `404`.
- [x] `/lightcurves` is in the nav between Conflicts and Follow-up and renders at 1280x800 and
      390x844 without horizontal page scroll.
- [x] Against a database with a full 58-target run, the summary reproduces the report's headline
      counts for the same run: gold planets recovered 16/20, gold false positives with a signal
      20/20, discovery signals 16/18 (`curl ... | jq '.gold_planets.recovered,
      .gold_false_positives.with_signal, .discovery.with_signal'`). Verified 2026-10-16 on a
      local rerun over the restored seed dump: 16 (15 exact), 20, 16.
- [ ] Production shows real rows: `curl -s https://exo.vibcreates.com/api/lightcurves/summary |
      jq .processed` prints a number above 0 the morning after a nightly rebuild (blocked on the
      open questions below).

## Open questions
- **Vib: how should results survive the nightly rebuild?** Options: (a) drop the
  `target.candidate_id` foreign key so the TRUNCATE CASCADE no longer reaches the Wave 2 tables,
  keep TOI/TIC as the stable key and resolve candidate_id at read time through
  `entity_identifier` (the API would then join on TOI); (b) move the Wave 2 tables to their own
  schema with no reference into the graph; (c) re-run `select_targets` after every build (does not
  help: `pipeline_run` and `detection` still go). Recommendation: (a).
- **Vib: where does the pipeline run for production?** The Parquet files exist only on the
  laptop, and the image omits `pipeline/` and the lightkurve/TLS stacks. Either run
  `select_targets.py` + `process.py` from the laptop against production over an SSH tunnel
  (a write to prod; about 1-2 hours for 58 targets), or ship the files and a pipeline image to the
  box. Either way it is only worth doing after the first question is settled.

## Decision log & lessons learned
- 2026-10-16 (Claude) — The 2026-07-15 run's rows are gone from production and from the
  2026-07-21 seed dump (`deploy/seed/exo.dump`: `target`, `pipeline_run`, `detection`,
  `fp_scenario` all 0 rows; `lightcurve_file` 749 rows). The cause is the CASCADE above, not a
  failed run.
- 2026-10-16 (Claude) — Re-running `select_targets.py` against the restored dump selects the same
  58 targets (20 / 20 / 18), and 56 of their stars have light curves on disk.
- 2026-10-16 (Claude) — A local rerun of `process.py` over the same Parquet files (three cohorts
  in parallel, about 35 minutes) reproduces the July report's headline counts through the new
  endpoints: 16/20 (15 at the catalog period, TOI-2134.02 at x0.5), 20/20, 16/18.
