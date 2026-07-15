-- Wave 2: light-curve pipeline. Five tables, all provenance-linked back to the Wave 1 graph and
-- the ingest_run ledger:
--   target           - the reproducibly-selected slice (gold planets, gold FPs, discovery), with
--                       the KNOWN ephemeris carried along as the recovery answer key.
--   lightcurve_file  - index of the Parquet light curves on disk (one row per TIC/sector/author),
--                       each tied to the MAST ingest_run that fetched it. Resumability lives here.
--   pipeline_run     - one per target processing attempt; status + WHY-on-failure, timing, detrend
--                       choices, data vintage + git sha for a dated, reproducible result.
--   detection        - per target, per method (bls|tls|single_event) signal + metrics, ranked.
--   fp_scenario      - TRICERATOPS per-scenario false-positive probabilities (FPP/NFPP).
-- "We recover/flag signals; we do not confirm planets" — the schema stores measurements + honest
-- status, never a verdict.

-- The selected target slice. Deterministic SQL in pipeline/select_targets.py truncates + repopulates
-- this table; select_rule documents which rule picked each row.
CREATE TABLE target (
    target_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    candidate_id       BIGINT NOT NULL REFERENCES candidate,
    tic_id             BIGINT NOT NULL,
    toi                TEXT,
    cohort             TEXT NOT NULL,     -- gold_planet | gold_fp | discovery
    stratum            TEXT,              -- deep_short | shallow_long | single_transit | long_period | ...
    tfopwg_disp        TEXT,              -- CP | KP | FP | FA | PC | APC (the source-of-truth label)
    canonical_disp     TEXT,              -- CONFIRMED | KNOWN_PLANET | FALSE_POSITIVE | CANDIDATE | AMBIGUOUS
    -- Answer key: the catalog ephemeris we grade our independent recovery against (from the TOI
    -- assertion). For the discovery slice these may be NULL/uncertain by construction.
    known_period_days  NUMERIC,
    known_epoch_bjd    NUMERIC,
    known_depth_ppm    NUMERIC,
    known_duration_hr  NUMERIC,
    tmag               NUMERIC,
    select_rule        TEXT NOT NULL,
    selected_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (candidate_id)
);
CREATE INDEX ON target (tic_id);
CREATE INDEX ON target (cohort);

-- On-disk Parquet index. One row per (TIC, sector, author, cadence). Presence of a row = the file
-- is downloaded and valid; fetch_lightcurves.py skips anything already here (resumable).
CREATE TABLE lightcurve_file (
    lightcurve_file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tic_id             BIGINT NOT NULL,
    sector             INT NOT NULL,
    author             TEXT NOT NULL,     -- SPOC | QLP | TESS-SPOC | ...
    cadence_s          INT,               -- 120 | 200 | 1800 ...
    flux_kind          TEXT,              -- pdcsap | sap | kspsap | det ...
    mission            TEXT,              -- TESS | Kepler | K2
    path               TEXT NOT NULL,     -- relative to repo root, under data/lightcurves/
    n_points           INT,
    t_start            DOUBLE PRECISION,  -- BTJD of first cadence
    t_end              DOUBLE PRECISION,  -- BTJD of last cadence
    ingest_run_id      BIGINT REFERENCES ingest_run,   -- the MAST pull that produced it
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tic_id, sector, author, cadence_s)
);
CREATE INDEX ON lightcurve_file (tic_id);

-- One row per target processing attempt. status carries the honest outcome; notes carries WHY on
-- any non-ok status (no silent failures). data_vintage + git_sha make a result dated + reproducible.
CREATE TABLE pipeline_run (
    pipeline_run_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_id          BIGINT REFERENCES target,
    tic_id             BIGINT NOT NULL,
    status             TEXT NOT NULL,     -- ok | no_data | timeout | error
    n_sectors          INT,
    n_points           INT,
    baseline_days      DOUBLE PRECISION,  -- span of stitched light curve
    detrend            JSONB,             -- {method, window_length_days, sigma, ...}
    runtime_s          DOUBLE PRECISION,
    data_vintage       DATE,              -- date the light curves were downloaded
    git_sha            TEXT,
    notes              TEXT,
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at        TIMESTAMPTZ
);
CREATE INDEX ON pipeline_run (target_id);
CREATE INDEX ON pipeline_run (tic_id);

-- Per method signal + metrics. Multiple ranked rows per run are allowed (best signal = rank 1).
CREATE TABLE detection (
    detection_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pipeline_run_id    BIGINT NOT NULL REFERENCES pipeline_run,
    tic_id             BIGINT NOT NULL,
    method             TEXT NOT NULL,     -- bls | tls | single_event
    rank               INT NOT NULL DEFAULT 1,
    period_days        NUMERIC,
    epoch_bjd          NUMERIC,           -- BTJD
    depth_ppm          NUMERIC,
    duration_hr        NUMERIC,
    snr                NUMERIC,
    sde                NUMERIC,           -- TLS SDE (signal detection efficiency); BLS uses power/SNR
    power              NUMERIC,           -- BLS max power / TLS peak statistic
    metrics            JSONB,             -- grid params, n_transits, odd/even, chi2, timing, ...
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON detection (pipeline_run_id);
CREATE INDEX ON detection (tic_id, method);

-- TRICERATOPS (or fallback) per-scenario false-positive probabilities. One row per scenario code
-- plus summary rows scenario='FPP'/'NFPP'. tool + notes record if a fallback/isolation was used.
CREATE TABLE fp_scenario (
    fp_scenario_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_id          BIGINT REFERENCES target,
    tic_id             BIGINT NOT NULL,
    tool               TEXT NOT NULL DEFAULT 'triceratops',
    scenario           TEXT NOT NULL,     -- TP | EB | EBx2P | PTP | PEB | STP | SEB | DTP | DEB | BTP | BEB | NTP | NEB | FPP | NFPP
    probability        NUMERIC,
    metrics            JSONB,
    computed_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    notes              TEXT
);
CREATE INDEX ON fp_scenario (tic_id);
CREATE INDEX ON fp_scenario (target_id);
