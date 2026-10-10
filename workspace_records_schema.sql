-- Workspace records (layout redesign, built 9 Oct). Additive and idempotent: applied on demand by
-- workspace_records.ensure_schema, like integrity_schema.sql. The ledger's schema_version stays 1.
--
-- Three human records the redesigned overview needs and integrity Part B does not provide:
--   deal_notes        the typed two-line deal note and the one decision deadline per deal (latest row wins)
--   signing_flags     "Must fix before signing" on one finding, with name and reason
--   flag_clearances   a named person clearing a flag, with a reason (one clearance per flag)
-- All append-only (triggers abort UPDATE and DELETE). None of them writes to issues or closure_checks, and none feeds
-- source_set_sha256 or decision_evidence_sha256: a note, a deadline or a flag never changes a finding and never marks
-- the review out of date. "Okay to proceed" is not here: it is integrity's accepted_risks, bound to the three hashes.

CREATE TABLE IF NOT EXISTS deal_notes (
    id          INTEGER PRIMARY KEY,
    deal_id     INTEGER NOT NULL REFERENCES deals (id),
    note        TEXT NOT NULL CHECK (length(trim(note)) > 0 AND length(note) <= 300),
    entered_by  TEXT NOT NULL CHECK (length(trim(entered_by)) > 0),
    deadline    TEXT CHECK (deadline IS NULL OR deadline GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS signing_flags (
    id          INTEGER PRIMARY KEY,
    deal_id     INTEGER NOT NULL REFERENCES deals (id),
    issue_id    INTEGER NOT NULL REFERENCES issues (id),
    flagged_by  TEXT NOT NULL CHECK (length(trim(flagged_by)) > 0),
    reason      TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS flag_clearances (
    id          INTEGER PRIMARY KEY,
    flag_id     INTEGER NOT NULL UNIQUE REFERENCES signing_flags (id),
    cleared_by  TEXT NOT NULL CHECK (length(trim(cleared_by)) > 0),
    reason      TEXT NOT NULL CHECK (length(trim(reason)) > 0),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS deal_notes_append_only_u BEFORE UPDATE ON deal_notes
BEGIN SELECT RAISE(ABORT, 'deal notes are append-only; record a new one'); END;
CREATE TRIGGER IF NOT EXISTS deal_notes_append_only_d BEFORE DELETE ON deal_notes
BEGIN SELECT RAISE(ABORT, 'deal notes are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS signing_flags_append_only_u BEFORE UPDATE ON signing_flags
BEGIN SELECT RAISE(ABORT, 'signing flags are append-only; clear a flag instead'); END;
CREATE TRIGGER IF NOT EXISTS signing_flags_append_only_d BEFORE DELETE ON signing_flags
BEGIN SELECT RAISE(ABORT, 'signing flags are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS flag_clearances_append_only_u BEFORE UPDATE ON flag_clearances
BEGIN SELECT RAISE(ABORT, 'flag clearances are append-only'); END;
CREATE TRIGGER IF NOT EXISTS flag_clearances_append_only_d BEFORE DELETE ON flag_clearances
BEGIN SELECT RAISE(ABORT, 'flag clearances are never deleted'); END;
