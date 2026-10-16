/* Response types — mirror api/queries.py exactly. */

export interface IngestRun {
  source: string;
  endpoint: string;
  status: string | null;
  rows_ingested: number | null;
  bytes_downloaded: number | null;
  finished_at: string | null;
  /** The last pull that actually landed rows (a skipped_fresh check leaves these untouched). */
  last_ok_at: string | null;
  last_ok_rows: number | null;
}

export interface Stats {
  stars: number;
  candidates: number;
  identifiers: number;
  source_assertions: number;
  merge_events: number;
  conflicts: {
    disposition: number;
    disposition_dramatic: number;
    radius: number;
    teff: number;
  };
  ingest_runs: IngestRun[];
}

export interface SearchResult {
  candidate_id: number;
  target: string;
  host: string;
  tic_id: string | null;
  disposition: string | null;
}

export interface SearchResponse {
  query: string;
  count: number;
  results: SearchResult[];
}

export interface Identifier {
  id_type: string;
  id_value: string;
  source: string;
  confidence: number | null;
  owner: "candidate" | "star";
}

export interface Assertion {
  source: string;
  value: string;
  canonical_disposition: string | null;
  source_ref: string | null;
  observed_at: string | null;
}

export interface AttributeGroup {
  attribute: string;
  level: "candidate" | "star";
  unit: string | null;
  kind: "numeric" | "disposition";
  conflict: boolean;
  resolved: string | number | null;
  assertions: Assertion[];
}

export interface Sibling {
  candidate_id: number;
  name: string;
  disposition: string | null;
}

export interface TargetDetail {
  candidate: {
    candidate_id: number;
    name: string;
    disposition: string | null;
    period_days: number | null;
    planet_radius_re: number | null;
  };
  star: {
    star_id: number;
    name: string;
    tic_id: string | null;
    ra_deg: number | null;
    dec_deg: number | null;
    teff_k: number | null;
    logg: number | null;
    rstar_rsun: number | null;
  };
  identifiers: Identifier[];
  attributes: AttributeGroup[];
  conflict_attributes: string[];
  sibling_candidates: Sibling[];
}

export type ConflictType = "disposition" | "radius" | "teff";

export interface BySourceDisposition {
  source: string;
  disposition: string | null;
}
export interface BySourceRange {
  source: string;
  min: number | null;
  max: number | null;
  n: number;
}

export interface ConflictRow {
  candidate_id: number;
  target: string;
  host: string;
  tic_id: string | null;
  attribute: string;
  resolved: string | number | null;
  unit?: string | null;
  // disposition rows
  dispositions?: string[];
  dramatic?: boolean;
  // numeric rows
  min?: number | null;
  max?: number | null;
  spread_pct?: number;
  n_sources?: number;
  by_source: (BySourceDisposition | BySourceRange)[];
}

export interface ConflictsResponse {
  type: ConflictType;
  rows: ConflictRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface AttributionSource {
  name: string;
  operator: string;
  used_for: string;
  url: string;
  citation: string;
}
export interface Attribution {
  summary: string;
  sources: AttributionSource[];
  notes: string;
}

/* ---- light-curve pipeline (/api/lightcurves) ------------------------------ */
export type LightcurveCohort = "gold_planet" | "gold_fp" | "discovery";

export interface LightcurveDetection {
  method: string;
  period_days: number | null;
  depth_ppm: number | null;
  duration_hr: number | null;
  snr: number | null;
  sde: number | null;
}

export interface LightcurveCohortSummary {
  label: string;
  description: string;
  targets: number;
  processed: number;
  by_verdict: Record<string, number>;
}

export interface LightcurveSummary {
  state: "ready" | "empty";
  targets: number;
  processed: number;
  not_processed: number;
  pending: number;
  gold_planets: { targets: number; recovered: number; recovered_exact: number };
  gold_false_positives: { targets: number; with_signal: number };
  discovery: { targets: number; with_signal: number };
  by_cohort: Record<LightcurveCohort, LightcurveCohortSummary>;
  last_run_at: string | null;
  data_vintage: string | null;
  run_attempts: number;
  median_runtime_s: number | null;
  lightcurve_files: number;
  lightcurve_stars: number;
  last_fetch_at: string | null;
  rules: { period_tolerance: number; snr_min: number; statement: string };
  verdicts: Record<string, string>;
}

export interface LightcurveRow {
  target_id: number;
  candidate_id: number;
  name: string;
  host: string;
  tic_id: string;
  toi: string | null;
  cohort: LightcurveCohort;
  stratum: string | null;
  tfopwg_disp: string | null;
  canonical_disp: string | null;
  known_period_days: number | null;
  known_depth_ppm: number | null;
  tmag: number | null;
  run_status: string | null;
  n_sectors: number | null;
  baseline_days: number | null;
  runtime_s: number | null;
  data_vintage: string | null;
  finished_at: string | null;
  verdict: string;
  match: number | null;
  phase_offset: number | null;
  reason: string | null;
  best: LightcurveDetection | null;
  single_event: LightcurveDetection | null;
}

export interface LightcurveResults {
  rows: LightcurveRow[];
  total: number;
  limit: number;
  offset: number;
  sort: string;
  cohort: LightcurveCohort | null;
}
