import { describe, expect, it } from "vitest";
import { dramaticCounterpart } from "../lib/conflicts";

/** A dramatic row pairs a FALSE POSITIVE with a CONFIRMED or a KNOWN PLANET claim, and its badge
    names the one its sources make: TOI 7858.01 is KNOWN PLANET against FALSE POSITIVE, with no
    CONFIRMED claim at all. */
describe("dramaticCounterpart", () => {
  it("names CONFIRMED when a source says so", () => {
    expect(dramaticCounterpart(["CANDIDATE", "CONFIRMED", "FALSE_POSITIVE"])).toBe("CONFIRMED");
  });
  it("names KNOWN PLANET when no source says CONFIRMED", () => {
    expect(dramaticCounterpart(["FALSE_POSITIVE", "KNOWN_PLANET"])).toBe("KNOWN PLANET");
  });
  it("names both when the row carries no dispositions", () => {
    expect(dramaticCounterpart(undefined)).toBe("CONFIRMED or KNOWN PLANET");
  });
});
