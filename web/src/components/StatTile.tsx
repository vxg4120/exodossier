import type { ReactNode } from "react";
import { compact, fmtInt } from "../lib/format";

interface StatTileProps {
  label: string;
  /** A raw count renders compacted ("71.1K") with the exact figure in its title; anything else
      renders as given. */
  value: number | ReactNode;
  sub?: ReactNode;
  lead?: boolean;
  hero?: boolean;
  conflict?: boolean;
}

/** Stat tile: micro label, large tabular value, optional context line. */
export function StatTile({ label, value, sub, lead, hero, conflict }: StatTileProps) {
  const isCount = typeof value === "number";
  return (
    <div className={`stat${lead ? " stat--lead" : ""}${conflict ? " stat--conflict" : ""}`}>
      <span className="stat__label">{label}</span>
      <span
        className={`stat__value num${hero ? " is-hero" : ""}${conflict ? " is-conflict" : ""}`}
        title={isCount ? fmtInt(value) : undefined}
      >
        {isCount ? compact(value) : value}
      </span>
      {sub !== undefined ? <span className="stat__sub">{sub}</span> : null}
    </div>
  );
}
