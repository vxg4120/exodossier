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
