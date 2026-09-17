# Exo identity follow-up — source verification

2026-09-17. Isolated branch `codex/audit-followup-20260917`, base `a7259d6`.
Status: source implementation and independent verification complete through `ced85b5`.
The initial review of `ba58354` found two P2 consistency gaps, both reproduced and fixed below.
No production access or mutation, harvest, deployment, or external message was performed.
All database writes were isolated local fixtures.

## Verified defect and corrected behavior

A disposable fixture with two hosts both named `Collision`, TIC 111 and TIC 222,
each carrying one source's assertions, produced the following on the released base:

| Surface | Base `a7259d6` | Guarded implementation |
|---|---|---|
| Teff / radius / disposition conflict counts | 1 / 1 / 1 (fabricated) | 0 / 0 / 0 |
| TIC 111 dossier host crosswalk | TIC 111 + TIC 222 | TIC 111 only |
| TIC 111 dossier siblings | Both hosts' planets | TIC 111 planets only |
| TIC 111 dossier conflict flags | All three axes | None |

Six new regression cases initially failed on the unchanged base: different TICs,
an ambiguous null-TIC intermediary, separate null-only hosts, separate real conflicts,
a lowest-ID twin without claims, and host claims on a twin with no candidate.
All now pass, as do existing unambiguous TIC/KIC twin cases.

## Identity contract

One shared SQL relation computes host groups from `star.tic_id`, which is UNIQUE
when present. A null-TIC host can join a same-name host only if that case-insensitive
name has exactly one non-null TIC. Two non-null TICs never join; a null-TIC row with
zero or multiple possible TIC anchors keeps its own star ID. Candidate identity is
the guarded host group plus case-folded candidate name. Counts, lists, per-source
ranges, dossier crosswalks/claims/siblings and MCP `target_conflicts` share that rule.
Search expands host-name and host-identifier matches through this same guard while
preserving candidate-level matching and exact/prefix/substring ranks, with candidate
ID breaking equal rank/name ties.
Page-scoped queries inspect **all** same-name hosts before deciding whether an
anchor is unambiguous; limiting the page cannot hide a conflicting TIC.

Representatives are the lowest candidate IDs in their identity groups, independent
of which twin carries an attribute. Host-level rows link to the group's first
candidate, including when the actual claims live on a candidate-less host twin.
An exact identifier on that candidate-less alias resolves through the guarded group;
an ambiguous alias cannot borrow a foreign host's candidate. The alias lookup gap
was independently identified, reproduced as a failing test, and corrected.
Host groups with no candidate anywhere are excluded from the candidate-linked
conflict corpus, preventing count/list mismatch. Their raw assertions remain intact.
Equal display names and spreads use candidate ID as a stable pagination tie-break.

This preserves the existing unambiguous TIC/KIC presentation heuristic; a name and
one TIC are not independent astronomical proof of identity. Other identifiers and
coordinates are not newly interpreted. Separate null-only hosts can now produce
multiple rows with the same display name: preserving uncertainty is safer than an
unsupported merge. Existing name-only lookup still selects the lowest matching
candidate ID; numeric tokens still prefer candidate IDs, and an ambiguous alternate identifier
still selects the lowest matching candidate. Crosswalk uniqueness includes source
and owner, so alternate identifiers are not universally unique. This pre-existing
resolver precedence is unchanged; no general identifier redesign is claimed.

## Local verification

Inspected `conftest.py` first: `clean_graph` TRUNCATEs graph tables in a transaction.
All tests used a private process and explicit DSN, never the default port 5433 DB.

- Server: local Homebrew PostgreSQL 14.13, data directory
  `/tmp/codex-exo-identity-20260917/data`, loopback port 58945, database
  `exo_identity_test`, role `exo_test`. Runtime details in sibling `runtime.json`.
- Schema: all six source migrations applied only to the private DB. PostgreSQL 14
  lacks `UNIQUE NULLS NOT DISTINCT`, so the temporary in-memory migration text used
  `UNIQUE` instead. **Tracked migrations are unchanged.** Fixtures use distinct
  identifier rows valid under production constraints; insert-idempotency behavior
  and the production PostgreSQL query planner are not certified by this test run.
- Source assertions and identifiers are read, never changed by the implementation.
- No frontend changed, so no web build was needed.

Exact final checks from this isolated checkout:

```sh
DATABASE_URL='postgresql://exo_test@127.0.0.1:58945/exo_identity_test' \
  /Users/vgupta/Development/repos/exodossier/.venv/bin/python -m pytest \
  tests/test_api_conflicts_dedupe.py tests/test_normalize.py tests/test_cluster.py \
  tests/test_resolve.py tests/test_report.py
/Users/vgupta/Development/repos/exodossier/.venv/bin/ruff check \
  api/queries.py tests/test_api_conflicts_dedupe.py
git diff --check
```

Result: **40 passed in 4.95s**, ruff passed, diff whitespace check passed.
This includes 27 conflict/dossier tests (18 new cases),10 existing normalization/
clustering tests, and 3 existing resolver/report tests. The existing fixed-production-
dataset HTTP/MCP suites were not run against synthetic data; MCP's shared
`target_conflicts` query is directly covered, not its stdio transport.

## Synthetic performance check

A private synthetic graph contained 21,555 hosts, 25,921 candidates and 654,515
assertions. No production data was copied. Five warm samples per operation were
measured sequentially using the existing `/tmp/exo_bench_gen.py` and
`/tmp/exo_bench_run.py` scripts, after inspecting their local-only behavior:

