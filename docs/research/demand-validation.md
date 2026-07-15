# ExoDossier — Demand / Pain Validation

**Question:** Do researchers, grad students, and serious citizen-scientists actually *feel* the
pains ExoDossier addresses, and would they value / adopt a conflict-aware provenance + AI-vetting
dossier tool? This is a **scientific / passion project** — "demand" means *contribution + adoption*,
not revenue. So the bar is: *is the pain real and felt, or is this a solution in search of a problem?*

**Method & honesty caveat.** Evidence below was mined 2026-07-15 via web search + fetch. Two of the
requested source classes were **largely inaccessible to the crawler**: `reddit.com` is hard-blocked
to Anthropic's user agent (confirmed 400 errors), and `astronomy.stackexchange.com` pages could not be
fetched or reliably surfaced. As a result, the evidence here **skews toward the published literature
and citizen-science human-factors research** rather than raw forum grievance. Peer-reviewed papers that
complain about a problem in their intro/limitations are *strong* evidence of felt pain — but they are
professionals writing papers, not a random grad student venting. Where a quote is a search-snippet or a
fetch-model paraphrase I could not confirm against the primary text verbatim, it is tagged
**[unverified]**. Treat verbatim wording of any [unverified] quote as approximate.

---

## 1. Evidence FOR demand, by pain

### Pain 1 — Catalogs disagree on the same object's parameters (and on whether it's a planet)

**Strength: STRONG and well-documented. Felt by: professionals (demographics + characterization), less so by citizen scientists.**

- **Direct catalog-comparison paper.** Pascucci et al. / *"A Quantitative Comparison of Exoplanet
  Catalogs"* (Geosciences 2018; arXiv:1808.10236) compares NASA Exoplanet Archive, exoplanet.eu, the
  Exoplanet Orbit Database (ORG) and the Open Exoplanet Catalogue. It finds the catalogs mostly agree
  *but* names specific planets with inconsistent radii — **CoRoT-21 b** and **HD 219134 d** — and notes
  ORG fills missing masses from a *theoretical* mass–radius relation, and that exoplanet.eu vs NASA use
  different mass cut-offs (60 vs 30 M_Jup) for what even counts as a planet. [unverified verbatim]
  URL: https://www.mdpi.com/2076-3263/8/9/325 and https://arxiv.org/pdf/1808.10236 (2018; accessed 2026-07-15).

- **Review-level statement of the problem.** *"Exoplanet Catalogues"* (arXiv:1803.11158, 2018): the
  major catalogues "are not fully consistent, with discrepancies partly due to different selection
  criteria, notations, and diligence in updating their data bases, and … due to the heterogeneity of
  information provided in discovery papers that different catalogues capture in different ways."
  [unverified verbatim] URL: https://arxiv.org/pdf/1803.11158 (2018; accessed 2026-07-15).

- **The archive itself can be wrong.** *"A Word of Caution about Exoplanet Archival Data"*
  (Christodoulou & Kazanas, RNAAS 4, 217, Dec 2020): the data "are copied from discovery and
  characterization papers, which can at times be inaccurate, unreliable, poorly-constrained,
  contradicted by other papers, or copied incorrectly in spite of best efforts," and the paper flags a
  cluster of period-2–2.5 d **outliers (TOI-6130, TOI-3714, EPIC 201757695, K2-216, TOI-2266)** whose
  archive "default parameters" are inconsistent with Kepler's third law. Its recommendation is exactly
  ExoDossier's thesis: **verify values against the original papers.** [unverified verbatim]
  URL: https://iopscience.iop.org/article/10.3847/2515-5172/abcf4d/ampdf (2020; accessed 2026-07-15).

- **Revisions move real numbers.** The SWEET-Cat radius-valley re-analysis (A&A 2026;
  arXiv:2601.12396) reports the *same* Kepler planets are on average ~0.05 R⊕ larger in the
  Berger et al. (2020) catalog than in Berger et al. (2023), "with discrepancies growing to ~0.1 Earth
  radii for more massive stars." That is precisely the rocky-vs-sub-Neptune boundary. [unverified verbatim]
  URL: https://arxiv.org/html/2601.12396 (2026; accessed 2026-07-15).

