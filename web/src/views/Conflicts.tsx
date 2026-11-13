import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { getConflicts, getStats } from "../api/client";
import type {
  BySourceDisposition,
  BySourceRange,
  ConflictRow,
  ConflictsResponse,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtInt, fmtNum } from "../lib/format";
import { CONFLICT_TABS, dramaticCounterpart, toConflictTab } from "../lib/conflicts";
import { dispositionMeta } from "../lib/dispositions";
import { Panel } from "../components/Panel";
import { DataTable, Pager, pastTheEnd, type Column } from "../components/DataTable";
import { DispositionBadge } from "../components/DispositionBadge";
import { Async, EmptyState } from "../components/States";

const LIMIT = 40;

export function Conflicts() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const tab = toConflictTab(params.get("tab"));
  // One page offset per tab, so a tab change never first asks for the old page.
  const [offsets, setOffsets] = useState<Record<string, number>>({});
  const offset = offsets[tab] ?? 0;
  const setOffset = (next: number) => setOffsets((o) => ({ ...o, [tab]: next }));

  const stats = useApi(() => getStats(), []);
  // keep: the rows stay on screen, dimmed, while the next page loads, so the pager keeps focus;
  // keyed by the tab, so a tab change shows the loader, not the old tab's rows under new headers
  const page = useApi<ConflictsResponse>(() => getConflicts(tab, LIMIT, offset), [tab, offset], {
    keep: true,
    keepKey: tab,
  });
  const counts = stats.data?.conflicts;
  const open = (r: ConflictRow) => navigate(`/target/${r.candidate_id}`);

  return (
    <div className="view fadein">
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Conflicts</h1>
          <p className="vhead__desc">
            The browsable corpus of cross-source disagreement — the same star or candidate described
            differently by ExoFOP, the NASA TOI table, the Kepler KOI table, and the Archive&rsquo;s
            per-publication and composite tables. Every row deep-links to the full provenance.
          </p>
        </div>
      </header>

      <Panel title="Cross-source conflicts" flush>
        <div className="tabs">
          {CONFLICT_TABS.map((t) => {
            const count = counts?.[t.statsKey];
            return (
              <button
                key={t.key}
                type="button"
                className={`tab${tab === t.key ? " is-active" : ""}`}
                aria-pressed={tab === t.key}
                onClick={() => setParams({ tab: t.key })}
              >
                {t.tabLabel}
                {count !== undefined ? (
                  <span className="tab__count num">{fmtInt(count)}</span>
                ) : null}
              </button>
            );
          })}
        </div>

        <p className="conflict-headline">{CONFLICT_TABS.find((t) => t.key === tab)?.headline}</p>

        <Async state={page} loadingLabel="Loading conflicts" loadingRows={10}>
          {(data) => (
            <>
              {pastTheEnd(data.rows.length, data.total) ? (
                // a page past the end: the list shrank since it was counted
                <EmptyState
                  title="Nothing on this page"
                  message="The list changed since it was counted. Go back a page."
                />
              ) : tab === "disposition" ? (
                <DataTable<ConflictRow>
                  columns={DISPOSITION_COLS}
                  rows={data.rows}
                  rowKey={(r) => r.candidate_id}
                  onRowClick={open}
                  stickyFirst
                />
              ) : (
                <DataTable<ConflictRow>
                  columns={numericCols(tab === "teff" ? "K" : "R⊕")}
                  rows={data.rows}
                  rowKey={(r) => r.candidate_id}
                  onRowClick={open}
                  stickyFirst
                />
              )}
              <Pager
                offset={offset}
                limit={LIMIT}
                total={data.total}
                shown={page.loading ? undefined : data.rows.length}
                onOffset={setOffset}
              />
            </>
          )}
        </Async>
      </Panel>
    </div>
  );
}

function BySourceDispositions({ rows }: { rows: BySourceDisposition[] }) {
  return (
    <div className="bysrc">
      {rows.map((b, i) => (
        <span className="bysrc__item" key={`${b.source}-${i}`}>
          <span className="bysrc__src">{b.source}</span>
          <span className="bysrc__v">{dispositionMeta(b.disposition).label}</span>
        </span>
      ))}
    </div>
  );
}

function BySourceRanges({ rows }: { rows: BySourceRange[] }) {
  return (
    <div className="bysrc">
      {rows.map((b, i) => {
        // Compare the rendered figures: values that agree at display precision are one value.
        const lo = fmtNum(b.min);
        const hi = fmtNum(b.max);
        return (
          <span className="bysrc__item" key={`${b.source}-${i}`}>
            <span className="bysrc__src">{b.source}</span>
            <span className="bysrc__v">
              {lo === hi ? lo : `${lo}–${hi}`}
              {b.n > 1 ? ` (${b.n})` : ""}
            </span>
          </span>
        );
      })}
    </div>
  );
}

/** The row deep-links as a whole (click, Enter); the name is also a real link, so the page can
    be opened in a new tab and a screen reader hears where the row goes. */
function TargetLink({ row }: { row: ConflictRow }) {
  return (
    <Link to={`/target/${row.candidate_id}`} className="mono-hi" onClick={(e) => e.stopPropagation()}>
      {row.target}
    </Link>
  );
}

const DISPOSITION_COLS: Column<ConflictRow>[] = [
  { key: "target", header: "Candidate", render: (r) => <TargetLink row={r} /> },
  { key: "host", header: "Host", render: (r) => r.host },
  {
    key: "resolved",
    header: "Resolved",
    render: (r) => <DispositionBadge disposition={typeof r.resolved === "string" ? r.resolved : null} />,
  },
  {
    key: "kind",
    header: "Flag",
    render: (r) =>
      r.dramatic ? (
        <span className="badge badge--conflict">
          <span className="badge__glyph" aria-hidden="true" />
          FP vs {dramaticCounterpart(r.dispositions).toLowerCase()}
        </span>
      ) : null,
  },
  {
    key: "who",
    header: "Who says what",
    render: (r) => <BySourceDispositions rows={(r.by_source as BySourceDisposition[]) ?? []} />,
  },
];

function numericCols(unit: string): Column<ConflictRow>[] {
  return [
    { key: "target", header: "Candidate", render: (r) => <TargetLink row={r} /> },
    { key: "host", header: "Host", render: (r) => r.host },
    {
      key: "spread",
      header: "Spread",
      num: true,
      render: (r) => (
        <span className="num" style={{ color: "var(--conflict)" }}>
          {r.spread_pct == null ? "—" : `${Number(r.spread_pct).toFixed(1)}%`}
        </span>
      ),
    },
    {
      key: "range",
      header: `Range (${unit})`,
      num: true,
      render: (r) =>
        r.min == null || r.max == null ? (
          <span className="dash">—</span>
        ) : (
          <span className="num">{`${fmtNum(r.min)} – ${fmtNum(r.max)}`}</span>
        ),
    },
    {
      key: "who",
      header: "Who says what",
      render: (r) => <BySourceRanges rows={(r.by_source as BySourceRange[]) ?? []} />,
    },
  ];
}
