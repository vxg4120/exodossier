import { describe, expect, it } from "vitest";
import { tfopwgLabel } from "../views/Lightcurves";

/** The TFOPWG cell keeps the answer key and adds today's disposition when TFOPWG has changed it,
    as for TOI-4307.01, which was PC in ExoFOP's July 15, 2026 list and is CP now. */
describe("tfopwgLabel", () => {
  it("shows both when the disposition changed since the answer key", () => {
    expect(tfopwgLabel({ tfopwg_disp: "PC", tfopwg_disp_now: "CP" })).toBe("PC, now CP");
  });
  it("shows the answer key alone when nothing changed or nothing is known now", () => {
    expect(tfopwgLabel({ tfopwg_disp: "CP", tfopwg_disp_now: "CP" })).toBe("CP");
    expect(tfopwgLabel({ tfopwg_disp: "PC", tfopwg_disp_now: null })).toBe("PC");
    expect(tfopwgLabel({ tfopwg_disp: "PC" })).toBe("PC");
  });
});
