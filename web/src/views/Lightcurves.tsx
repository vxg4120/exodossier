import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getLightcurveResults, getLightcurveSummary } from "../api/client";
import type {
  LightcurveCohort,
  LightcurveResults,
  LightcurveRow,
  LightcurveSummary,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtDate, fmtInt, fmtNum } from "../lib/format";
import { Panel } from "../components/Panel";
import { Cell, DataTable, Pager, type Column } from "../components/DataTable";
import { StatTile } from "../components/StatTile";
import { Async, EmptyState } from "../components/States";

const LIMIT = 40;

const COHORT_TABS: { key: LightcurveCohort | null; label: string }[] = [
  { key: null, label: "All targets" },
  { key: "gold_planet", label: "Known planets" },
  { key: "gold_fp", label: "Known false positives" },
  { key: "discovery", label: "Discovery slice" },
];

const COHORT_SHORT: Record<LightcurveCohort, string> = {
  gold_planet: "Planet",
  gold_fp: "False pos.",
  discovery: "Discovery",
};

function toCohort(v: string | null): LightcurveCohort | null {
  return v === "gold_planet" || v === "gold_fp" || v === "discovery" ? v : null;
}

/** Verdict -> the existing badge tones, so no new colours: a match reads as confirmed, a
    harmonic or off-period signal as known, a non-result as unknown, a failed run as a conflict. */
const VERDICT_TONE: Record<string, string> = {
  recovered: "badge--disp disp-confirmed",
  signal_at_catalog_period: "badge--disp disp-confirmed",
  recovered_harmonic: "badge--disp disp-known",
  signal: "badge--disp disp-known",
  missed: "badge--disp disp-unknown",
  no_signal: "badge--disp disp-unknown",
  below_threshold: "badge--disp disp-unknown",
  pending: "badge--disp disp-unknown",
  running: "badge--disp disp-unknown",
  not_processed: "badge--conflict",
};

const VERDICT_SHORT: Record<string, string> = {
  recovered: "Recovered",
  recovered_harmonic: "Harmonic",
  missed: "Missed",
  signal_at_catalog_period: "Signal at catalog P",
  signal: "Signal",
  no_signal: "No signal",
  below_threshold: "Below threshold",
  not_processed: "Run failed",
  running: "Running",
  pending: "Not run",
};

function VerdictBadge({ verdict, title }: { verdict: string; title?: string }) {
  return (
    <span className={`badge ${VERDICT_TONE[verdict] ?? "badge--disp disp-unknown"}`} title={title}>
      <span className="badge__glyph" aria-hidden="true" />
      {VERDICT_SHORT[verdict] ?? verdict}
    </span>
  );
}

export function Lightcurves() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const cohort = toCohort(params.get("cohort"));
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [cohort]);

  useEffect(() => {
    const previous = document.title;
    document.title = "Light curves · ExoDossier";
    return () => {
      document.title = previous;
    };
  }, []);

  const summary = useApi<LightcurveSummary>(() => getLightcurveSummary(), []);
  const page = useApi<LightcurveResults>(
    () => getLightcurveResults(LIMIT, offset, cohort),
    [cohort, offset],
  );
  const open = (r: LightcurveRow) => navigate(`/target/${r.candidate_id}`);

  return (
    <div className="view fadein">
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Light curves</h1>
          <p className="vhead__desc">
            An independent check on the catalogs. For a fixed slice of TOIs, the pipeline downloads
            the TESS light curves from MAST, searches them for a periodic transit (BLS across every
            sector, TLS on the longest single stretch, and a single-dip search for the discovery
            slice), then grades what it finds against the catalog period. It recovers or flags
            signals; it does not confirm or reject planets.
          </p>
        </div>
      </header>

      <Async state={summary} loadingLabel="Loading pipeline summary" loadingRows={3}>
        {/* With nothing graded the tiles would be four dashes; the empty state below says it. */}
        {(s) => (s.state === "empty" ? null : <SummaryStrip s={s} />)}
      </Async>

      <Panel title="Per-target results" flush>
        <div className="tabs">
          {COHORT_TABS.map((t) => {
            const n =
              t.key === null ? summary.data?.targets : summary.data?.by_cohort[t.key]?.targets;
            return (
              <button
                key={t.label}
                className={`tab${cohort === t.key ? " is-active" : ""}`}
                onClick={() => setParams(t.key ? { cohort: t.key } : {})}
              >
                {t.label}
                {n !== undefined ? <span className="tab__count num">{fmtInt(n)}</span> : null}
              </button>
            );
          })}
        </div>
        {summary.data ? (
          <p className="conflict-headline">
            {cohort && summary.data.by_cohort[cohort]
              ? summary.data.by_cohort[cohort].description
              : summary.data.rules.statement}
          </p>
        ) : null}

        <Async state={page} loadingLabel="Loading results" loadingRows={10}>
          {(data) =>
            data.total === 0 ? (
              <EmptyState
                title="No pipeline results on this server yet"
                message={
                  summary.data && summary.data.lightcurve_files > 0
                    ? `${fmtInt(summary.data.lightcurve_files)} TESS light curves for ${fmtInt(
                        summary.data.lightcurve_stars,
                      )} stars are indexed (fetched ${fmtDate(
                        summary.data.last_fetch_at,
                      )}), but no target slice has been selected and processed against the current catalog graph. The table fills in after the next pipeline run.`
                    : "No light curves have been fetched or processed for this catalog yet. The table fills in after the next pipeline run."
                }
              />
            ) : (
              <>
                <DataTable<LightcurveRow>
                  columns={COLUMNS}
                  rows={data.rows}
                  rowKey={(r) => r.target_id}
                  onRowClick={open}
                />
                <Pager offset={offset} limit={LIMIT} total={data.total} onOffset={setOffset} />
              </>
            )
          }
        </Async>
      </Panel>
    </div>
  );
}

