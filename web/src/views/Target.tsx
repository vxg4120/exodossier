import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { getTarget } from "../api/client";
import type { Identifier, Sibling, TargetDetail } from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtNum } from "../lib/format";
import { dispositionMeta } from "../lib/dispositions";
import { Panel } from "../components/Panel";
import { DispositionBadge } from "../components/DispositionBadge";
import { SourceBadge } from "../components/SourceBadge";
import { WhoSaysWhat } from "../components/WhoSaysWhat";
import { Async } from "../components/States";
import { useDocumentTitle } from "../seo";

function groupBySource(ids: Identifier[]): [string, Identifier[]][] {
  const map = new Map<string, Identifier[]>();
  for (const it of ids) {
    const arr = map.get(it.source) ?? [];
    arr.push(it);
    map.set(it.source, arr);
  }
  return Array.from(map.entries());
}

/** "6 confirmed" / "3 confirmed · 2 candidate · 1 false positive" — the siblings summarized by
    their own dispositions, so a system of confirmed planets is never labeled "candidates". */
function siblingSummary(siblings: Sibling[]): string {
  const counts = new Map<string, number>();
  for (const s of siblings) {
    const label = s.disposition ? dispositionMeta(s.disposition).label.toLowerCase() : "undispositioned";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([label, n]) => `${n} ${label}`)
    .join(" · ");
}

/** The Follow-up hand-off for a candidate's host. The forecaster's warning says the catalogs
    disagree on disposition, so the flag travels only with a disposition conflict, never with a
    disagreement on radius or another attribute. Exported for its unit test. */
export function followupHref(
  star: { ra_deg: number; dec_deg: number; name: string },
  conflictAttributes: string[],
): string {
  const flag = conflictAttributes.includes("disposition") ? "&conflict=1" : "";
  return `/followup?ra=${star.ra_deg}&dec=${star.dec_deg}&name=${encodeURIComponent(star.name)}${flag}`;
}

export function Target() {
  const { id = "" } = useParams<{ id: string }>();
  const detail = useApi<TargetDetail>(() => getTarget(id), [id]);

  return (
    <div className="view fadein">
      <Async state={detail} loadingLabel="Resolving target" loadingRows={10}>
        {(t) => <TargetCard detail={t} />}
      </Async>
    </div>
  );
}

function TargetCard({ detail }: { detail: TargetDetail }) {
  const { candidate, star } = detail;
  useDocumentTitle(candidate.name ? `${candidate.name} · ExoDossier` : undefined);
  const nConflict = detail.conflict_attributes.length;
  const crosswalk = useMemo(() => groupBySource(detail.identifiers), [detail.identifiers]);

  return (
    <div className="stack">
      {/* the chapter head every route opens with (Fraunces narrates); the candidate's name is
          the dossier's own heading below it, not the page title */}
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Target</h1>
          <p className="vhead__desc">Every source&rsquo;s claim about one candidate, before resolution.</p>
        </div>
        <div className="inline">
          <Link to="/search" className="hint back-link">
            ‹ Search
          </Link>
          <span className="hint" aria-hidden="true">
            ·
          </span>
          <span className="hint">candidate #{candidate.candidate_id}</span>
        </div>
      </header>

      <div className={`idhead${nConflict > 0 ? " is-conflict" : ""}`}>
        <div>
          <h2 className="idhead__name">{candidate.name}</h2>
          <div className="idhead__host">
            host <span className="mono-hi">{star.name}</span>
            {star.tic_id ? <span className="muted"> · TIC {star.tic_id}</span> : null}
          </div>
          <div className="idhead__badges">
            <DispositionBadge disposition={candidate.disposition} />
            {nConflict > 0 ? (
              <span className="badge badge--conflict">
                <span className="badge__glyph" aria-hidden="true" />
                {nConflict} conflicting {nConflict === 1 ? "attribute" : "attributes"}
              </span>
            ) : (
              <span className="badge">sources agree</span>
            )}
          </div>
        </div>
        <div className="kv">
          <KV k="Period (d)" v={fmtNum(candidate.period_days)} />
          <KV k="Radius (R⊕)" v={fmtNum(candidate.planet_radius_re)} />
          <KV k="Host Teff (K)" v={fmtNum(star.teff_k)} />
          <KV k="Host R (R☉)" v={fmtNum(star.rstar_rsun)} />
          <KV k="RA (deg)" v={star.ra_deg == null ? "—" : star.ra_deg.toFixed(4)} />
          <KV k="Dec (deg)" v={star.dec_deg == null ? "—" : star.dec_deg.toFixed(4)} />
        </div>
      </div>

      {star.ra_deg != null && star.dec_deg != null ? (
        <Link
          to={followupHref(
            { ra_deg: star.ra_deg, dec_deg: star.dec_deg, name: star.name },
            detail.conflict_attributes,
          )}
          className="followup-link"
        >
          Check follow-up passes — which satellites cross this sightline when you observe it ›
        </Link>
      ) : null}

      <Panel
        title="Who says what"
        meta={
          nConflict > 0
            ? `${nConflict} attribute${nConflict === 1 ? " disagrees" : "s disagree"} across sources`
            : "every source's claim, by attribute"
        }
        flush
      >
        <WhoSaysWhat attributes={detail.attributes} />
        <p className="conflict-headline" style={{ borderTop: "1px solid var(--rule)", borderBottom: "none" }}>
          Highlighted rows are attributes where the catalogs disagree. Values are the per-source
          claims; &ldquo;Resolved&rdquo; is the graph&rsquo;s current canonical winner — surfaced,
          not adjudicated.
        </p>
      </Panel>

      <Panel
        title="Identifier crosswalk"
        meta={`${detail.identifiers.length === 1 ? "1 id" : `${detail.identifiers.length} ids`} · by source`}
        flush
      >
        {crosswalk.map(([source, ids]) => (
          <div className="crosswalk-src" key={source}>
            <div className="crosswalk-src__head">
              <SourceBadge source={source} />
              <span className="hint">{ids.length === 1 ? "1 id" : `${ids.length} ids`}</span>
            </div>
            {ids.map((id, i) => (
              <div className="idpair" key={`${id.id_type}-${id.id_value}-${i}`}>
                <span className="idpair__type">{id.id_type}</span>
                <span className="idpair__val">{id.id_value}</span>
                <span className="idpair__owner">{id.owner}</span>
              </div>
            ))}
          </div>
        ))}
      </Panel>

      {detail.sibling_candidates.length > 0 ? (
        <Panel
          title="Others in this system"
          meta={siblingSummary(detail.sibling_candidates)}
          flush
        >
          {detail.sibling_candidates.map((s) => (
            <Link key={s.candidate_id} to={`/target/${s.candidate_id}`} className="assert-line">
              <span className="assert-val mono-hi">{s.name}</span>
              <DispositionBadge disposition={s.disposition} />
            </Link>
          ))}
        </Panel>
      ) : null}
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="kv__item">
      <span className="kv__k">{k}</span>
      <span className="kv__v">{v}</span>
    </div>
  );
}
