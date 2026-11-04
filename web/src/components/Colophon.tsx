import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getStats } from "../api/client";

/** The plate's edge-notes: every view closes under a double rule with the record's provenance
 *  in one engraved line: freshest pull, the archives the data belongs to, the correction
 *  channel. A colophon rather than a footer, as on orbital. */
export function Colophon() {
  const [refreshed, setRefreshed] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getStats()
      .then((s) => {
        if (!alive) return;
        const stamps = s.ingest_runs
          .map((r) => r.last_ok_at ?? r.finished_at)
          .filter((t): t is string => Boolean(t))
          .sort();
        const newest = stamps[stamps.length - 1];
        setRefreshed(newest ? newest.slice(0, 10) : "—");
      })
      .catch(() => {
        /* the colophon is annotation, never an error surface */
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="colophon">
      <span>ExoDossier</span>
      <span>
        refreshed <span className="num">{refreshed ?? "—"}</span>
      </span>
      <span>
        sources:{" "}
        <a href="https://exoplanetarchive.ipac.caltech.edu/" target="_blank" rel="noreferrer">
          NASA Exoplanet Archive
        </a>{" "}
        ·{" "}
        <a href="https://exofop.ipac.caltech.edu/tess/" target="_blank" rel="noreferrer">
          ExoFOP-TESS
        </a>
      </span>
      <span>
        <Link to="/about">about &amp; methodology</Link>
      </span>
      <span>
        corrections:{" "}
        <a href="https://github.com/vxg4120/exodossier/issues" target="_blank" rel="noreferrer">
          open an issue
        </a>
      </span>
    </div>
  );
}
