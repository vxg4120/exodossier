import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { getConflicts, getStats, getStories } from "../api/client";
import type { ConflictRow, IngestRun, NewPlanet, PlanetRecord, Stats, Stories, VerdictWindow } from "../api/types";
import { useApi } from "../hooks/useApi";
import { DASH, fmtDate, fmtInt, fmtNum } from "../lib/format";
import { CONFLICT_TABS } from "../lib/conflicts";
import { runStatusMeta } from "../lib/dispositions";
import {
  awaitingVerdict,
  confirmedFromCandidates,
  dispatch,
  fmtDay,
  fmtDayShort,
  fmtMonth,
  MIX_ORDER,
  pct,
  plural,
  ruledOutFromCandidates,
  shortFacility,
  SIZE_HINT,
  SIZE_PLURAL,
  tfopwgMeta,
  toiTotal,
} from "../lib/stories";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { Async, Loading } from "../components/States";
import { DataTable, type Column } from "../components/DataTable";
import { TfopwgBadge } from "../components/DispositionBadge";
import { BarRows, MixBar, MonthBars, SnapshotSteps, type BarRow } from "../components/StoryCharts";

/** How many of the dramatic cases the panel lists (dramatic rows sort first in the corpus). */
const DRAMATIC_SHOWN = 3;
/** Verdict movements listed before "show all". */
const TRANSITIONS_SHOWN = 7;
/** Facilities named before the rest fold into one row. */
const FACILITIES_SHOWN = 5;

export function Overview() {
  const stories = useApi(() => getStories(), []);
  const stats = useApi(() => getStats(), []);
  const dramatic = useApi(() => getConflicts("disposition", DRAMATIC_SHOWN, 0), []);
  const s = stories.data;

  return (
    <div className="view fadein">
      <header className="vhead">
        <div className="story-head">
          <h1 className="vhead__title">What&rsquo;s new in exoplanets</h1>
          {s ? (
            <p className="story-dispatch">{dispatch(s).join(" ")}</p>
          ) : stories.error ? null : (
            <Loading label="Reading the latest snapshots" rows={2} />
          )}
          <p className="vhead__desc">
            ExoDossier stitches the NASA Exoplanet Archive and ExoFOP into one record per star and
            candidate, and shows where they disagree, with provenance for every value. It does not
            adjudicate or confirm.
          </p>
          {s?.as_of ? (
            <p className="hint">
              Figures as of {fmtDay(s.as_of, true)}, from the archive snapshots kept since{" "}
              {fmtDay(s.confirmed.baseline_date ?? s.as_of)}.
            </p>
          ) : null}
        </div>
      </header>

      <Async state={stories} loadingLabel="Loading the stories" loadingRows={8}>
        {(st) => <StoryPanels s={st} />}
      </Async>

      <Async state={stats} loadingLabel="Loading catalog telemetry" loadingRows={6}>
        {(cat) => (
          <>
            <div className="grid grid--2">
              <DisagreePanel s={cat} />
              <Panel
                title={`The dramatic ${fmtInt(cat.conflicts.disposition_dramatic)}`}
                meta="FALSE POSITIVE vs CONFIRMED"
                dataTour="dramatic"
              >
                <p className="story__headline">
                  {cat.conflicts.disposition_dramatic === 1
                    ? "One candidate is confirmed by one catalog and called a false positive by another."
                    : `${fmtInt(cat.conflicts.disposition_dramatic)} candidates are confirmed by one catalog and called false positives by another.`}
                </p>
                <Async state={dramatic} loadingLabel="Loading the dramatic cases" loadingRows={3}>
                  {(page) => (
                    <DramaticList rows={page.rows} total={cat.conflicts.disposition_dramatic} />
                  )}
                </Async>
                <p className="hint story__how">
                  This is the sharpest form of &ldquo;nobody agrees on a planet.&rdquo; Open one to
                  see who said what.
                </p>
              </Panel>
            </div>

            <section className="story-hood" aria-labelledby="under-the-hood">
              <h2 className="story-divider" id="under-the-hood">
                Under the hood
              </h2>
              <p className="hint">
                The identity graph behind the stories: how much it holds, and when each catalog was
                last pulled.
              </p>
            </section>

            <div className="grid grid--stats">
              <StatTile
                lead
                label="Candidates"
                value={cat.candidates}
                sub={
                  <>
                    host stars <span className="num">{fmtInt(cat.stars)}</span>
                  </>
                }
              />
              <StatTile
                label="Crosswalk identifiers"
                value={cat.identifiers}
                sub="TIC · TOI · CTOI · KOI · Gaia · HD · HIP"
              />
              <StatTile
                label="Source assertions"
                value={cat.source_assertions}
                sub="per-publication provenance"
              />
              <StatTile
                conflict
                label="Disposition conflicts"
                value={cat.conflicts.disposition}
                sub={
                  <>
                    incl. <span className="num">{cat.conflicts.disposition_dramatic}</span> FALSE
                    POSITIVE vs CONFIRMED
                  </>
                }
              />
            </div>

            <Panel title="Ingestion ledger" meta="last landed pull · latest check per endpoint" flush>
              <LedgerTable runs={cat.ingest_runs} />
            </Panel>
          </>
        )}
      </Async>
    </div>
  );
}

