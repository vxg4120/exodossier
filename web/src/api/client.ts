/* =============================================================================
   API client. Real mode: fetch JSON from the FastAPI service under /api (dev-proxied to :8700, or
   same-origin when the SPA is served from web/dist). Mock mode (VITE_API_MOCK=1): resolve every
   request from the JSON fixtures in ./fixtures — no network — so the catalog is fully explorable
   before the API is up. The mock router mirrors the API's query semantics (substring search,
   limit/offset pagination + total, id/name lookup) so views exercise the same code paths.
   ============================================================================= */

import type {
  Attribution,
  ConflictsResponse,
  ConflictType,
  LightcurveCohort,
  LightcurveResults,
  LightcurveSummary,
  SearchResponse,
  SearchResult,
  Stats,
  Stories,
  TargetDetail,
} from "./types";

import statsFixture from "./fixtures/stats.json";
import searchFixture from "./fixtures/search.json";
import targetsFixture from "./fixtures/targets.json";
import conflictsDisposition from "./fixtures/conflicts_disposition.json";
import conflictsRadius from "./fixtures/conflicts_radius.json";
import conflictsTeff from "./fixtures/conflicts_teff.json";
import attributionFixture from "./fixtures/attribution.json";
import storiesFixture from "./fixtures/stories.json";
import lightcurvesFixture from "./fixtures/lightcurves.json";

export const MOCK = import.meta.env.VITE_API_MOCK === "1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/* ---- real transport ------------------------------------------------------- */
/** Upper bound on any GET, as on orbital. A request the API never answers (a cold cache warming
    an aggregate, a dropped connection) would otherwise leave the view on its loading state with
    no way out; past this the caller's Async state shows the error with a Retry control. */
export const REQUEST_TIMEOUT_MS = 30_000;

/** fetch with the timeout, the JSON accept header and a readable failure for every outcome:
    a non-2xx status, a timeout, and a body that is not JSON (a proxy's HTML error page served
    with a 200) each name the path they failed on. */
