-- Ingestion ledger: politeness made visible. Every network pull in ingest/ opens and closes a
-- row here (ported verbatim in shape from the satellite platform's 0002_ingest_ledger.sql).
CREATE TABLE ingest_run (
    ingest_run_id    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source           TEXT NOT NULL,   -- exofop | nea
    endpoint         TEXT NOT NULL,   -- toi_csv | ctoi_csv | tap_toi | tap_cumulative | tap_ps | ...
    started_at       TIMESTAMPTZ NOT NULL,
    finished_at      TIMESTAMPTZ,
    rows_ingested    INT,
    bytes_downloaded BIGINT,
    status           TEXT,            -- ok | skipped_fresh | error
    notes            TEXT
);
