# ExoDossier — Wave 2 Recovery Report

_Generated 2026-07-15; light-curve data vintage 2026-07-15; 58 targets, 58 processed ok._

**Framing.** This pipeline independently RECOVERS or FLAGS transit signals from raw TESS photometry and grades them against the known TFOPWG answer key. It does not confirm planets. A recovery = a BLS/TLS period within 1% of the catalog period or an integer harmonic, at depth-SNR ≥ 7.

## Gold planets: 16/20 known planets recovered

| TOI | disp | P_known(d) | P_rec(d) | method | match | SNR | phaseΔ/miss-reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2134.02 | CP | 95.853 | 47.927 | BLS | harmonic x0.5 | 313.5 | 0.000 |
| 1898.01 | CP | 45.522 | 45.521 | BLS | exact | 147.8 | 0.000 |
| 1456.01 | CP | 18.712 | 18.712 | BLS | exact | 416.4 | 0.001 |
| 2180.01 | CP | 260.174 | MISS | - | - | - | P=260.2 d > 50 d periodic-search cap (blind spot; needs single-event) |
| 1573.01 | KP | 21.216 | 21.217 | BLS | exact | 393.9 | 0.001 |
| 1150.01 | KP | 1.481 | 1.481 | BLS | exact | 530.8 | 0.020 |
| 1151.01 | KP | 3.474 | 3.474 | BLS | exact | 2099.4 | 0.006 |
| 4470.01 | KP | 2.219 | 2.219 | BLS | exact | 1914.5 | 0.002 |
| 1271.01 | KP | 6.135 | 6.135 | BLS | exact | 260.2 | 0.002 |
| 5972.01 | KP | 3.525 | 3.525 | BLS | exact | 1520.1 | 0.000 |
| 5789.01 | CP | 12.926 | 12.914 | TLS | exact | 15.2 | 0.010 |
| 1726.02 | CP | 20.544 | MISS | - | - | - | strongest signal did not match catalog P (best SNR=48.8); wrong-alias/blend? |
| 2011.01 | KP | 11.578 | MISS | - | - | - | shallow (217 ppm); best BLS/TLS SNR=30.8 < 7 |
| 2011.02 | KP | 27.592 | 27.592 | BLS | exact | 30.8 | 0.001 |
| 396.03 | CP | 11.230 | MISS | - | - | - | shallow (209 ppm); best BLS/TLS SNR=26.5 < 7 |
| 1462.01 | CP | 2.178 | 2.178 | BLS | exact | 38.1 | 0.004 |
| 144.01 | CP | 6.268 | 6.268 | BLS | exact | 95.5 | 0.002 |
| 1469.01 | KP | 3.093 | 3.091 | TLS | exact | 21.0 | 0.003 |
| 1469.02 | KP | 6.765 | 6.765 | BLS | exact | 42.3 | 0.001 |
| 1773.01 | KP | 0.737 | 0.737 | BLS | exact | 115.1 | 0.002 |


## BLS vs TLS (gold planets)

| method | planets recovered | of |
| --- | --- | --- |
| BLS | 14 | 20 |
| TLS | 14 | 20 |


## Gold false positives: pipeline found a transit-like signal in 20/20

These ARE eclipsing binaries / blends / false alarms. That the pipeline recovers a signal is expected and correct — recovery is NOT what rejects them. The FP verdict comes from odd/even depth, secondary eclipse, centroid, and TRICERATOPS scenarios (see fp_scenario). Recovering their ephemerides cleanly is what lets that analysis run.

