import { getAttribution } from "../api/client";
import { useApi } from "../hooks/useApi";
import { Panel } from "../components/Panel";
import { Async } from "../components/States";

export function About() {
  const attribution = useApi(() => getAttribution(), []);

  return (
    <div className="view fadein">
      <header className="vhead">
        <div>
          <h1 className="vhead__title">About &amp; Methodology</h1>
          <p className="vhead__desc">
            What this is, how the conflicts are computed, and who the data belongs to.
          </p>
        </div>
      </header>

      <Panel title="What ExoDossier is">
        <div className="prose">
          <p>
            ExoDossier is a <strong>conflict-aware provenance layer</strong> over the public
            exoplanet catalogs. It reconciles the identifiers that describe the same star and
            candidate — TIC, TOI, CTOI, KOI, Gaia DR3, HD, HIP — into one graph, then records what
            every source claims about each attribute (period, radius, disposition, host temperature,
            and more) <em>before</em> any resolution. Where the sources disagree, it says so, and it
            shows you exactly who said what, with the publication behind each value.
          </p>
          <p>
            <strong>It surfaces disagreement; it does not adjudicate or confirm.</strong> When a row
            is marked &ldquo;Resolved,&rdquo; that is the graph&rsquo;s current canonical winner under
            a precedence policy — not a claim that the other sources are wrong. Confirming a planet is
            a telescope problem, not a software one, and we never pretend otherwise. This is Stage 1:
            a read-only catalog + API + agent tools. AI-orchestrated dossiers that weigh the evidence
            come later — and even then, a human adjudicates.
          </p>
        </div>
      </Panel>

      <Panel title="How the conflicts are computed">
        <div className="prose">
          <h2>Disposition conflicts</h2>
          <p>
            Each source&rsquo;s raw disposition is mapped to a canonical taxonomy —{" "}
            <code>CONFIRMED</code>, <code>KNOWN_PLANET</code>, <code>CANDIDATE</code>,{" "}
            <code>AMBIGUOUS</code>, <code>FALSE_POSITIVE</code>. A candidate is in conflict when its
            sources map to two or more distinct canonical dispositions. The <em>dramatic</em> kind
            pairs a FALSE&nbsp;POSITIVE with a CONFIRMED or KNOWN&nbsp;PLANET.
          </p>
          <h2>Numeric conflicts (radius, host Teff)</h2>
          <p>
            A numeric attribute is in conflict when at least two <em>distinct sources</em> report
            values whose relative spread, <code>(max − min) / max</code>, exceeds a threshold: 10% for
            planet radius, 5% for host effective temperature (Kane 2014 — a ~5% Teff error shifts the
            habitable-zone boundary ~10%, so HZ membership can flip). Within-source per-publication
            ranges are preserved so a Gaia radius revision reads as the real revision it is.
          </p>
          <p>
            Counts are recomputed live from the graph and track the published v0 conflict report:
            3,274 disposition conflicts (3 of the dramatic kind), 1,083 host-Teff conflicts, and
            thousands of radius disagreements.
          </p>
        </div>
      </Panel>

      <Panel title="Data attribution &amp; citations">
        <Async state={attribution} loadingLabel="Loading attribution">
          {(a) => (
            <div className="prose">
              <p>{a.summary}</p>
              {a.sources.map((s) => (
                <p className="cite" key={s.name}>
                  <strong>{s.name}</strong>
                  {s.used_for}{" "}
                  <a href={s.url} target="_blank" rel="noreferrer noopener">
                    {s.url}
                  </a>
                  <br />
                  <em>{s.citation}</em>
                </p>
              ))}
              <p className="hint">{a.notes}</p>
            </div>
          )}
        </Async>
      </Panel>

      <Panel title="License &amp; contributing">
        <div className="prose">
          <p>
            ExoDossier&rsquo;s code is released under the <strong>MIT License</strong>. The catalog
            data is the property of its sources (above) and is redistributed under their public-use
            terms — please cite them, not this tool.
          </p>
          <p>
            This is an open, early-stage project and contributors are welcome: new catalog sources,
            better conflict heuristics, a sanity-flag layer that separates genuine parameter revisions
            from obvious placeholders (a solar-default 5780&nbsp;K on a cool dwarf, a 1&nbsp;R☉
            white-dwarf default), and researchers who want to point the agent tools at their own
            follow-up questions. The whole point is to make cross-catalog disagreement legible — if
            you find a conflict we surface wrongly, that is a bug worth filing.
          </p>
        </div>
      </Panel>
    </div>
  );
}