function SummaryStrip({ s }: { s: LightcurveSummary }) {
  const runtime = s.median_runtime_s === null ? null : Math.round(s.median_runtime_s);
  return (
    <div className="grid grid--stats" style={{ marginBottom: "var(--pad)" }}>
      <StatTile
        lead
        hero
        label="Known planets recovered"
        value={s.gold_planets.targets ? `${s.gold_planets.recovered}/${s.gold_planets.targets}` : "—"}
        sub={
          s.gold_planets.targets ? (
            <>
              <span className="num">{s.gold_planets.recovered_exact}</span> at the catalog period
            </>
          ) : (
            "no graded run yet"
          )
        }
      />
      <StatTile
        label="False positives with a signal"
        value={
          s.gold_false_positives.targets
            ? `${s.gold_false_positives.with_signal}/${s.gold_false_positives.targets}`
            : "—"
        }
        sub="expected: eclipsing binaries dip too"
      />
      <StatTile
        label="Discovery signals"
        value={s.discovery.targets ? `${s.discovery.with_signal}/${s.discovery.targets}` : "—"}
        sub="long-period and single-transit TOIs"
      />
      <StatTile
        label="Targets processed"
        value={s.targets ? `${s.processed}/${s.targets}` : "—"}
        sub={
          s.last_run_at ? (
            <>
              last run <span className="num">{fmtDate(s.last_run_at)}</span>
              {runtime !== null ? (
                <>
                  {" "}
                  · median <span className="num">{runtime}</span> s
                </>
              ) : null}
            </>
          ) : (
            <>
              <span className="num">{fmtInt(s.lightcurve_files)}</span> light curves indexed
            </>
          )
        }
      />
    </div>
  );
}

const COLUMNS: Column<LightcurveRow>[] = [
  {
    key: "target",
    header: "Candidate",
    render: (r) => (
      <span>
        <span className="mono-hi">{r.name}</span>
        {r.toi ? <span className="hint"> TOI-{r.toi}</span> : null}
      </span>
    ),
  },
  { key: "cohort", header: "Slice", render: (r) => COHORT_SHORT[r.cohort] ?? r.cohort },
  { key: "disp", header: "TFOPWG", render: (r) => <Cell>{r.tfopwg_disp}</Cell> },
  {
    key: "pk",
    header: "Catalog P (d)",
    num: true,
    render: (r) => <span className="num">{fmtNum(r.known_period_days, 4)}</span>,
  },
  {
    key: "pr",
    header: "Found P (d)",
    num: true,
    render: (r) => <span className="num">{fmtNum(r.best?.period_days, 4)}</span>,
  },
  {
    key: "method",
    header: "Method",
    render: (r) => <Cell>{r.best?.method.toUpperCase()}</Cell>,
  },
  {
    key: "snr",
    header: "SNR",
    num: true,
    render: (r) => <span className="num">{fmtNum(r.best?.snr, 3)}</span>,
  },
  {
    key: "verdict",
    header: "Result",
    render: (r) => (
      <VerdictBadge
        verdict={r.verdict}
        title={r.match && r.match !== 1 ? `period ratio ×${fmtNum(r.match, 3)}` : undefined}
      />
    ),
  },
  {
    key: "why",
    header: "Note",
    render: (r) => (
      <span className="wrap-cell">
        <Cell>{r.reason ?? singleEventNote(r)}</Cell>
      </span>
    ),
  },
];

function singleEventNote(r: LightcurveRow): string | null {
  const se = r.single_event;
  if (!se || se.snr === null) return null;
  return `single dip SNR ${fmtNum(se.snr, 3)}`;
}