/* =============================================================================================
   The stories
   ============================================================================================= */
function StoryPanels({ s }: { s: Stories }) {
  const c = s.confirmed;
  const v = s.toi_verdicts;
  const hasConfirmedChange = c.series.length >= 2;
  const hasVerdicts = v.from_date !== null && v.from_date !== v.to_date;
  const base = c.baseline_date;
  const last = c.series[c.series.length - 1];

  return (
    <>
      <div className="grid grid--stats" data-tour="stats">
        <StatTile
          lead
          hero
          label="Confirmed planets"
          value={last ? last.count : 0}
          sub={
            hasConfirmedChange && base ? (
              <>
                on NASA&rsquo;s list, <span className="num">+{fmtInt(c.added_since_baseline)}</span>{" "}
                added since {fmtDayShort(base)}
              </>
            ) : (
              "on NASA's confirmed-planet list"
            )
          }
        />
        <StatTile
          label="Awaiting a verdict"
          value={awaitingVerdict(s)}
          sub="TESS candidates (PC or APC) on ExoFOP's list"
        />
        <StatTile
          label="Confirmed by follow-up"
          value={confirmedFromCandidates(v.transitions)}
          sub={
            hasVerdicts && v.from_date
              ? `TESS candidates moved to CP since ${fmtDayShort(v.from_date)}`
              : "no earlier snapshot to compare yet"
          }
        />
        <StatTile
          label="Ruled out"
          value={ruledOutFromCandidates(v.transitions)}
          sub={
            hasVerdicts && v.from_date
              ? `TESS candidates moved to FP or FA since ${fmtDayShort(v.from_date)}`
              : "no earlier snapshot to compare yet"
          }
        />
      </div>

      {hasConfirmedChange ? <ConfirmedPanel s={s} /> : null}
      {hasConfirmedChange && c.added_since_baseline > 0 ? (
        <div className="grid grid--2">
          <SizesPanel s={s} />
          <FacilitiesPanel s={s} />
        </div>
      ) : null}
      <div className="grid grid--2">
        {hasVerdicts ? <VerdictsPanel s={s} /> : null}
        {s.toi_mix.length > 0 ? <QueuePanel s={s} /> : null}
      </div>
    </>
  );
}

function Story({
  title,
  meta,
  headline,
  how,
  children,
}: {
  title: string;
  meta?: ReactNode;
  headline: ReactNode;
  how: ReactNode;
  children: ReactNode;
}) {
  return (
    <Panel title={title} meta={meta}>
      <div className="story">
        <p className="story__headline">{headline}</p>
        {children}
        <p className="hint story__how">{how}</p>
      </div>
    </Panel>
  );
}

const targetHref = (ident: string) => `/target/${encodeURIComponent(ident)}`;

