/* Response types — mirror api/queries.py exactly. */

export interface IngestRun {
  source: string;
  endpoint: string;
  status: string | null;
  rows_ingested: number | null;
  bytes_downloaded: number | null;
  finished_at: string | null;
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
