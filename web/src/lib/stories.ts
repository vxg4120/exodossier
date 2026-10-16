/* The landing's stories: the API returns facts (counts, dates, names) and this module phrases
   them, so copy changes never need an API deploy. Every number in a sentence comes from the
   payload; nothing here invents or rounds a count. */

import type { Stories, TfopwgCode, VerdictTransition } from "../api/types";
import { dispositionMeta, type DispositionMeta } from "./dispositions";
import { fmtInt } from "./format";

/* ---- TFOPWG vocabulary ------------------------------------------------------------------ */
// The codes map to the canonical scale exactly as disposition_mapping does for exofop_toi, so a
// TOI badge wears the same glyph and color as everywhere else in the catalog.
const TFOPWG: Record<string, { canonical: string; label: string; title: string }> = {
  PC: { canonical: "CANDIDATE", label: "Candidate", title: "PC: planet candidate" },
  APC: { canonical: "AMBIGUOUS", label: "Ambiguous", title: "APC: ambiguous planet candidate" },
  CP: { canonical: "CONFIRMED", label: "Confirmed", title: "CP: confirmed planet" },
  KP: { canonical: "KNOWN_PLANET", label: "Known planet", title: "KP: known planet (pre-TESS)" },
  FP: { canonical: "FALSE_POSITIVE", label: "False positive", title: "FP: false positive" },
  FA: { canonical: "FALSE_POSITIVE", label: "False alarm", title: "FA: false alarm" },
};

export const NEW = "NEW";
export const DROPPED = "DROPPED";
export const CANDIDATE_CODES = ["PC", "APC"];
export const RULED_OUT_CODES = ["FP", "FA"];

export interface TfopwgMeta extends DispositionMeta {
  title: string;
  /** CSS class for a filled mark (bar segment) in the disposition hue */
  fill: string;
}

export function tfopwgMeta(code: TfopwgCode): TfopwgMeta {
  if (code === NEW) {
    return { className: "disp-unknown", label: "New TOI", title: "Not on the earlier list", fill: "fill-unknown" };
  }
  if (code === DROPPED) {
    return { className: "disp-unknown", label: "Dropped", title: "Not on the later list", fill: "fill-unknown" };
  }
  if (code === null || code === "") {
    return { className: "disp-unknown", label: "No verdict yet", title: "No TFOPWG disposition", fill: "fill-unknown" };
  }
  const t = TFOPWG[code.toUpperCase()];
  if (!t) return { ...dispositionMeta(code), title: code, fill: "fill-unknown" };
  const meta = dispositionMeta(t.canonical);
  // FA shares the false-positive hue; a stripe tells the two apart in a filled mark
  const fill = meta.className.replace("disp-", "fill-") + (code.toUpperCase() === "FA" ? " is-striped" : "");
  return { className: meta.className, label: t.label, title: t.title, fill };
}

/** The order the queue reads in: settled planets, then the waiting room, then the ruled out. */
export const MIX_ORDER: TfopwgCode[] = ["CP", "KP", "PC", "APC", "FP", "FA", null];

/* ---- dates ------------------------------------------------------------------------------- */
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

/** "2026-07-15" -> "July 15" (or "July 15, 2026"). Parsed by hand: no timezone can shift it. */
export function fmtDay(iso: string | null | undefined, withYear = false): string {
  if (!iso) return "the first snapshot";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const day = `${MONTHS[m - 1]}\u00a0${d}`; // "October 1" never breaks across a line
  return withYear ? `${day}, ${y}` : day;
}