/* ---- a. the confirmed list grew ---------------------------------------------------------- */
function ConfirmedPanel({ s }: { s: Stories }) {
  const c = s.confirmed;
  const first = c.series[0];
  const last = c.series[c.series.length - 1];
  const net = last.count - first.count;
  const headline =
    net === 0
      ? `NASA's confirmed list holds ${fmtInt(last.count)} planets, the same count as on ${fmtDay(first.date)}.`
      : `NASA's confirmed list ${net > 0 ? "grew" : "shrank"} by ${plural(Math.abs(net), "planet", "planets")} since ${fmtDay(first.date)}, to ${fmtInt(last.count)}.`;

  const columns: Column<NewPlanet>[] = [
    {
      key: "name",
      header: "Planet",
      render: (p) => (
        <Link to={targetHref(p.pl_name)} className="mono-hi">
          {p.pl_name}
        </Link>
      ),
    },
    {
      key: "facility",
      header: "Found by",
      render: (p) =>
        p.facility ? <span title={p.facility}>{shortFacility(p.facility)}</span> : <span className="dash">{DASH}</span>,
    },
    { key: "radius", header: "Radius (R⊕)", num: true, render: (p) => <span className="num">{fmtNum(p.radius_re)}</span> },
    { key: "period", header: "Period (d)", num: true, render: (p) => <span className="num">{fmtNum(p.period_days)}</span> },
    { key: "seen", header: "First seen", num: true, render: (p) => <span className="num">{fmtDayShort(p.first_seen)}</span> },
  ];

  return (
    <Story
      title="The confirmed list grew"
      meta={`${fmtDayShort(first.date)} to ${fmtDayShort(last.date)}`}
      headline={headline}
      how={
        <>
          Each point counts the planets in one retained snapshot of the archive&rsquo;s confirmed
          table: the first of each month, then the newest three days. Nothing is known between
          points, so the line steps. &ldquo;First seen&rdquo; is the first snapshot that lists a
          planet; arrivals inside one snapshot are in name order.
        </>
      }
    >
      <SnapshotSteps points={c.series} />
          {c.removed.length > 0 ? (
            <p className="hint">
              Left the list:{" "}
              {c.removed.map((r, i) => (
                <span key={r.pl_name}>
                  {i > 0 ? ", " : null}
                  <span className="mono-hi">{r.pl_name}</span> (last seen {fmtDayShort(r.last_seen)})
                </span>
              ))}
              . A name can leave when the archive renames a planet, so a departure is not always a
              retraction.
            </p>
          ) : null}
      <h3 className="story__subhead">Newest arrivals</h3>
      <DataTable columns={columns} rows={c.newest} rowKey={(p) => p.pl_name} />
    </Story>
  );
}

/* ---- b. what the new planets look like --------------------------------------------------- */
function SizesPanel({ s }: { s: Stories }) {
  const c = s.confirmed;
  const total = c.added_since_baseline;
  const ranked = [...c.sizes].filter((b) => b.count > 0).sort((a, b) => b.count - a.count);
  const [top1, top2] = ranked;
  const earth = c.sizes.find((b) => b.bin === "Earth-size");
  let headline = `Of the ${fmtInt(total)} new planets, ${fmtInt(top1.count)} ${SIZE_PLURAL[top1.bin] ?? top1.bin}`;
  if (top2) headline += ` and ${fmtInt(top2.count)} ${SIZE_PLURAL[top2.bin] ?? top2.bin}`;
  if (earth && earth.count > 0 && earth !== top1 && earth !== top2) {
    headline += `; ${earth.count === 1 ? "one is" : `${fmtInt(earth.count)} are`} Earth-size`;
  }
  headline += ".";

  // the unknown-radius bin is listed only when some new planet has no radius
  const bins = c.sizes.filter((b) => b.bin !== "Unknown radius" || b.count > 0);
  const rows: BarRow[] = bins.map((b) => ({
    key: b.bin,
    label: (
      <>
        {b.bin} <span className="muted">{SIZE_HINT[b.bin]}</span>
      </>
    ),
    value: b.count,
    note: pct(b.count, total),
    title: `${b.bin}: ${fmtInt(b.count)} of ${fmtInt(total)} new planets`,
  }));
  const r = c.records;

  return (
    <Story
      title="What the new planets look like"
      meta={`${fmtInt(total)} new since ${fmtDayShort(c.baseline_date ?? "")}`}
      headline={headline}
      how={
        <>
          Planets on the {fmtDay(c.series[c.series.length - 1].date)} list that were not on the{" "}
          {fmtDay(c.baseline_date)} list, binned by radius in Earth radii. Records skip planets
          with no measured radius or period.
        </>
      }
    >
      <BarRows rows={rows} />
      <div className="story-records">
        {r.smallest ? (
          <RecordTile label="Smallest" value={fmtNum(r.smallest.value)} unit="Earth radii" rec={r.smallest}>
            {r.smallest.value < 1
              ? "slightly smaller than Earth"
              : r.smallest.value === 1
                ? "the same size as Earth"
                : `${fmtNum(r.smallest.value)} times as wide as Earth`}
          </RecordTile>
        ) : null}
        {r.shortest_period ? <YearRecord label="Shortest year" rec={r.shortest_period} /> : null}
        {r.longest_period ? <YearRecord label="Longest year" rec={r.longest_period} /> : null}
      </div>
    </Story>
  );
}

