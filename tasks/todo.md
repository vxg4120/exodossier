# Exo identity follow-up plan

Spec: `docs/specs/audit-followup-20260917.md`.

- [x] Isolate from released source a7259d6 and define the identity boundary.
- [x] Reproduce distinct-TIC name collision in a disposable local fixture database.
- [x] Correct the common identity keys and all consumers without changing raw records.
- [x] Run covering tests, evaluate compatibility with existing twin behavior.
- [ ] Commit, run independent read-only verify, resolve verified findings.
- [ ] Record final source/test state and operator handoff; no deployment by Codex.

## Review
Implementation and local verification complete: 40 tests, ruff and diff checks pass.
See `tasks/exo-followup-report.md` for baseline reproduction, identity tradeoffs,
PG14 schema limitation and synthetic benchmark. Initial review P2s reproduced and fixed; final re-review next; no deployment.