```sh
/Users/vgupta/Development/repos/exodossier/.venv/bin/python /tmp/exo_bench_gen.py \
  'postgresql://exo_test@127.0.0.1:58945/exo_identity_test'
git show a7259d6:api/queries.py > /tmp/codex-exo-identity-20260917/baseline_queries.py
/Users/vgupta/Development/repos/exodossier/.venv/bin/python /tmp/exo_bench_run.py \
  'postgresql://exo_test@127.0.0.1:58945/exo_identity_test' \
  /tmp/codex-exo-identity-20260917/baseline_queries.py baseline
/Users/vgupta/Development/repos/exodossier/.venv/bin/python /tmp/exo_bench_run.py \
  'postgresql://exo_test@127.0.0.1:58945/exo_identity_test' api/queries.py final-exact-guarded
```

| Median local operation | Base | Final guarded source |
|---|---:|---:|
| Disposition page40 | 295ms | 327ms |
| Radius page40 | 397ms | 451ms |
| Teff page40 | 239ms | 375ms |
| Disposition per-source page | 8.1ms | 4.2ms |
| Radius per-source page | 8.3ms | 4.5ms |
| Teff per-source page | 4.1ms | 4.1ms |
| Catalog statistics | 578ms | 723ms |

Totals stayed 15,534 disposition / 2,525 radius / 339 Teff in the synthetic graph,
which has only unambiguous twins. Added guard work raises some full-graph timings. The accepted local budget is a
five-warm-sample median below 1 second for each 40-row conflict page; all three
pass. Production-major query-plan verification remains an operator/release check.
This is not a live benchmark or an uptime claim. An early 6.2s radius regression was
rejected: EXPLAIN showed a 95x cardinality overestimate and >50 million join-filter
comparisons. Window-based host anchors, scoped PK-led twin expansion, a materialized
attribute filter before numeric regex, and a conflict-result boundary remove that
plan without weakening identity rules. A scoped dossier check took 13ms.

## Independent review fixes and semantic limits

The read-only review of `a7259d6...ba58354` found two pre-existing gaps within the
consistency acceptance criterion. Both were reproduced with disposable-DB tests:

1. `search_targets` did not expand a candidate-less alias whose exact identifier
   could resolve. It now expands host matches through the same guarded relation.
   Exact alias search succeeds; an ambiguous alias cannot borrow foreign candidates.
2. Dossier/MCP float arithmetic flagged exactly `1.17` versus `1.3` as a radius
   conflict while SQL excluded the exact 10% threshold; Python accepted `+2`, which
   SQL excluded. Both now use the existing SQL decimal grammar and exact strict
   cross-multiplication. SQL compares numeric products; Python parses Decimal and
   compares Fractions internally. Public JSON field types are unchanged.

Numeric fixtures cover below/exact/above 10%, a difference beyond default Decimal
context precision, leading plus, invalid text, NaN, Infinity and large finite
scientific notation. All raw strings remain visible. Thresholds and source-count
rules are unchanged; **flags/counts can change for previously inconsistent boundary
values**. The near-above case `1.169999999999999999999999999999` versus `1.3` was also
rounded out by the old SQL division; exact cross-multiplication correctly includes
it. Leading-plus and nonfinite strings remain excluded from the numeric conflict
vote under the established SQL grammar, and are now excluded consistently by MCP
and dossiers. No scientific measurements are corrected or discarded.

The initial review independently ran 10 pure tests, lint and diff checks; all passed.
Its P3 measured-overhead observation is accepted with the explicit budget above.
Artifacts: `/tmp/codex-exo-identity-20260917/verify.md` and `verify.log`.
The private server was stopped after the final tests and benchmark.

## Final independent verdict

Read-only Codex reviewed `a7259d6...ba58354`, then the bounded follow-up
`ba58354...ced85b5`. The final exact verdict was:

> No new findings requiring changes. Reviewed `ba58354...ced85b5` and the amended
> spec/report. Both earlier P2 findings are resolved in source.

All acceptance criteria passed source review or the explicitly reported local DB
and benchmark evidence. The reviewer independently passed 10 pure pytest tests,
lint, whitespace checks, 27 numeric/raw-response checks across Decimal precisions
2/28/80, and 900 integer-oracle boundary checks at 1%, 5% and 10%. It did not execute
PostgreSQL or verify deployment. Final artifact:
`/tmp/codex-exo-identity-20260917/verify-final.md` (execution log `verify-final.log`).

The parent separately reviewed the final source and independently ran eight pure
numeric probes with an unreachable DSN: exact/below/above 10%, a beyond-28-digit
near-boundary value, leading plus, NaN, Infinity and large finite scientific
notation. All passed; no DB connection was made. The parent confirmed the remaining
performance overhead is accepted under the documented budget.

## Release handoff

1. Parent hands the reviewed branch to the confirmed operator for release review,
   build and deployment. None is implied by these commits or local DB results.
2. Verify query plans on the deployment PostgreSQL major and live representative
   links after release, especially null-only same-name hosts and ambiguous aliases.
3. HTTP/MCP transport and live deployment remain unverified for this patch.

The private PostgreSQL process is stopped. The final documentation-only commit
records these results; reviewed implementation ends at `ced85b5`.
