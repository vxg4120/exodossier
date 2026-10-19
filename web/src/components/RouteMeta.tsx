import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { applyRouteMeta } from "../seo";

/** Renders nothing. On every navigation it writes the route's title, description, canonical
    link and robots directive into the document head from the table in seo.ts. */
export function RouteMeta() {
  const { pathname } = useLocation();
  useEffect(() => {
    applyRouteMeta(pathname);
  }, [pathname]);
  return null;
}
