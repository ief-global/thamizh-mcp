-- THAMIZH MCP knowledge store (blueprint §5): self-enriching cache, keyed by normalized word.
-- One row per (word, field, source) claim — provenance is per-claim, not per-word.
CREATE TABLE IF NOT EXISTS claims (
    word        TEXT NOT NULL,              -- normalized form
    field       TEXT NOT NULL,              -- origin | lemma | meaning | formation | grammar | native_equivalent
    value_json  TEXT NOT NULL,              -- the claim payload (schema fragment)
    source      TEXT NOT NULL,              -- e.g. ThamizhiMorph, Tamil Wiktionary
    tier        TEXT NOT NULL CHECK (tier IN ('anchor', 'evolving')),
    authority   TEXT CHECK (authority IN ('Tholkappiyam', 'Nannūl')),
    confidence  REAL,
    retrieved   TEXT NOT NULL,              -- ISO date (evolving) or version pin (anchor)
    PRIMARY KEY (word, field, source)
);
CREATE INDEX IF NOT EXISTS idx_claims_word ON claims(word);
CREATE INDEX IF NOT EXISTS idx_claims_stale ON claims(tier, retrieved);
