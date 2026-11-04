import { describe, expect, it } from "vitest";
import { canonicalFor, metaForPath, ROUTE_META, SITE_ORIGIN } from "../seo";

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
