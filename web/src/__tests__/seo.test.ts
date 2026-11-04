import { describe, expect, it } from "vitest";
import indexHtml from "../../index.html?raw";
import { canonicalFor, metaForPath, ROUTE_META, SITE_ORIGIN } from "../seo";

/** index.html carries the root copy for whoever reads the raw file (static hosting, view-source,
    a fetcher that runs neither api/seo.py nor the app); the served shell and the mounted head
    take theirs from the table's "/" entry, so the file must say what the entry says. */
describe("index.html root copy", () => {
  const root = ROUTE_META.find((m) => m.pattern === "/");
  const content = (key: string) =>
    new RegExp(`<meta\\s+(?:name|property)="${key}"\\s+content="([^"]*)"`, "s").exec(indexHtml)?.[1];
  it("describes the page the '/' entry describes, in all three description metas", () => {
    expect(root).toBeDefined();
    expect(content("description")).toBe(root?.description);
    expect(content("og:description")).toBe(root?.description);
    expect(content("twitter:description")).toBe(root?.description);
  });
  it("carries the '/' title", () => {
    expect(/<title>([^<]*)<\/title>/.exec(indexHtml)?.[1]).toBe(root?.title);
    expect(content("og:title")).toBe(root?.title);
    expect(content("twitter:title")).toBe(root?.title);
  });
});

/** The route table drives the tab title, the share tags and the server-rendered head (api/seo.py
    reads the same JSON), so it has to agree with the paths App.tsx serves. */
describe("route table", () => {
  it("has one entry per view App.tsx routes, plus the catch-all", () => {
    const patterns = ROUTE_META.map((m) => m.pattern);
    for (const p of ["/", "/search", "/target/:id", "/conflicts", "/lightcurves", "/followup", "/about", "*"]) {
      expect(patterns).toContain(p);
    }
  });
  it("gives every route a title that names the site and a description", () => {
    for (const m of ROUTE_META) {
      expect(m.title).toMatch(/ExoDossier/);
      expect(m.description.length).toBeGreaterThan(30);
    }
  });
});

describe("metaForPath", () => {
  it("resolves a deep link to its view's entry and regenerates the canonical from the pattern", () => {
    const m = metaForPath("/target/10589");
    expect(m.pattern).toBe("/target/:id");
    expect(m.canonical).toBe(`${SITE_ORIGIN}/target/10589`);
  });
  it("encodes an id exactly once, whether the pathname arrives encoded or not", () => {
    expect(metaForPath("/target/TOI-1836%20b").canonical).toBe(`${SITE_ORIGIN}/target/TOI-1836%20b`);
    expect(metaForPath("/target/TOI-1836 b").canonical).toBe(`${SITE_ORIGIN}/target/TOI-1836%20b`);
    expect(metaForPath("/target/100%").canonical).toBe(`${SITE_ORIGIN}/target/100%25`);
  });
  it("lowercases static segments but keeps an id's case, and drops the trailing slash", () => {
    expect(metaForPath("/LightCurves/").canonical).toBe(`${SITE_ORIGIN}/lightcurves`);
    expect(metaForPath("/target/TOI-1836/").canonical).toBe(`${SITE_ORIGIN}/target/TOI-1836`);
    expect(metaForPath("/").canonical).toBe(`${SITE_ORIGIN}/`);
  });
  it("falls back to the catch-all, with no canonical, for an unknown path", () => {
    const m = metaForPath("/nope");
    expect(m.noindex).toBe(true);
    expect(m.canonical).toBeNull();
    expect(metaForPath("/target/1/extra").noindex).toBe(true);
  });
});

describe("canonicalFor", () => {
  it("never ends in a slash except at the root", () => {
    expect(canonicalFor("/conflicts/")).toBe(`${SITE_ORIGIN}/conflicts`);
    expect(canonicalFor("/")).toBe(`${SITE_ORIGIN}/`);
  });
});