/** "2026-07-15" -> "Jul 15" for tight labels. */
export function fmtDayShort(iso: string): string {
  const [, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[m - 1].slice(0, 3)}\u00a0${d}`;
}

/** "2026-06" -> "June 2026" / "Jun". */
export function fmtMonth(ym: string, short = false): string {
  const [y, m] = ym.split("-").map(Number);
  return short ? MONTHS[m - 1].slice(0, 3) : `${MONTHS[m - 1]} ${y}`;
}

/* ---- counting ---------------------------------------------------------------------------- */
export function sumWhere(
  transitions: VerdictTransition[],
  from: (c: TfopwgCode) => boolean,
  to: (c: TfopwgCode) => boolean,
): number {
  return transitions.reduce((n, t) => (from(t.from) && to(t.to) ? n + t.count : n), 0);
}

const isCandidate = (c: TfopwgCode) => c !== null && CANDIDATE_CODES.includes(c);
const isRuledOut = (c: TfopwgCode) => c !== null && RULED_OUT_CODES.includes(c);

/** Candidates (PC or APC) the follow-up working group moved to CP. */
export function confirmedFromCandidates(transitions: VerdictTransition[]): number {
  return sumWhere(transitions, isCandidate, (c) => c === "CP");
}

/** Candidates (PC or APC) the follow-up working group moved to FP or FA. */
export function ruledOutFromCandidates(transitions: VerdictTransition[]): number {
  return sumWhere(transitions, isCandidate, isRuledOut);
}

export function awaitingVerdict(s: Stories): number {
  return s.toi_mix.reduce((n, m) => (isCandidate(m.disposition) ? n + m.count : n), 0);
}

export function toiTotal(s: Stories): number {
  return s.toi_mix.reduce((n, m) => n + m.count, 0);
}

export function pct(part: number, whole: number): string {
  if (whole <= 0) return "0%";
  const p = (100 * part) / whole;
  if (p > 0 && p < 0.1) return "<0.1%";
  return `${p < 1 && p > 0 ? p.toFixed(1) : Math.round(p)}%`;
}

export function plural(n: number, one: string, many: string): string {
  return `${fmtInt(n)} ${n === 1 ? one : many}`;
}

/** "Transiting Exoplanet Survey Satellite (TESS)" -> "TESS"; the full name stays in a title. */
export function shortFacility(name: string): string {
  const m = /\(([A-Za-z0-9 .-]+)\)\s*$/.exec(name);
  return m ? m[1] : name;
}

/* ---- the dispatch ------------------------------------------------------------------------ */
/** Two plain sentences: how the confirmed list moved, and what TESS follow-up decided. Each
    clause appears only when its numbers exist; the queue size lives in the stat tiles. */
export function dispatch(s: Stories): string[] {
  const c = s.confirmed;
  const out: string[] = [];
  if (c.series.length >= 2) {
    const first = c.series[0];
    const last = c.series[c.series.length - 1];
    const net = last.count - first.count;
    let lead =
      net >= 0
        ? `NASA's list of confirmed exoplanets has grown by ${plural(net, "planet", "planets")} since ${fmtDay(first.date)}, to ${fmtInt(last.count)}`
        : `NASA's list of confirmed exoplanets has shrunk by ${plural(-net, "planet", "planets")} since ${fmtDay(first.date)}, to ${fmtInt(last.count)}`;
    if (c.month_baseline_date && c.added_since_month > 0) {
      lead += `, and ${plural(c.added_since_month, "new planet", "new planets")} arrived after ${fmtDay(c.month_baseline_date)}`;
    }
    out.push(lead + ".");
  }
  const v = s.toi_verdicts;
  if (v.transitions.length > 0) {
    const conf = confirmedFromCandidates(v.transitions);
    const out_ = ruledOutFromCandidates(v.transitions);
    const demoted = v.demoted.length;
    // "In the same span" only when the TOI window starts where the confirmed series does
    const sameSpan = c.series.length >= 2 && c.series[0].date === v.from_date;
    const since = sameSpan ? "In the same span" : `Since ${fmtDay(v.from_date)}`;
    const clauses: string[] = [];
    if (conf > 0 || out_ > 0) {
      clauses.push(
        `TESS follow-up confirmed ${plural(conf, "candidate", "candidates")} and ruled out ${fmtInt(out_)}`,
      );
    }
    if (demoted > 0) {
      clauses.push(
        `${plural(demoted, "planet", "planets")} that had been marked ${demotedFrom(v.demoted)} turned out to be ${demotedTo(v.demoted)}`,
      );
    }
    if (clauses.length > 0) out.push(`${since}, ${clauses.join(", and ")}.`);
  }
  return out;
}

/** What the demoted TOIs had been: "confirmed" when every one was CP, "confirmed or known" when
    any was KP (a known planet from before TESS). */
export function demotedFrom(demoted: { from: string }[]): string {
  return demoted.some((d) => d.from === "KP") ? "confirmed or known" : "confirmed";
}

/** What they became: false positives, false alarms, or both. */
export function demotedTo(demoted: { to: string }[]): string {
  const one = demoted.length === 1;
  if (demoted.every((d) => d.to === "FP")) return one ? "a false positive" : "false positives";
  if (demoted.every((d) => d.to === "FA")) return one ? "a false alarm" : "false alarms";
  return "false positives or false alarms";
}

/* ---- planet comparisons ------------------------------------------------------------------ */
/** A year (one orbit) in plain units, computed from the period exactly as given. */
export function yearLength(periodDays: number): string {
  if (periodDays < 1) return `${(periodDays * 24).toFixed(1)} hours`;
  if (periodDays < 730) return `${fmtNum1(periodDays)} days`;
  return `${fmtInt(Math.round(periodDays))} days, about ${(periodDays / 365.25).toFixed(1)} Earth years`;
}

function fmtNum1(n: number): string {
  return n >= 100 ? n.toFixed(1) : n.toFixed(2);
}

export const SIZE_PLURAL: Record<string, string> = {
  "Earth-size": "are Earth-size",
  "Super-Earth": "are super-Earths",
  "Sub-Neptune": "are sub-Neptunes",
  "Neptune-size": "are Neptune-size",
  Giant: "are giants",
  "Unknown radius": "have no radius yet",
};

export const SIZE_HINT: Record<string, string> = {
  "Earth-size": "under 1.25",
  "Super-Earth": "1.25 to 2",
  "Sub-Neptune": "2 to 4",
  "Neptune-size": "4 to 6",
  Giant: "6 and up",
  "Unknown radius": "",
};
