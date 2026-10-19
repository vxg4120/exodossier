import { useEffect } from "react";
import { matchPath } from "react-router-dom";

/** Document metadata per route: the tab title, the description that search engines quote, and
    the canonical URL. One table, one writer (RouteMeta), so no view sets document.title on its
    own. index.html carries the same root title and description for crawlers that do not run
    JavaScript; keep the two in step. */

export const SITE_ORIGIN = "https://exo.vibcreates.com";
export const SITE_NAME = "ExoDossier";
export const ROOT_TITLE = "ExoDossier · Exoplanet Conflict Explorer";
export const ROOT_DESCRIPTION =
  "A read-only catalog over the exoplanet identity graph. It crosswalks TIC, TOI, CTOI, KOI and Gaia identifiers, records what each source asserts with its provenance, and shows where the NASA Exoplanet Archive, ExoFOP and the Kepler KOI table disagree about the same star or candidate. It surfaces disagreement and does not adjudicate.";

export interface RouteMetaEntry {
  /** React Router pattern, matched with end: true. */
  path: string;
  title: string;
  description: string;
  /** Unknown paths are kept out of the index; everything else is indexable. */
  noindex?: boolean;
}

export const ROUTE_META: RouteMetaEntry[] = [
  { path: "/", title: ROOT_TITLE, description: ROOT_DESCRIPTION },
  {
    path: "/search",
    title: "Search · ExoDossier",
    description:
      "Resolve any star or candidate by TIC, TOI, CTOI, KOI, planet name or host name, and open its crosswalk and per-source provenance.",
  },
  {
    path: "/target/:id",
    title: "Target · ExoDossier",
    description:
      "One candidate and its host star: the identifier crosswalk, what every source asserts about each attribute, and where those sources disagree.",
  },
  {
    path: "/conflicts",
    title: "Conflicts · ExoDossier",
    description:
      "The browsable corpus of cross-source disagreement, where ExoFOP, the NASA TOI table, the Kepler KOI table and the Archive's per-publication and composite tables describe the same star or candidate differently.",
  },
  {
    path: "/lightcurves",
    title: "Light curves · ExoDossier",
    description:
      "An independent check on the catalogs: TESS light curves from MAST searched for a periodic transit and graded against the catalog period for a fixed slice of TOIs.",
  },
  {
    path: "/followup",
    title: "Follow-up · ExoDossier",
    description:
      "Follow-up priorities for TESS candidates, joined to the live satellite catalog so an observer can see what else crosses the sky above a target.",
  },
  {
    path: "/about",
    title: "About · ExoDossier",
    description:
      "What ExoDossier is, how the disposition, radius and host temperature conflicts are computed, and which archives the data belongs to.",
  },
];

export const NOT_FOUND_META: RouteMetaEntry = {
  path: "*",
  title: "Page not found · ExoDossier",
  description: "Nothing resolves at this path on ExoDossier.",
  noindex: true,
};

export function metaForPath(pathname: string): RouteMetaEntry {
  return ROUTE_META.find((m) => matchPath({ path: m.path, end: true }, pathname)) ?? NOT_FOUND_META;
}

/** "https://exo.vibcreates.com" + pathname with trailing slashes stripped; the root keeps its
    slash. Query strings are dropped on purpose: a search or a follow-up filter is not a page. */
export function canonicalFor(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, "");
  return trimmed ? `${SITE_ORIGIN}${trimmed}` : `${SITE_ORIGIN}/`;
}

function setMeta(selector: string, attr: string, value: string) {
  const el = document.head.querySelector<HTMLElement>(selector);
  if (el) el.setAttribute(attr, value);
}

export function applyRouteMeta(pathname: string) {
  const meta = metaForPath(pathname);
  const canonical = canonicalFor(pathname);
  document.title = meta.title;
  setMeta('meta[name="description"]', "content", meta.description);
  setMeta('link[rel="canonical"]', "href", canonical);
  setMeta('meta[property="og:title"]', "content", meta.title);
  setMeta('meta[property="og:description"]', "content", meta.description);
  setMeta('meta[property="og:url"]', "content", canonical);
  setMeta('meta[name="twitter:title"]', "content", meta.title);
  setMeta('meta[name="twitter:description"]', "content", meta.description);

  const robots = document.head.querySelector('meta[name="robots"]');
  if (meta.noindex) {
    if (!robots) {
      const el = document.createElement("meta");
      el.setAttribute("name", "robots");
      el.setAttribute("content", "noindex");
      document.head.appendChild(el);
    }
  } else if (robots) {
    robots.remove();
  }
}

/** A view that knows more than the route table (a resolved candidate name, say) narrows the tab
    title through here. RouteMeta writes first on every navigation, so the override only has to
    win within its own render; nothing is restored on the way out. */
export function useDocumentTitle(override: string | undefined) {
  useEffect(() => {
    if (override) document.title = override;
  }, [override]);
}
