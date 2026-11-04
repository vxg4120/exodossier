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

- [x] L. Adversarial review of the branch itself (three independent refuters per finding; what
      survived, exo's share): a forecast still in flight when the query changes is dropped
      when it lands instead of shown under the new selection (a request nonce); the client
      decodes a matched id once before encoding it (an encoded pathname was encoded twice) and
      the server encodes exactly as encodeURIComponent does, with tests on both sides; the
      slot that bounds concurrent /passes requests also brackets the per-step geometry and
      each (nsat × nt) plane is freed before the next is built, so the bound holds for memory
      as its comment claimed; the graph mark moved from module level onto the catalog spot
      checks so the contract and error-path tests (and a new one for the MCP server's
      limit/offset validation) run on CI's empty graph; pyarrow ships with the ingest
      requirements; the Follow-up test instant is the same calendar instant in the current
      year, inside the ten-year bound; the CI header says three jobs and the duplicated -q no
      longer hides pytest's tally.
- [x] M. Design pass (21 items from a ranked plan scored by two reviewers for look, feel and
      consistency across both apps, in three batches; then an independent verifier measured
      every item against a build of the base commit, two fix rounds closed what it found, and
      a parity pass aligned the orbital app to this one on every shared point; everything
      measured with Playwright at 1440, 1024, 390 and 360 px; the final sweep of 13 routes x
      2 widths has scrollWidth == clientWidth, no console errors and one h1 per page). Lists
      reload in place: useApi({ keep, keepKey }) keeps the Conflicts and Light curves lists
      mounted and dimmed while a page loads (focus and scroll hold), a tab or cohort switch
      shows the loader (a kept page had rendered under the new tab's columns for the whole
      fetch), a failed reload's Retry shows the loader, the pager's end buttons are
      aria-disabled so landing on page one keeps the focus, and a page past the end reads
      "Nothing on this page" instead of "41–40 of 3,274" (8 vitest cases). Phones: the top
      bar is one 79 px row at 360 (the clock pushed the help button onto a second row,
      115 px); the conflict and light-curve tables pin their first column and keep 38 px rows
      (one row was 177 px tall, the page 5,444 px long) and the note column wraps to two
      lines at most on tablets; tab strips fade where they scroll ("Host Teff 1,083" was
      off-screen), to 1024 px where the rail still cut "Discovery slice" flush; the
      congestion heatmap sizes its cells to the panel; focus rings draw inside their
      scroller and the pinned first cell paints its share; the search, date and select
      fields are 16 px; colophon and table links are 37–40 px tall on touch screens. Tablet:
      panel heads wrap to a one-line title over a right-aligned meta at 1024. Type: conflict
      counts are Fraunces like the stat value that shows the same figure; story headlines
      step to 19 px; display titles on a 1.15 line-height; 72ch / 48ch measures; citations
      and units 11 px; About's sub-heads are the micro-voice label; closing notes share one
      rule. Honest states: disabled controls are legible (4.7–5.3:1, were 2.2–2.7:1); "Run
      forecast" stays enabled with aria-busy; an empty start date is a field error with
      focus on the field and the other fields level, instead of a "Signal lost" alert; a
      changed window marks the forecast out of date instead of blanking it; a failed search
      has Retry; light-curve results are a verdict family instead of the disposition badges
      and the conflict triangle; the forecaster's caveat is a quiet note. Copy and
      structure: the Target page is a chapter with the candidate name as its h2; "1 id",
      "1 attribute disagrees"; "Search stars and candidates"; four waiting tiles on a cold
      start; "Period (d)", "SNR ≥ 7", "P ≥ 30 d" in the API, fixture and page; "host Teff",
      "Who says what", "About & methodology"; the landing description says what the page
      shows in the route table, the static shell and the served head, held together by a test.
- [x] N. Code review of the design diff (six readers per repo — state logic, markup and a11y,
      CSS cascade, copy and docs, tests and gates, API and shell — each measured in the
      browser; 26 findings for this repo, four confirmed by an adversarial refuter, the rest
      hand-triaged, 23 fixed). Phones: the colophon's touch tap boxes lay over the next line's
      links, so a tap on "ExoFOP-TESS" could open the issues page (the box pushes the lines
      apart now, and the dotted rule reads at 5.5:1, was 1.5:1); hiding the clock left the "?"
      tour button floating beside the brand, 179 px short of the edge (the brand takes the
      row); the forecaster's Run button dropped 22 px under the pointer when the start-date
      message grew the line (pinned under the label line beside the fields); the 16 px control
      floor was keyed on width, so a phone in landscape still zoomed (device trait now); the
      forecaster's submit stayed 36 px on touch; a pinned name link could not be truncated by
      the cell's ellipsis on a 320 px phone (it truncates itself). Keyboard: a list reloading
      in place was inert for the mouse only, so Enter on the pager kept paging through the
      request (the kept wrapper swallows clicks while it loads); a failed page turn dropped the
      focus to the body (Retry takes it); a tab or view link focused by keyboard stayed clipped
      under its strip's fade (revealed on focus, with scroll-margin clear of the fade); the
      pager's range is a status region so a page landing is heard; the search bar rang for any
      descendant; a control scrolled under a pinned column stayed hidden on focus. Lists: while
      a kept page reloaded the pager printed a range true of neither the rows on screen nor the
      page in flight (it names the page in flight); Next stayed live on a page past the end;
      one past-the-end predicate for the pager and both views, with a test. API and copy: GET /
      was the one shell served verbatim from web/dist, with its build-time head and no cache
      header, because Starlette normalises the root to "." before the fallback sees it (it
      renders like every route now, and the served-shell test holds it to the table); "Orbital
      period · days" under a KV strip that says "Period (d)"; the README and the MCP README
      still said "host-Teff" and "host-temperature"; "1 ids · by source". Tests: the
      forecaster's settings-change updater is a pure function with a test; the inert pager ends
      and the past-the-end predicate are tested; test_root binds to the route table instead of
      a copy literal; the fast CI job names its skips. Left: the fixture mock's total is the
      fixture's (so Next in fixture mode lands on "nothing on this page"); a hook test would
      need a DOM environment; a tab's focus ring under the fade is pre-existing where the strip
      fits.
