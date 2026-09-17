import { Link } from "react-router-dom";
import { getConflicts, getStats } from "../api/client";
import type { ConflictRow, IngestRun } from "../api/types";
import { useApi } from "../hooks/useApi";
import { compact, fmtDate, fmtInt } from "../lib/format";
import { CONFLICT_TABS } from "../lib/conflicts";
import { runStatusMeta } from "../lib/dispositions";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { Async } from "../components/States";

/** How many of the dramatic cases the panel lists (dramatic rows sort first in the corpus). */
const DRAMATIC_SHOWN = 3;

export function Overview() {
  const stats = useApi(() => getStats(), []);
  const dramatic = useApi(() => getConflicts("disposition", DRAMATIC_SHOWN, 0), []);

  return (
    <div className="view fadein">
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Overview</h1>
          <p className="vhead__desc">
            A read-only window on the exoplanet identity graph — one resolved record per host star
            and candidate, stitched from the NASA Exoplanet Archive and ExoFOP. The numbers below are
            the coverage of the graph and the cross-source disagreements it surfaces. ExoDossier shows
            where the archives disagree, with provenance; it does not adjudicate or confirm.
          </p>
        </div>
      </header>

      <Async state={stats} loadingLabel="Loading catalog telemetry">
        {(s) => (
          <>
            <div className="grid grid--stats" data-tour="stats">
              <StatTile
                lead
                hero
                label="Candidates"
                value={compact(s.candidates)}
                sub={
                  <>
                    host stars <span className="num">{fmtInt(s.stars)}</span>
                  </>
                }
              />
              <StatTile
                label="Crosswalk identifiers"
                value={compact(s.identifiers)}
                sub="TIC · TOI · CTOI · KOI · Gaia · HD · HIP"
              />
              <StatTile
                label="Source assertions"
                value={compact(s.source_assertions)}
                sub="per-publication provenance"
              />
              <StatTile
                conflict
                label="Disposition conflicts"
                value={compact(s.conflicts.disposition)}
                sub={
                  <>
                    incl. <span className="num">{s.conflicts.disposition_dramatic}</span> FALSE
                    POSITIVE vs CONFIRMED
                  </>
                }
              />
            </div>

            <div className="grid grid--2">
              <Panel title="Where the archives disagree" meta="disagreements are data">
                <div className="conflict-list">
                  {CONFLICT_TABS.map((c) => (
                    <Link key={c.key} to={`/conflicts?tab=${c.key}`} className="conflict-row">
                      <span className="conflict-row__count num">
                        {fmtInt(s.conflicts[c.statsKey])}
                      </span>
                      <span className="conflict-row__body">
                        <span className="conflict-row__label">{c.cardLabel}</span>
                        <span className="conflict-row__sub">{c.cardSub}</span>
                      </span>
                      <span className="conflict-row__arrow" aria-hidden="true">
                        →
                      </span>
                    </Link>
                  ))}
                </div>
              </Panel>

              <Panel
                title={`The dramatic ${fmtInt(s.conflicts.disposition_dramatic)}`}
                meta="FALSE POSITIVE vs CONFIRMED"
                dataTour="dramatic"
              >
                <p className="hint" style={{ marginBottom: 12 }}>
                  Candidates where one catalog calls it a false positive while another confirms it
                  — the sharpest form of &ldquo;nobody agrees on a planet.&rdquo;
                </p>
                <Async state={dramatic} loadingLabel="Loading the dramatic cases">
                  {(page) => (
                    <DramaticList rows={page.rows} total={s.conflicts.disposition_dramatic} />
                  )}
                </Async>
              </Panel>
            </div>

            <Panel title="Ingestion ledger" meta="last landed pull · latest check per endpoint" flush>
              <LedgerTable runs={s.ingest_runs} />
            </Panel>
          </>
        )}
      </Async>
    </div>
  );
}

/** The first dramatic rows of the disposition corpus (they sort first), with the way to the rest
    when the live count outruns the panel. */
function DramaticList({ rows, total }: { rows: ConflictRow[]; total: number }) {
  const shown = rows.filter((r) => r.dramatic);
  if (shown.length === 0) {
    return <p className="hint">No FALSE POSITIVE vs CONFIRMED case in the current graph.</p>;
  }
  return (
    <div className="stack stack--sm">
      {shown.map((r) => (
        <Link key={r.candidate_id} to={`/target/${r.candidate_id}`} className="assert-line">
          <span className="assert-val mono-hi">{r.target}</span>
          <span className="badge badge--conflict">
            <span className="badge__glyph" aria-hidden="true" />
            FP vs CONFIRMED
          </span>
        </Link>
      ))}
      {total > shown.length ? (
        <Link to="/conflicts?tab=disposition" className="assert-line">
          <span className="assert-val hint">
            all {fmtInt(total)} in the conflict corpus →
          </span>
        </Link>
      ) : null}
    </div>
  );
}

/** Rows and "Last pull" come from the last run that actually landed data; "State" and "Checked"
    from the latest run, which inside the 24h freshness window is a skipped_fresh check that pulls
    nothing — showing that run's zero rows alone made the puller look silently dead. */
function LedgerTable({ runs }: { runs: IngestRun[] }) {
  return (
    <div className="table-wrap">
      <table className="dtable">
        <thead>
          <tr>
            <th>Source</th>
            <th>Endpoint</th>
            <th>State</th>
            <th className="is-num">Rows</th>
            <th className="is-num">Last pull</th>
            <th className="is-num">Checked</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => {
            const meta = runStatusMeta(r.status);
            return (
              <tr key={`${r.source}-${r.endpoint}`}>
                <td className="mono-hi">{r.source}</td>
                <td>{r.endpoint}</td>
                <td>
                  <span className="run-state">
                    <span className={`run-dot ${meta.className}`} aria-hidden="true" />
                    {meta.label}
                  </span>
                </td>
                <td className="is-num num">{fmtInt(r.last_ok_rows)}</td>
                <td className="is-num num">{fmtDate(r.last_ok_at)}</td>
                <td className="is-num num">{fmtDate(r.finished_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
