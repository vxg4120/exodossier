import type { ReactNode } from "react";

interface StatTileProps {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  lead?: boolean;
  hero?: boolean;
  conflict?: boolean;
}

/** Stat tile: micro label, large tabular value, optional context line. */
export function StatTile({ label, value, sub, lead, hero, conflict }: StatTileProps) {
  return (
    <div className={`stat${lead ? " stat--lead" : ""}${conflict ? " stat--conflict" : ""}`}>
      <span className="stat__label">{label}</span>
      <span className={`stat__value num${hero ? " is-hero" : ""}${conflict ? " is-conflict" : ""}`}>
        {value}
      </span>
      {sub !== undefined ? <span className="stat__sub">{sub}</span> : null}
    </div>
  );
}
