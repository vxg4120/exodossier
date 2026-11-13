import { describe, expect, it } from "vitest";
import { followupHref } from "../views/Target";

/** The Follow-up warning says the catalogs disagree on disposition, so the hand-off carries the
    flag only for a disposition conflict. Kepler-1999 b disagrees on radius and stellar radius. */
describe("followupHref", () => {
  const star = { ra_deg: 282.3705675, dec_deg: 48.259234, name: "Kepler-1999" };
  it("does not flag a candidate whose only conflicts are numeric", () => {
    expect(followupHref(star, ["planet_radius_re", "rstar_rsun"])).toBe(
      "/followup?ra=282.3705675&dec=48.259234&name=Kepler-1999",
    );
  });
  it("flags a disposition conflict", () => {
    expect(followupHref(star, ["disposition", "teff_k"])).toMatch(/&conflict=1$/);
  });
  it("encodes the host name once", () => {
    expect(followupHref({ ...star, name: "TOI-1836 A" }, [])).toContain("name=TOI-1836%20A");
  });
});
