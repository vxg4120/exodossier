import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { ConfirmedPoint, TfopwgCode } from "../api/types";
import { fmtInt } from "../lib/format";
import { fmtDay, fmtDayShort, fmtMonth, pct, tfopwgMeta } from "../lib/stories";
import { TfopwgBadge } from "./DispositionBadge";

/* Hand-rolled story visuals in the CongestionHeatmap manner: plain SVG and CSS, no chart
   library. The SVGs render at their container's measured pixel width rather than scaling a
   viewBox, so type stays at its token size on a phone instead of shrinking with the plot. */

/** Width of the element, tracked with a ResizeObserver; `fallback` until the first measure. */
function useWidth<T extends HTMLElement>(fallback: number) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth || fallback);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry.contentRect.width);
      if (w > 0) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [fallback]);
  return [ref, width] as const;
}

/** 1, 2 or 5 times a power of ten: the step for roughly `n` ticks across `span`. */
function niceStep(span: number, n: number): number {
  const raw = Math.max(span / n, 1);
  const pow = 10 ** Math.floor(Math.log10(raw));
  const f = raw / pow;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * pow;
}

const dayNumber = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / 86_400_000;

/** Pick which of the x positions get a text label: both ends always, then any point between
    that sits at least `gap` px from the last label kept and from the final one. */
function spacedLabels(xs: number[], gap: number): Set<number> {
  const n = xs.length;
  const keep = new Set<number>([0, n - 1]);
  let prev = xs[0];
  for (let i = 1; i < n - 1; i++) {
    if (xs[i] - prev >= gap && xs[n - 1] - xs[i] >= gap) {
      keep.add(i);
      prev = xs[i];
    }
  }
  return keep;
}

/* ---- the confirmed count across snapshots ------------------------------------------------ */
/** Steps with points, not a smooth line: the snapshots are monthly and then daily, so nothing
    is known between two points except that the count moved by the next one. The x axis is true
    time, so the uneven spacing between snapshots shows. The y axis does not start at zero (the
    change is a few percent of the total), which is why it is a line and not a filled area. */
export function SnapshotSteps({ points }: { points: ConfirmedPoint[] }) {
  const [ref, width] = useWidth<HTMLDivElement>(560);
  if (points.length === 0) return null;
  const W = Math.max(width, 260);
  const H = 220;
  const m = { l: 50, r: 18, t: 28, b: 30 };
  const plotW = W - m.l - m.r;
  const plotH = H - m.t - m.b;

  const d0 = dayNumber(points[0].date);
  const d1 = dayNumber(points[points.length - 1].date);
  const x = (iso: string) => m.l + (d1 === d0 ? plotW / 2 : ((dayNumber(iso) - d0) / (d1 - d0)) * plotW);

  const counts = points.map((p) => p.count);
  const lo0 = Math.min(...counts);
  const hi0 = Math.max(...counts);
  const step = niceStep(Math.max(hi0 - lo0, 10), 3);
  // a step of headroom whenever an extreme sits within half a step of a gridline, so the end
  // labels never crowd an axis label
  const loTick = Math.floor(lo0 / step) * step;
  const hiTick = Math.ceil(hi0 / step) * step;
  const lo = lo0 - loTick < step / 2 ? loTick - step : loTick;
  const hi = hiTick - hi0 < step / 2 ? hiTick + step : hiTick;
  const y = (n: number) => m.t + plotH - ((n - lo) / (hi - lo)) * plotH;
  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += step) ticks.push(t);

  const xs = points.map((p) => x(p.date));
  const dated = spacedLabels(xs, 58);
  let path = `M${xs[0]},${y(points[0].count)}`;
  for (let i = 1; i < points.length; i++) path += ` H${xs[i]} V${y(points[i].count)}`;

  const first = points[0];
  const last = points[points.length - 1];
  const summary =
    `Confirmed planets in each retained snapshot, from ${fmtInt(first.count)} on ` +
    `${fmtDay(first.date)} to ${fmtInt(last.count)} on ${fmtDay(last.date)}.`;

  return (
    <div className="story-plot" ref={ref}>
      <svg className="story-svg" width={W} height={H} role="img" aria-label={summary}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="story-grid" x1={m.l} x2={W - m.r} y1={y(t)} y2={y(t)} />
            <text className="story-axis" x={m.l - 8} y={y(t) + 3} textAnchor="end">
              {fmtInt(t)}
            </text>
          </g>
        ))}
        <path className="story-step" d={path} />
        {points.map((p, i) => (
          <g key={p.date}>
            {dated.has(i) ? (
              <text className="story-axis" x={xs[i]} y={H - 10} textAnchor={i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"}>
                {fmtDayShort(p.date)}
              </text>
            ) : null}
            <circle className="story-point" cx={xs[i]} cy={y(p.count)} r={4} />
          </g>
        ))}
        {/* the first value sits under its point: the line leaves it rightwards and upwards */}
        <text className="story-value" x={xs[0]} y={y(first.count) + 18} textAnchor="start">
          {fmtInt(first.count)}
        </text>
        <text className="story-value is-strong" x={xs[xs.length - 1]} y={y(last.count) - 10} textAnchor="end">
          {fmtInt(last.count)}
        </text>
        {/* hover targets wider than the marks, each with its own tooltip */}
        {points.map((p, i) => {
          const left = i === 0 ? m.l - 12 : (xs[i - 1] + xs[i]) / 2;
          const right = i === points.length - 1 ? W - m.r + 12 : (xs[i] + xs[i + 1]) / 2;
          const moved =
            p.added === null
              ? "the first retained snapshot"
              : `${fmtInt(p.added)} added and ${fmtInt(p.removed ?? 0)} removed since the snapshot before`;
          return (
            <rect key={p.date} className="story-hit" x={left} y={m.t - 16} width={Math.max(right - left, 1)} height={plotH + 32}>
              <title>{`${fmtDay(p.date, true)}: ${fmtInt(p.count)} confirmed planets, ${moved}`}</title>
            </rect>
          );
        })}
      </svg>
    </div>
  );
}

