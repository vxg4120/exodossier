import { describe, expect, it } from "vitest";
import { afterSettingsChange, type PassState } from "../views/FollowUp";
import type { PassesResponse } from "../api/twoskies";

const idle: PassState = { loading: false, data: null, error: null, stale: false };
const data = { passes: [], n_found: 0, truncated: false } as unknown as PassesResponse;

/** A setting change under a forecast marks the slot "out of date"; under an error or a run in
    flight it just clears; an idle slot is the same object (no re-render). */
describe("afterSettingsChange", () => {
  it("leaves an idle slot alone", () => {
    expect(afterSettingsChange(idle)).toBe(idle);
  });
  it("marks a forecast on screen as out of date", () => {
    expect(afterSettingsChange({ ...idle, data })).toEqual({ ...idle, stale: true });
  });
  it("clears an error or a run in flight without the out-of-date word", () => {
    expect(afterSettingsChange({ ...idle, error: "x" })).toEqual(idle);
    expect(afterSettingsChange({ ...idle, loading: true })).toEqual(idle);
  });
});
