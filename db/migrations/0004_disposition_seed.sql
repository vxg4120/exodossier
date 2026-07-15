-- Per-source disposition vocabularies -> canonical taxonomy.
-- Canonical set: CONFIRMED | CANDIDATE | AMBIGUOUS | FALSE_POSITIVE | KNOWN_PLANET.
-- Sources use the TFOPWG codes (ExoFOP/NEA TOI), the Archive KOI words, and the ps soltype/flags.
-- Idempotent: ON CONFLICT refreshes the canonical + notes so re-running the migration is a no-op.

INSERT INTO disposition_mapping (source, source_value, canonical_disposition, notes) VALUES
    -- TFOPWG dispositions, shared vocabulary of the ExoFOP TOI list and the NEA `toi` table.
    ('exofop_toi', 'PC',  'CANDIDATE',      'Planet Candidate'),
    ('exofop_toi', 'APC', 'AMBIGUOUS',      'Ambiguous Planet Candidate'),
    ('exofop_toi', 'CP',  'CONFIRMED',      'Confirmed Planet'),
    ('exofop_toi', 'KP',  'KNOWN_PLANET',   'Known Planet (pre-TESS)'),
    ('exofop_toi', 'FP',  'FALSE_POSITIVE', 'False Positive'),
    ('exofop_toi', 'FA',  'FALSE_POSITIVE', 'False Alarm (non-astrophysical)'),
    ('nea_toi', 'PC',  'CANDIDATE',      'Planet Candidate'),
    ('nea_toi', 'APC', 'AMBIGUOUS',      'Ambiguous Planet Candidate'),
    ('nea_toi', 'CP',  'CONFIRMED',      'Confirmed Planet'),
    ('nea_toi', 'KP',  'KNOWN_PLANET',   'Known Planet (pre-TESS)'),
    ('nea_toi', 'FP',  'FALSE_POSITIVE', 'False Positive'),
    ('nea_toi', 'FA',  'FALSE_POSITIVE', 'False Alarm (non-astrophysical)'),
    -- ExoFOP CTOI user dispositions (free-ish text; the common transit-vetting codes).
    ('exofop_ctoi', 'PC', 'CANDIDATE',      'Planet Candidate'),
    ('exofop_ctoi', 'EB', 'FALSE_POSITIVE', 'Eclipsing Binary'),
    ('exofop_ctoi', 'FP', 'FALSE_POSITIVE', 'False Positive'),
    ('exofop_ctoi', 'V',  'FALSE_POSITIVE', 'Stellar Variability'),
    -- Archive KOI cumulative dispositions (koi_disposition + koi_pdisposition share the vocab).
    ('koi', 'CONFIRMED',       'CONFIRMED',      'Archive-confirmed Kepler planet'),
    ('koi', 'CANDIDATE',       'CANDIDATE',      'Kepler planet candidate'),
    ('koi', 'FALSE POSITIVE',  'FALSE_POSITIVE', 'Kepler false positive'),
    ('koi', 'NOT DISPOSITIONED','AMBIGUOUS',     'Pipeline did not disposition'),
    -- Archive Planetary Systems (ps) solution types.
    ('ps', 'Published Confirmed',      'CONFIRMED', 'Peer-reviewed confirmed planet'),
    ('ps', 'Published Candidate',      'CANDIDATE', 'Published candidate'),
    ('ps', 'TESS Project Candidate',   'CANDIDATE', 'TESS project candidate'),
    ('ps', 'Kepler Project Candidate', 'CANDIDATE', 'Kepler project candidate'),
    ('ps', 'CONTROVERSIAL',            'AMBIGUOUS', 'pl_controv_flag = 1 (disputed existence)'),
    -- Composite Planetary Systems (pscomppars) holds confirmed planets only.
    ('pscomppars', 'CONFIRMED', 'CONFIRMED', 'Member of the confirmed-planet composite table')
ON CONFLICT (source, source_value)
DO UPDATE SET canonical_disposition = EXCLUDED.canonical_disposition, notes = EXCLUDED.notes;