function YearRecord({ label, rec }: { label: string; rec: PlanetRecord }) {
  const d = rec.value;
  const [value, unit] =
    d < 1
      ? [(d * 24).toFixed(1), "hours"]
      : d < 730
        ? [d >= 100 ? d.toFixed(1) : d.toFixed(2), "days"]
        : [(d / 365.25).toFixed(1), "Earth years"];
  return (
    <RecordTile label={label} value={value} unit={unit} rec={rec}>
      one orbit of its star takes {fmtNum(d, 4)} days
    </RecordTile>
  );
}

function RecordTile({
  label,
  value,
  unit,
  rec,
  children,
}: {
  label: string;
  value: string;
  unit: string;
  rec: PlanetRecord;
  children: ReactNode;
}) {
  return (
    <div className="story-record">
      <span className="stat__label">{label}</span>
      <span className="story-record__value num">
        {value} <span className="story-record__unit">{unit}</span>
      </span>
      <span className="story-record__line">
        <Link to={targetHref(rec.pl_name)}>{rec.pl_name}</Link>, {children}
      </span>
    </div>
  );
}

/* ---- c. who found them ------------------------------------------------------------------- */
function FacilitiesPanel({ s }: { s: Stories }) {
  const c = s.confirmed;
  const total = c.added_since_baseline;
  const named = c.facilities.slice(0, FACILITIES_SHOWN);
  const rest = c.facilities.slice(FACILITIES_SHOWN);
  const restCount = rest.reduce((n, f) => n + f.count, 0);
  const top = c.facilities[0];
  const rows: BarRow[] = named.map((f) => ({
    key: f.facility,
    label: <span title={f.facility}>{shortFacility(f.facility)}</span>,
    value: f.count,
    note: pct(f.count, total),
    title: `${f.facility}: ${fmtInt(f.count)} of ${fmtInt(total)} new planets`,
  }));
  if (restCount > 0) {
    rows.push({
      key: "other",
      label: <span className="muted">{plural(rest.length, "other facility", "other facilities")}</span>,
      value: restCount,
      note: pct(restCount, total),
      title: rest.map((f) => `${f.facility}: ${f.count}`).join("\n"),
      fill: "is-muted",
    });
  }
  return (
    <Story
      title="Who found them"
      meta="discovery facility"
      headline={
        top
          ? `${shortFacility(top.facility)} found ${fmtInt(top.count)} of the ${fmtInt(total)} new planets (${pct(top.count, total)}).`
          : "No facility is recorded for the new planets."
      }
      how={
        <>
          The discovery facility the NASA Exoplanet Archive records for each of the same{" "}
          {fmtInt(total)} planets. &ldquo;Multiple&rdquo; entries are the archive&rsquo;s own
          labels.
        </>
      }
    >
      <BarRows rows={rows} />
    </Story>
  );
}