- **"Confirmed" isn't final.** *"Ephemeris Matching Reveals False Positive Validated and Candidate
  Planets from the K2 Mission"* (arXiv:2402.07903, 2024) shows even *validated* planets get demoted to
  false positives — i.e. the "is it a planet" disposition genuinely churns.
  URL: https://arxiv.org/pdf/2402.07903 (2024; accessed 2026-07-15).

- **Habitable-zone membership flips on stellar params.** Kane (2014), *"Habitable Zone Dependence on
  Stellar Parameter Uncertainties"* (ApJ 782, 111; arXiv:1401.3349) quantifies how HZ boundaries — and
  therefore whether a planet is "in the HZ" — move with host-star parameter uncertainties. This is the
  citation ExoDossier's README already leans on, and it holds up.
  URL: https://arxiv.org/abs/1401.3349 (2014; accessed 2026-07-15).

- **ExoDossier's own Wave-1 report** independently reproduces the pain at scale: 3,274 candidates with
  conflicting dispositions across sources, 3 with the dramatic FALSE-POSITIVE-vs-CONFIRMED split
  (Kepler-1517 b, TOI-1836 c), and 3,614 candidates disagreeing on radius by >10%. (Internal:
  `docs/reports/conflict_report.md`.) That the numbers are large is corroborating evidence the pain is real.

**Verdict on Pain 1:** genuinely felt, repeatedly written down by professionals. It is *latent*, though
— people cope by adopting one archive and moving on, rather than screaming for a fix (see §2).

### Pain 2 — Cross-matching the same star/planet across ID systems is a manual pain

**Strength: MODERATE, real but partly tooled-over. Felt by: grad students / data-wranglers most.**

- **A whole 2026 paper exists just to build one crosswalk.** *"Gaia DR3 IDs for TESS Input Catalog
  Targets"* (arXiv:2603.28850, 2026): the TIC was built on Gaia **DR2** and "there had not been an
  update to incorporate Gaia DR3 IDs" — so the authors had to construct the DR2→DR3 crosswalk by hand,
  with the caveat that DR2 and DR3 source IDs "do not necessarily directly map to each other" (one DR2
  source can split into several DR3 sources). [unverified verbatim] The existence of the paper *is* the
  demand signal. URL: https://arxiv.org/html/2603.28850v1 (2026; accessed 2026-07-15).

- **User-facing cross-ID bugs in the standard tooling.** lightkurve Issue #148, *"Downloading target
  from archive returns data for a different, nearby star"* — a real reproducible failure where the
  identifier/coordinate resolution grabs the wrong star ~4″ away. lightkurve later (v1.1.1) had to add a
  warning for the range where **EPIC and TIC IDs overlap**. This is exactly the "same number means two
  different objects" hazard ExoDossier's identity graph is built to catch.
  URLs: https://github.com/lightkurve/lightkurve/issues/148 and
  https://github.com/lightkurve/lightkurve/blob/main/CHANGES.rst (accessed 2026-07-15).

- **Community-built crosswalk tools exist because people need them.** `gaia-kepler.fun`
  (Bedell) and `dfm/gaia-kepler` are standalone projects whose entire purpose is Gaia↔Kepler/TESS
  cross-matching; ExoFOP publishes a downloadable TIC/Gaia-DR3 crosswalk table with a reproduction
  notebook. People routinely hand-roll these in TOPCAT at 1″ tolerance (e.g. GALAH DR3 × TIC × Gaia).
  URLs: https://gaia-kepler.fun/ , https://github.com/dfm/gaia-kepler (accessed 2026-07-15).

- **Exo-MerCat's own reason for existing.** The Exo-MerCat v2 paper states merging catalog entries
  "proved to be a challenging problem because of the presence of aliases (i.e., the same exoplanet
  listed in one or more catalogs using different nomenclature)." [unverified verbatim]
  URL: https://arxiv.org/html/2502.08473v1 (2025; accessed 2026-07-15).