/* ---- TOI alerts per month ---------------------------------------------------------------- */
export function MonthBars({ months }: { months: { month: string; count: number; partial: boolean }[] }) {
  const [ref, width] = useWidth<HTMLDivElement>(520);
  if (months.length === 0) return null;
  const W = Math.max(width, 260);
  const H = 168;
  const m = { l: 2, r: 2, t: 20, b: 34 };
  const plotW = W - m.l - m.r;
  const plotH = H - m.t - m.b;
  const band = plotW / months.length;
  const barW = Math.max(Math.min(band * 0.64, 34), 5);
  const max = Math.max(...months.map((d) => d.count), 1);
  const peak = months.findIndex((d) => d.count === max);
  const roomy = band >= 24;
  const everyMonth = band >= 30;
  const base = m.t + plotH;
  const labelled = (i: number) => everyMonth || (months.length - 1 - i) % 3 === 0;
  const firstLabelled = months.findIndex((_, i) => labelled(i));

  const summary =
    `TOIs alerted per month for ${months.length} months, ${fmtMonth(months[0].month)} to ` +
    `${fmtMonth(months[months.length - 1].month)}. The busiest month was ` +
    `${fmtMonth(months[peak].month)} with ${fmtInt(max)}.`;

  return (
    <div className="story-plot" ref={ref}>
      <svg className="story-svg" width={W} height={H} role="img" aria-label={summary}>
        <line className="story-baseline" x1={m.l} x2={W - m.r} y1={base} y2={base} />
        {months.map((d, i) => {
          const cx = m.l + band * i + band / 2;
          const h = (d.count / max) * plotH;
          const r = Math.min(3, barW / 2, h);
          const x0 = cx - barW / 2;
          const bar =
            h > 0
              ? `M${x0},${base} V${base - h + r} Q${x0},${base - h} ${x0 + r},${base - h} ` +
                `H${x0 + barW - r} Q${x0 + barW},${base - h} ${x0 + barW},${base - h + r} V${base} Z`
              : null;
          const showValue = roomy || i === peak || i === months.length - 1 || d.count === 0;
          const showMonth = labelled(i);
          // the year rides under the first labelled month and under each labelled January
          const showYear = showMonth && (i === firstLabelled || d.month.endsWith("-01"));
          return (
            <g key={d.month}>
              {bar ? <path className={`story-bar${d.partial ? " is-partial" : ""}`} d={bar} /> : null}
              {showValue ? (
                <text className={`story-value${d.count === 0 ? " is-zero" : ""}`} x={cx} y={base - h - 6} textAnchor="middle">
                  {fmtInt(d.count)}
                </text>
              ) : null}
              {showMonth ? (
                <text className="story-axis" x={cx} y={base + 14} textAnchor="middle">
                  {fmtMonth(d.month, true)}
                </text>
              ) : null}
              {showYear ? (
                <text className="story-axis is-year" x={cx} y={base + 27} textAnchor="middle">
                  {d.month.slice(0, 4)}
                </text>
              ) : null}
              <rect className="story-hit" x={m.l + band * i} y={m.t - 14} width={band} height={plotH + 28}>
                <title>
                  {`${fmtMonth(d.month)}: ${fmtInt(d.count)} ${d.count === 1 ? "TOI" : "TOIs"} alerted${
                    d.partial ? " so far (month in progress)" : ""
                  }`}
                </title>
              </rect>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/* ---- labelled bar rows (CSS) ------------------------------------------------------------- */
export interface BarRow {
  key: string;
  label: ReactNode;
  value: number;
  /** tooltip on the row */
  title?: string;
  /** secondary text after the value, e.g. a share */
  note?: string;
  fill?: string;
}

/** `stacked` puts each label on its own line above its bar, for labels too wide to share a row. */
export function BarRows({ rows, max, stacked }: { rows: BarRow[]; max?: number; stacked?: boolean }) {
  const top = max ?? Math.max(...rows.map((r) => r.value), 1);
  return (
    <ul className={`story-bars${stacked ? " story-bars--stacked" : ""}`}>
      {rows.map((r) => (
        <li key={r.key} className="story-bars__row" title={r.title}>
          <span className="story-bars__label">{r.label}</span>
          <span className="story-bars__track" aria-hidden="true">
            {r.value > 0 ? (
              <span className={`story-bars__fill ${r.fill ?? ""}`} style={{ width: `${(100 * r.value) / top}%` }} />
            ) : null}
          </span>
          <span className="story-bars__value num">
            {fmtInt(r.value)}
            {r.note ? <span className="story-bars__note"> {r.note}</span> : null}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ---- the TFOPWG mix as one stacked bar, directly labelled -------------------------------- */
/** The disposition hues are close for some color-vision types, so the bar never carries
    identity alone: every segment is labelled below with its glyph badge, count and share, the
    segments are separated by gaps, and false alarms are striped to tell them from false
    positives (they share the false-positive hue). */
export function MixBar({ mix, order }: { mix: { disposition: TfopwgCode; count: number }[]; order: TfopwgCode[] }) {
  const total = mix.reduce((n, m) => n + m.count, 0);
  const rank = (c: TfopwgCode) => {
    const i = order.indexOf(c);
    return i < 0 ? order.length : i;
  };
  const rows = [...mix].filter((m) => m.count > 0).sort((a, b) => rank(a.disposition) - rank(b.disposition));
  const summary =
    `TFOPWG dispositions of ${fmtInt(total)} TOIs: ` +
    rows.map((r) => `${tfopwgMeta(r.disposition).label} ${fmtInt(r.count)}`).join(", ") + ".";
  return (
    <div className="story-mix">
      <div className="story-mix__bar" role="img" aria-label={summary}>
        {rows.map((r) => {
          const meta = tfopwgMeta(r.disposition);
          return (
            <span
              key={r.disposition ?? "none"}
              className={`story-mix__seg ${meta.fill}`}
              style={{ flexGrow: r.count }}
              title={`${meta.title}: ${fmtInt(r.count)} (${pct(r.count, total)})`}
            />
          );
        })}
      </div>
      <ul className="story-mix__key">
        {rows.map((r) => (
          <li key={r.disposition ?? "none"} className="story-mix__item">
            <TfopwgBadge code={r.disposition} />
            <span className="num mono-hi">{fmtInt(r.count)}</span>
            <span className="num muted">{pct(r.count, total)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
