# ExoDossier

**The evidence-synthesis layer for exoplanet discovery: a provenance-tracked identity graph that
reconciles the catalogs (TIC / TOI / CTOI / KOI / EPIC / Gaia) which disagree about the same stars
and planets — feeding both candidate vetting and JWST/HWO target re-ranking.**

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
AI-orchestrated cited dossiers graded against TFOPWG dispositions (gold program), then a public
dossier site and MCP server (`resolve_target`, `candidate_dossier`, `conflicts_for_target`,
`rerank_targets`). See [`docs/SPEC.md`](docs/SPEC.md) for the full roadmap.

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

## License

Copyright (c) 2026 Vibhav Gupta. Licensed under the **MIT License** — see [`LICENSE`](LICENSE).
MIT is deliberate: the goal here is scientific adoption, collaboration, and credit
(contribution + co-authorship), not commercialization. See [`LICENSING.md`](LICENSING.md).