**Verdict on Pain 2:** real, but this is the pain the community has already thrown the most tooling at
(Exo-MerCat, gaia-kepler.fun, ExoFOP crosswalks, astroquery/SIMBAD name resolution). ExoDossier's
differentiator here is *auditable per-identifier provenance*, not the crosswalk existing at all.

### Pain 3 — Vetting candidates / triaging false positives is laborious, evidence scattered

**Strength: STRONGEST / most viscerally felt. Felt by: pros, grad students, AND citizen scientists.**

- **The quantified labor.** Yu et al. (2019), *"Identifying Exoplanets with Deep Learning III"*
  (AstroNet-Triage; AJ 158, 25): for a typical TESS sector it "may take a few experienced humans up to
  a few days to perform triage on tens of thousands of candidates," after which "a team of ~10 vetters
  may spend up to a week classifying the remaining ~1000 high-quality candidates if each one is viewed
  by at least three different people." [unverified verbatim] This is the single most concrete
  labor-cost statement found. URL: https://iopscience.iop.org/article/10.3847/1538-3881/ab21d6 and
  https://dspace.mit.edu/bitstream/handle/1721.1/124704/Yu_2019_AJ_158_25.pdf (2019; accessed 2026-07-15).

- **Still true in 2025.** LEO-Vetter (arXiv:2509.10619, 2025): "The traditional methods of manually
  vetting planet candidates are time-consuming and labor-intensive, making it impractical to keep up
  with the influx of new data," and manual catalogs are "rendered unsuitable by the subjectivity of
  vetting by eye"; fainter searches "would overwhelm operators with the number of candidates needing
  manual review." [unverified verbatim] URL: https://arxiv.org/html/2509.10619 (2025; accessed 2026-07-15).

- **Ongoing uniform-vetting grind.** The *TESS Triple-9* series (e.g. Catalog II, arXiv:2303.00624,
  2023) — "a new set of 999 uniformly-vetted exoplanet candidates" — is literally a rolling manual
  vetting effort. URL: https://arxiv.org/pdf/2303.00624 (2023; accessed 2026-07-15).

- **Citizen-science evidence (the direct target user).** Planet Patrol (Fausnaugh et al.-style, PASP
  2022) built its whole workflow around volunteer vetting and a "Talk" bulletin board; the *Exoplanet
  Citizen Science Pipeline: Human Factors and ML* paper (arXiv:2503.14575, 2025) reports that "jargon
  terms familiar to a professional (e.g. ephemerides, limb darkening) may be unknown to citizen
  scientists … These terms can be off-putting," that target/reference-star selection "is not always
  obvious," and that participation "can prove daunting for inexperienced observers." [unverified verbatim]
  Scattered, jargon-heavy evidence is *exactly* the gap a cited, plain-language dossier fills.
  URLs: https://iopscience.iop.org/article/10.1088/1538-3873/ac5de0 (2022);
  https://arxiv.org/html/2503.14575v1 (2025) (accessed 2026-07-15).

**Verdict on Pain 3:** this is the pain with the clearest, most repeated, most quantified felt cost —
and it is felt across all three user tiers.

### Pain 4 — Follow-up backlog: more candidates than telescope time

**Strength: STRONG and worsening. Felt by: pros writing telescope/JWST proposals; PIs.**

- **Roman makes it an order-of-magnitude worse.** *"Towards Instrument-Agnostic Exoplanet Candidate
  Prioritization"* (arXiv:2606.07769, 2026): Roman "is expected to yield between 60,000 and 200,000
  transiting exoplanets … The order of magnitude increase in exoplanet candidates will quickly become
  intractable for the same quality of examination … especially considering a relatively constant
  quantity of available resources," and "a means of intelligently selecting candidates for further
  in-depth analysis is of paramount importance." [unverified verbatim]
  URL: https://arxiv.org/html/2606.07769 (2026; accessed 2026-07-15).

- **The RV bottleneck is explicit.** TESS follow-up planning papers (e.g. arXiv:1701.03539) note TESS
  was expected to find >10,000 candidates while "the RV measurements required to obtain precise mass
  measurements even for just a few tens of these planets will easily exceed the many hundreds [of
  nights]." [unverified verbatim] This is the "RV time is the real bottleneck" point ExoDossier's README
  already concedes. URL: https://arxiv.org/pdf/1701.03539 (2017; accessed 2026-07-15).

