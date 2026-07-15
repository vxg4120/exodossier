import type { Assertion, AttributeGroup } from "../api/types";
import { fmtNum, fmtValue } from "../lib/format";
import { dispositionMeta } from "../lib/dispositions";
import { SourceBadge } from "./SourceBadge";

/* The who-says-what table: one row per attribute, every source's claim side by side, with the
   cells that disagree across sources highlighted (the visual payoff). Per-source claims are
   collapsed to a summary — a value or a min–max range with a publication count — so a Teff row
   backed by 30+ ps publications still reads at a glance while keeping full provenance one row away
   (the ps citation is shown when a source carries one). */

interface SourceClaim {
  source: string;
  numericMin: number | null;
  numericMax: number | null;
  count: number;
  dispositions: string[];
  ref: string | null;
}

function summarize(assertions: Assertion[]): SourceClaim[] {
  const bySource = new Map<string, Assertion[]>();
  for (const a of assertions) {
    const arr = bySource.get(a.source) ?? [];
    arr.push(a);
    bySource.set(a.source, arr);
  }
  return Array.from(bySource.entries()).map(([source, items]) => {
    const nums = items
      .map((i) => Number(i.value))
      .filter((n) => Number.isFinite(n));
    const dispositions = Array.from(
      new Set(items.map((i) => i.canonical_disposition).filter((d): d is string => Boolean(d))),
    );
    const ref = items.find((i) => i.source_ref)?.source_ref ?? null;
    return {
      source,
      numericMin: nums.length ? Math.min(...nums) : null,
      numericMax: nums.length ? Math.max(...nums) : null,
      count: items.length,
      dispositions,
      ref,
    };
  });
}

function ClaimValue({ claim, kind }: { claim: SourceClaim; kind: string }) {
  if (kind === "disposition") {
    if (claim.dispositions.length === 0) return <span className="dash">—</span>;
    return (
      <span className="claim__val">
        {claim.dispositions.map((d) => dispositionMeta(d).label).join(" / ")}
      </span>
    );
  }
  if (claim.numericMin === null) return <span className="dash">—</span>;
  if (claim.numericMin === claim.numericMax) {
    return <span className="claim__val">{fmtNum(claim.numericMin)}</span>;
  }
  return (
    <span className="claim__val">
      {fmtNum(claim.numericMin)} – {fmtNum(claim.numericMax)}
    </span>
  );
}

function AttributeRow({ group }: { group: AttributeGroup }) {
  const claims = summarize(group.assertions);
  return (
    <tr className={group.conflict ? "is-conflict" : undefined}>
      <th className="claims__attr" scope="row">
        {group.attribute}
        {group.conflict ? <span className="claims__flag" title="sources disagree" /> : null}
        {group.unit ? <div className="claims__unit">{group.unit}</div> : null}
      </th>
      <td>
        <span className="claims__resolved">{fmtValue(group.resolved)}</span>
      </td>
      <td className={group.conflict ? "is-conflict" : undefined}>
        {claims.map((c) => (
          <div className="claim" key={c.source}>
            <div className="claim__head">
              <SourceBadge source={c.source} />
              <ClaimValue claim={c} kind={group.kind} />
              {c.count > 1 ? <span className="claim__canon">×{c.count}</span> : null}
            </div>
            {c.ref ? <div className="claim__ref">{c.ref}</div> : null}
          </div>
        ))}
      </td>
    </tr>
  );
}

export function WhoSaysWhat({ attributes }: { attributes: AttributeGroup[] }) {
  return (
    <div className="table-wrap">
      <table className="claims">
        <thead>
          <tr>
            <th>Attribute</th>
            <th>Resolved</th>
            <th>Who says what — by source</th>
          </tr>
        </thead>
        <tbody>
          {attributes.map((g) => (
            <AttributeRow key={g.attribute} group={g} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
