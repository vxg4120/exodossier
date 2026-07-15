# ExoDossier — Domain & Speaking Study Guide

Your single reference for getting fluent in the exoplanet world fast, understanding exactly what is
done today and by whom, knowing the limits honestly, and articulating what **ExoDossier** does that
is genuinely new. Read it until the vocabulary is yours. Companion docs go deeper:
`SPEC.md` (what we're building), `research-exoplanet-hunter.md` (the verified landscape + novelty
check), `research-exoplanets.md` (catalog disagreements + the re-ranking angle).

Every load-bearing name, date, and mission status below was web-verified on **2026-07-15**; key
claims carry an inline source. Anything I could not pin is tagged `[unverified]`.

---

## How to use this guide

Four modes, four audiences:

- **Speak** (Part I): the pitch, the bridge from your satellite work, the positioning — for
  interviews, cold emails, DMs to astronomers.
- **Understand the science** (Parts II–III): how planets are found and what data exists — the part
  that makes you sound like you belong instead of like a tourist.
- **Understand the field** (Parts IV–VI): who does what, where the identity mess lives (our home
  turf), and the honest limits.
- **Defend** (Parts VII–VIII): the novelty claim and the hard questions, with strong answers.
- **Reference** (Part IX): glossary + flashcards for spaced review.

**A 5-day study plan.**
- **Day 1 — Speak.** Part I until you can deliver the one-paragraph story and all three elevator
  pitches cold, including the "one engine, two skies" bridge.
- **Day 2 — The physics.** Part II, especially the transit deep-dive and the false-positive
  taxonomy. If you can explain *why* an odd/even depth difference means "eclipsing binary, not
  planet," you sound like an insider.
- **Day 3 — The map.** Parts III–IV: missions, data you can actually download, and the who-does-what
  of the discovery pipeline. Memorize the players and the acronyms.
- **Day 4 — Home turf + limits.** Parts V–VI: the identity/provenance mess and the honest map of
  limitations. This is where your background is the sharpest edge — spend real time here.
- **Day 5 — Defend.** Parts VII–VIII out loud: the novelty statement and the hard questions. Then
  reread Part I; it will mean more.

---

# PART I — THE STORY

## The one-paragraph story (memorize this)

> Exoplanet science has, in fifteen years, become an industrial pipeline. Space telescopes stare at
> millions of stars, software finds the tiny brightness dips that mean a planet crossed in front,
> and machine-learning classifiers score each candidate for how likely it is to be real. That part
> works. What *doesn't* work is everything downstream of the score: the same star wears a dozen
> different catalog IDs that don't cleanly map to each other, the "authoritative" archives disagree
> with each other about how many confirmed planets even exist, and the *case* for or against any
> given candidate — the light-curve evidence, the imaging, the spectroscopy, the prior literature,
> the follow-up notes — lives scattered across a half-dozen systems and gets reassembled by hand,
> every time, by whoever has the patience. **ExoDossier builds the missing evidence-synthesis layer:
> an identity graph that reconciles the disagreeing catalogs with per-attribute provenance, feeding
> AI-orchestrated, cited, gold-graded vetting dossiers per candidate — and, from the same graph,
> a re-ranking of the JWST/HWO target lists that shows which targets change priority depending on
> which catalog you trust.** We don't confirm planets — that needs telescope time we don't have. We
> make the evidence and the follow-up decisions better.

That is the whole thing: **the pipeline finds and scores candidates; nobody builds the cased,
provenance-tracked dossier. We do.**

## The "one engine, two skies" bridge (your unfair advantage)

