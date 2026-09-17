# Spec: Guard Exo conflict identity pooling

**Status:** active
**Owner:** Vib
**Repos touched:** exodossier
**Last updated:** 2026-09-17

## Goal
Prevent different identified host stars with the same display name from pooling
claims, crosswalks or siblings, while preserving proven catalog twins and consistent
conflict counts, list links, target dossiers and MCP results. Base `a7259d6`.

## Architecture decisions
- 2026-09-17 — Fix the common identity grouping contract consistently across SQL
  counts/lists, target lookup, and target_conflicts. No data merge or production repair.
- 2026-09-17 — Distinct non-null TIC identities must never pool because a name matches.
  A missing TIC must not arbitrarily attach to one of multiple same-name TIC identities.

## Constraints
- No production mutation, deployment, AWS/kubectl, production DB access/writes,
  harvests, paid APIs, or emails. Disposable local test database fixtures are allowed.
- Preserve source assertions and IDs; do not rewrite the identity graph or discard claims.
- Do not invent catalog identity, coordinates, epoch/proper-motion explanations or provenance.
- Keep public API shape, stable target links and scientific conflict rules.
- Never share a database with another running session or inherit a live DSN.

## Interfaces & ownership
Worker owns this isolated repo's implementation/tests and `tasks/exo-followup-report.md`.
Read `docs/SPEC.md` plus the prior independent report in the sibling Codex audit worktree.
Update common grouping logic in `api/queries.py` and every consumer consistently.

## Edge cases
Same host name with different TICs; a TIC-less alias with one unambiguous TIC host;
ambiguous null-TIC rows; multiple planets at one host; case differences; conflicting
sources on alternate IDs; stable canonical representative links; crosswalk/sibling isolation.

## Acceptance criteria
- [x] Fixture with same host name and two distinct TICs produces no fabricated Teff
  conflict and never returns foreign crosswalks, assertions or siblings in either dossier.
- [x] A TIC-less same-name alias can preserve the established unambiguous single-TIC
  twin behavior; ambiguous aliases cannot bridge distinct identified hosts.
- [x] Numeric/disposition counts equal unpaginated list cardinality; target links and
  target_conflicts expose exactly the same claims/conflict semantics as the listed group.
- [x] Meaningful disposable-local-Postgres regression tests pass with explicit DSN,
  including conflicting alternate twins and empty/non-conflict cases. Document exact commands.
- [x] Relevant existing tests pass; web build if frontend is changed.
- [x] Exact and search lookup of candidate-less aliases use the guarded host group;
  ambiguous aliases never borrow a foreign candidate. Candidate-level search ranking remains.
- [x] Numeric parsing and strict threshold comparison match across SQL, dossier and MCP,
  including exact/below/above threshold, leading plus, invalid and nonfinite raw claims.
- [x] Median of five warm synthetic runs for each 40-row conflict page stays below 1s;
  accept documented identity-safety overhead. Production-major planning remains a release check.
- [ ] Independent read-only Codex verify covers `a7259d6...HEAD`; findings are verified
  before source/spec amendments. Final report separates tested source from live deployment.

## Open questions
- Resolved in source: hosts with no unambiguous TIC anchor remain separate by star ID.
  Other catalog identifiers and coordinate evidence require a separately validated policy.
- Production PostgreSQL planner and live behavior remain operator verification work.

## Decision log & lessons learned
- 2026-09-17 (prior review, to reproduce here) — Two same-name stars with TIC 111
  and TIC 222 manufactured a Teff conflict and foreign siblings under lower(name) grouping.

- 2026-09-17 (Codex implementation, verified with disposable fixtures) — A single TIC
  anchor preserves the established same-name null-TIC twin behavior; zero/multiple TIC
  anchors preserve separate null-TIC hosts. This is a presentation heuristic, not a
  claim of scientific identity. All raw rows and public response fields remain intact.
- 2026-09-17 (Codex implementation, verified with disposable fixtures) — Representatives
  must come from the whole identity group, not only rows carrying an attribute. Host
  claims on a candidate-less twin can link to another twin's candidate. Host groups
  with no candidate are outside the candidate-linked corpus; assertions remain stored.
- 2026-09-17 (Codex implementation, verified locally) — 31 tests pass on a private
  PostgreSQL 14.13 instance with a temporary migration-text compatibility substitution
  for UNIQUE NULLS NOT DISTINCT. Source migrations are unchanged; this does not verify
  production uniqueness-idempotency or PostgreSQL-version-specific query planning.
- 2026-09-17 (Codex implementation, verified with EXPLAIN and synthetic graph) — Computed
  identity joins can misestimate row counts and reorder into quadratic joins. Scoped
  lookup still needs all same-name hosts; window anchors and materialized filtering
  boundaries avoid the observed regression without weakening the guard. Final synthetic
  pages were 324/442/367 ms for disposition/radius/Teff; these are not live timings.
- 2026-09-17 (independent peer finding, verified and fixed by Codex) — A candidate-less
  alias's identifier previously appeared in the pooled dossier but could not resolve
  back to it. Host identifier lookup now expands through the same guarded group; an
  ambiguous null-TIC alias without its own candidate remains unresolved. Regression
  was reproduced before the fix and the final 31-test suite passes.
- 2026-09-17 (independent Codex P2 findings, reproduced and fixed) — Search omitted
  candidate-less aliases, and float/SQL numeric grammar differed at threshold boundaries.
  Search now expands through guarded host groups. SQL and Python now use exact strict
  cross-products with the established decimal grammar; raw claims and JSON types remain.
  Below/exact/above and beyond-28-digit cases pass. Counts may change only where previous
  numeric classification was inconsistent; scientific thresholds/source rules are unchanged.
- 2026-09-17 (parent-reviewed P3 budget) — Accept measured guard overhead under a median
  1s synthetic page-40 budget; final measured pages were 327/451/375 ms and statistics 723 ms.
  Production-major planner verification remains an operator limitation, not a prerequisite
  requiring paid infrastructure. The final local suite passes 40 tests.
- 2026-09-17 (reviewed limitation) — Numeric candidate IDs take lookup precedence;
  otherwise shared alternate identifiers select the lowest match. Crosswalk uniqueness is
  scoped by source and owner, not global. This existing behavior is not redesigned here.
