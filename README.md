# ExoDossier

**The evidence-synthesis layer for exoplanet discovery: a provenance-tracked identity graph that
reconciles the NASA Exoplanet Archive and ExoFOP, which disagree about the same stars and planets,
across TIC, TOI, CTOI and KOI identifiers, with Gaia DR3, HD and HIP names attached as
cross-identifiers. It feeds both candidate vetting and JWST/HWO target re-ranking.**

Everyone treats exoplanet catalogs as physics. This project treats them as a master-data problem.
The same star is a TIC number, a TOI, a CTOI, a KOI, an EPIC id, a Gaia DR3 source, an HD name — and
the catalogs *disagree* about its parameters and even about whether its candidate is a planet at all.
ExoDossier builds the crosswalk with **per-attribute provenance** (`source_assertion` for period,
radius, teff, disposition, ...), a **precedence-as-config** resolver, and an **auditable merge log** —
then exposes the disagreement as a product.

**One provenance graph, two products.** It is the same entity-resolution engine as the satellite
identity graph [Orbital Economy Intelligence](../space) — *same engine, different sky.* One reconciles
who owns which satellite across catalogs that disagree; this one reconciles which star hosts which
planet across catalogs that disagree.

## The verified-novel angle

Statistical vetting of transit candidates is crowded (ExoMiner, LEO-Vetter, RAVEN — non-LLM
classifiers). What does **not** exist is the *evidence-synthesis* layer: an open, provenance-tracked
reconciliation of the catalogs, and cited vetting dossiers built on top of it. Host-star cross-ID is a
known-hard problem, per-publication parameters genuinely conflict, and habitable-zone membership can
flip depending on which source you trust (Kane 2014) — yet nobody publishes the rank-order churn as a
function of provenance. That execution gap is the opening. *We never claim to "confirm" planets — RV
telescope time is the field's real bottleneck; our contribution is a better evidence layer and smarter
follow-up prioritization.*

## Wave 1 — the conflict report (built)

From one polite pull each of ExoFOP (TOI/CTOI) and the NASA Exoplanet Archive TAP (ps, pscomppars,
TOI, KOI cumulative):

- **20,341 stars** and **23,031 candidates** resolved, with **76,534 crosswalk identifiers** and
  **684,210 source assertions** — every merge audited in `merge_log` (no silent merges).
- **3,274 candidates** carry **conflicting dispositions** across sources; **3** are the dramatic kind
  — one catalog calls it a FALSE POSITIVE while another calls it CONFIRMED (e.g. *Kepler-1517 b*,
  *TOI-1836 c*).
- **3,614 candidates** disagree on planet radius by >10% across sources — exactly where
  rocky-vs-sub-Neptune classification flips as Gaia parallax revisions propagate into stellar (then
  planetary) radii.

Regenerate it with `make report` → [`docs/reports/conflict_report.md`](docs/reports/conflict_report.md).
*Nobody agrees on a planet.*

## Status

**Wave 2 in progress** — the light-curve pipeline (MAST / `lightkurve` download for a
long-period / single-transit target slice, detrend, multi-sector stitch, independent BLS/TLS transit
recovery, TRICERATOPS false-positive scenarios), with Parquet columnar storage. Later waves:
AI-orchestrated cited dossiers graded against TFOPWG dispositions (gold program), then the
dossier tools (`candidate_dossier`, `rerank_targets`) on the MCP server that already serves
`resolve_target`, `target_conflicts`, `search_targets`, `list_conflicts` and `catalog_stats`. See [`docs/SPEC.md`](docs/SPEC.md) for the full roadmap.

The pipeline's recovery results are on the site at `/lightcurves`, read from
`GET /api/lightcurves/summary`, `GET /api/lightcurves/results?limit&offset&sort&cohort` and
`GET /api/lightcurves/target/{candidate_id}` (spec:
[`docs/specs/lightcurves-wave2.md`](docs/specs/lightcurves-wave2.md)).