- **JWST target selection is an active, time-pressured ranking problem.** *"Identification of the Top
  TESS Objects of Interest for Atmospheric Characterization … with JWST"* (Hord et al., AJ 2024;
  arXiv:2308.09617) ranks TOIs by TSM/ESM (Kempton et al. 2018) within radius–T_eq cells and stresses
  "Time is of the essence." [unverified verbatim] These metrics depend on planet radius and T_eq —
  which depend on the stellar params ExoDossier tracks provenance for.
  URL: https://arxiv.org/abs/2308.09617 (2023–24; accessed 2026-07-15).

**Verdict on Pain 4:** real and growing, but "prioritization" as a task already has an established
metric vocabulary (TSM/ESM). ExoDossier's angle — re-ranking *as a function of provenance/parameter
churn* — is novel but adjacent to solved.

### Pain 5 — Reproducibility: hard to trace where a parameter value came from

**Strength: MODERATE, real but usually met by "just re-derive homogeneously." Felt by: demographics researchers.**

- **The community's own fix implies the pain.** The standard response to heterogeneous provenance is to
  *re-derive everything uniformly*: the Gaia–Kepler Stellar Properties Catalog (Berger et al. 2020,
  AJ 159, 280), SWEET-Cat, and the Gaia-Kepler-TESS host catalog all exist because "exoplanet archives
  and catalogs usually consist of heterogeneous compilation[s] of stellar properties which … lead to
  significant discrepancies when compared with homogeneously derived parameters." [unverified verbatim]
  URLs: https://iopscience.iop.org/article/10.3847/1538-3881/159/6/280 (2020);
  https://arxiv.org/pdf/2301.11338 (2023) (accessed 2026-07-15).

- **NASA Archive's design is itself an acknowledgement.** The Archive maintains a single-reference
  "default parameter set" per planet precisely to give "a self-consistent set of parameters for any
  system" — an admission that mixing sources breaks provenance. Its own recent tools paper (PSJ 2025)
  documents the KIC/EPIC/TIC cross-match effort. URLs:
  https://exoplanetarchive.ipac.caltech.edu/docs/intro.html ;
  https://iopscience.iop.org/article/10.3847/PSJ/ade3c2 (2025) (accessed 2026-07-15).

**Verdict on Pain 5:** felt by demographics/occurrence-rate people specifically, but the dominant coping
mechanism (re-derive uniformly) means *provenance-tracing* is more of a "nice, and correct" than a
"screaming" pain. It is the intellectual foundation of ExoDossier more than an independent market.

---

## 2. Evidence AGAINST / "already handled"

- **For many pros, the NASA Exoplanet Archive already IS the trusted source.** It is vetted by
  astronomers, linked back to original literature, updated weekly, and provides a self-consistent
  default-parameter set; it is "the most widely used archive … for studying exoplanet demographics."
  A large fraction of working scientists resolve "which value do I trust?" by simply saying "the
  Archive default," and consider the question closed. [unverified] URLs:
  https://exoplanetarchive.ipac.caltech.edu/ ; https://exoplanetarchive.ipac.caltech.edu/docs/intro.html
  (accessed 2026-07-15). *This is the most important headwind: the felt pain is real but many users have
  a "good enough" answer.*

- **Exo-MerCat already reconciles IDs across the major catalogs.** It links aliases to a preferred
  SIMBAD/TIC identifier and returns "the most precise estimate for each planetary parameter … based on
  the lowest relative error," across exoplanet.eu, NASA Archive, OEC, TOI and EPIC/K2. It is open-source
  as of v2 (2025). This overlaps ExoDossier's Pains 1 and 2 substantially. **However**, the same paper
  concedes the merged catalog "is not self-consistent (i.e., all measurements for the same target do not
  belong to the same reference paper)" — i.e. Exo-MerCat **collapses each parameter to one "best" number
  and does not expose the disagreement, per-attribute provenance, or the rank-order churn as a product.**
  That is the precise seam ExoDossier occupies. [unverified verbatim]
  URLs: https://arxiv.org/html/2502.08473v1 ; https://exo-mercat.readthedocs.io/ (2025; accessed 2026-07-15).

