import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getConflicts, getStats } from "../api/client";
import type {
  BySourceDisposition,
  BySourceRange,
  ConflictRow,
  ConflictsResponse,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtInt, fmtNum } from "../lib/format";
import { CONFLICT_TABS, toConflictTab } from "../lib/conflicts";
import { dispositionMeta } from "../lib/dispositions";
import { Panel } from "../components/Panel";
import { Cell, DataTable, Pager, type Column } from "../components/DataTable";
import { DispositionBadge } from "../components/DispositionBadge";
import { Async } from "../components/States";

const LIMIT = 40;

export function Conflicts() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const tab = toConflictTab(params.get("tab"));
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    setOffset(0);
  }, [tab]);

  const stats = useApi(() => getStats(), []);
  const page = useApi<ConflictsResponse>(() => getConflicts(tab, LIMIT, offset), [tab, offset]);
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
                className={`tab${tab === t.key ? " is-active" : ""}`}
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

        <Async state={page} loadingLabel="Loading conflicts">
          {(data) => (
            <>
              {tab === "disposition" ? (
                <DataTable<ConflictRow>
                  columns={DISPOSITION_COLS}
                  rows={data.rows}
                  rowKey={(r) => r.candidate_id}
                  onRowClick={open}
                />
              ) : (
                <DataTable<ConflictRow>
                  columns={numericCols(tab === "teff" ? "K" : "R⊕")}
                  rows={data.rows}
                  rowKey={(r) => r.candidate_id}
                  onRowClick={open}
                />
              )}
              <Pager offset={offset} limit={LIMIT} total={data.total} onOffset={setOffset} />
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
      {rows.map((b, i) => (
        <span className="bysrc__item" key={`${b.source}-${i}`}>
          <span className="bysrc__src">{b.source}</span>
          <span className="bysrc__v">
            {b.min === b.max ? fmtNum(b.min) : `${fmtNum(b.min)}–${fmtNum(b.max)}`}
            {b.n > 1 ? ` (${b.n})` : ""}
          </span>
        </span>
      ))}
    </div>
  );
}

const DISPOSITION_COLS: Column<ConflictRow>[] = [
  { key: "target", header: "Candidate", render: (r) => <span className="mono-hi">{r.target}</span> },
  { key: "host", header: "Host", render: (r) => r.host },
  {
    key: "resolved",
    header: "Resolved",
    render: (r) => <DispositionBadge disposition={typeof r.resolved === "string" ? r.resolved : null} />,
  },
  {
    key: "kind",
    header: "",
    render: (r) =>
      r.dramatic ? (
        <span className="badge badge--conflict">
          <span className="badge__glyph" aria-hidden="true" />
          FP vs confirmed
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
    { key: "target", header: "Candidate", render: (r) => <span className="mono-hi">{r.target}</span> },
    { key: "host", header: "Host", render: (r) => r.host },
    {
      key: "spread",
      header: "Spread",
      num: true,
      render: (r) => <span className="num" style={{ color: "var(--conflict)" }}>{r.spread_pct}%</span>,
    },
    {
      key: "range",
      header: `Range (${unit})`,
      num: true,
      render: (r) => (
        <span className="num">
          <Cell>{`${fmtNum(r.min)} – ${fmtNum(r.max)}`}</Cell>
        </span>
      ),
    },
    {
      key: "who",
      header: "By source",
      render: (r) => <BySourceRanges rows={(r.by_source as BySourceRange[]) ?? []} />,
    },
  ];
}