/* ---- d. verdicts on TESS candidates ------------------------------------------------------ */
function VerdictsPanel({ s }: { s: Stories }) {
  const windows: { key: string; label: string; w: VerdictWindow }[] = [
    { key: "base", label: `Since ${fmtDayShort(s.toi_verdicts.from_date ?? "")}`, w: s.toi_verdicts },
  ];
  if (s.toi_verdicts_month.from_date && s.toi_verdicts_month.from_date !== s.toi_verdicts.from_date) {
    windows.push({
      key: "month",
      label: `Since ${fmtDayShort(s.toi_verdicts_month.from_date)}`,
      w: s.toi_verdicts_month,
    });
  }
  const [active, setActive] = useState(windows[0].key);
  const [showAll, setShowAll] = useState(false);
  const cur = (windows.find((x) => x.key === active) ?? windows[0]).w;
  const conf = confirmedFromCandidates(cur.transitions);
  const out = ruledOutFromCandidates(cur.transitions);
  const shown = showAll ? cur.transitions : cur.transitions.slice(0, TRANSITIONS_SHOWN);
  const demoted = s.toi_verdicts.demoted;

  const rows: BarRow[] = shown.map((t) => ({
    key: `${t.from}>${t.to}`,
    label: (
      <span className="story-move" aria-label={`${tfopwgMeta(t.from).label} to ${tfopwgMeta(t.to).label}`}>
        <TfopwgBadge code={t.from} />
        <span className="story-move__arrow" aria-hidden="true">
          →
        </span>
        <TfopwgBadge code={t.to} />
      </span>
    ),
    value: t.count,
    fill: tfopwgMeta(t.to).fill,
    title: `${tfopwgMeta(t.from).title} to ${tfopwgMeta(t.to).title}: ${fmtInt(t.count)} TOIs`,
  }));
  const max = Math.max(...cur.transitions.map((t) => t.count), 1);

  return (
    <Story
      title="Verdicts on TESS candidates"
      meta="TFOPWG dispositions"
      headline={
        cur.transitions.length === 0
          ? `No TOI changed its disposition between ${fmtDay(cur.from_date)} and ${fmtDay(cur.to_date)}.`
          : `Since ${fmtDay(cur.from_date)}, ${plural(conf, "TESS candidate was", "TESS candidates were")} confirmed and ${fmtInt(out)} ${out === 1 ? "was" : "were"} ruled out.`
      }
      how={
        <>
          The TESS Follow-up Observing Program working group&rsquo;s disposition for each TOI on
          ExoFOP&rsquo;s list, compared TOI by TOI between the {fmtDay(cur.from_date)} and{" "}
          {fmtDay(cur.to_date)} snapshots. TOIs whose disposition did not change are left out.
        </>
      }
    >
      {windows.length > 1 ? (
        <div className="tabs story-tabs" role="group" aria-label="Comparison window">
          {windows.map((x) => (
            <button
              key={x.key}
              type="button"
              className={`tab${x.key === active ? " is-active" : ""}`}
              aria-pressed={x.key === active}
              onClick={() => {
                setActive(x.key);
                setShowAll(false);
              }}
            >
              {x.label}
            </button>
          ))}
        </div>
      ) : null}
      {rows.length > 0 ? <BarRows rows={rows} max={max} stacked /> : null}
      {cur.transitions.length > TRANSITIONS_SHOWN ? (
        <button type="button" className="btn story-more" onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Show the largest movements" : `Show all ${fmtInt(cur.transitions.length)} movements`}
        </button>
      ) : null}
      {demoted.length > 0 ? (
        <div className="story-demoted">
          <h3 className="story__subhead">
            Confirmed, then ruled out, since {fmtDay(s.toi_verdicts.from_date)}
          </h3>
          <ul className="story-demoted__list">
            {demoted.map((d) => (
              <li key={d.toi}>
                <Link to={targetHref(d.toi)} className="mono-hi">
                  TOI-{d.toi}
                </Link>
                <span className="story-move" aria-label={`${tfopwgMeta(d.from).label} to ${tfopwgMeta(d.to).label}`}>
                  <TfopwgBadge code={d.from} />
                  <span className="story-move__arrow" aria-hidden="true">
                    →
                  </span>
                  <TfopwgBadge code={d.to} />
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </Story>
  );
}

/* ---- e. the TESS candidate queue --------------------------------------------------------- */
function QueuePanel({ s }: { s: Stories }) {
  const waiting = awaitingVerdict(s);
  const total = toiTotal(s);
  const months = s.toi_alerts_monthly;
  const partial = months.find((m) => m.partial);
  return (
    <Story
      title="The TESS candidate queue"
      meta={`${fmtInt(total)} TOIs on ExoFOP`}
      headline={`${plural(waiting, "TESS candidate is", "TESS candidates are")} still waiting for a verdict, ${pct(waiting, total)} of the TOI list.`}
      how={
        <>
          Dispositions in the {fmtDay(s.as_of)} snapshot of ExoFOP&rsquo;s TOI list. Alerts are
          counted by each TOI&rsquo;s alert date on that list; months with no alerts show 0
          {partial ? `, and ${fmtMonth(partial.month)} is still in progress` : ""}.
        </>
      }
    >
      <MixBar mix={s.toi_mix} order={MIX_ORDER} />
      <h3 className="story__subhead">New TOIs alerted per month</h3>
      <MonthBars months={months} />
    </Story>
  );
}

/* ---- f. where the archives disagree ------------------------------------------------------ */
function DisagreePanel({ s }: { s: Stats }) {
  const k = s.conflicts;
  return (
    <Panel title="Where the archives disagree" meta="disagreements are data">
      <p className="story__headline">
        The catalogs disagree on {plural(k.disposition, "candidate's disposition", "candidates' dispositions")},{" "}
        {plural(k.radius, "planet radius", "planet radii")} and{" "}
        {plural(k.teff, "host star temperature", "host star temperatures")}.
      </p>
      <div className="conflict-list">
        {CONFLICT_TABS.map((c) => (
          <Link key={c.key} to={`/conflicts?tab=${c.key}`} className="conflict-row">
            <span className="conflict-row__count num">{fmtInt(s.conflicts[c.statsKey])}</span>
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
      <p className="hint story__how">
        Counted live from the identity graph. Each row opens that part of the conflict corpus.
      </p>
    </Panel>
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
