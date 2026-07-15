import { Link } from "react-router-dom";
import { getStats } from "../api/client";
import type { IngestRun } from "../api/types";
import { useApi } from "../hooks/useApi";
import { compact, fmtDate, fmtInt } from "../lib/format";
import { CONFLICT_TABS } from "../lib/conflicts";
import { runStatusMeta } from "../lib/dispositions";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { Async } from "../components/States";

export function Overview() {
  const stats = useApi(() => getStats(), []);

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
            <div className="grid grid--stats">
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

              <Panel title="The dramatic three" meta="FALSE POSITIVE vs CONFIRMED">
                <p className="hint" style={{ marginBottom: 12 }}>
                  Three candidates where one catalog calls it a false positive while another confirms
                  it — the sharpest form of &ldquo;nobody agrees on a planet.&rdquo;
                </p>
                <div className="stack stack--sm">
                  {["Kepler-1517 b", "TOI-1836 c", "Kepler-404 b"].map((name) => (
                    <Link key={name} to={`/target/${encodeURIComponent(name)}`} className="assert-line">
                      <span className="assert-val mono-hi">{name}</span>
                      <span className="badge badge--conflict">
                        <span className="badge__glyph" aria-hidden="true" />
                        FP vs CONFIRMED
                      </span>
                    </Link>
                  ))}
                </div>
              </Panel>
            </div>

            <Panel title="Ingestion ledger" meta="last catalog pull per endpoint" flush>
              <LedgerTable runs={s.ingest_runs} />
            </Panel>
          </>
        )}
      </Async>
    </div>
  );
}

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
            <th className="is-num">Last run</th>
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
                <td className="is-num num">{fmtInt(r.rows_ingested)}</td>
                <td className="is-num num">{fmtDate(r.finished_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
