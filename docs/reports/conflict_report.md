# ExoDossier Conflict Report v0

Generated at: 2026-07-15 19:09:29 UTC

Nobody agrees on a planet. Every row below is a live query against the identity graph: the same star or candidate, described differently by TOI vs CTOI vs the NASA Archive's per-publication `ps` rows vs the `pscomppars` composite vs the Kepler KOI table. Disagreements are data, not errors.

## Graph at a glance

- Stars: **20,341**  |  Candidates: **23,031**
- Crosswalk identifiers: **76,534**  |  Source assertions: **684,210**  |  merge_log rows: **76,534**

## Ingestion ledger (last run per endpoint)

| source | endpoint | status | rows_ingested | bytes_downloaded | finished_at |
| --- | --- | --- | --- | --- | --- |
| exofop | ctoi_csv | ok | 3964 | 1414974 | 2026-07-15 18:43:38.845934+00:00 |
| exofop | toi_csv | ok | 8064 | 3735481 | 2026-07-15 18:43:33.276666+00:00 |
| nea | tap_cumulative | ok | 9564 | 1350065 | 2026-07-15 18:43:58.762061+00:00 |
| nea | tap_ps | ok | 39978 | 20689114 | 2026-07-15 18:44:42.315020+00:00 |
| nea | tap_pscomppars | ok | 6319 | 1378194 | 2026-07-15 18:44:48.005534+00:00 |
| nea | tap_toi | ok | 8064 | 1552171 | 2026-07-15 18:43:46.605537+00:00 |

## 1. Disposition fights: is it even a planet?

Candidates with >= 2 conflicting canonical dispositions across sources: **3,274**. Of those, **3** are the dramatic kind — one catalog calls it a FALSE POSITIVE while another calls it CONFIRMED or a KNOWN PLANET.

**FALSE POSITIVE vs CONFIRMED/KNOWN — named examples:**

| candidate | host | who says what |
| --- | --- | --- |
| Kepler-404 b | Kepler-404 | koi=CONFIRMED; koi=FALSE_POSITIVE; ps=CANDIDATE; ps=CONFIRMED; pscomppars=CONFIRMED |
| Kepler-1517 b | Kepler-1517 | exofop_toi=FALSE_POSITIVE; koi=CONFIRMED; nea_toi=FALSE_POSITIVE; ps=CANDIDATE; ps=CONFIRMED; pscomppars=CONFIRMED |
| TOI-1836 c | TOI-1836 | exofop_toi=FALSE_POSITIVE; nea_toi=FALSE_POSITIVE; ps=CANDIDATE; ps=CONFIRMED; pscomppars=CONFIRMED |

## 2. Same candidate, conflicting planet radius (> 10% across sources)

Count: **3,614** candidates. Gaia parallax revisions to stellar radii propagate straight into planet radii — this is where rocky-vs-sub-Neptune classification flips.

| candidate | host | disposition | spread | R_Earth by source |
| --- | --- | --- | --- | --- |
| Kepler-1999 b | Kepler-1999 | CONFIRMED | 100% | koi: 3.29; ps: 3.29–4283 (3); pscomppars: 3.29 |
| Kepler-1946 b | Kepler-1946 | CONFIRMED | 100% | koi: 3.59; ps: 2.488–3164 (5); pscomppars: 2.488 |
| Kepler-230 b | Kepler-230 | CONFIRMED | 100% | koi: 3.36; ps: 3.303–3791 (8); pscomppars: 4.26 |
| Kepler-29 b | Kepler-29 | CONFIRMED | 100% | koi: 2.98; ps: 2.55–2784 (10); pscomppars: 2.55 |
| Kepler-29 c | Kepler-29 | CONFIRMED | 100% | koi: 2.78; ps: 2.34–1226 (10); pscomppars: 2.34 |
| Kepler-444 e | Kepler-444 | CONFIRMED | 100% | ps: 0.42–86.5 (9); pscomppars: 0.546 |
| Kepler-444 e | Kepler-444 | CONFIRMED | 100% | koi: 0.62; ps: 0.42–86.5 (9); pscomppars: 0.546 |
| Kepler-444 c | Kepler-444 | CONFIRMED | 99% | ps: 0.39–75.16 (8); pscomppars: 0.497 |
| Kepler-444 c | Kepler-444 | CONFIRMED | 99% | koi: 0.65; ps: 0.39–75.16 (8); pscomppars: 0.497 |
| Kepler-1698 b | Kepler-1698 | CONFIRMED | 99% | koi: 0.99; ps: 0.99–180.7 (6); pscomppars: 1.073 |
| Kepler-444 f | Kepler-444 | CONFIRMED | 99% | ps: 0.51–90.81 (8); pscomppars: 0.741 |
| Kepler-444 f | Kepler-444 | CONFIRMED | 99% | koi: 0.95; ps: 0.51–90.81 (8); pscomppars: 0.741 |

