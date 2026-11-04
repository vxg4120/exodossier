import { describe, expect, it } from "vitest";
import { compact, DASH, fmtDate, fmtInt, fmtNum, fmtPct, fmtValue } from "../lib/format";

describe("fmtInt / compact", () => {
  it("renders null as the em dash, never a blank", () => {
    expect(fmtInt(null)).toBe(DASH);
    expect(compact(undefined)).toBe(DASH);
  });
  it("keeps the thousands separator below ten thousand and compacts above it", () => {
    expect(compact(3274)).toBe("3,274");
    expect(compact(23_031)).toBe("23K");
    expect(compact(684_210)).toBe("684.2K");
    expect(compact(4_200_000)).toBe("4.2M");
  });
});

describe("compact unit promotion", () => {
  it("promotes a value that rounds to 1000K to 1M", () => {
    expect(compact(999_950)).toBe("1M");
    expect(compact(999_949)).toBe("999.9K");
  });
});

describe("fmtNum (significant figures for physical quantities)", () => {
  it("keeps four significant figures and the thousands separator", () => {
    expect(fmtNum(5842)).toBe("5,842");
    expect(fmtNum(7147)).toBe("7,147");
    expect(fmtNum(2559.4)).toBe("2,559");
    expect(fmtNum(1.5104)).toBe("1.51");
    expect(fmtNum(0.119)).toBe("0.119");
    expect(fmtNum(292.1669)).toBe("292.2");
  });
  it("keeps a BJD epoch or a ppm depth in fixed notation", () => {
    expect(fmtNum(2458712.3)).toBe("2,458,712.3");
    expect(fmtNum(120000)).toBe("120,000");
  });
  it("uses exponent form only far outside the everyday range", () => {
    expect(fmtNum(0.0004)).toBe("4.00e-4");
    expect(fmtNum(2.5e9)).toBe("2.50e+9");
    expect(fmtNum(0)).toBe("0");
    expect(fmtNum(null)).toBe(DASH);
  });
  it("takes a precision override", () => {
    expect(fmtNum(1.5104, 3)).toBe("1.51");
    expect(fmtNum(16.6208, 5)).toBe("16.621");
  });
});

describe("fmtValue / fmtPct / fmtDate", () => {
  it("renders a disposition string as is and a number through fmtNum", () => {
    expect(fmtValue("CONFIRMED")).toBe("CONFIRMED");
    expect(fmtValue(5780)).toBe("5,780");
    expect(fmtValue(null)).toBe(DASH);
  });
  it("fixes percentage decimals and keeps the calendar date", () => {
    expect(fmtPct(65.04)).toBe("65.0%");
    expect(fmtDate("2026-07-15T18:43:38.845934+00:00")).toBe("2026-07-15");
    expect(fmtDate(undefined)).toBe(DASH);
  });
});