| TOI | disp | P_catalog(d) | P_rec(d) | SNR | pipeline |
| --- | --- | --- | --- | --- | --- |
| 1946.01 | FP | 10.846 | 45.013 | 205.7 | signal |
| 586.01 | FP | 22.638 | 22.638 | 133.3 | signal@catalog-P |
| 1029.01 | FP | 36.222 | 36.227 | 509.4 | signal@catalog-P |
| 1405.01 | FP | 12.640 | 12.652 | 247.5 | signal@catalog-P |
| 1104.01 | FP | 341.279 | 43.496 | 217.8 | signal |
| 1830.01 | FP | 9.782 | 9.782 | 711.4 | signal@catalog-P |
| 1013.01 | FP | 5.426 | 5.425 | 346.0 | signal@catalog-P |
| 587.01 | FP | 8.044 | 42.664 | 238.6 | signal |
| 1025.01 | FP | 9.684 | 9.684 | 432.6 | signal@catalog-P |
| 1978.01 | FP | 6.081 | 41.495 | 417.3 | signal |
| 886.01 | FP | 20.428 | 14.455 | 35.9 | signal |
| 1051.01 | FA | 21.702 | 44.869 | 103.3 | signal |
| 389.01 | FP | 13.459 | 13.459 | 59.2 | signal@catalog-P |
| 4314.01 | FA | 73.581 | 37.002 | 24.8 | signal@catalog-P |
| 1487.01 | FA | 23.288 | 17.587 | 15.6 | signal |
| 1689.01 | FA | 9.124 | 45.696 | 59.7 | signal |
| 1418.01 | FA | 0.676 | 0.677 | 41.9 | signal@catalog-P |
| 1250.01 | FA | 1.442 | 40.493 | 26.7 | signal |
| 1665.01 | FP | 1.764 | 1.764 | 62.5 | signal@catalog-P |
| 589.01 | FP | 2.518 | 2.518 | 53.1 | signal@catalog-P |


## Discovery slice: 16/18 targets show a signal worth a dossier

Long-period / single-transit candidates — the pipelines' documented blind spot. The single-event lens localises a lone dip (epoch/depth/duration/SNR) but claims NO period; the periodic columns show what BLS found within the 50-day cap. These are candidate signals for a dossier, not planets.

| TOI | kind | P_catalog(d) | P_bls(d) | BLS SNR | single-event SNR | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| 4494.01 | long_period | 32.54 | 32.535 | 167.0 | 95.4 | signal worth a dossier |
| 4328.01 | long_period | 703.79 | 43.400 | 21.6 | 18.9 | signal worth a dossier |
| 588.01 | long_period | 39.47 | 39.472 | 659.4 | 363.6 | signal worth a dossier |
| 4307.01 | long_period | 32.70 | 32.697 | 16.5 | 23.5 | signal worth a dossier |
| 2082.01 | long_period | 30.20 | 30.200 | 16.2 | 7.3 | signal worth a dossier |
| 5724.01 | long_period | 697.40 | 34.870 | 11.9 | 10.2 | signal worth a dossier |
| 6902.01 | long_period | 36.44 | 43.018 | 60.0 | 216.9 | signal worth a dossier |
| 2009.01 | long_period | 1071.09 | 33.265 | 45.1 | 44.0 | signal worth a dossier |
| 4326.01 | long_period | 1826.08 | 17.558 | 16.7 | 9.2 | signal worth a dossier |
| 2112.02 | long_period | 155.82 | 42.109 | 59.7 | 68.4 | signal worth a dossier |
| 6664.01 | single_transit | single | 27.676 | 24.7 | 31.1 | signal worth a dossier |
| 2666.01 | single_transit | single | 25.571 | 364.1 | 253.9 | signal worth a dossier |
| 2270.01 | single_transit | single | 36.795 | 6.7 | 6.9 | below threshold |
| 4355.01 | single_transit | single | 47.267 | 62.3 | 243.6 | signal worth a dossier |
| 2277.01 | single_transit | single | 7.698 | 6.3 | 6.0 | below threshold |
| 4321.01 | single_transit | single | 41.316 | 12.5 | 15.4 | signal worth a dossier |
| 1835.02 | single_transit | single | 43.605 | 22.5 | 16.8 | signal worth a dossier |
| 6980.01 | single_transit | single | 47.323 | 8.5 | 6.2 | signal worth a dossier |


## Processing failures / timeouts

_None — every target processed ok._

Per-target runtime: median 59s, max 684s (TLS wall-clock cap enforced per SPEC).

