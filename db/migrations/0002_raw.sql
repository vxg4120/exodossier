-- Per-source raw landing tables. Raw values land VERBATIM (SPEC provenance discipline): every
-- table keeps the full source row in `extra` JSONB plus a typed projection of the identity +
-- attribute columns the identity graph needs. All carry ingest_run_id + loaded_at for lineage.
-- Surrogate PKs (not natural keys) so a null/duplicate source key never aborts a bulk load.

-- ExoFOP TESS TOI list (download_toi.php?output=csv, ~7k rows).
CREATE TABLE raw_exofop_toi (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    toi                  TEXT,
    tic_id               BIGINT,
    tfopwg_disposition   TEXT,
    tess_disposition     TEXT,
    period_days          NUMERIC,
    duration_hr          NUMERIC,
    depth_ppm            NUMERIC,
    planet_radius_re     NUMERIC,
    epoch_bjd            NUMERIC,
    teff_k               NUMERIC,
    logg                 NUMERIC,
    rstar_rsun           NUMERIC,
    tmag                 NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_exofop_toi (ingest_run_id);

-- ExoFOP TESS CTOI list (download_ctoi.php?output=csv).
CREATE TABLE raw_exofop_ctoi (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ctoi                 TEXT,
    tic_id               BIGINT,
    promoted_to_toi      TEXT,
    user_disposition     TEXT,
    period_days          NUMERIC,
    duration_hr          NUMERIC,
    depth_ppm            NUMERIC,
    planet_radius_re     NUMERIC,
    epoch_bjd            NUMERIC,
    tmag                 NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_exofop_ctoi (ingest_run_id);

-- NASA Exoplanet Archive `toi` table (TAP/ADQL). The Archive's own TOI copy — a second opinion
-- vs ExoFOP's live one.
CREATE TABLE raw_nea_toi (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    toi                  TEXT,
    tid                  BIGINT,      -- TIC id
    tfopwg_disp          TEXT,
    period_days          NUMERIC,
    duration_hr          NUMERIC,
    depth_ppm            NUMERIC,
    planet_radius_re     NUMERIC,
    epoch_bjd            NUMERIC,
    teff_k               NUMERIC,
    logg                 NUMERIC,
    rstar_rsun           NUMERIC,
    tmag                 NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_nea_toi (ingest_run_id);

-- NASA Exoplanet Archive `cumulative` (KOI) table (TAP/ADQL).
CREATE TABLE raw_koi_cumulative (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kepid                BIGINT,      -- KIC id
    kepoi_name           TEXT,        -- e.g. K00752.01
    kepler_name          TEXT,        -- e.g. Kepler-227 b
    koi_disposition      TEXT,        -- Archive disposition (CONFIRMED/CANDIDATE/FALSE POSITIVE)
    koi_pdisposition     TEXT,        -- pipeline disposition
    period_days          NUMERIC,
    duration_hr          NUMERIC,
    depth_ppm            NUMERIC,
    planet_radius_re     NUMERIC,
    epoch_bjd            NUMERIC,
    teff_k               NUMERIC,
    logg                 NUMERIC,
    rstar_rsun           NUMERIC,
    kepmag               NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_koi_cumulative (ingest_run_id);

-- NASA Exoplanet Archive `ps` (Planetary Systems) — ONE ROW PER PLANET PER PUBLICATION. The
-- per-attribute conflict corpus: pl_refname/st_refname carry the citation for each competing value.
CREATE TABLE raw_ps (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pl_name              TEXT,
    hostname             TEXT,
    tic_id               BIGINT,
    gaia_id              TEXT,
    hd_name              TEXT,
    hip_name             TEXT,
    default_flag         INT,         -- 1 = the Archive's default parameter set for this planet
    soltype              TEXT,
    pl_controv_flag      INT,
    period_days          NUMERIC,
    planet_radius_re     NUMERIC,
    depth_pct            NUMERIC,     -- pl_trandep in the ps table is PERCENT (not ppm)
    duration_hr          NUMERIC,
    epoch_bjd            NUMERIC,
    teff_k               NUMERIC,
    logg                 NUMERIC,
    rstar_rsun           NUMERIC,
    vmag                 NUMERIC,
    tmag                 NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    disc_facility        TEXT,
    pl_refname           TEXT,        -- the publication this planet-parameter row came from
    st_refname           TEXT,        -- the publication the stellar parameters came from
    pl_pubdate           TEXT,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_ps (ingest_run_id);
CREATE INDEX ON raw_ps (pl_name);

-- NASA Exoplanet Archive `pscomppars` (Composite Planetary Systems) — ONE ROW PER PLANET,
-- composited across publications ("more complete but not necessarily self-consistent").
CREATE TABLE raw_pscomppars (
    raw_id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pl_name              TEXT,
    hostname             TEXT,
    tic_id               BIGINT,
    gaia_id              TEXT,
    hd_name              TEXT,
    hip_name             TEXT,
    period_days          NUMERIC,
    planet_radius_re     NUMERIC,
    depth_pct            NUMERIC,
    duration_hr          NUMERIC,
    epoch_bjd            NUMERIC,
    teff_k               NUMERIC,
    logg                 NUMERIC,
    rstar_rsun           NUMERIC,
    vmag                 NUMERIC,
    tmag                 NUMERIC,
    ra_deg               NUMERIC,
    dec_deg              NUMERIC,
    disc_facility        TEXT,
    extra                JSONB NOT NULL DEFAULT '{}',
    ingest_run_id        BIGINT NOT NULL REFERENCES ingest_run,
    loaded_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON raw_pscomppars (ingest_run_id);
CREATE INDEX ON raw_pscomppars (pl_name);