You are not arriving as a random outsider — you built this engine once, pointed at a different sky.
The satellite project is a provenance-tracked entity-resolution graph over the disagreeing orbital
catalogs (SATCAT vs Jonathan McDowell's GCAT vs the UCS database), with per-attribute
`source_assertion`, an auditable `merge_log`, temporal ownership, and a human-adjudicated gold-standard
accuracy program. The exoplanet problem is **structurally the same shape**:

| Satellite sky | Exoplanet sky |
|---|---|
| One object = a NORAD number + COSPAR ID + commercial name + ITU filing + stale owner code | One star = TIC + TOI + KOI + KIC + EPIC + Gaia DR3 + HD + HIP + 2MASS designations |
| SATCAT vs GCAT vs UCS disagree on decay date, owner, status | NASA Archive vs exoplanet.eu vs the discovery paper disagree on radius, mass, disposition |
| "Disagreements are data, not errors" | Same motto — the conflict *is* the product |
| Behavioral oracle: physics reveals true status when the catalog is stale | Light-curve recovery: independently re-derive the transit when the catalogs conflict |
| Gold program graded vs adjudicated ground truth | Gold program graded vs known **TFOPWG dispositions** (confirmed planets vs known false positives) |

So the pitch is literally: **"Same engine, different sky. One provenance graph, two products."** The
identity/provenance/gold-standard machinery ports directly; only the domain vocabulary changes.

## The CannMenus lineage (the deeper root)

Before satellites there was CannMenus: entity resolution over messy retail cannabis data — SKU
normalization with no universal identifier, matching the same product across thousands of dispensary
menus, where the business was never the matcher (anyone can write a matcher) but the **accuracy
program** that took matches from ~78% to ~96% through evaluation, curation, and time. That's the
through-line of your whole career: **the value was never the code that proposes a match — it was the
discipline that proves the match is right.** Exoplanets is the third instance of the same craft.

## Three elevator pitches (pick by who's across the table)

**To an astronomer** (lead with domain respect and the honest boundary):
> "The statistical-vetting layer is crowded and closing fast — ExoMiner++, LEO-Vetter, RAVEN all
> give you a false-positive *score*. What none of them gives you is the assembled *case*: the DV
> diagnostics, the ExoFOP dispositions, the cross-archive identity, the imaging and spectroscopy
> notes, and the prior literature, pulled into one cited, provenance-tracked dossier per candidate,
> graded against known TFOPWG labels so it has a published accuracy number. I'm building that
> evidence-synthesis layer, focused first on the long-period and single-transit candidates the
> pipelines discard by design. I don't confirm planets and I don't own a telescope — I make the
> vetting case and the follow-up prioritization better."

**To a tech / data-platform person** (lead with the engineering):
> "It's a master-data problem in an astronomy costume. One star carries a dozen catalog IDs that
> don't cleanly cross-map, and the authoritative archives disagree about the same planet's radius by
> tens of percent. I built an entity-resolution graph that reconciles them with per-attribute
> provenance — every value keeps its source and its conflicts instead of being flattened — then run
> AI-orchestrated, cited dossiers on top, with a gold-standard accuracy program. It's MCP-native, so
> an agent can ask 'give me the vetting case for TOI-XXXX and tell me which conclusion flips if I use
> the Gaia stellar radius instead of the discovery paper's.' Same engine I built over the satellite
> catalogs — different sky."

**To a friend** (the shortest version):
> "When a telescope thinks it's found a new planet, someone has to build the case that it's real —
> pulling a dozen scattered pieces of evidence together by hand, every time. I'm building the thing
> that assembles that case automatically, every claim cited, with a track record you can check. I'm
> not the person who confirms the planet — I'm the person who builds the file on it."

## The narrative arc (when asked to walk through it)

Tell it as three acts:

1. **The reframe.** "The field thinks its bottleneck is *finding and scoring* candidates. Half true —
   finding is open in one lane (long-period/single-transit signals the pipelines discard) and
   *scoring* is being automated hard. The un-automated layer is *evidence synthesis*: turning
   scattered evidence into a coherent, cited case. Seeing that was the whole insight."
2. **The build proves velocity.** "The data is free and laptop-scale; I can orchestrate frontier AI
   agents to build the pipeline in days. That's table stakes now — the judgment about *what* to build
   is the differentiator."
3. **The moat is what AI can't generate.** "Anyone can prompt up a dossier generator. Nobody can
   prompt up a measured accuracy number graded against real TFOPWG dispositions, or an open provenance
   graph that keeps the catalog conflicts instead of hiding them. So that's where I pointed the work."

## The evolution (the ambitious frame)

The thesis it grows into: **the open, agent-native evidence layer for the exoplanet follow-up era.**
The field is about to be flooded — Roman launches this August, PLATO next year, and the TESS candidate
pile already outruns the telescope time to confirm it. The candidates needing a *case built* explode
while the human labor to build cases by hand stays fixed — and every layer we build is a piece of that
answer: identity graph, provenance, dossier, gold program.

---

# PART II — HOW WE FIND EXOPLANETS

You don't need to be an astronomer — just enough to not get caught out and to sound like you belong.

## The five methods, one line each (and who they've found)

As of early-mid July 2026 the NASA Exoplanet Archive lists **6,319 confirmed planets**, and the
method split tells you which techniques do the work
(https://exoplanetarchive.ipac.caltech.edu/docs/counts_detail.html, 2026-07-15):

- **Transit (~4,662, the overwhelming majority).** The planet crosses in front and the star dims a
  tiny, repeating amount. Cheap (one telescope watches thousands of stars at once), gives the planet's
  *radius*, and is what Kepler and TESS do. **This is our entire world.**
- **Radial velocity (RV) (~1,195).** The planet's gravity tugs the star, Doppler-shifting its
  spectrum; gives the planet's *mass* (minimum mass). How most transiting candidates get *confirmed* —
  and the telescopes that do it are the field's true bottleneck (Part VI).
- **Direct imaging (~98).** Actually photograph the planet, blocking the star's glare. Only works for
  big, hot, young planets far from bright stars. Rare but spectacular.
- **Microlensing (~281).** A foreground star+planet magnifies a background star; the planet adds a
  blip. Finds distant, wide-orbit, and free-floating planets. **Roman** (launching 2026-08-30) will do
  this at industrial scale (https://en.wikipedia.org/wiki/Nancy_Grace_Roman_Space_Telescope, 2026-07-15).
- **Astrometry (~6 today).** Measure the star's positional wobble; barely productive yet, but **Gaia
  DR4** should deliver the first big batch of astrometric giant-planet candidates.

Take the point: **transit dominates, and everything ExoDossier touches is a transit candidate.**

## Transit deep-dive

### Light-curve anatomy

A **light curve** is a star's brightness over time. When a planet transits, you see a **U-shaped
dip**: a sloped **ingress** (planet sliding onto the disk), a rounded **bottom** (planet fully in
front), and a sloped **egress** (planet sliding off) — round-bottomed, not flat, because of limb
darkening (below). Three numbers define the geometry:

- **Period (P)** — time between successive transits = the orbital period.
- **Epoch (T₀)** — the timestamp of one transit center; P and T₀ together predict all future transits.
- **Duration (T)** — how long one transit lasts, hours typically; set by the orbital speed and the
  chord the planet cuts across the star.

### Transit depth → planet radius (the one piece of math to internalize)

The fractional dip in brightness — the **transit depth δ** — is just the ratio of the areas of the
two disks:

> **δ = (R_planet / R_star)²**, so **R_planet = R_star × √δ**

That's the whole intuition. Three things worth on the tip of your tongue:
- A **Jupiter across a Sun-like star** blocks ~1% of the light (δ ≈ 0.01) — easy.
- An **Earth across the Sun** blocks ~**84 parts per million** — why Earth-analogs are brutally hard
  and need space-grade photometric stability.
- The killer subtlety that runs straight into our home turf: **you cannot get the planet's radius
  without the star's radius.** Revise R_star and every planet's radius revises with it. When Gaia's
  parallaxes sharpened stellar radii, thousands of planet radii shifted by tens of percent — Berger et
  al. and the California-Kepler Survey re-derived the whole population, and the "radius gap" only
  appeared once the stellar radii got good (https://arxiv.org/abs/1805.00231, 2026-07-15). The physics
  *forces* the provenance problem.

### Limb darkening (one line)

A star's disk is brighter at the center than the edge, so a transit is round-bottomed and the
ingress/egress are curved — modeling this correctly is what separates a real planet shape from a
box, and it's exactly what TLS does that BLS doesn't (below).

### Detrending, systematics, and phase folding

Raw light curves are dominated by things that are *not* the planet: **instrumental systematics**
(pointing jitter, momentum-dump thruster fires, scattered light) and **stellar variability**
(starspots, pulsations, flares). Before searching for a ~100-ppm dip you must **detrend** — flatten
these slow wiggles with splines, Savitzky-Golay filters, Gaussian processes, or cotrending basis
vectors — without flattening the transit itself. Then, because one transit is buried in noise, you
**phase-fold**: chop the curve into period-length segments and stack them so N transits add coherently
while the noise averages down. A dip invisible in one orbit becomes obvious folded on the right period.

### BLS and TLS (the two search algorithms — name-drop both correctly)

You don't know the period in advance, so you scan every plausible period for a repeating dip:

- **BLS — Box Least Squares** (Kovács, Zucker & Mazeh 2002, A&A 391, 369): models a transit as a
  periodic upside-down top-hat "box" and finds the best-fit period/duration/depth/epoch. The workhorse
  for two decades; what `astropy` ships (https://docs.astropy.org/en/stable/timeseries/bls.html, 2026-07-15).
- **TLS — Transit Least Squares** (Michael Hippke & René Heller 2019, A&A 623, A39): same idea but fits
  a *realistic* limb-darkened shape with curved ingress/egress instead of a box, buying ~10% higher
  detection efficiency for small planets at higher compute cost (https://github.com/hippke/tls,
  2026-07-15). The one we run for independent recovery.

### SNR, SDE, and the detection threshold

A search returns a **strength**, not "planet / no planet." **SNR / MES (Multiple Event Statistic)** is
the folded transit's signal-to-noise; SPOC promotes a signal to a TCE only above **MES ≈ 7.1σ** (set
to control false alarms across a huge search). **SDE (Signal Detection Efficiency)** is TLS's peak
periodogram significance — higher = more convincing period.

### Why single-transits are hard (and why they're our lane)

If a planet's period exceeds the observing window, you may catch **only one transit** — a
**monotransit** — giving depth and duration but **no period**. SPOC, by design, requires *multiple*
events above threshold, so it **discards lone transits** to control false alarms. That means
long-period and single-transit planets **fall straight through the automated pipeline**, and
recovering them (stitching multiple TESS sectors to hunt for a second transit, or constraining the
period from the transit shape) is proven outsider territory. It's *also* exactly the population that
needs the most evidence synthesis — so the long-period hunt and the dossier engine are one project
from two ends.

### The false-positive taxonomy (learn each tell-tale signature)

Most transit-shaped signals are **not** planets. Knowing the mimics — and the diagnostic that unmasks
each — is the single most "insider" thing you can rattle off. This is the DV report and the whole
vetting stack:

| Mimic | What it is | The tell-tale signature |
|---|---|---|
| **Eclipsing binary (EB)** | Two stars orbiting each other; one eclipses the other | **Secondary eclipse** (a second dip half a period later); **odd/even depth difference** (alternate eclipses differ → it's an EB at *twice* your period); **V-shaped** (grazing) rather than U-shaped; **too deep** (stars block far more than planets); ellipsoidal variation |
| **Background EB (BEB)** | A faint eclipsing binary *behind/near* the target, its light blended into the aperture | **Centroid offset** — the flux dip's center-of-light shifts *off the target star* during transit; depth changes as you change the photometric aperture |
| **Nearby EB (NEB)** | A resolved-ish neighboring star that is an EB, bleeding into the aperture | **Difference-image / per-pixel photometry** localizes the dip to a *different pixel* than the target — this is precisely what TFOP SG1 seeing-limited photometry goes and checks on the sky |
| **Instrumental systematics** | Momentum dumps, scattered light, cosmic-ray hits, detector rolls | Correlated with **spacecraft events**, not with orbital phase; often single-cadence or non-repeating; vanishes with better detrending |
| **Stellar variability** | Starspots, pulsations, flares | **Quasi-periodic**, not sharply U-shaped; depth/duration don't obey the transit geometry; changes over time as spots evolve |

The three classic DV diagnostics map straight onto this table: **odd/even depth test** (catches EBs
at 2×P), **secondary-eclipse search** (catches EBs), and **difference-image centroiding** (catches
BEBs/NEBs by localizing the transit source). If you can say "we ran the odd/even test and the depths
match, so it's not a half-period EB; the centroid stays on target, so it's not a blend," you are
speaking the language.

---

# PART III — THE MISSIONS & DATA

## Kepler / K2 (the legacy)

**Kepler** (2009–2013) stared at one patch of sky and delivered the field's statistical backbone —
**~2,784 confirmed planets**, the largest yield of any mission. Its candidates are **KOIs** (Kepler
Objects of Interest), its stars **KIC** (Kepler Input Catalog) IDs. After its reaction wheels failed
it became **K2**, surveying the ecliptic (~549 confirmed); K2 stars carry **EPIC** (Ecliptic Plane
Input Catalog) IDs. All public on MAST via `lightkurve`. Kepler is *done* producing data but alive as
a labeled training/gold set — its dispositions are ground truth.

## TESS (the operating workhorse — know its status cold)

**TESS** (Transiting Exoplanet Survey Satellite, launched 2018) is the all-sky successor and the
source of essentially all *active* candidates. Status as of 2026-07-15:

- **Alive and healthy, in its third extended mission (EM3, ~Sept 2025 – Sept 2028)**, currently in
  **Cycle 8**, observing **Sector 106** (2026-07-11 → 2026-08-09)
  (https://heasarc.gsfc.nasa.gov/docs/tess/sector.html, 2026-07-15). Each sector ~27 days; new sectors
  keep coming; no fuel/health alarms.
- **The data-product asymmetry is the whole opportunity.** SPOC (the Science Processing Operations
  Center at NASA Ames, manager/science lead **Jon Jenkins**, the Kepler pipeline's direct descendant;
  https://www.nasa.gov/ames/nisv-podcast-ep91-jon-jenkins, 2026-07-15) makes **2-minute** light curves
  for tens of thousands of pre-selected stars and **20-second** for ≤1,000. Everyone else — *millions*
  of stars — appears only in the **Full-Frame Images (FFIs)**, now **200-second cadence**, turned into
  light curves by MIT's **Quick Look Pipeline (QLP)**. So SPOC serves tens of thousands deeply; QLP/FFI
  serves millions shallowly. **The under-served FFI population, and its long-period signals, is where an
  outsider works.**
- **Access is free and laptop-scale.** Pull anything from **MAST** (Mikulski Archive for Space
  Telescopes, STScI) with the open-source Python package **`lightkurve`** — search, download, detrend,
  fold, search. No credentials, no cost.

## Gaia (the stellar-parameter spine — don't skip this)

**Gaia** is ESA's astrometry mission — upstream of *everything* in transit science even though it
finds few planets directly. The chain that matters:

> **Gaia parallax → distance → stellar luminosity + radius → (via δ = (R_p/R_star)²) planet radius.**

Get the star wrong and you get the planet wrong. Gaia is why the whole population's radii got
re-derived (Part II). Two Gaia signals you'll cite constantly in dossiers:
- **RUWE (Renormalised Unit Weight Error)** — a goodness-of-fit of the single-star astrometric
  model. **RUWE > ~1.4 is a classic flag for an unresolved binary** (Lindegren 2018) — which is a
  false-positive red flag for a "planet" candidate (https://www.aanda.org/articles/aa/full_html/2024/08/aa50172-24/aa50172-24.html, 2026-07-15).
- **Neighbors / contamination** — Gaia's exquisite catalog of nearby sources tells you whether a
  faint background/nearby star could be diluting the transit or hosting the real eclipse (the
  BEB/NEB scenarios). This feeds TRICERATOPS directly.

Gaia DR3 is current; **Gaia DR4** (expected ~end of 2026, `[unverified]` exact month) adds epoch
photometry and the first big astrometric planet-candidate batch. Live wrinkle: the TESS Input Catalog
is still largely on **Gaia DR2**, so the DR2→DR3 crossmatch is an active 2026 problem — real
identity-graph work sitting unglamorously in everyone's way.

## Upcoming (know the names and rough dates)

- **Roman** — launch **moved up to 2026-08-30**, to L2; a microlensing survey expected to find
  **thousands** of exoplanets (plus a huge transiting census) — a flood arriving imminently.
- **PLATO** (ESA) — spacecraft complete, launching **~early 2027** to L2; 26 cameras aimed at
  Earth-analogs around bright Sun-like stars. No science data yet.
- **HWO** (Habitable Worlds Observatory) — NASA's future flagship (2040s), a ~6 m telescope to image
  and take spectra of ~25 potentially-Earth-like planets. Doesn't exist yet, but **its target list is
  being argued over right now** — a provenance-sensitive argument that is our second product (Part V).

**Bottom line for an individual:** all of TESS (2-min, 20-s, FFI), all of Kepler/K2, the whole ExoFOP
corpus and DV reports, and Gaia — **all free, license-clean, laptop-scale.** Data access is not the
constraint; what you *do* with it is.

---

# PART IV — THE DISCOVERY PIPELINE TODAY (who does what)

Memorize this flow and the players on it — knowing the who-does-what turns "I did a project" into "I
understand this field."

## The main line (mission → candidate → confirmed planet)

1. **Detection.** **SPOC** (NASA Ames, Jon Jenkins) processes the 2-min/20-s targets; **QLP** (MIT)
   the FFIs. A signal above **MES ≈ 7.1σ** becomes a **Threshold Crossing Event (TCE)**; the **Data
   Validation (DV)** module then runs the diagnostics — odd/even depth, secondary-eclipse search,
   difference-image centroiding, "ghost" test, bootstrap significance — and emits a **DV report**.
2. **TOI designation.** Human vetters at the **MIT TESS Science Office (TSO)** group-vet the TCEs and
   promote good ones to **TOIs — TESS Objects of Interest** — the official candidate list (~**8,064**
   as of 2026-07-15).
3. **Automated vetting / statistical validation.** A crowded, fast-moving layer of ML classifiers and
   statistical tools that score candidates:
   - **ExoMiner / ExoMiner++** — NASA Ames' explainable deep-learning classifier (lead **Hamed
     Valizadegan**); validated **301 new Kepler planets** (2021), transferred to 2-min TESS as
     ExoMiner++ (*AJ*, 2025-10-27), extended to FFIs in ExoMiner++ 2.0 (Jan 2026)
     (https://arxiv.org/abs/2502.09790, 2026-07-15).
   - **LEO-Vetter** — **Michelle Kunimoto**'s automated flux/pixel vetter, **91% completeness / 97%
     reliability**, open source (AJ 2025; https://arxiv.org/abs/2509.10619, 2026-07-15).
   - **RAVEN** — a 2026 Warwick-led ML framework; reprocessed TESS-SPOC FFIs across 2.2M stars →
     **~118 newly validated planets, 2,000+ vetted candidates** (MNRAS 2026;
     https://academic.oup.com/mnras/advance-article/doi/10.1093/mnras/stag512/8528996, 2026-07-15).
   - **TRICERATOPS** — **Steven Giacalone** & **Courtney Dressing**'s Bayesian tool computing
     per-scenario **false-positive probability (FPP)** and **nearby-FPP (NFPP)** by weighing planet vs
     EB/BEB/NEB/triple scenarios. Successor to **vespa** — **Timothy Morton**'s pioneering validator,
     which Morton himself recommended **retiring** in a 2023 Research Note
     (https://ui.adsabs.harvard.edu/abs/2023RNAAS...7..107M, 2026-07-15).
   - **The honest read:** this sub-layer gives a *score*, is being automated fast, and is closing.
     **Not where an outsider competes, and not what ExoDossier does** (Part VII).
4. **TFOP follow-up.** The **TESS Follow-up Observing Program** coordinates assets in five sub-groups:
   **SG1** seeing-limited photometry (rules out nearby EBs, refines the transit), **SG2** recon
   spectroscopy, **SG3** high-res imaging (resolves close blends), **SG4** precise RV (measures mass —
   the scarce resource), **SG5** space photometry. **SG1 explicitly recruits advanced amateurs**, and
   observers routinely earn co-authorship.
5. **Confirmation vs statistical validation (get this distinction exactly right).**
   - **Statistical validation (VP — Validated Planet):** show the false-positive probability is tiny
     (**FPP < ~1%**) so it's *almost certainly* a planet — but **no mass is measured** (TRICERATOPS/
     vespa/ExoMiner).
   - **Confirmation (CP — Confirmed Planet):** actually **measure the mass**, usually via RV. Requires
     scarce telescope time.
   - The ladder: **TCE → TOI → PC → VP (validated) → CP (confirmed).** "Validated" and "confirmed" are
     *not* synonyms — mixing them up marks you instantly as an outsider.
6. **Publication → Archive ingestion.** A peer-reviewed paper (or RNAAS note) announces it; the **NASA
   Exoplanet Archive** ingests it — one row per publication in `ps` (Part V).

## The outsider lane (proven, and our natural home)

Independents have a real, well-trodden track record — overwhelmingly in the long-period/single-transit
regime the pipelines miss:

- **Planet Hunters TESS (PHT)** — the Zooniverse project led by **Nora Eisner** (now at the Flatiron
  Institute; 40,000+ volunteers; https://www.zooniverse.org/projects/nora-dot-eisner/planet-hunters-tess,
  2026-07-15). Volunteers eyeball light curves and catch what BLS discards: per a 2025 paper, **183
  community TOIs, 109 promoted to official TOI (~60%), 19 confirmed planets.** Famous finds include
  **TOI-1338 b** (TESS's first transiting circumbinary planet, spotted on the PHT forum, six volunteer
  co-authors) and **HD 152843**, where SPOC *merged two planets' transits into one* TCE until citizen
  scientists caught all three.
- **The Visual Survey Group (VSG)** — the **Jacobs / LaCourse / Kristiansen / Rappaport / Vanderburg**
  pro-am collaboration that has **visually surveyed ~10 million light curves** with the **`LcTools`**
  software and authored ~69 peer-reviewed papers, catching aperiodic/single-transit signals BLS can't
  (https://arxiv.org/abs/2205.07832, 2026-07-15). Amateurs appear as **direct co-authors**.
- **The CTOI process.** Anyone can register on **ExoFOP-TESS** and submit a **CTOI (Community TOI)**;
  the TOI team may promote it — mission-level credit. **⚠️ ExoFOP temporarily paused new CTOI uploads on
  2026-03-31**, pending updated guidelines (https://exofop.ipac.caltech.edu/tess/, 2026-07-15). Verify
  before relying on it — and note stricter, evidence-heavier guidelines would *help* a dossier tool.
- **RNAAS (Research Notes of the AAS)** — the lowest-barrier venue: editor-checked, ~72-hour, free,
  DOI'd and ADS-indexed, for single-object announcements. The interim channel while CTOIs are paused.

**The infrastructure is deliberately open. An outsider can get their name on a discovery** — through
a CTOI→TOI promotion, an RNAAS note, or co-authorship by feeding a good candidate (or a good tool) to
PHT / VSG / TFOP SG1.

---

# PART V — THE IDENTITY & PROVENANCE MESS (our home turf)

This is where your background is the sharpest edge in the room — a master-data problem the physics
community has but doesn't treat as one.

## The cross-ID tangle

One host star is, simultaneously: a **TIC** number (TESS Input Catalog), a **TOI** (its candidate),
maybe a **CTOI**, maybe a **KOI**+**KIC** (Kepler), maybe an **EPIC** (K2), a **Gaia DR3** source ID,
an **HD** (Henry Draper) number, an **HIP** (Hipparcos) number, and a **2MASS** designation — and the
ID in one release doesn't always map to the same object in another. Resolving one physical star across
all of these (SIMBAD main-ID + positional fallback) is exactly the crosswalk you built for satellites
(`satellite_identifier`), ported. And it matters: attach a transit to the wrong star's radius and you
get the wrong planet.

## The catalogs disagree — and it's structural, not sloppy

There is no single authority for "the truth about this planet." Three sources, three answers:

- **NASA Archive `ps` (Planetary Systems) table** — **one row per planet *per publication*.** Each row
  is internally self-consistent but sparse. **The `ps` table literally *is* a per-attribute conflict
  corpus** — the exoplanet analog of "SATCAT says X, GCAT says Y," already laid out. The single most
  important structural fact for our project.
- **NASA Archive `pscomppars` (Composite Parameters)** — **one row per planet**, composited across
  papers: "more complete but not necessarily self-consistent." It fills each field by default solution,
  else most-precise value, else a calculated one — i.e., it **flattens the disagreement to one answer**,
  exactly what we choose *not* to do.
- **exoplanet.eu (Extrasolar Planets Encyclopaedia)** — European catalog, **CC BY 4.0**, more inclusive
  (higher mass cutoff, carries candidates).

**The confirmed-count discrepancy, and why:** NASA lists **~6,319** confirmed; exoplanet.eu lists
**~8,260** — a ~30% gap on the *same sky*, from four levers: (a) **mass cutoff** — NASA ≤ ~30 Jupiter
masses, exoplanet.eu ≤ ~60 (the planet/brown-dwarf boundary); (b) **candidate handling** —
exoplanet.eu folds in candidates NASA excludes; (c) **validation philosophy** — statistical vs RV; (d)
**update drift** — values copied from papers, sometimes contradicted or mis-transcribed later. Exactly
why SATCAT and GCAT disagree on counts: **each source encodes a different definitional choice, and the
disagreement localizes it.** "Disagreements are data, not errors" ports word-for-word.

## Why the disagreement is *scientific*, not cosmetic — the Kane HZ-flip

The killer result — your "Kane 2014" fact — is **Stephen Kane's 2014 paper on how habitable-zone
membership depends on stellar-parameter uncertainty** (https://arxiv.org/abs/1401.3349, 2026-07-15):
a **~5% error in a star's temperature shifts the HZ boundary by ~10%**, and across Kepler candidates
the HZ uncertainty region is **200–400% of the HZ width**. Translation: **whether a planet is even *in*
the habitable zone can flip depending on which catalog's stellar parameters you trust.** The strongest
evidence that habitability rankings are *provenance-sensitive* — the conflict isn't data hygiene, it
changes the science. It's the exoplanet twin of your satellite "13.6× under different ownership
attribution": one number proving modeling choices change the answer.

## Nobody maintains open, provenance-tracked reconciliation

There *is* an incumbent reconciler — **Exo-MerCat** — merging NASA + exoplanet.eu + KOI + TOI + EPIC
via SIMBAD main IDs (https://arxiv.org/abs/2502.08473, 2026-07-15). But **it flattens to one value per
parameter** (lowest-relative-error), exactly like `pscomppars`. So the honest positioning: **the
"merge them" lane has an incumbent — don't claim it's empty.** The *un*-occupied move is what you did
for satellites — **keep the disagreement, attach per-attribute provenance (`source_assertion`), audit
every merge (`merge_log`), propagate the conflict downstream** into dossiers and re-ranking. That's the
differentiator.

## The stakes: target selection

This isn't tidiness — the disagreement decides where multi-billion-dollar telescopes point:
- **JWST atmospheric targets** are ranked by **TSM/ESM** (Transmission/Emission Spectroscopy Metrics,
  Kempton et al. 2018), and *every* input (planet radius, mass, equilibrium temperature, stellar
  radius, magnitudes) comes from the disagreeing catalogs. List-builders warn that "the most precise
  value is often chosen, but there's no guarantee it's the most accurate, and solutions may disagree."
- **HWO's target list** — the living **TSS25** list (Tier 1 = 164 stars, Tiers 1+2 = 659), auto-built
  by cross-matching TIC + Gaia + SIMBAD + 2MASS and compositing stellar parameters
  (https://arxiv.org/abs/2509.20544, 2026-07-15) — is itself an entity-resolution + parameter-composite
  pipeline, the exact shape of your engine. Which stars rank into the prioritized ~25 is **not agreed**
  and is provenance-sensitive (they had to *union two independent yield codes* whose per-star rankings
  disagreed). **Nobody publishes the rank-order churn as a function of provenance.** That "could-not-
  find" is our second product: the re-ranking report.

---

# PART VI — CURRENT LIMITATIONS (the honest map)

Being clear-eyed about what this does *not* solve makes you credible, not weaker. Say these before an
astronomer says them to you.

1. **Statistical vetting ≠ evidence synthesis.** The ML classifiers (ExoMiner++, LEO-Vetter, RAVEN)
   are excellent and improving fast; they output a *score*. ExoDossier doesn't compete with them — it
   *consumes* their scores into an assembled, cited case. Don't pitch "a better FP classifier"; you'd
   be racing funded teams on their turf.
2. **The RV telescope-time bottleneck is not software-fixable.** The hard constraint on *confirmation*
   is precise-RV instrument time — "too many planets, too few telescopes" — and no software creates
   telescope hours. **We never claim to confirm planets.** Deciding which candidates deserve the scarce
   RV night is a real contribution; manufacturing the night is not.
3. **The single-transit / long-period blind spot is real but hard.** Under-served, so it's our lane —
   but monotransits have no period, multi-sector stitching is fiddly, and aliases are many. High value,
   genuinely difficult; it's a hunt, not a guarantee.
4. **The ExoFOP CTOI pause (2026-03-31) gates the cleanest credit channel.** Until it reopens, the
   mission-level-designation path is closed and RNAAS notes are the interim venue. Verify before
   promising a CTOI.
5. **The literature evidence is fragmented.** DV reports, ExoFOP dispositions (50+ TFOP codes),
   imaging/spectroscopy notes, and prior papers live in different systems with no common identity
   spine — *why* the dossier is valuable, but also why synthesis is only as good as the retrieval, and
   agentic retrieval can be "plausible but wrong." The gold program (Part VII) is our answer, but the
   risk is real and worth naming.

---

# PART VII — WHAT EXODOSSIER DOES THAT'S NOVEL

The novelty check comes back clean. After hard searching — "LLM exoplanet vetting," "AI agent
exoplanet candidate," "agentic astronomy," "exoplanet dossier," plus the named systems — **no
published LLM/agent system performs exoplanet-candidate vetting or builds cited evidence dossiers for
specific candidates.** The nearest neighbors each miss on a different axis: **ASTER** does atmospheric
*retrieval*, **AstroAgents** does astrobiology hypothesis generation, **StarWhisper** does telescope
*scheduling*. This is an absence-of-evidence claim — strong but rebuttable, so state it as "as of
mid-2026 I could not find one," not as a theorem.

Six things ExoDossier does that, in combination, nobody else does:

1. **The verified-unoccupied dossier layer.** An AI-orchestrated, retrieval-grounded, **cited** vetting
   *case* per candidate — light-curve evidence + catalog cross-checks + Gaia RUWE/neighbors +
   TRICERATOPS scenarios + literature — with each claim cited, each parameter carrying its provenance,
   confidence stated. The classifiers give a score; **we give the file.**
2. **An identity graph with per-attribute provenance.** Cross-ID resolution over
   TIC/TOI/CTOI/KOI/KIC/EPIC/Gaia/HD/HIP with `source_assertion` per parameter and an auditable
   `merge_log` — going **beyond Exo-MerCat by keeping the conflict instead of flattening it.**
3. **A gold-graded accuracy number vs TFOPWG labels.** Every dossier disposition back-tested against
   **known** TFOPWG dispositions, producing a published precision/recall — the satellite gold program's
   credibility move, and the direct answer to the "agentic systems are plausible but wrong" critique.
   **Not optional; it *is* the credibility.**
4. **MCP-native, agent-first delivery.** An MCP server (`resolve_target`, `candidate_dossier`,
   `conflicts_for_target`, `rerank_targets`) so an agent can ask one question spanning dossier +
   provenance + re-rank. Nobody has wrapped a reconciled, provenance-aware exoplanet service in the
   agent protocol.
5. **The re-ranking product (second consumer of the same graph).** Provenance-tracked re-ranking of
   JWST TSM/ESM and HWO targets — "which targets change rank, cross a threshold, or flip in/out of the
   habitable zone, depending on which catalog you trust" — quantifying the churn Kane 2014 predicts but
   nobody has tabulated. **One graph, two products.**
6. **Explicit, honest boundaries.** We **don't confirm planets**, own **no telescope**, and don't build
   another classifier — we make **evidence synthesis** and **follow-up prioritization** better. Stating
   the boundary *is* part of the novelty; it's what makes the claim credible instead of hype.

The one-line version: **"The pipeline finds and scores candidates; the classifiers are closing the
scoring layer; the evidence-synthesis layer above it — the cased, cited, provenance-tracked dossier —
is empty, and I'm building it, graded against real dispositions, on a graph that also re-ranks the
flagship target lists."**

---

# PART VIII — HARD QUESTIONS (defend the work)

Rehearse these out loud. They're the ones astronomers, collaborators, and interviewers will actually ask.

**"ExoMiner already does ML vetting — why you?"**
> "ExoMiner, LEO-Vetter, and RAVEN are excellent, and I use them — as *inputs*. They answer a
> different question than I do. They output a probability that a signal is a planet. I output the
> assembled *case*: the light-curve recovery, the catalog cross-checks, the Gaia binarity flag, the
> TRICERATOPS scenarios, and the literature, each claim cited and each parameter carrying its source,
> so a human can adjudicate and a follow-up team can prioritize. A score tells you *what*; a dossier
> tells you *why, according to whom, and how confident.* And critically, none of them touches the
> identity/provenance problem underneath — which catalog's stellar radius you believe — which changes
> the answer. I'm the layer above the classifier, not a competing classifier."

**"You're not an astronomer."**
> "Correct, and I'm precise about it. I won't out-astrophysics an astrophysicist and I don't try — I
> don't confirm planets or measure masses. What I bring is what this field's *downstream* problem
> actually needs and mostly lacks: someone who has built commercial master-data and entity-resolution
> systems twice — cannabis SKUs at CannMenus, satellite catalogs after — and knows what 'correct'
> costs, because I've run the accuracy programs that prove it. I learn the domain the way I learned the
> other two: by operating the gold program, one adjudicated case at a time. The instinct for what makes
> reconciled data trustworthy is the hard, transferable part, and I have it."

**"Isn't this just an LLM wrapper on lightkurve?"**
> "The demo is; the product isn't. Anyone can prompt an LLM to call `lightkurve` and write prose —
> distrust anyone who claims that alone is a contribution. What can't be prompted up in a weekend: an
> identity graph with real per-attribute provenance over catalogs that genuinely disagree; a measured
> accuracy number graded against known TFOPWG dispositions; and an independent light-curve recovery
> that produces an *original datum*, not a scrape. The LLM is orchestration glue. The moat is the
> provenance graph, the gold program, and the judgment about what to synthesize."

**"What if ExoFOP never reopens the CTOI channel?"**
> "The dossier's value doesn't depend on that channel. CTOI→TOI promotion is one credit pathway; it's
> not the product. If uploads stay paused, the interim venue is RNAAS — 72-hour, DOI'd, ADS-indexed —
> and the real distribution is offering the tool as infrastructure to PHT, VSG, and TFOP SG1, who
> assemble these dossiers by hand today and would welcome a good one. And if ExoFOP reopens with
> *stricter, evidence-heavier* guidelines, that helps me — a dossier tool is exactly what tighter
> submission standards demand."

**"How do you know your dossiers are right?"**
> "I don't assert they're right — I *measure* it. That's the whole point of the gold program: I
> back-test dossier dispositions against known TFOPWG labels — confirmed planets and known false
> positives — on a held-out set, and publish the precision/recall and calibration. 'I can tell you my
> system's error rate and show you the graded cases' is a sentence almost nobody here can say, and it's
> the direct answer to the documented failure mode of agentic science — being fluent and wrong. Every
> claim is cited and every parameter carries its source, so a human can check any link."

**"Why would TFOP trust a tool from an outsider?"**
> "Because it's graded, cited, and saves them work on exactly the tedious part they do by hand. Trust
> here is earned by being checkable and useful, not by credentials — the gold number is the checkable
> part, and the focus on long-period/single-transit candidates the pipelines discard is the useful
> part. I'm entering where these communities are explicitly open to outsiders (SG1 recruits advanced
> amateurs; VSG and PHT co-author with volunteers), with an artifact that makes their workflow faster
> and auditable."

**"What's a realistic 3-month win?"**
> "A live, public dossier site covering the long-period/APC slice — each candidate showing its
> independent light-curve recovery, TRICERATOPS scenarios, catalog cross-checks, and cited evidence —
> with a *published gold-graded accuracy number*; plus at least one submitted CTOI or RNAAS note, and
> the re-ranking report showing real rank-churn on a JWST/HWO list. An artifact an astronomer can
> browse, a number they can check, and one warm collaboration started."

**"Why does entity resolution matter here — isn't astronomy already precise?"**
> "The measurements are precise; the *bookkeeping* isn't. The same star has a dozen IDs that don't
> cleanly cross-map, and the archives disagree about the same planet's radius by tens of percent because
> they composite different publications differently. Not a rounding issue — via Kane 2014, a 5%
> temperature disagreement can flip whether a planet is even in the habitable zone, and whether it ranks
> onto a flagship telescope's target list. Entity resolution with provenance lets you say 'these two
> rows are the same object, here's every source's value, here's which conclusions depend on the choice.'
> The identical problem I solved over the satellite catalogs — precise sensors, incoherent identity —
> one sky over."

---

# PART IX — REFERENCE

## Glossary (plain definitions)

- **Transit** — a planet crossing in front of its star, dimming it slightly and periodically.
- **Light curve** — a star's brightness over time; the raw material of transit science.
- **Transit depth (δ)** — the fractional dip in brightness; equals (R_planet/R_star)².
- **Period (P) / Epoch (T₀) / Duration (T)** — orbital period between transits / timestamp of one
  transit / how long a transit lasts.
- **Limb darkening** — a star looks brighter at its center than its edge, rounding the transit shape.
- **Detrending** — removing instrumental and stellar wiggles before searching for a transit.
- **Phase folding** — stacking all transits on the orbital period to boost signal-to-noise.
- **BLS (Box Least Squares)** — the classic transit-search algorithm (Kovács, Zucker & Mazeh 2002);
  fits a periodic box.
- **TLS (Transit Least Squares)** — Hippke & Heller (2019); fits a realistic limb-darkened transit
  shape; ~10% better for small planets.
- **SNR / MES (Multiple Event Statistic)** — folded-transit signal strength; SPOC's TCE threshold is
  ~7.1σ. (TLS's analog is the **SDE**, Signal Detection Efficiency.)
- **Monotransit / single-transit** — only one transit observed; no period known. The pipelines' blind
  spot and the outsider lane.
- **False positive (FP)** — a transit-shaped signal that isn't a planet.
- **Eclipsing binary (EB)** — two stars eclipsing each other; a common FP (tell: secondary eclipse,
  odd/even depth difference, V-shape).
- **BEB / NEB (Background / Nearby Eclipsing Binary)** — a blended EB behind or beside the target
  (tell: centroid offset / difference-image localization).
- **Odd/even test** — comparing alternate transit depths; a difference means an EB at twice the period.
- **Difference-image centroiding** — locating which pixel the dip comes from; catches blends.
- **TCE (Threshold Crossing Event)** — a signal above SPOC's detection threshold; a proto-candidate.
- **DV report (Data Validation report)** — SPOC's per-TCE diagnostic bundle (odd/even, secondary,
  centroid, ghost, bootstrap).
- **TOI (TESS Object of Interest)** — an official TESS candidate, promoted from a TCE by the MIT TSO.
- **CTOI (Community TOI)** — a candidate submitted by anyone via ExoFOP (uploads paused 2026-03-31).
- **KOI / KIC** — Kepler Object of Interest / Kepler Input Catalog (Kepler-era candidate/star IDs).
- **EPIC** — Ecliptic Plane Input Catalog (K2-era star IDs).
- **TIC** — TESS Input Catalog (the star catalog TESS candidates hang off).
- **PC / VP / CP** — Planet Candidate / Validated Planet (FPP small, no mass — "statistical
  validation") / Confirmed Planet (mass measured). "Validated" ≠ "confirmed."
- **SPOC** — Science Processing Operations Center (NASA Ames, Jon Jenkins); makes 2-min/20-s TESS
  light curves and TCEs.
- **QLP (Quick Look Pipeline)** — MIT's pipeline for TESS FFIs; serves millions of stars.
- **FFI (Full-Frame Image)** — TESS's whole field, 200-s cadence in the extended mission; the
  under-served population.
- **MAST** — Mikulski Archive for Space Telescopes (STScI); where you download the data, free.
- **lightkurve** — the open-source Python package for pulling and analyzing TESS/Kepler light curves.
- **TFOP** — TESS Follow-up Observing Program; SG1 photometry / SG2 spectroscopy / SG3 imaging / SG4
  RV / SG5 space photometry.
- **TFOPWG disposition** — the official follow-up label (KP/CP/PC/APC/FP...) used as our gold ground
  truth.
- **TRICERATOPS** — Giacalone & Dressing's Bayesian FP-probability validator (FPP/NFPP).
- **vespa** — Morton's pioneering validator, formally recommended for retirement (2023) in favor of
  TRICERATOPS.
- **ExoMiner / ExoMiner++** — NASA Ames explainable-DL classifier (Valizadegan); scores candidates.
- **LEO-Vetter** — Kunimoto's automated flux/pixel vetter (91% complete / 97% reliable).
- **RAVEN** — 2026 Warwick ML framework; ~118 newly validated planets from TESS FFIs.
- **Gaia** — ESA astrometry mission; the stellar-parameter spine (parallax → radius → planet radius).
- **RUWE** — Gaia's single-star fit quality; > ~1.4 flags an unresolved binary (an FP red flag).
- **Habitable zone (HZ)** — the orbital range where liquid water could exist; boundaries depend on
  stellar luminosity and temperature. **Kane 2014**: a ~5% temperature error shifts the HZ boundary
  ~10%, so HZ membership can *flip* by catalog choice.
- **TSM / ESM** — Transmission / Emission Spectroscopy Metrics (Kempton 2018); rank JWST atmospheric
  targets; provenance-sensitive.
- **NASA Exoplanet Archive** — the authoritative catalog (NExScI/Caltech); `ps` = one row per
  publication, `pscomppars` = one composited row per planet.
- **exoplanet.eu** — the European catalog; more inclusive; ~30% higher confirmed count than NASA.
- **Exo-MerCat** — the incumbent catalog reconciler; flattens to one value (we keep the conflict).
- **PLATO / Roman / HWO** — upcoming: ESA Earth-analog transits (~2027) / NASA microlensing (launch
  2026-08-30) / future direct-imaging flagship (2040s).
- **RNAAS** — Research Notes of the AAS; 72-hour, editor-checked, DOI'd; the low-barrier credit venue.
- **PHT / VSG** — Planet Hunters TESS (Eisner, Zooniverse) / Visual Survey Group (Jacobs/LaCourse/
  Kristiansen/Rappaport/Vanderburg, LcTools) — the credited outsider communities.

## Flashcards (self-test — cover the answer)

- *The one-line ExoDossier pitch?* → The pipeline finds and scores candidates; nobody builds the
  cased, cited, provenance-tracked dossier — I do, graded against real TFOPWG dispositions.
- *Transit depth → radius?* → δ = (R_planet/R_star)²; you can't get planet radius without star radius,
  which is why provenance matters.
- *Why is a single-transit hard, and why our lane?* → One event gives no period; SPOC discards lone
  transits by design, so long-period planets fall through — proven outsider territory.
- *EB vs planet — the tells?* → Secondary eclipse, odd/even depth difference (EB at 2×P), V-shape, too
  deep. Blends show a centroid offset.
- *Validated vs confirmed?* → Validated = FP probability tiny, no mass. Confirmed = mass measured
  (usually RV). Not synonyms.
- *BLS vs TLS?* → BLS fits a box (Kovács 2002); TLS fits a limb-darkened shape (Hippke & Heller 2019),
  ~10% better for small planets.
- *RUWE > 1.4?* → Gaia thinks the star may be an unresolved binary — an FP red flag.
- *The Kane 2014 result?* → A ~5% stellar-temperature error shifts the HZ boundary ~10%; HZ membership
  can flip on which catalog you trust.
- *ps vs pscomppars vs exoplanet.eu?* → `ps` = one row per publication (the conflict corpus);
  `pscomppars` = one composited/flattened row; exoplanet.eu = more inclusive, ~30% higher count.
- *Who runs SPOC? Who leads Planet Hunters TESS?* → Jon Jenkins (NASA Ames) / Nora Eisner (Zooniverse).
- *The "one engine, two skies" bridge?* → Same provenance-tracked entity-resolution + gold engine from
  the satellite catalogs, repointed at exoplanet catalogs. One graph, two products.
- *What does ExoDossier NOT do?* → Confirm planets, own a telescope, or build another FP classifier —
  it makes evidence synthesis and follow-up prioritization better.

---

*Counts (NASA 6,319 confirmed; 8,064 TOIs; exoplanet.eu ~8,260) drift weekly — re-pull before
quoting. All named people, tools, dates, and mission statuses verified 2026-07-15; treat the
"no LLM dossier system exists" novelty claim as a strong-but-rebuttable absence-of-evidence result.*
