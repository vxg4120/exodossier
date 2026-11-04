/* Formatting helpers. NULL-safe throughout — every nullable field renders as an em dash. */

export const DASH = "—";

export function fmtInt(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  return n.toLocaleString("en-US");
}

/** Auto-compact large counts: 1,284 / 12.9K / 4.2M. */
export function compact(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  const abs = Math.abs(n);
  if (abs < 10_000) return n.toLocaleString("en-US");
  // round before choosing the unit: 999,950 is "1M", not "1000K"
  if (Math.abs(Math.round((n / 1_000) * 10) / 10) < 1000) return trim(n / 1_000) + "K";
  return trim(n / 1_000_000) + "M";
}

function trim(x: number): string {
  return (Math.round(x * 10) / 10).toString();
}

/** Significant-figure number for physical quantities (radius, Teff, period). Four figures by
    default: three rounded a 5,842 K host to "5,840" and a 292.1669° coordinate to "292" in a
    catalog that promises each source's value. Large values (a BJD epoch, a deep eclipse in
    ppm) stay in fixed notation with one decimal; only the far tails use an exponent. */
export function fmtNum(n: number | null | undefined, digits = 4): string {
  if (n === null || n === undefined) return DASH;
  if (n === 0) return "0";
  const abs = Math.abs(n);
  if (abs >= 1e9 || abs < 0.001) return n.toExponential(2);
  if (abs >= 100000) return n.toLocaleString("en-US", { maximumFractionDigits: 1 });
  const sig = Number(n.toPrecision(digits));
  return sig.toLocaleString("en-US", { maximumFractionDigits: 6 });
}

/** Render a resolved value that may be a string (disposition) or number. */
export function fmtValue(v: string | number | null | undefined): string {
  if (v === null || v === undefined) return DASH;
  if (typeof v === "number") return fmtNum(v);
  return v;
}

export function fmtPct(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined) return DASH;
  return n.toFixed(digits) + "%";
}

/** ISO date (YYYY-MM-DD) or em dash. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  return iso.slice(0, 10);
}