export async function fetchJson<T>(url: string, path: string): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(url, {
      headers: { accept: "application/json" },
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText} for ${path}`;
      try {
        const j = (await res.json()) as { detail?: string };
        if (typeof j?.detail === "string") detail = `${res.status} ${j.detail} for ${path}`;
      } catch {
        /* non-JSON error body: keep the status line */
      }
      throw new ApiError(detail, res.status);
    }
    try {
      return (await res.json()) as T;
    } catch {
      throw new ApiError(`Not JSON from the API for ${path}`, res.status);
    }
  } catch (err) {
    if (controller.signal.aborted) {
      throw new ApiError(
        `No answer from the API within ${REQUEST_TIMEOUT_MS / 1000}s for ${path}`,
        0,
      );
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

async function realGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const qs = params
    ? "?" +
      new URLSearchParams(Object.entries(params).map(([k, v]) => [k, String(v)])).toString()
    : "";
  return fetchJson<T>(`/api${path}${qs}`, path);
}

/* ---- mock transport ------------------------------------------------------- */
const MOCK_LATENCY_MS = 130;
export const delay = <T>(value: T): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), MOCK_LATENCY_MS));

const searchPool = (searchFixture as { results: SearchResult[] }).results;
const targetData = targetsFixture as unknown as {
  targets: Record<string, TargetDetail>;
  aliases: Record<string, number>;
};
const conflictFixtures: Record<ConflictType, ConflictsResponse> = {
  disposition: conflictsDisposition as ConflictsResponse,
  radius: conflictsRadius as ConflictsResponse,
  teff: conflictsTeff as ConflictsResponse,
};

function mockSearch(q: string): SearchResponse {
  const query = q.trim().toLowerCase();
  if (!query) return { query: q, count: 0, results: [] };
  const hits = searchPool
    .filter(
      (r) =>
        r.target.toLowerCase().includes(query) ||
        r.host.toLowerCase().includes(query) ||
        (r.tic_id ?? "").toLowerCase().includes(query) ||
        String(r.candidate_id) === query,
    )
    .sort((a, b) => {
      const ap = a.target.toLowerCase().startsWith(query) ? 0 : 1;
      const bp = b.target.toLowerCase().startsWith(query) ? 0 : 1;
      return ap - bp || a.target.localeCompare(b.target);
    })
    .slice(0, 50);
  return { query: q, count: hits.length, results: hits };
}

function mockTarget(id: string): TargetDetail {
  const byId = targetData.targets[id];
  if (byId) return byId;
  const cid = targetData.aliases[id.toLowerCase()];
  if (cid !== undefined) {
    const resolved = targetData.targets[String(cid)];
    if (resolved) return resolved;
  }
  throw new ApiError(`No target resolves for ${id} (mock)`, 404);
}

function mockConflicts(type: ConflictType, limit: number, offset: number): ConflictsResponse {
  const f = conflictFixtures[type];
  return { ...f, rows: f.rows.slice(offset, offset + limit), limit, offset };
}

/* ---- public API ----------------------------------------------------------- */
// The topbar telemetry and the Overview both ask for the stats on the same first render; the
// second caller joins the first caller's in-flight request instead of opening a second one. The
// promise is dropped once it settles, so a later mount or a reload still fetches fresh numbers.
let statsInFlight: Promise<Stats> | null = null;

export function getStats(): Promise<Stats> {
  if (!statsInFlight) {
    const request = MOCK ? delay(statsFixture as Stats) : realGet<Stats>("/stats");
    statsInFlight = request.finally(() => {
      statsInFlight = null;
    });
  }
  return statsInFlight;
}

export function searchTargets(q: string): Promise<SearchResponse> {
  if (MOCK) return delay(mockSearch(q));
  return realGet<SearchResponse>("/search", { q });
}

export function getTarget(id: string): Promise<TargetDetail> {
  if (MOCK) {
    try {
      return delay(mockTarget(id));
    } catch (e) {
      return Promise.reject(e);
    }
  }
  return realGet<TargetDetail>(`/target/${encodeURIComponent(id)}`);
}

export function getConflicts(
  type: ConflictType,
  limit: number,
  offset: number,
): Promise<ConflictsResponse> {
  if (MOCK) return delay(mockConflicts(type, limit, offset));
  return realGet<ConflictsResponse>("/conflicts", { type, limit, offset });
}

export function getAttribution(): Promise<Attribution> {
  if (MOCK) return delay(attributionFixture as Attribution);
  return realGet<Attribution>("/attribution");
}

/* Mock mode replays a small pipeline output (fixtures/lightcurves.json: twenty graded TOIs across
   the three cohorts, generated from the mock target map so every row's link resolves), paged and
   filtered the way the API does it. */
const lightcurveData = lightcurvesFixture as unknown as {
  summary: LightcurveSummary;
  rows: LightcurveResults["rows"];
};

export function getLightcurveSummary(): Promise<LightcurveSummary> {
  if (MOCK) return delay(lightcurveData.summary);
  return realGet<LightcurveSummary>("/lightcurves/summary");
}

export function getLightcurveResults(
  limit: number,
  offset: number,
  cohort: LightcurveCohort | null,
): Promise<LightcurveResults> {
  if (MOCK) {
    const all = cohort
      ? lightcurveData.rows.filter((r) => r.cohort === cohort)
      : lightcurveData.rows;
    return delay({
      rows: all.slice(offset, offset + limit),
      total: all.length,
      limit,
      offset,
      sort: "cohort",
      cohort,
    });
  }
  const params: Record<string, string | number> = { limit, offset };
  if (cohort) params.cohort = cohort;
  return realGet<LightcurveResults>("/lightcurves/results", params);
}

export function getStories(): Promise<Stories> {
  if (MOCK) return delay(storiesFixture as Stories);
  return realGet<Stories>("/stories");
}