## The site and the API

A read-only FastAPI service (`api/`, every query parameterized and LIMIT-bounded) over the graph,
and a Vite + React + TypeScript SPA (`web/`) served from the same process, sharing one
instrument-style design with the satellite terminal (dark plate, Fraunces headings, mono data).
Live at <https://exo.vibcreates.com>.

- **Overview (`/`)** — what changed across the retained archive snapshots: the confirmed list's
  growth, what the new planets look like and who found them, TESS follow-up verdicts, the
  candidate queue, the conflict corpus and the dramatic cases, then the graph under the hood.
- **Search (`/search`)** — resolve any star or candidate by TIC, TOI, CTOI, KOI, planet name or
  host name.
- **Target (`/target/:id`)** — one candidate and its host: the identifier crosswalk, what every
  source asserts about each attribute (the who-says-what table), and where they disagree.
- **Conflicts (`/conflicts`)** — the browsable corpus: disposition, planet-radius and host Teff
  disagreements, every row linking to the target.
- **Light curves (`/lightcurves`)** — the pipeline's transit-recovery results, graded against the
  catalog period.
- **Follow-up (`/followup`)** — for a candidate you want to confirm from the ground, which tracked
  satellites cross its line of sight during your observing window (joins the hosts to the
  satellite graph; illustrative, not operational).
- **About (`/about`)** — what the conflicts mean, how they are computed, and whose data it is.

Endpoints: `/api/health`, `/api/stats`, `/api/stories`, `/api/search?q=`, `/api/target/{id}`,
`/api/conflicts?type=disposition|radius|teff&limit&offset`, `/api/attribution`,
`/api/lightcurves/*`, `/api/twoskies/*`. The MCP server in [`mcp/`](mcp/README.md) exposes the
same graph to agents as five read-only tools.

CI (`.github/workflows/ci.yml`) runs ruff and the network-free unit tests, a Postgres 16 job that
migrates the schema and runs the full suite (tests marked `graph` need a built catalog and skip on
the empty database), and the web build.

## Quickstart

```bash
make venv        # create the Python venv + install deps
cp .env.example .env   # DATABASE_URL points at a local `exo` db on the oei-db TimescaleDB container (port 5433)
make migrate     # apply db/migrations
make ingest      # polite, ledgered pulls (NASA Archive TAP + ExoFOP TOI/CTOI)
make build       # build the identity graph (crosswalk + assertions + merge log)
make report      # regenerate the conflict report
make test        # pytest (-W error), then `make lint`
```

## Data sources and attribution

The public repo ships **code, schema, and derived aggregates/reports only — never raw catalog
dumps.** `data/` is gitignored. Each source keeps its own terms:

- **NASA Exoplanet Archive** (NExScI, IPAC/Caltech) — Planetary Systems (`ps`, `pscomppars`), TOI, and
  KOI cumulative tables via the IVOA TAP service. **U.S. Government work / public domain**; please cite
  the archive and its dataset DOI. <https://exoplanetarchive.ipac.caltech.edu/>
- **ExoFOP-TESS** (the TESS Follow-up Observing Program working group archive) — TOI and CTOI lists.
  Attribution required; cite ExoFOP-TESS and the relevant TFOPWG. <https://exofop.ipac.caltech.edu/tess/>

## Design notes

- 2026-10-16 — Type: Fraunces display layer over mono body, shared with orbital (decided 2026-10-16).
  Fraunces (SIL OFL 1.1) is vendored via `@fontsource-variable/fraunces` and bundled; it sets page
  titles, panel titles and hero stat figures only, while data, labels and tables stay mono.

## License

Copyright (c) 2026 Vibhav Gupta. Licensed under the **MIT License** — see [`LICENSE`](LICENSE).
MIT is deliberate: the goal here is scientific adoption, collaboration, and credit
(contribution + co-authorship), not commercialization. See [`LICENSING.md`](LICENSING.md).
