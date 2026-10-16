import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { EmptyState } from "../components/States";

/** Catch-all for unknown paths: the shell stays, the main plane says so and points back into the
    catalog instead of rendering a void. The tab title says so too, so a dead link reads as one in
    the browser history; the previous title comes back on the way out. */
export function NotFound() {
  const { pathname } = useLocation();
  useEffect(() => {
    const previous = document.title;
    document.title = "Page not found · ExoDossier";
    return () => {
      document.title = previous;
    };
  }, []);
  return (
    <div className="view fadein">
      <EmptyState title="Page not found" message={`Nothing resolves at ${pathname}.`} />
      <div className="inline" style={{ justifyContent: "center" }}>
        <Link to="/" className="btn">
          Overview
        </Link>
        <Link to="/search" className="btn">
          Search
        </Link>
      </div>
    </div>
  );
}
