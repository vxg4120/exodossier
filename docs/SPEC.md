# ExoDossier — Build Spec v1

**One-line pitch:** The evidence-synthesis layer for exoplanet discovery: AI-orchestrated, cited,
provenance-tracked vetting dossiers for transit candidates, built on an identity graph that
reconciles the catalogs (TIC/TOI/CTOI/KOI/EPIC/Gaia) which disagree about the same stars and
planets — feeding both candidate vetting and JWST/HWO target re-ranking. One provenance graph,
two products. Same engine as the satellite identity graph; different sky.

**Optimization target:** novelty + real contribution to the field + coolness. NOT revenue.
**Grounding research (read first):** `docs/research-exoplanet-hunter.md` (the project thesis,
verified-unoccupied novelty check, credit pathways) and `docs/research-exoplanets.md` (catalog
disagreement landscape, Kane HZ-flip, re-ranking angle).

## The verified opening (mid-2026)

- No LLM/agent-based candidate-vetting or cited-dossier system exists for exoplanets. Statistical
  vetting is crowded (ExoMiner++, LEO-Vetter, RAVEN — non-LLM classifiers); the *evidence
  synthesis* layer is empty.
- TESS is in Extended Mission 3 (through Sept 2028), ~Sector 106 now, all data free (MAST,
  `lightkurve`). The single-transit/long-period slice is the pipelines' documented blind spot and
  proven outsider territory (Planet Hunters TESS, Visual Survey Group credited discoveries).
- The catalogs genuinely disagree (host-star cross-ID tangle; per-publication parameter conflicts;
  HZ membership can flip on which source you trust — Kane 2014). Nobody maintains an open
  provenance-tracked reconciliation.
- Honest framing: RV telescope time is the field's true confirmation bottleneck and is not
  software-fixable. Our contribution = better evidence layer + smarter follow-up prioritization.
  We never claim to "confirm" planets.
- Credit pathway: CTOI→TOI promotion (NOTE: ExoFOP uploads paused since 2026-03-31 — RNAAS
  72-hour research notes are the interim), then offer the tool to PHT / VSG / TFOP for
  collaboration/co-authorship.

## Architecture (mirrors the satellite platform — reuse its patterns, not its code)

```
SURFACE:   dossier site + MCP server (agent-native vetting layer)
PRODUCTS:  vetting dossiers  |  habitability/observability re-ranking
ANALYSIS:  light-curve pipeline (lightkurve: detrend, stitch sectors, change-point/transit
           recovery, TRICERATOPS FP scenarios)
IDENTITY:  star + candidate entity graph — crosswalk (TIC/TOI/CTOI/KOI/EPIC/Gaia DR3/HD/HIP),
           per-attribute source_assertion (period, radius, teff, logg, parallax, disposition...),
           precedence-as-config, merge audit log
RAW:       per-source landing + ingest_run politeness ledger (NASA Exoplanet Archive TAP,
           ExoFOP TOI/CTOI lists, KOI cumulative, Gaia xmatch, MAST light curves)
```

**Stack:** same as satellite platform — Postgres (new `exo` database on the existing oei-db
TimescaleDB container, port 5433), Python venv (`lightkurve`, `astropy`, `transitleastsquares`,
`triceratops` as needed — verify Python-version compatibility; fall back from 3.14 to 3.12/3.13
venv if wheels are missing), pytest with `-W error`, ruff, provenance/ledger patterns copied
conceptually from `/Users/vgupta/Development/repos/space` (readable reference).

**The gold-standard program is not optional — it IS the credibility:** every dossier
recommendation is graded against known TFOPWG dispositions (confirmed planets vs known false
positives) exactly like the satellite gold program; published accuracy number.

## Waves

- **Wave 1 (foundation + identity graph):** repo scaffold, db, migrations, catalog ingestion
  (TOI, CTOI, KOI cumulative, `ps`/`pscomppars` from the Archive TAP), cross-match/entity-resolve
  hosts and candidates with provenance, conflict report v0 (where do TOI/Archive/exoplanet.eu
  disagree on the same object — counts + examples).
- **Wave 2 (light-curve pipeline):** MAST/lightkurve download for a target slice (long-period/
  single-transit APCs + a gold set of known planets/FPs), detrend, multi-sector stitch,
  independent transit recovery (BLS/TLS + the satellite-style change-point lens), TRICERATOPS
  scenario probabilities. Cheap columnar storage for light curves (Parquet).
- **Wave 3 (dossiers):** AI-orchestrated research dossiers per candidate — light-curve evidence,
  catalog cross-checks, Gaia RUWE/neighbors, literature search, cited sources, recommended
  disposition + confidence — human-adjudicated; gold-graded vs TFOPWG labels.
- **Wave 4 (products):** public dossier site, MCP server (`resolve_target`, `candidate_dossier`,
  `conflicts_for_target`, `rerank_targets`), the JWST/HWO re-ranking report (rank-churn under
  parameter provenance), RNAAS/CTOI submissions.

## Success (3 months)

Live dossier site with a published gold-graded accuracy number; ≥1 submitted CTOI or RNAAS note;
≥1 named researcher/collaboration using the tool; the re-ranking report showing real rank-churn
on JWST/HWO target lists.
