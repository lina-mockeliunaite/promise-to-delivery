-- Handover records (16 Oct, after Checkpoint 3 with a Delivery lead: "visibility, not workflow").
-- Additive and idempotent: applied on demand by handover.ensure_schema, like workspace_records_schema.sql.
-- The ledger's schema_version stays 1.
--
--   item_seen              "Seen by <name>" on one finding: someone has looked at it. Never a decision, never a fix.
--   handover_notes         the deal owner's handoff note (role 'sales') and the accepting Delivery lead's note
--                          (role 'delivery'); latest row per role wins
--   document_links         where a document lives (a Drive link), per document, latest row wins; the file itself is
--                          never copied or changed
--   handover_completions   one row per deal: handover complete, with a frozen snapshot of what was handed over.
--                          Once it exists the API refuses every change to the deal.
-- All append-only (triggers abort UPDATE and DELETE). None writes to issues or closure_checks, and none feeds the
-- review hashes: a note, a link or a "seen" never changes a finding and never marks the review out of date.

CREATE TABLE IF NOT EXISTS item_seen (
    id          INTEGER PRIMARY KEY,
    deal_id     INTEGER NOT NULL REFERENCES deals (id),
    issue_id    INTEGER NOT NULL REFERENCES issues (id),
    seen_by     TEXT NOT NULL CHECK (length(trim(seen_by)) > 0 AND length(seen_by) <= 120),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (issue_id, seen_by)
);

CREATE TABLE IF NOT EXISTS handover_notes (
    id          INTEGER PRIMARY KEY,
    deal_id     INTEGER NOT NULL REFERENCES deals (id),
    role        TEXT NOT NULL CHECK (role IN ('sales', 'delivery')),
    note        TEXT NOT NULL CHECK (length(trim(note)) > 0 AND length(note) <= 2000),
    entered_by  TEXT NOT NULL CHECK (length(trim(entered_by)) > 0 AND length(entered_by) <= 120),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS document_links (
    id          INTEGER PRIMARY KEY,
    deal_id     INTEGER NOT NULL REFERENCES deals (id),
    source_id   INTEGER NOT NULL REFERENCES sources (id),
    url         TEXT NOT NULL CHECK (url GLOB 'https://*' AND length(url) <= 2000),
    set_by      TEXT NOT NULL CHECK (length(trim(set_by)) > 0 AND length(set_by) <= 120),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS handover_completions (
    id             INTEGER PRIMARY KEY,
    deal_id        INTEGER NOT NULL UNIQUE REFERENCES deals (id),
    completed_by   TEXT NOT NULL CHECK (length(trim(completed_by)) > 0 AND length(completed_by) <= 120),
    snapshot_json  TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- signature recorded by a person (16 Oct): the deal is signed. The v2 pipeline reads draft contracts only, so signature
-- is a recorded fact, as a CRM would hold it. One per deal; Complete handover needs it.
CREATE TABLE IF NOT EXISTS deal_signatures (
    id           INTEGER PRIMARY KEY,
    deal_id      INTEGER NOT NULL UNIQUE REFERENCES deals (id),
    signed_on    TEXT NOT NULL CHECK (signed_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    recorded_by  TEXT NOT NULL CHECK (length(trim(recorded_by)) > 0 AND length(recorded_by) <= 120),
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS deal_signatures_append_only_u BEFORE UPDATE ON deal_signatures
BEGIN SELECT RAISE(ABORT, 'a recorded signature is not changed'); END;
CREATE TRIGGER IF NOT EXISTS deal_signatures_append_only_d BEFORE DELETE ON deal_signatures
BEGIN SELECT RAISE(ABORT, 'a recorded signature is never deleted'); END;

-- resolved by a note (16 Oct): a named person says a gap is settled without a document (e.g. agreed on a call). Shown
-- apart from gaps closed by the documents, labelled "not in the documents". Bound to the document set at the time: when
-- the documents change, it no longer counts and the gap is open again until someone re-confirms. Latest row wins.
CREATE TABLE IF NOT EXISTS note_resolutions (
    id                 INTEGER PRIMARY KEY,
    deal_id            INTEGER NOT NULL REFERENCES deals (id),
    issue_id           INTEGER NOT NULL REFERENCES issues (id),
    resolved_by        TEXT NOT NULL CHECK (length(trim(resolved_by)) > 0 AND length(resolved_by) <= 120),
    reason             TEXT NOT NULL CHECK (length(trim(reason)) > 0 AND length(reason) <= 2000),
    source_set_sha256  TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS note_resolutions_append_only_u BEFORE UPDATE ON note_resolutions
BEGIN SELECT RAISE(ABORT, 'note resolutions are append-only'); END;
CREATE TRIGGER IF NOT EXISTS note_resolutions_append_only_d BEFORE DELETE ON note_resolutions
BEGIN SELECT RAISE(ABORT, 'note resolutions are never deleted'); END;

CREATE TRIGGER IF NOT EXISTS item_seen_append_only_u BEFORE UPDATE ON item_seen
BEGIN SELECT RAISE(ABORT, 'seen marks are append-only'); END;
CREATE TRIGGER IF NOT EXISTS item_seen_append_only_d BEFORE DELETE ON item_seen
BEGIN SELECT RAISE(ABORT, 'seen marks are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS handover_notes_append_only_u BEFORE UPDATE ON handover_notes
BEGIN SELECT RAISE(ABORT, 'handover notes are append-only; record a new one'); END;
CREATE TRIGGER IF NOT EXISTS handover_notes_append_only_d BEFORE DELETE ON handover_notes
BEGIN SELECT RAISE(ABORT, 'handover notes are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS document_links_append_only_u BEFORE UPDATE ON document_links
BEGIN SELECT RAISE(ABORT, 'document links are append-only; set a new one'); END;
CREATE TRIGGER IF NOT EXISTS document_links_append_only_d BEFORE DELETE ON document_links
BEGIN SELECT RAISE(ABORT, 'document links are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS handover_completions_immutable_u BEFORE UPDATE ON handover_completions
BEGIN SELECT RAISE(ABORT, 'a completed handover is frozen'); END;
CREATE TRIGGER IF NOT EXISTS handover_completions_immutable_d BEFORE DELETE ON handover_completions
BEGIN SELECT RAISE(ABORT, 'a completed handover is never deleted'); END;