## 3. Same candidate, conflicting orbital period (> 1% across sources)

Count: **375** candidates. Large spreads are usually period aliases (2x/3x) — themselves a real cross-catalog disagreement about the true period.

| candidate | host | disposition | spread | period_days by source |
| --- | --- | --- | --- | --- |
| HD 106315 c | HD 106315 | CONFIRMED | 98% | ps: 21.06–1221 (12); pscomppars: 21.06 |
| TOI-6478 b | TOI-6478 | CONFIRMED | 98% | ps: 34.01–1462 (2); pscomppars: 34.01 |
| TOI-6041 b | TOI-6041 | CONFIRMED | 98% | ps: 26.05–1094 (2); pscomppars: 26.05 |
| NGTS-35 b | NGTS-35 | CONFIRMED | 97% | ps: 25.24–732 (2); pscomppars: 25.24 |
| HIP 41378 f | HIP 41378 | CONFIRMED | 96% | ps: 46.4–1084 (5); pscomppars: 542.1 |
| HIP 41378 d | HIP 41378 | CONFIRMED | 96% | ps: 48.1–1114 (5); pscomppars: 278.4 |
| TOI-815 c | TOI-815 | CONFIRMED | 95% | ps: 34.98–734.5 (2); pscomppars: 34.98 |
| TOI-2010 b | TOI-2010 | CONFIRMED | 88% | ps: 141.8–1135 (2); pscomppars: 141.8 |
| TOI-2449 b | TOI-2449 | CONFIRMED | 84% | ps: 16.65–106.1 (2); pscomppars: 106.1 |
| HD 181433 d | HD 181433 | CONFIRMED | 83% | ps: 2172–1.3e+04 (6); pscomppars: 6896 |
| Kepler-19 c | Kepler-19 | CONFIRMED | 82% | ps: 28.52–160 (3); pscomppars: 28.73 |
| MOA-2011-BLG-293L b | MOA-2011-BLG-293L | CONFIRMED | 82% | ps: 550–3000 (4); pscomppars: 550 |

## 4. Host stellar-parameter conflicts (would move HZ membership)

Hosts whose effective temperature disagrees by > 5% across sources: **1,083** — Kane 2014: a ~5% Teff error shifts the habitable-zone boundary by ~10%, so these are stars whose HZ membership depends on which catalog you trust. Stellar-radius disagreements > 10%: **2,098**.

**Biggest Teff disagreements:**

