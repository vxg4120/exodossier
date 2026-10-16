-- Wave 2 results survive the nightly graph rebuild.
--
-- identity/build.py rebuilds the graph with `TRUNCATE merge_log, source_assertion,
-- entity_identifier, candidate, star RESTART IDENTITY CASCADE` (twice a day on the box). CASCADE
-- reaches every table with a foreign key into those, and target.candidate_id referenced candidate,
-- so each rebuild emptied target and, through target, pipeline_run, detection and fp_scenario.
-- RESTART IDENTITY also renumbers candidates, so a stored candidate_id points at a different
-- planet after a rebuild.
--
-- From here on target is keyed by what the rebuild does not change: the TOI (candidate level) and
-- the TIC (star level, which the light curves are indexed by). candidate_id stays as a nullable
-- cached hint written at selection time; readers resolve the current candidate from the TOI through
-- entity_identifier and never link through the hint.

ALTER TABLE target DROP CONSTRAINT IF EXISTS target_candidate_id_fkey;
ALTER TABLE target DROP CONSTRAINT IF EXISTS target_candidate_id_key;
ALTER TABLE target ALTER COLUMN candidate_id DROP NOT NULL;

-- Backfill any row selected before this migration that lacks a key, from the current crosswalk.
UPDATE target t
SET toi = ei.id_value
FROM entity_identifier ei
WHERE t.toi IS NULL
  AND ei.candidate_id = t.candidate_id
  AND ei.id_type = 'toi';

UPDATE target t
SET tic_id = s.tic_id
FROM candidate c
JOIN star s ON s.star_id = c.star_id
WHERE t.tic_id IS NULL
  AND c.candidate_id = t.candidate_id
  AND s.tic_id IS NOT NULL;

-- A row that still has no TOI cannot be re-resolved after a rebuild; it is not a usable target.
-- (select_targets.py only ever selects through a TOI identifier, so none is expected.)
DELETE FROM detection WHERE pipeline_run_id IN (
    SELECT pipeline_run_id FROM pipeline_run
    WHERE target_id IN (SELECT target_id FROM target WHERE toi IS NULL)
);
DELETE FROM pipeline_run WHERE target_id IN (SELECT target_id FROM target WHERE toi IS NULL);
DELETE FROM fp_scenario WHERE target_id IN (SELECT target_id FROM target WHERE toi IS NULL);
DELETE FROM target WHERE toi IS NULL;

ALTER TABLE target ALTER COLUMN toi SET NOT NULL;
ALTER TABLE target ALTER COLUMN tic_id SET NOT NULL;
ALTER TABLE target ADD CONSTRAINT target_toi_key UNIQUE (toi);
CREATE INDEX IF NOT EXISTS target_candidate_id_idx ON target (candidate_id);
-- target (tic_id) is already indexed by 0006.

COMMENT ON COLUMN target.candidate_id IS
    'Cached hint from selection time; may be stale after a graph rebuild. Resolve the current '
    'candidate from toi through entity_identifier.';