- **Cross-ID (Pain 2) is the most tooled-over.** gaia-kepler.fun, dfm/gaia-kepler, ExoFOP's TIC/Gaia-DR3
  table, astroquery + SIMBAD name resolution, and lightkurve's ambiguity warnings already cover the
  common cases. A new tool must beat "download the existing crosswalk."

- **Statistical vetting (Pain 3) is a crowded field.** ExoMiner, LEO-Vetter, RAVEN, AstroNet-Triage,
  ExoNet, TRICERATOPS, NotPlaNET, transformer-based FFI vetters — many groups already automate
  false-positive triage. ExoDossier explicitly does *not* compete here; its README concedes this and
  pivots to the *evidence-synthesis / cited-dossier* layer instead. That is the right read of the market.
  URLs: https://arxiv.org/html/2512.00967 ; https://iopscience.iop.org/article/10.3847/1538-3881/ad5f29
  (accessed 2026-07-15).

- **Stellar-parameter systematics (Pains 1/5) are being attacked by re-derivation, not reconciliation.**
  Homogeneous catalogs (Berger, SWEET-Cat, Gaia-Kepler-TESS) are the community's chosen fix; a
  reconciliation/provenance layer is complementary to, not a replacement for, that work.

---

## 3. Honest verdict — which pains have genuine felt demand

| Pain | Felt-demand rating | Who feels it | Already-handled? |
|---|---|---|---|
| 3 — Vetting labor / scattered evidence | **Highest** | pros, grad students, citizen scientists | classification yes; *cited evidence-synthesis* no |
| 1 — Catalogs disagree on params / disposition | **High (latent)** | demographics + characterization pros | partially (Exo-MerCat collapses it; Archive picks one) |
| 4 — Follow-up backlog / re-ranking | **High but adjacent-solved** | PIs, proposal writers | TSM/ESM metrics exist; provenance-aware re-rank doesn't |
| 5 — Reproducibility / provenance | **Moderate (foundational)** | occurrence-rate researchers | coped via re-derivation; tracing itself not productized |
| 2 — Cross-ID pain | **Moderate (most tooled-over)** | data-wranglers, grad students | yes, heavily (Exo-MerCat, gaia-kepler.fun, ExoFOP) |

**On the three specific offerings:**

- **(a) Conflict-aware provenance reconciliation — GENUINE, and the most defensible novel angle.** The
  disagreement is documented (§1 Pain 1) and *no existing tool exposes it as a first-class product*:
  Exo-MerCat merges to a single "lowest-error" value and is admittedly not self-consistent; the NASA
  Archive picks one reference. Publishing the *disagreement itself* — per-attribute source assertions,
  an auditable merge log, and rank-order churn as a function of which source you trust — is a real,
  unoccupied seam. Caveat: the demand is *latent* (people cope), so adoption depends on making the value
  obvious (e.g., "these 3,614 planets flip rocky↔sub-Neptune depending on the source").

- **(b) AI cited vetting dossiers — GENUINE demand on the pain, RISKIEST on the solution.** Pain 3 is the
  most felt pain in the whole space. But (i) statistical vetting is crowded, so the wedge must be the
  *cited, evidence-synthesizing, plain-language* dossier, not another classifier; (ii) professionals may
  distrust an LLM verdict unless every claim is cited and checkable against TFOPWG dispositions (the
  README's "graded against TFOPWG" gold program is the right instinct); (iii) the clearest enthusiastic
  audience is citizen scientists, for whom jargon and scattered diagnostics are a documented barrier.

- **(c) JWST/HWO target re-ranking — REAL but the WEAKEST/most-solved.** Prioritization is an active,
  time-pressured need, but TSM/ESM already give the community a shared ranking language. "Re-rank as a
  function of provenance churn" is intellectually novel yet niche; best positioned as a *demonstration*
  of why (a) matters ("your top-10 JWST list reshuffles when the stellar params update"), not a
  standalone product.

**Overall (for a scientific / passion tool, adoption not revenue): MIXED-leaning-YES.** The underlying
pains are real, repeatedly documented, and worsening (Roman). For a *revenue* product the verdict would
be shakier — most pains have a "good enough" workaround and buyers are scarce. But the bar here is
"would researchers find it useful, cite it, and contribute," and for **(a) conflict/provenance report**
and **(b) citizen-science-facing cited dossiers** the answer is a defensible *yes*: they occupy a real
gap (evidence-synthesis + provenance) that the crowded classifier and merged-catalog tools deliberately
step around. The honest risk is that Pain 1/5 demand is *latent* — people know the problem exists but
have stopped complaining because they've each made private peace with one archive. Adoption therefore
hinges less on "does the pain exist" (it does) and more on **surfacing the disagreement so vividly that
people realize their private peace was unearned.** ExoDossier's own conflict-report numbers (3 dramatic
FP-vs-CONFIRMED cases, 3,614 >10% radius disagreements) are the right kind of ammunition for that.