| host | tic | delta | spread | Teff (K) by source |
| --- | --- | --- | --- | --- |
| TRAPPIST-1 | TIC 278892590 | 3260 K | 56% | exofop_toi: 5780; nea_toi: 5780; ps: 2520–5780 (27); pscomppars: 2566 |
| K2-52 | TIC 399155300 | 3887 K | 54% | ps: 3260–7147 (3); pscomppars: 7147 |
| ZTF J1230-2655 | TIC 951438622 | 4220 K | 42% | exofop_toi: 5780; nea_toi: 5780; ps: 1e+04; pscomppars: 1e+04 |
| K2-289 | TIC 413753029 | 1720 K | 31% | ps: 3809–5529 (3); pscomppars: 5529 |
| Kepler-1649 | TIC 137558813 | 1185 K | 30% | ps: 2703–3888 (11); pscomppars: 3240 |
| Kepler-1512 | TIC 158989438 | 1389 K | 29% | koi: 3419; ps: 3419–4808 (10); pscomppars: 4372 |
| Kepler-42 | TIC 63126862 | 1120 K | 27% | ps: 3068–4188 (34); pscomppars: 3068 |
| TOI-1518 | TIC 427761355 | 2619 K | 26% | exofop_toi: 9918; nea_toi: 9918; ps: 7299–9918 (4); pscomppars: 7299 |
| Kepler-577 | TIC 378085037 | 1270 K | 25% | koi: 3787; ps: 3787–5057 (10); pscomppars: 4984 |
| Kepler-1388 | TIC 164524311 | 1161 K | 23% | koi: 3891; ps: 3891–5052 (38); pscomppars: 4098 |
| Kepler-913 | TIC 169465273 | 1381 K | 23% | koi: 6068; ps: 4687–6068 (16); pscomppars: 4687–6068 (2) |
| Kepler-1314 | TIC 270955259 | 948 K | 23% | koi: 4137; ps: 3240–4188 (9); pscomppars: 4188 |

**Biggest stellar-radius disagreements:**

| host | tic | spread | R_sun by source |
| --- | --- | --- | --- |
| ZTF J1230-2655 | TIC 951438622 | 99% | exofop_toi: 1; nea_toi: 1; ps: 0.0123; pscomppars: 0.0123 |
| Kepler-141 | TIC 273681580 | 96% | koi: 0.782; ps: 0.778–19.2 (23); pscomppars: 0.787 |
| Kepler-1025 | TIC 164727439 | 95% | koi: 19.53; ps: 0.927–19.53 (11); pscomppars: 1.13 |
| K2-52 | TIC 399155300 | 90% | ps: 0.23–2.192 (4); pscomppars: 2.192 |
| K2-33 | TIC 49040478 | 85% | ps: 0.16–1.1 (6); pscomppars: 1.05 |
| K2-11 | TIC 301609547 | 85% | ps: 0.78–5.15 (4); pscomppars: 5.15 |
| Kepler-770 | TIC 120891972 | 85% | koi: 4.885; ps: 0.753–4.885 (28); pscomppars: 0.92 |
| Kepler-959 | TIC 137411481 | 82% | koi: 7.663; ps: 1.37–7.663 (10); pscomppars: 2.01 |
| Kepler-1633 | TIC 158789121 | 81% | koi: 4.912; ps: 0.921–4.912 (8); pscomppars: 1.32 |
| K2-39 | TIC 250977648 | 81% | exofop_toi: 3.121; nea_toi: 3.121; ps: 0.74–3.88 (8); pscomppars: 2.97 |
| Kepler-1649 | TIC 137558813 | 81% | ps: 0.118–0.609 (11); pscomppars: 0.2317 |
| DH Tau | TIC 268148971 | 80% | ps: 0.27–1.367 (2); pscomppars: 0.27 |

## 5. Crosswalk statistics

**Identifiers by type:**

| id_type | count |
| --- | --- |
| ctoi | 3964 |
| gaia_dr3 | 4382 |
| hd | 744 |
| hip | 793 |
| kic | 8214 |
| koi | 9564 |
| name | 11121 |
| tic | 21624 |
| toi | 16128 |

**Distinct identifier-types per star (breadth of the graph):**

| distinct_id_types | stars |
| --- | --- |
| 1 | 15855 |
| 2 | 44 |
| 3 | 1623 |
| 4 | 2192 |
| 5 | 626 |
| 6 | 1 |

**merge_log by rule (every link + flagged non-merge is audited):**

| rule_fired | count |
| --- | --- |
| candidate_seed | 29270 |
| catalog_xref | 10369 |
| coord_match<2arcsec | 2006 |
| hostname_new_star | 285 |
| koi_new_star | 6208 |
| period_match<1pct | 6772 |
| tic_exact | 21624 |
