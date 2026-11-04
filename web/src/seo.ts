import { useEffect } from "react";
import { generatePath, matchPath } from "react-router-dom";
import table from "../public/seo-routes.json";

/** Document metadata per route. The table lives in public/seo-routes.json so the API can serve
    the same title, description and canonical in the shell for a deep link (api/seo.py reads the
    copy Vite drops into dist). This module is the client half: on navigation RouteMeta rewrites
    the head from the same table, so the two never disagree. index.html carries the root values
    for crawlers that read the raw file; keep it in step with the "/" entry. */

export interface RouteMetaEntry {
  /** React Router pattern. "*" is the catch-all for unknown paths. */
  pattern: string;
  end?: boolean;
  title: string;
  description: string;
  /** Unknown paths are kept out of the index and carry no canonical. */
  noindex?: boolean;
}

export const SITE_ORIGIN: string = table.site.origin;
export const SITE_NAME: string = table.site.name;
export const ROUTE_META: RouteMetaEntry[] = table.routes;

export interface ResolvedMeta extends RouteMetaEntry {
  /** Absolute canonical URL, or null when the route is noindex. */
  canonical: string | null;
}

/** The entry for a path plus its canonical: the matched pattern regenerated with the actual
    params, so static segments come out as the table spells them (lowercase) and ids keep their
    case. Trailing slashes are dropped; the root keeps its slash. Query strings never take part,
    because a search or a follow-up filter is not a page. */
export function metaForPath(pathname: string): ResolvedMeta {
  for (const entry of ROUTE_META) {
    if (entry.pattern === "*") continue;
    const m = matchPath({ path: entry.pattern, end: entry.end ?? true }, pathname);
    if (m) return { ...entry, canonical: canonicalFor(entry.pattern, m.params) };
  }
  const fallback = ROUTE_META.find((e) => e.pattern === "*");
  return { ...(fallback ?? { pattern: "*", title: SITE_NAME, description: "", noindex: true }), canonical: null };
}

export function canonicalFor(pattern: string, params: Record<string, string | undefined> = {}): string {
  // matchPath hands back decoded params and generatePath inserts them raw; the canonical must
  // carry the encoded form, as the address bar and the server-rendered head do
  const encoded = Object.fromEntries(
    Object.entries(params).map(([k, v]) => [k, v === undefined ? v : encodeURIComponent(v)]),
  );
  const path = generatePath(pattern, encoded).replace(/\/+$/, "");
  return path ? `${SITE_ORIGIN}${path}` : `${SITE_ORIGIN}/`;
}

function setMeta(selector: string, attr: string, value: string) {
  const el = document.head.querySelector<HTMLElement>(selector);
  if (el) el.setAttribute(attr, value);
}

/** The robots tag this module owns is marked data-route-meta; a hand-written one is left alone. */
function setRobots(noindex: boolean) {
  const own = document.head.querySelector('meta[name="robots"][data-route-meta]');
  if (noindex && !own) {
    const el = document.createElement("meta");
    el.setAttribute("name", "robots");
    el.setAttribute("content", "noindex");
    el.setAttribute("data-route-meta", "");
    document.head.appendChild(el);
  } else if (!noindex && own) {
    own.remove();
  }
}

/** The canonical link and og:url are removed on a noindex route and put back on the next
    indexable one (the server also serves a 404 shell without them). */
function setUrlTag(
  selector: string,
  create: () => HTMLElement,
  attr: string,
  value: string | null,
) {
  let el = document.head.querySelector<HTMLElement>(selector);
  if (!value) {
    el?.remove();
    return;
  }
  if (!el) {
    el = create();
    document.head.appendChild(el);
  }
  el.setAttribute(attr, value);
}

function setCanonical(href: string | null) {
  setUrlTag(
    'link[rel="canonical"]',
    () => {
      const link = document.createElement("link");
      link.setAttribute("rel", "canonical");
      return link;
    },
    "href",
    href,
  );
  setUrlTag(
    'meta[property="og:url"]',
    () => {
      const meta = document.createElement("meta");
      meta.setAttribute("property", "og:url");
      return meta;
    },
    "content",
    href,
  );
}

export function applyRouteMeta(pathname: string) {
  const meta = metaForPath(pathname);
  document.title = meta.title;
  setMeta('meta[name="description"]', "content", meta.description);
  setMeta('meta[property="og:title"]', "content", meta.title);
  setMeta('meta[property="og:description"]', "content", meta.description);
  setMeta('meta[name="twitter:title"]', "content", meta.title);
  setMeta('meta[name="twitter:description"]', "content", meta.description);
  setCanonical(meta.canonical);
  setRobots(Boolean(meta.noindex));
}

/** A view that knows more than the route table (a resolved candidate name, say) narrows the tab
    title through here. RouteMeta writes first on every navigation, so the override only has to
    win within its own render; nothing is restored on the way out. */
export function useDocumentTitle(override: string | undefined) {
  useEffect(() => {
    if (override) document.title = override;
  }, [override]);
}
