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
- [x] G. vitest (3.x, the line that runs on Vite 5) with 22 unit tests over lib/format (the
      significant-figure fmtNum), seo (route table vs App.tsx, canonical case and slash rules)
      and States.visitorMessage; the CI web job runs them before the build.
- [x] H. README: the site's views, the API endpoints, the MCP server that already exists (the
      roadmap called it a later wave), and CI.
- [x] I. Phone nav strip and stat strip follow orbital's rules: the 00-05 indices go under 560px,
      links tighten (three views fully visible at 390px instead of two), the right-edge fade is a
      fixed 40px band and the last view and last stat chip get room to scroll out from under it
      (measured: last link's right edge meets the fade start exactly, as on orbital).
- [x] J. Web audit (an independent read of every view, component and helper; 23 findings, each
      re-verified before the fix): the Follow-up forecast stayed on screen under another
      target's hint line after a target or input change (it clears on any change now); "Run
      forecast" threw an uncaught RangeError on an empty start date (a readable message now);
      fmtNum's three significant figures rounded a 5,842 K host to "5,840" and a BJD epoch to
      "2.46e+6" (four figures, fixed notation up to 1e9, coordinates at four decimals); the
      site's own search example "TIC 278892590" returned nothing because identifiers are stored
      bare (the API and the mock strip the catalog prefix; LIKE metacharacters are literal);
      About quoted the live radius count (3,611) as the frozen report's (3,614); conflict and
      light-curve tabs carried no aria-pressed; table rows deep-linked with no real link (the
      candidate cell is a Link now); tab changes fetched the old page offset first; the
      disagreement flag was colour-only; an unmapped disposition read as a dash instead of the
      source's own words; an empty cohort on a populated server read "no results on this
      server yet"; a cold-start stories payload rendered "0 confirmed planets"; "50 hits" was
      the cap, not the count; the pager used the browser locale; the client canonical was not
      percent-encoded (it disagreed with the server's); fmtDayShort threw on a missing date;
      the heatmap caption counted undrawn bins; the colophon's About link reloaded the app;
      spread_pct and orbit heights rendered unformatted; About's prose used h2 under an h2.
- [x] K. API audit (both services): /api/target/² and the MCP resolve tools raised on a
      unicode digit that str.isdigit() accepts and int() rejects (ASCII digits only now, and
      the MCP tools return their error dict); /api/twoskies/passes answered 500 for an ISO
      instant at the calendar's edge (OverflowError) and accepted a start centuries away
      (422 beyond ten years); its time grid could reach 721 points over the real LEO catalog
      (~1.5 GB per request; capped at 241 by coarsening the step, velocities dropped, two
      propagations at a time); an empty catalog was cached for the whole TTL and every
      request at expiry rebuilt its own copy (single-flight, empty never cached); MCP
      list_conflicts/search_targets passed limit and offset to SQL unchecked; offsets above
      int8 reached Postgres as NUMERIC and failed; the server canonical for "/target/TOI-1836
      b" carried the raw space while the client's carried %20; a matched route marked noindex
      would have shipped a canonical; bad input answered 400 on some routes and 422 on others
      (422 everywhere, tests moved).
