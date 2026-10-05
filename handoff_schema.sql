-- Saved handoff versions. Additive and idempotent: applied on demand by handoff.ensure_schema, so the ledger's
-- schema_version stays 1 and an existing database keeps its data. See DECISIONS.md (5 Oct, handoff).
-- A version is a frozen snapshot of one specific review. Immutable: BEFORE UPDATE / BEFORE DELETE triggers abort.
-- The snapshot holds the reviewer's per-issue owner confirmations; nothing here touches the issues table.

CREATE TABLE IF NOT EXISTS handoff_versions (
    id                       INTEGER PRIMARY KEY,
    deal_id                  INTEGER NOT NULL REFERENCES deals (id),
    version_no               INTEGER NOT NULL CHECK (version_no >= 1),
    review_id                INTEGER NOT NULL REFERENCES reviews (id),
    source_set_sha256        TEXT CHECK (source_set_sha256 IS NULL OR (length(source_set_sha256) = 64 AND source_set_sha256 NOT GLOB '*[^0-9a-f]*')),
    decision_evidence_sha256 TEXT CHECK (decision_evidence_sha256 IS NULL OR (length(decision_evidence_sha256) = 64 AND decision_evidence_sha256 NOT GLOB '*[^0-9a-f]*')),
    decision                 TEXT NOT NULL CHECK (decision IN ('ready', 'proceed', 'not_ready')),
    reviewer                 TEXT NOT NULL CHECK (length(trim(reviewer)) > 0),
    decided_on               TEXT NOT NULL CHECK (decided_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    note                     TEXT,
    snapshot_json            TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (deal_id, version_no)
);

CREATE TRIGGER IF NOT EXISTS handoff_versions_immutable_u BEFORE UPDATE ON handoff_versions
BEGIN SELECT RAISE(ABORT, 'saved handoff versions are immutable; save a new version'); END;
CREATE TRIGGER IF NOT EXISTS handoff_versions_immutable_d BEFORE DELETE ON handoff_versions
BEGIN SELECT RAISE(ABORT, 'saved handoff versions are never deleted'); END;
