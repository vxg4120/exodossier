-- CTOI user dispositions occasionally carry the TFOPWG confirmed/known codes too (a CTOI whose
-- planet was later confirmed). Add them so those candidates resolve instead of counting unmapped.
INSERT INTO disposition_mapping (source, source_value, canonical_disposition, notes) VALUES
    ('exofop_ctoi', 'CP', 'CONFIRMED',    'Confirmed Planet'),
    ('exofop_ctoi', 'KP', 'KNOWN_PLANET', 'Known Planet'),
    ('exofop_ctoi', 'APC','AMBIGUOUS',    'Ambiguous Planet Candidate')
ON CONFLICT (source, source_value)
DO UPDATE SET canonical_disposition = EXCLUDED.canonical_disposition, notes = EXCLUDED.notes;
