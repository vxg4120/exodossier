import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { getTarget } from "../api/client";
import type { Identifier, TargetDetail } from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtNum } from "../lib/format";
import { Panel } from "../components/Panel";
import { DispositionBadge } from "../components/DispositionBadge";
import { SourceBadge } from "../components/SourceBadge";
import { WhoSaysWhat } from "../components/WhoSaysWhat";
import { Async } from "../components/States";

function groupBySource(ids: Identifier[]): [string, Identifier[]][] {
  const map = new Map<string, Identifier[]>();
  for (const it of ids) {
    const arr = map.get(it.source) ?? [];
    arr.push(it);
    map.set(it.source, arr);
  }
  return Array.from(map.entries());
}

export function Target() {
  const { id = "" } = useParams<{ id: string }>();
  const detail = useApi<TargetDetail>(() => getTarget(id), [id]);

  return (
    <div className="view fadein">
      <Async state={detail} loadingLabel="Resolving target">
        {(t) => <TargetCard detail={t} />}
      </Async>
    </div>
  );
}

function TargetCard({ detail }: { detail: TargetDetail }) {
  const { candidate, star } = detail;
  const nConflict = detail.conflict_attributes.length;
  const crosswalk = useMemo(() => groupBySource(detail.identifiers), [detail.identifiers]);

  return (
    <div className="stack">
      <div className="inline" style={{ justifyContent: "space-between" }}>
        <Link to="/search" className="hint">
          ‹ Search
        </Link>
        <span className="hint">candidate #{candidate.candidate_id}</span>
      </div>

      <div className={`idhead${nConflict > 0 ? " is-conflict" : ""}`}>
        <div>
          <h1 className="idhead__name">{candidate.name}</h1>
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
          <KV k="Period (days)" v={fmtNum(candidate.period_days)} />
          <KV k="Radius (R⊕)" v={fmtNum(candidate.planet_radius_re)} />
          <KV k="Host Teff (K)" v={fmtNum(star.teff_k)} />
          <KV k="Host R (R☉)" v={fmtNum(star.rstar_rsun)} />
          <KV k="RA (deg)" v={fmtNum(star.ra_deg)} />
          <KV k="Dec (deg)" v={fmtNum(star.dec_deg)} />
        </div>
      </div>

      {star.ra_deg != null && star.dec_deg != null ? (
        <Link
          to={`/followup?ra=${star.ra_deg}&dec=${star.dec_deg}&name=${encodeURIComponent(
            star.name,
          )}${nConflict > 0 ? "&conflict=1" : ""}`}
          className="followup-link"
        >
          Check follow-up passes — which satellites cross this sightline when you observe it ›
        </Link>
      ) : null}

      <Panel
        title="Who says what"
        meta={
          nConflict > 0
            ? `${nConflict} attribute${nConflict === 1 ? "" : "s"} disagree across sources`
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

      <Panel title="Identifier crosswalk" meta={`${detail.identifiers.length} ids · by source`} flush>
        {crosswalk.map(([source, ids]) => (
          <div className="crosswalk-src" key={source}>
            <div className="crosswalk-src__head">
              <SourceBadge source={source} />
              <span className="hint">{ids.length} ids</span>
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
          meta={`${detail.sibling_candidates.length} sibling candidate${
            detail.sibling_candidates.length === 1 ? "" : "s"
          }`}
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
