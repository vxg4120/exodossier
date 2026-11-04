# Exo identity follow-up plan

Spec: `docs/specs/audit-followup-20260917.md`.

- [x] Isolate from released source a7259d6 and define the identity boundary.
- [x] Reproduce distinct-TIC name collision in a disposable local fixture database.
- [x] Correct the common identity keys and all consumers without changing raw records.
- [x] Run covering tests, evaluate compatibility with existing twin behavior.
- [x] Commit, run independent read-only verify, resolve verified findings.
- [x] Record final source/test state and parent release handoff; no deployment by Codex.

## Review
Source verification complete through `ced85b5`: 40 local tests, ruff and diff checks
pass. Independent review resolved two reproduced P2s and ended with no new findings;
10 pure tests plus numeric boundary probes independently passed. See
`tasks/exo-followup-report.md` for evidence, PG14 schema limitation, accepted synthetic
budget, and final exact verdict. Private PostgreSQL stopped. Parent will send the
release handoff; no production access, push or deployment was performed here.

# Look-and-feel and consistency batch, 2026-11-04 (Vib: "keep going … check for bugs,
# check for inconsistencies … make it really, really good")
Owner: session faraday. Both apps built in fixture mode and screenshotted on every route at
1440 and 375 px; measured with Playwright, not eyeballed.
- [x] A. Top bar: "Conflict Explorer · Read-only" ran 26 px past the brand column's border at
      every desktop width (sub-line 203 px of text in a 177 px box). --rail-w 210 -> 244 px,
      the width orbital already uses for the same reason.
- [x] B. A colophon under every view, as on orbital: freshest pull from the ingest ledger, the
      archives the data belongs to, the about page, the corrections channel.
- [x] C. API client: the 30 s request timeout orbital has (a request the API never answers now
      ends in Retry, not an endless skeleton), one fetch path for /api and /api/twoskies, and
      a readable message for a body that is not JSON (the Follow-up view showed
      "Unexpected token '<'" when the API was down behind a proxy page). 4xx detail text from
      the API passes through to the visitor.
- [x] D. Tests: mcp==1.14.1 no longer imports beside the current pydantic (its private
      _typing_extra helper is gone), so `import mcp` failed and test_mcp_server could not even
      collect. Bounded to mcp>=1.30,<2 (2.x renames FastMCP). Ported orbital's `graph` marker
      and skip-on-empty conftest: on a migrated, empty database the suite now skips 34 and fails
      0 (it failed 13 before); test_api_* modules no longer probe the database at import time;
      test_marker_hygiene.py is the tripwire; test_pipeline importorskips the Parquet engine.
- [x] E. CI: .github/workflows/ci.yml (ruff + network-free unit job against a closed port, a
      Postgres 16 db job with migrations and the full suite, a pnpm build job).
Gates: ruff clean; full suite on the local empty graph 0 failed; `-m "not db"` against a
closed port all passed; `pnpm build` clean.
- [x] F. Fixture mode covers every view now: fixtures/lightcurves.json (twenty graded TOIs across
      the three cohorts) and fixtures/twoskies.json (targets, the congestion field, one canned
      Kitt Peak forecast) served by the mock clients. Rendering them exposed a live bug: the
      Follow-up "Largest operator" tile divided every payload SpaceX ever flew by the tracked LEO
      population (~113% of LEO). The top-operators query now counts on-orbit payloads only
      (decay_date IS NULL) and the tile reads as a share of tracked LEO, clamped at 100.
- [x] G. vitest (3.x, the line that runs on Vite 5) with 19 unit tests over lib/format (the
      significant-figure fmtNum), seo (route table vs App.tsx, canonical case and slash rules)
      and States.visitorMessage; the CI web job runs them before the build.
- [x] H. README: the site's views, the API endpoints, the MCP server that already exists (the
      roadmap called it a later wave), and CI.
