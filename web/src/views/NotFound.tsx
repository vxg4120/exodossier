import { Link, useLocation } from "react-router-dom";

/** Catch-all for unknown paths: the shell stays, the main plane says so and points back into the
    catalog instead of rendering a void. The tab title and the noindex directive come from
    RouteMeta (see seo.ts), so a dead link reads as one in the browser history too. */
export function NotFound() {
  const { pathname } = useLocation();
  return (
    <div className="view fadein">
      {/* the chapter head every other view opens with, so the page has its h1 and reads as
          part of the plate rather than an empty state floating in the plane */}
      <header className="vhead">
        <div>
          <h1 className="vhead__title">Page not found</h1>
          <p className="vhead__desc">
            Nothing resolves at <span className="num">{pathname}</span>.
          </p>
        </div>
      </header>
      <div className="inline">
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
