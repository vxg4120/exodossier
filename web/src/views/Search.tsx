import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { searchTargets } from "../api/client";
import type { SearchResult } from "../api/types";
import { useApi } from "../hooks/useApi";
import { fmtInt } from "../lib/format";
import { Panel } from "../components/Panel";
import { DispositionBadge } from "../components/DispositionBadge";
import { EmptyState, ErrorState, Loading } from "../components/States";

const EXAMPLES = [
  { q: "TRAPPIST-1", label: "TRAPPIST-1 · Teff conflict (5780 K vs ~2560 K)" },
  { q: "Kepler-1517 b", label: "Kepler-1517 b · FALSE POSITIVE vs CONFIRMED" },
  { q: "TOI-1836", label: "TOI-1836 · disposition fight" },
  { q: "Kepler-1999 b", label: "Kepler-1999 b · 100% radius spread" },
  { q: "55 Cnc", label: "55 Cnc · a bright multi-planet host" },
];

export function Search() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 180);
    return () => clearTimeout(t);
  }, [query]);

  const search = useApi(
    () => (debounced.trim() ? searchTargets(debounced) : Promise.resolve(null)),
    [debounced],
  );

  return (
    <div className="view fadein">
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Search</h1>
          <p className="vhead__desc">
            Resolve any star or candidate by TIC, TOI, CTOI, KOI, planet name or host name. A host
            match returns every candidate in the system. Pick a result to open its full provenance —
            the crosswalk and the who-says-what table.
          </p>
        </div>
      </header>

      <div className="searchbar">
        <span className="searchbar__prompt" aria-hidden="true">
          ⌕
        </span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. TRAPPIST-1, TOI-1836, Kepler-1517 b, K03728.01, TIC 278892590"
          aria-label="Search targets"
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <Panel
        title="Results"
        meta={search.data ? `${fmtInt(search.data.count)} hits` : ""}
        flush
      >
        <Results
          hasQuery={Boolean(debounced.trim())}
          loading={search.loading}
          error={search.error}
          results={search.data?.results ?? []}
          onPick={(id) => navigate(`/target/${id}`)}
        />
      </Panel>
    </div>
  );
}

function Results({
  hasQuery,
  loading,
  error,
  results,
  onPick,
}: {
  hasQuery: boolean;
  loading: boolean;
  error: string | null;
  results: SearchResult[];
  onPick: (id: number) => void;
}) {
  if (!hasQuery) {
    return (
      <div className="results-empty">
        <span className="label">Try an example</span>
        <ul className="example-list">
          {EXAMPLES.map((e) => (
            <li key={e.q}>
              <Link to={`/target/${encodeURIComponent(e.q)}`}>{e.label}</Link>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (error) return <ErrorState message={error} />;
  if (loading) return <Loading label="Searching" />;
  if (results.length === 0)
    return <EmptyState title="No matches" message="Nothing in the graph matches that." />;

  return (
    <ul className="results">
      {results.map((r) => (
        <li key={r.candidate_id}>
          <button className="result-row" onClick={() => onPick(r.candidate_id)}>
            <span className="result-row__name">{r.target}</span>
            <span className="result-row__meta">
              <span className="muted">{r.host}</span>
              {r.tic_id ? (
                <>
                  {" · "}
                  <span className="num">TIC {r.tic_id}</span>
                </>
              ) : null}
            </span>
            <DispositionBadge disposition={r.disposition} />
          </button>
        </li>
      ))}
    </ul>
  );
}
