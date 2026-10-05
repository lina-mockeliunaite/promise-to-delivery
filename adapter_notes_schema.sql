-- Problems an adapter found while reading a document (a page with no readable text, skipped images, ...).
-- Additive and idempotent: applied on demand by adapters.ensure_notes_schema, so the ledger's schema_version stays 1
-- and an existing database keeps its data. Rows are written with the source version and never change.

CREATE TABLE IF NOT EXISTS source_version_notes (
    id                INTEGER PRIMARY KEY,
    source_version_id INTEGER NOT NULL REFERENCES source_versions (id),
    ordinal           INTEGER NOT NULL CHECK (ordinal >= 1),
    message           TEXT NOT NULL CHECK (length(trim(message)) > 0),
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (source_version_id, ordinal)
);

CREATE TRIGGER IF NOT EXISTS source_version_notes_immutable_u BEFORE UPDATE ON source_version_notes
BEGIN SELECT RAISE(ABORT, 'source version notes are immutable'); END;
CREATE TRIGGER IF NOT EXISTS source_version_notes_immutable_d BEFORE DELETE ON source_version_notes
BEGIN SELECT RAISE(ABORT, 'source version notes are never deleted'); END;
