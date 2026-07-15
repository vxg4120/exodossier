-- Identity graph: SPEC Wave 1 §3, mirroring the satellite platform's 0004_identity.sql shape
-- (canonical entity + identifier crosswalk + per-attribute source_assertion + merge audit),
-- adapted to the two-level exoplanet hierarchy: a STAR (canonical host) has many CANDIDATEs
-- (canonical planet/candidate). Resolved winners live on the canonical rows; every competing
-- claim stays queryable in source_assertion ("disagreements are data, not errors").

-- Canonical host star.
CREATE TABLE star (
    star_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tic_id           BIGINT UNIQUE,           -- TESS Input Catalog id; NULL for KOI stars with no
                                              -- TIC crossmatch (linked by coordinates instead)
    canonical_name   TEXT NOT NULL,
    ra_deg           NUMERIC,
    dec_deg          NUMERIC,
    teff_k           NUMERIC,                 -- resolved winner; conflicts live in source_assertion
    logg             NUMERIC,
    rstar_rsun       NUMERIC,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Canonical planet / candidate, belonging to exactly one star.
CREATE TABLE candidate (
    candidate_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    star_id          BIGINT NOT NULL REFERENCES star,
    canonical_name   TEXT NOT NULL,
    disposition      TEXT,                    -- resolved canonical disposition (see dispo taxonomy)
    period_days      NUMERIC,                 -- resolved winner; conflicts in source_assertion
    planet_radius_re NUMERIC,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON candidate (star_id);

-- Identifier crosswalk: the heart of the graph. Polymorphic — an identifier attaches to a STAR
-- (tic|kic|epic|gaia_dr3|hd|hip|name) or to a CANDIDATE (toi|ctoi|koi|name); exactly one of
-- star_id/candidate_id is set. UNIQUE NULLS NOT DISTINCT so the ON CONFLICT idempotency in
-- identity/merge.link works despite the always-null sibling FK column.
CREATE TABLE entity_identifier (
    identifier_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    star_id          BIGINT REFERENCES star,
    candidate_id     BIGINT REFERENCES candidate,
    id_type          TEXT NOT NULL,   -- tic | toi | ctoi | koi | kic | epic | gaia_dr3 | hd |
                                      -- hip | name
    id_value         TEXT NOT NULL,
    source           TEXT NOT NULL,   -- exofop | nea (which pull asserted this identifier)
    confidence       NUMERIC(3,2) NOT NULL DEFAULT 1.00,
    first_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT entity_identifier_one_owner CHECK (num_nonnulls(star_id, candidate_id) = 1),
    UNIQUE NULLS NOT DISTINCT (id_type, id_value, source, star_id, candidate_id)
);
CREATE INDEX ON entity_identifier (id_value);
CREATE INDEX ON entity_identifier (star_id);
CREATE INDEX ON entity_identifier (candidate_id);

-- Field-level provenance: what each source claims about an attribute, BEFORE resolution.
-- attribute in {period_days, planet_radius_re, depth_ppm, duration_hr, epoch_bjd, disposition}
-- (candidate-level) or {teff_k, logg, rstar_rsun, parallax_mas, vmag, tmag} (star-level).
-- source_ref carries the per-publication citation (ps.pl_refname) so competing ps rows are
-- distinguishable. star_id/candidate_id are NULL until the row is matched (source_key keeps an
-- unmatched assertion attachable later).
CREATE TABLE source_assertion (
    assertion_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    star_id          BIGINT REFERENCES star,
    candidate_id     BIGINT REFERENCES candidate,
    source_key       TEXT NOT NULL,   -- source-native object key (toi number, kepoi_name, pl_name)
    attribute        TEXT NOT NULL,
    value            TEXT NOT NULL,
    unit             TEXT,            -- e.g. days | R_earth | ppm | K | R_sun | mag
    source           TEXT NOT NULL,   -- exofop_toi | exofop_ctoi | nea_toi | koi | ps | pscomppars
    source_ref       TEXT,            -- publication citation for this value (ps per-pub provenance)
    observed_at      TIMESTAMPTZ NOT NULL,
    ingest_run_id    BIGINT NOT NULL REFERENCES ingest_run
);
CREATE INDEX ON source_assertion (candidate_id, attribute);
CREATE INDEX ON source_assertion (star_id, attribute);
CREATE INDEX ON source_assertion (source, source_key);

-- Merge / link audit: no silent merges, ever. Every crosswalk link AND every candidate/star merge
-- writes a row. entity_type distinguishes star-graph from candidate-graph audit rows; a LINK logs
-- surviving_id = merged_id = the entity it attached an identifier to (mirrors the satellite
-- merge.link convention).
CREATE TABLE merge_log (
    merge_id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_type      TEXT NOT NULL,   -- star | candidate
    surviving_id     BIGINT NOT NULL,
    merged_id        BIGINT NOT NULL,
    rule_fired       TEXT NOT NULL,   -- e.g. tic_exact | coord_match<2arcsec | period_match<1pct
    score            NUMERIC(4,3),
    merged_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    details          JSONB
);
CREATE INDEX ON merge_log (rule_fired);

-- Per-source disposition vocabularies -> canonical taxonomy. Populated by 0004_disposition_seed.
-- Canonical set: CONFIRMED | CANDIDATE | AMBIGUOUS | FALSE_POSITIVE | KNOWN_PLANET.
CREATE TABLE disposition_mapping (
    source           TEXT NOT NULL,   -- exofop | nea_toi | koi | ps
    source_value     TEXT NOT NULL,   -- PC | CP | KP | FP | FA | APC | CONFIRMED | CANDIDATE | ...
    canonical_disposition TEXT NOT NULL,
    notes            TEXT,
    PRIMARY KEY (source, source_value)
);
