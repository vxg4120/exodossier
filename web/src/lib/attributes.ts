/* Attribute vocabulary for the who-says-what table: the graph's attribute codes and API units
   (api/queries.py ATTRIBUTES) rendered as reader-facing names. Unknown codes and units fall
   through unchanged, so a new attribute never renders blank. */

const LABELS: Record<string, string> = {
  disposition: "Disposition",
  period_days: "Orbital period",
  planet_radius_re: "Planet radius",
  depth_ppm: "Transit depth",
  duration_hr: "Transit duration",
  epoch_bjd: "Transit epoch",
  teff_k: "Host Teff",
  rstar_rsun: "Host radius",
  logg: "Host log g",
  parallax_mas: "Parallax",
  tmag: "TESS magnitude",
  vmag: "V magnitude",
};

const UNITS: Record<string, string> = {
  R_earth: "R⊕",
  R_sun: "R☉",
  "log10(cm/s^2)": "log10(cm/s²)",
};

export function attributeLabel(attribute: string): string {
  return LABELS[attribute] ?? attribute;
}

export function unitLabel(unit: string | null | undefined): string | null {
  if (!unit) return null;
  return UNITS[unit] ?? unit;
}
