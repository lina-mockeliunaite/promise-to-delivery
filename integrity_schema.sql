-- Decision integrity (6 Oct). Additive and idempotent: applied on demand by integrity.ensure_schema, so the ledger's
-- schema_version stays 1 and an existing database keeps its data. See DECISIONS.md (5 Oct integrity rules) and
-- docs/BRIEF_2026-10-06_integrity.md.
--
-- Everything here is append-only (BEFORE UPDATE / BEFORE DELETE triggers abort), like fixes and handoff_versions.
-- Nothing here writes to issues or closure_checks, and none of it is read by decision_evidence_sha256: recording a
-- human opinion never changes a finding and never marks the review out of date.

-- The hash definition a review was made under, its definition-2 config hash, the extraction key each source used,
-- and whether its inputs differed from the previous review (NULL for a first review).
CREATE TABLE IF NOT EXISTS review_bindings (
    review_id        INTEGER PRIMARY KEY REFERENCES reviews (id),
    hash_definition  INTEGER NOT NULL CHECK (hash_definition >= 2),
    config_sha256    TEXT NOT NULL CHECK (length(config_sha256) = 64 AND config_sha256 NOT GLOB '*[^0-9a-f]*'),
    extraction_keys  TEXT NOT NULL CHECK (json_valid(extraction_keys)),
    inputs_changed   INTEGER CHECK (inputs_changed IS NULL OR inputs_changed IN (0, 1)),
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- The three hashes a saved decision was made against. One row per decision.
CREATE TABLE IF NOT EXISTS decision_bindings (
    id                       INTEGER PRIMARY KEY,
    decision_kind            TEXT NOT NULL CHECK (decision_kind IN ('handoff', 'accepted_risk', 'impact_assessment', 'accountability')),
    decision_id              INTEGER NOT NULL,
    hash_definition          INTEGER NOT NULL CHECK (hash_definition >= 2),
    source_set_sha256        TEXT NOT NULL CHECK (length(source_set_sha256) = 64 AND source_set_sha256 NOT GLOB '*[^0-9a-f]*'),
    decision_evidence_sha256 TEXT NOT NULL CHECK (length(decision_evidence_sha256) = 64 AND decision_evidence_sha256 NOT GLOB '*[^0-9a-f]*'),
    config_sha256            TEXT NOT NULL CHECK (length(config_sha256) = 64 AND config_sha256 NOT GLOB '*[^0-9a-f]*'),
    created_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (decision_kind, decision_id)
);

-- issue_context: a hash of what the issue was about when the record was made (its type and subject, the commitment's
-- terms, the quotes behind it and the conflicting side, the evidence of its latest closure check).
CREATE TABLE IF NOT EXISTS accepted_risks (
    id            INTEGER PRIMARY KEY,
    deal_id       INTEGER NOT NULL REFERENCES deals (id),
    issue_id      INTEGER NOT NULL REFERENCES issues (id),
    accepted_by   TEXT NOT NULL CHECK (length(trim(accepted_by)) > 0),
    rationale     TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
    issue_context TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS impact_assessments (
    id            INTEGER PRIMARY KEY,
    deal_id       INTEGER NOT NULL REFERENCES deals (id),
    issue_id      INTEGER NOT NULL REFERENCES issues (id),
    impact        TEXT NOT NULL CHECK (impact IN ('material', 'no_material_impact', 'unknown')),
    assessed_by   TEXT NOT NULL CHECK (length(trim(assessed_by)) > 0),
    note          TEXT,
    issue_context TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

-- evidence_check_id: the latest closure check of the issue when the person was set; ownership carries forward only
-- while the context is unchanged and no check has closed the issue since.
CREATE TABLE IF NOT EXISTS accountability (
    id                INTEGER PRIMARY KEY,
    deal_id           INTEGER NOT NULL REFERENCES deals (id),
    issue_id          INTEGER NOT NULL REFERENCES issues (id),
    person            TEXT NOT NULL CHECK (length(trim(person)) > 0),
    deadline          TEXT CHECK (deadline IS NULL OR deadline GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    set_by            TEXT NOT NULL CHECK (length(trim(set_by)) > 0),
    kind              TEXT NOT NULL CHECK (kind IN ('set', 'confirmed')),
    issue_context     TEXT NOT NULL,
    evidence_check_id INTEGER REFERENCES closure_checks (id),
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TRIGGER IF NOT EXISTS review_bindings_append_only_u BEFORE UPDATE ON review_bindings
BEGIN SELECT RAISE(ABORT, 'review_bindings are append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_bindings_append_only_d BEFORE DELETE ON review_bindings
BEGIN SELECT RAISE(ABORT, 'review_bindings are append-only'); END;
CREATE TRIGGER IF NOT EXISTS decision_bindings_append_only_u BEFORE UPDATE ON decision_bindings
BEGIN SELECT RAISE(ABORT, 'decision_bindings are append-only'); END;
CREATE TRIGGER IF NOT EXISTS decision_bindings_append_only_d BEFORE DELETE ON decision_bindings
BEGIN SELECT RAISE(ABORT, 'decision_bindings are append-only'); END;
CREATE TRIGGER IF NOT EXISTS accepted_risks_append_only_u BEFORE UPDATE ON accepted_risks
BEGIN SELECT RAISE(ABORT, 'accepted risks are append-only; record a new one'); END;
CREATE TRIGGER IF NOT EXISTS accepted_risks_append_only_d BEFORE DELETE ON accepted_risks
BEGIN SELECT RAISE(ABORT, 'accepted risks are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS impact_assessments_append_only_u BEFORE UPDATE ON impact_assessments
BEGIN SELECT RAISE(ABORT, 'impact assessments are append-only; record a new one'); END;
CREATE TRIGGER IF NOT EXISTS impact_assessments_append_only_d BEFORE DELETE ON impact_assessments
BEGIN SELECT RAISE(ABORT, 'impact assessments are never deleted'); END;
CREATE TRIGGER IF NOT EXISTS accountability_append_only_u BEFORE UPDATE ON accountability
BEGIN SELECT RAISE(ABORT, 'accountability records are append-only; record a new one'); END;
CREATE TRIGGER IF NOT EXISTS accountability_append_only_d BEFORE DELETE ON accountability
BEGIN SELECT RAISE(ABORT, 'accountability records are never deleted'); END;
