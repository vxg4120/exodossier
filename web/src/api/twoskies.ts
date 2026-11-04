/* =============================================================================
   Follow-up bridge API. The view calls the ExoDossier FastAPI service under /api/twoskies
   (same-origin in the built SPA, dev-proxied to :8700). Kept separate from the main client so the
   shared client/types stay untouched. In mock mode (VITE_API_MOCK=1) the answers come from
   fixtures/twoskies.json: the target list and the congestion field are shaped like the live ones,
   and /passes is one canned Kitt Peak forecast for every query, because the forecaster SGP4-
   propagates the satellite catalog server-side and the mock cannot.
   ============================================================================= */

import { delay, fetchJson, MOCK } from "./client";
import twoskiesFixture from "./fixtures/twoskies.json";

const BASE = "/api/twoskies";

export interface TwoSkyTarget {
  candidate_id: number | null;
  candidate: string;
  host: string;
  tic_id: string | null;
  ra_deg: number;
  dec_deg: number;
  disposition: string;
  has_conflict: boolean;
  n_candidates: number;
  category: "famous" | "conflict" | "custom";
}

export interface TargetsResponse {
  targets: TwoSkyTarget[];
  n_famous: number;
  n_conflict: number;
  note: string;
}

export interface CongestionBin {
  alt_bin_km: number;
  inc_bin_deg: number;
  object_count: number;
}

export interface CongestionAstronomy {
  catalog_objects: number;
  tracked_with_elements: number;
  leo_objects: number;
  payloads_launched_1y: number;
  payloads_launched_30d: number;
  top_operators: { operator: string; payloads: number }[];
  shells: { alt_lo_km: number; alt_hi_km: number; objects: number }[];
  peak_bin: CongestionBin;
  bins: CongestionBin[];
  caveats: string[];
  note: string;
}

export interface SatPass {
  norad: number;
  name: string;
  operator: string | null;
  alt_km: number;
  closest_sep_deg: number;
  alt_deg: number;
  time_utc: string;
}

export interface PassesResponse {
  target: { ra_deg: number; dec_deg: number };
  site: { key: string | null; name: string; lat_deg: number; lon_deg: number; elev_km: number };
  window: { start_utc: string; end_utc: string; window_min: number; step_sec: number; steps: number };
  sep_deg: number;
  min_alt_deg: number;
  target_visible: boolean;
  target_max_alt_deg: number;
  n_considered: number;
  n_found: number;
  truncated: boolean;
  passes: SatPass[];
  operator_tally: { operator: string; count: number }[];
  elapsed_ms: number;
  caveats: string[];
}

export interface SiteOption {
  key: string;
  name: string;
}

/** The observatory presets mirror api/routers/twoskies.SITES (real ground-based follow-up sites). */
export const SITES: SiteOption[] = [
  { key: "kitt_peak", name: "Kitt Peak, Arizona (TFOP)" },
  { key: "paranal", name: "Cerro Paranal / VLT, Chile" },
  { key: "mauna_kea", name: "Maunakea, Hawaii" },
  { key: "la_palma", name: "Roque de los Muchachos, La Palma" },
  { key: "siding_spring", name: "Siding Spring, Australia (TFOP)" },
  { key: "sutherland", name: "SAAO Sutherland, South Africa" },
  { key: "generic_north", name: "Generic mid-northern site (35N)" },
];

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const qs = params
    ? "?" + new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()
    : "";
  return fetchJson<T>(`${BASE}${path}${qs}`, `/twoskies${path}`);
}

const fixture = twoskiesFixture as unknown as {
  targets: TargetsResponse;
  congestion: CongestionAstronomy;
  passes: PassesResponse;
};

export function getTargets(): Promise<TargetsResponse> {
  if (MOCK) return delay(fixture.targets);
  return get<TargetsResponse>("/targets");
}

export function getCongestionAstronomy(): Promise<CongestionAstronomy> {
  if (MOCK) return delay(fixture.congestion);
  return get<CongestionAstronomy>("/congestion-astronomy");
}

export interface PassQuery {
  ra: number;
  dec: number;
  datetime?: string;
  site?: string;
  window_min?: number;
  sep_deg?: number;
  min_alt_deg?: number;
}

export function getPasses(q: PassQuery): Promise<PassesResponse> {
  if (MOCK) {
    // the canned forecast, re-labelled with the query's target, site and window
    const site = SITES.find((s) => s.key === q.site);
    return delay({
      ...fixture.passes,
      target: { ra_deg: q.ra, dec_deg: q.dec },
      site: site ? { ...fixture.passes.site, key: site.key, name: site.name } : fixture.passes.site,
      window: { ...fixture.passes.window, window_min: q.window_min ?? fixture.passes.window.window_min },
      sep_deg: q.sep_deg ?? fixture.passes.sep_deg,
      min_alt_deg: q.min_alt_deg ?? fixture.passes.min_alt_deg,
    });
  }
  const params: Record<string, string | number> = { ra: q.ra, dec: q.dec };
  if (q.datetime) params.datetime = q.datetime;
  if (q.site) params.site = q.site;
  if (q.window_min !== undefined) params.window_min = q.window_min;
  if (q.sep_deg !== undefined) params.sep_deg = q.sep_deg;
  if (q.min_alt_deg !== undefined) params.min_alt_deg = q.min_alt_deg;
  return get<PassesResponse>("/passes", params);
}