---

## 4. Who the actual users are, and where they hang out

- **Exoplanet demographics / occurrence-rate researchers** (radius-valley, Fulton-gap work) — feel Pains
  1 & 5 most. Reachable via arXiv astro-ph.EP, AAS/DPS meetings, and the radius-valley citation cluster
  (Fulton, Petigura, Van Eylen, Berger, SWEET-Cat/Adibekyan groups).
- **Grad students / postdocs doing target selection, cross-matching, and vetting** — feel Pains 2, 3, 4
  daily. Reachable via lightkurve/astroquery GitHub, the TESS Science Support, and university exoplanet
  groups.
- **TFOP / TESS Follow-up working group members** — live Pain 3 & 4; the TFOPWG SG1–SG5 structure and
  ExoFOP are where vetting evidence is actually assembled. https://exofop.ipac.caltech.edu/tess/
- **Serious citizen scientists** — the most enthusiastic likely early adopters of a cited dossier:
  **Planet Hunters TESS "Talk"** (https://talk.planethunters.org/), **Planet Patrol** Talk boards, and
  the Unistellar follow-up network. These are the amateurs already doing vetting and blocked by jargon.
- **JWST / Ariel / (future) HWO proposal writers** — feel Pain 4; reachable via the TSM/ESM target-list
  community (Kempton et al., Hord et al.).
- **Discussion venues to seed:** Astronomy StackExchange (high-signal, but note it was inaccessible to
  this crawl — worth manual review), the exoplanet community Slack/Discord, r/exoplanets and
  r/askastronomy (Reddit, blocked here — check manually), and astrobetter.com for tool announcements.

**Recommended "show it to" order for vib:** (1) a Planet Hunters TESS / Planet Patrol SuperUser — will
immediately get the cited-dossier value; (2) an occurrence-rate grad student — will immediately get the
conflict/provenance report; (3) a TFOP member — the credibility gatekeeper. If all three say "oh, that's
useful," the demand is validated for a passion tool.

---

## 5. Anyone explicitly asking for / half-building this?

- **Exo-MerCat (Alei et al.) is the closest half-build** — it reconciles aliases and merges the
  catalogs, and its open-source v2 (2025) shows sustained community interest. But it *collapses* to a
  single best value and is explicitly "not self-consistent," so it does **not** productize disagreement
  or per-attribute provenance. This is the strongest evidence that (i) the reconciliation problem is
  real enough that someone built a tool, and (ii) the *conflict-aware provenance* twist is still open.
  https://arxiv.org/html/2502.08473v1 (2025).

- **"A Word of Caution about Exoplanet Archival Data" (2020)** is effectively a published request for
  exactly ExoDossier's discipline — it warns the archive can be wrong and tells readers to trace values
  back to source papers. https://iopscience.iop.org/article/10.3847/2515-5172/abcf4d/ampdf (2020).

- **The candidate-prioritization papers (2026) explicitly ask** for "a means of intelligently selecting
  candidates," i.e. the re-ranking product (c). https://arxiv.org/html/2606.07769 (2026).

- **Homogeneous stellar catalogs (Berger 2020/2023, SWEET-Cat, Gaia-Kepler-TESS)** are the community
  half-solving Pains 1/5 from the *re-derivation* side — a signal that the parameter-provenance problem
  is taken seriously enough to fund large catalog efforts.

- **Not found:** a single tool or forum thread proposing "conflict-aware provenance graph + AI cited
  vetting dossiers" as one product. The pieces are all requested separately; nobody found is combining
  them. That absence is consistent with ExoDossier's "verified-novel / execution-gap" claim — with the
  caveat that Reddit and Astronomy StackExchange were not searchable in this pass, so a manual check of
  those two venues is advised before treating the gap as fully confirmed.

---

### Source list (URL + date accessed 2026-07-15)

- A Quantitative Comparison of Exoplanet Catalogs (2018): https://www.mdpi.com/2076-3263/8/9/325 · https://arxiv.org/pdf/1808.10236
- Exoplanet Catalogues review (2018): https://arxiv.org/pdf/1803.11158
- A Word of Caution about Exoplanet Archival Data (RNAAS 4, 217, 2020): https://iopscience.iop.org/article/10.3847/2515-5172/abcf4d/ampdf
- SWEET-Cat radius valley / Berger 2020-vs-2023 (2026): https://arxiv.org/html/2601.12396
- Ephemeris Matching false-positive validated planets (2024): https://arxiv.org/pdf/2402.07903
- Kane, Habitable Zone Dependence on Stellar Parameter Uncertainties (2014): https://arxiv.org/abs/1401.3349
- Gaia DR3 IDs for TIC Targets (2026): https://arxiv.org/html/2603.28850v1
- lightkurve Issue #148 / CHANGES: https://github.com/lightkurve/lightkurve/issues/148 · https://github.com/lightkurve/lightkurve/blob/main/CHANGES.rst
- gaia-kepler.fun / dfm-gaia-kepler: https://gaia-kepler.fun/ · https://github.com/dfm/gaia-kepler
- Exo-MerCat v2 (2025): https://arxiv.org/html/2502.08473v1 · https://exo-mercat.readthedocs.io/
- Yu et al. 2019 AstroNet-Triage (AJ 158, 25): https://iopscience.iop.org/article/10.3847/1538-3881/ab21d6 · https://dspace.mit.edu/bitstream/handle/1721.1/124704/Yu_2019_AJ_158_25.pdf
- LEO-Vetter (2025): https://arxiv.org/html/2509.10619
- TESS Triple-9 Catalog II (2023): https://arxiv.org/pdf/2303.00624
- Planet Patrol (PASP 2022): https://iopscience.iop.org/article/10.1088/1538-3873/ac5de0
- Exoplanet Citizen Science Pipeline: Human Factors & ML (2025): https://arxiv.org/html/2503.14575v1
- Instrument-Agnostic Candidate Prioritization (2026): https://arxiv.org/html/2606.07769
- TESS follow-up / RV bottleneck (2017): https://arxiv.org/pdf/1701.03539
- Top TESS TOIs for JWST atmospheric characterization (Hord et al. 2023-24): https://arxiv.org/abs/2308.09617
- Gaia-Kepler Stellar Properties Catalog I (Berger 2020): https://iopscience.iop.org/article/10.3847/1538-3881/159/6/280
- Gaia-Kepler-TESS host catalog (2023): https://arxiv.org/pdf/2301.11338
- NASA Exoplanet Archive (intro / tools paper 2025): https://exoplanetarchive.ipac.caltech.edu/docs/intro.html · https://iopscience.iop.org/article/10.3847/PSJ/ade3c2
- ML vetting / NotPlaNET (crowded-field evidence): https://arxiv.org/html/2512.00967 · https://iopscience.iop.org/article/10.3847/1538-3881/ad5f29
- Planet Hunters TESS Talk / ExoFOP-TESS: https://talk.planethunters.org/ · https://exofop.ipac.caltech.edu/tess/

**Access caveats:** reddit.com is hard-blocked to this crawler; astronomy.stackexchange.com pages could
not be fetched. Forum-level "felt pain" is therefore under-sampled and should be manually spot-checked.
