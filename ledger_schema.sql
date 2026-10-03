-- Ledger schema, schema_version = 1. Written once (3 Oct); see docs/LEDGER_SCHEMA.md.
-- Run on a connection with PRAGMA foreign_keys = ON (ledger.connect does this).
-- Hashes are lowercase SHA-256 hex. Timestamps are ISO-8601 UTC text. No filesystem paths are stored.
-- "Immutable" = BEFORE UPDATE / BEFORE DELETE triggers that abort. State is derived in views, never stored.

CREATE TABLE schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
INSERT INTO schema_meta (key, value) VALUES ('schema_version', '1');

-- 1 ---------------------------------------------------------------------------------------------
CREATE TABLE deals (
    id           INTEGER PRIMARY KEY,
    slug         TEXT NOT NULL UNIQUE,
    kind         TEXT NOT NULL CHECK (kind IN ('development', 'user')),
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- User slugs: u_ + 16 hex. Development slugs never start u_, so the kinds cannot collide.
    -- Development slugs must also be in config.LEDGER_DEALS; that is checked in code (ledger.py).
    CHECK (
        (kind = 'user' AND length(slug) = 18 AND slug GLOB 'u_*' AND substr(slug, 3) NOT GLOB '*[^0-9a-f]*')
        OR (kind = 'development' AND slug NOT GLOB 'u_*')
    )
);

-- 2 ---------------------------------------------------------------------------------------------
CREATE TABLE sources (
    id           INTEGER PRIMARY KEY,
    deal_id      INTEGER NOT NULL REFERENCES deals (id),
    source_key   TEXT NOT NULL,
    display_name TEXT NOT NULL,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (deal_id, source_key)
);

-- 3 ---------------------------------------------------------------------------------------------
-- doc_type is validated in code against config; there is deliberately no CHECK list.
CREATE TABLE source_versions (
    id                INTEGER PRIMARY KEY,
    source_id         INTEGER NOT NULL REFERENCES sources (id),
    version_no        INTEGER NOT NULL CHECK (version_no >= 1),
    original_sha256   TEXT NOT NULL CHECK (length(original_sha256) = 64 AND original_sha256 NOT GLOB '*[^0-9a-f]*'),
    canonical_sha256  TEXT NOT NULL CHECK (length(canonical_sha256) = 64 AND canonical_sha256 NOT GLOB '*[^0-9a-f]*'),
    adapter_name      TEXT NOT NULL,
    adapter_version   TEXT NOT NULL,
    doc_type          TEXT NOT NULL,
    doc_date          TEXT NOT NULL CHECK (doc_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    original_filename TEXT NOT NULL,
    canonical_text    TEXT NOT NULL,
    location_map      TEXT NOT NULL CHECK (json_valid(location_map)),
    included          INTEGER NOT NULL DEFAULT 1 CHECK (included IN (0, 1)),
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (source_id, version_no)
);

-- Immutable except `included`, the current selection.
CREATE TRIGGER source_versions_immutable BEFORE UPDATE OF
    id, source_id, version_no, original_sha256, canonical_sha256, adapter_name, adapter_version,
    doc_type, doc_date, original_filename, canonical_text, location_map, created_at
ON source_versions
BEGIN SELECT RAISE(ABORT, 'source_versions are immutable except included'); END;

CREATE TRIGGER source_versions_no_delete BEFORE DELETE ON source_versions
BEGIN SELECT RAISE(ABORT, 'source_versions are never deleted'); END;

-- 5 (created before 4, which points at it) ------------------------------------------------------
-- Hash columns are nullable so a build-time review is not forced to invent a value.
CREATE TABLE reviews (
    id                       INTEGER PRIMARY KEY,
    deal_id                  INTEGER NOT NULL REFERENCES deals (id),
    run_kind                 TEXT NOT NULL CHECK (run_kind IN ('review', 'recheck_after_fix', 'unchanged_input_rerun', 'fresh_model_run')),
    checker                  TEXT NOT NULL CHECK (checker IN ('rules', 'agent')),
    config_sha256            TEXT CHECK (config_sha256 IS NULL OR (length(config_sha256) = 64 AND config_sha256 NOT GLOB '*[^0-9a-f]*')),
    source_set_sha256        TEXT CHECK (source_set_sha256 IS NULL OR (length(source_set_sha256) = 64 AND source_set_sha256 NOT GLOB '*[^0-9a-f]*')),
    decision_evidence_sha256 TEXT CHECK (decision_evidence_sha256 IS NULL OR (length(decision_evidence_sha256) = 64 AND decision_evidence_sha256 NOT GLOB '*[^0-9a-f]*')),
    triggered_by_fix_id      INTEGER REFERENCES fixes (id),
    status                   TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'complete', 'failed')),
    started_at               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at              TEXT,
    cost_usd                 REAL,
    note                     TEXT
);

-- A review can change only while it is running.
CREATE TRIGGER reviews_frozen_after_running BEFORE UPDATE ON reviews
WHEN OLD.status <> 'running'
BEGIN SELECT RAISE(ABORT, 'a finished review is immutable'); END;

CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews
BEGIN SELECT RAISE(ABORT, 'reviews are never deleted'); END;

-- 4 ---------------------------------------------------------------------------------------------
-- target_source_id is NULL when status = 'missing' (no target source exists).
CREATE TABLE reference_resolutions (
    id                  INTEGER PRIMARY KEY,
    review_id           INTEGER NOT NULL REFERENCES reviews (id),
    from_version_id     INTEGER NOT NULL REFERENCES source_versions (id),
    from_locator        TEXT,
    target_source_id    INTEGER REFERENCES sources (id),
    target_locator      TEXT,
    cited_label         TEXT NOT NULL,
    cited_date          TEXT CHECK (cited_date IS NULL OR cited_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    resolved_version_id INTEGER REFERENCES source_versions (id),
    status              TEXT NOT NULL CHECK (status IN ('resolved', 'unresolved', 'missing')),
    reason              TEXT,
    CHECK ((status = 'resolved') = (resolved_version_id IS NOT NULL))
);

CREATE TRIGGER reference_resolutions_append_only_u BEFORE UPDATE ON reference_resolutions
BEGIN SELECT RAISE(ABORT, 'reference_resolutions are append-only'); END;
CREATE TRIGGER reference_resolutions_append_only_d BEFORE DELETE ON reference_resolutions
BEGIN SELECT RAISE(ABORT, 'reference_resolutions are append-only'); END;

-- 7 (before 6, which points at it) --------------------------------------------------------------
-- Imported run-file rows: origin = 'imported_run_file', reusable = 0, key_sha256 and missing key fields NULL.
CREATE TABLE extraction_cache (
    id                   INTEGER PRIMARY KEY,
    key_sha256           TEXT CHECK (key_sha256 IS NULL OR (length(key_sha256) = 64 AND key_sha256 NOT GLOB '*[^0-9a-f]*')),
    canonical_sha256     TEXT CHECK (canonical_sha256 IS NULL OR (length(canonical_sha256) = 64 AND canonical_sha256 NOT GLOB '*[^0-9a-f]*')),
    doc_type             TEXT,
    context_sha256       TEXT CHECK (context_sha256 IS NULL OR (length(context_sha256) = 64 AND context_sha256 NOT GLOB '*[^0-9a-f]*')),
    system_prompt_sha256 TEXT,
    user_template_sha256 TEXT,
    schema_sha256        TEXT,
    model_id             TEXT,
    thinking_mode        TEXT,
    thinking_param_sent  TEXT CHECK (thinking_param_sent IS NULL OR thinking_param_sent = 'none' OR json_valid(thinking_param_sent)),
    max_tokens           INTEGER,
    cache_format_version TEXT,
    output_json          TEXT NOT NULL CHECK (json_valid(output_json)),
    usage_json           TEXT CHECK (usage_json IS NULL OR json_valid(usage_json)),
    cost_usd             REAL,
    origin               TEXT NOT NULL CHECK (origin IN ('model_call', 'fresh_run', 'imported_run_file')),
    source_run_file      TEXT,
    reusable             INTEGER NOT NULL DEFAULT 0 CHECK (reusable IN (0, 1)),
    created_at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- Only complete model-call extractions with a full key are reusable. (Completeness is checked in code.)
    CHECK (
        reusable = 0
        OR (
            origin = 'model_call'
            AND key_sha256 IS NOT NULL AND canonical_sha256 IS NOT NULL AND doc_type IS NOT NULL
            AND context_sha256 IS NOT NULL AND system_prompt_sha256 IS NOT NULL
            AND user_template_sha256 IS NOT NULL AND schema_sha256 IS NOT NULL AND model_id IS NOT NULL
            AND thinking_mode IS NOT NULL AND thinking_param_sent IS NOT NULL AND max_tokens IS NOT NULL
            AND cache_format_version IS NOT NULL
        )
    )
);

-- Fresh runs and imports can store output without overwriting a reusable entry.
CREATE UNIQUE INDEX extraction_cache_reusable_key ON extraction_cache (key_sha256) WHERE reusable = 1;

CREATE TRIGGER extraction_cache_append_only_u BEFORE UPDATE ON extraction_cache
BEGIN SELECT RAISE(ABORT, 'extraction_cache is append-only'); END;
CREATE TRIGGER extraction_cache_append_only_d BEFORE DELETE ON extraction_cache
BEGIN SELECT RAISE(ABORT, 'extraction_cache is append-only'); END;

-- 6 ---------------------------------------------------------------------------------------------
CREATE TABLE review_sources (
    review_id         INTEGER NOT NULL REFERENCES reviews (id),
    source_version_id INTEGER NOT NULL REFERENCES source_versions (id),
    extraction_id     INTEGER REFERENCES extraction_cache (id),
    cache_outcome     TEXT NOT NULL CHECK (cache_outcome IN ('hit', 'miss_called', 'imported', 'not_extracted')),
    PRIMARY KEY (review_id, source_version_id),
    CHECK ((cache_outcome = 'not_extracted') = (extraction_id IS NULL))
);

CREATE TRIGGER review_sources_append_only_u BEFORE UPDATE ON review_sources
BEGIN SELECT RAISE(ABORT, 'review_sources are append-only'); END;
CREATE TRIGGER review_sources_append_only_d BEFORE DELETE ON review_sources
BEGIN SELECT RAISE(ABORT, 'review_sources are append-only'); END;

-- 8 ---------------------------------------------------------------------------------------------
CREATE TABLE statements (
    id             INTEGER PRIMARY KEY,
    extraction_id  INTEGER NOT NULL REFERENCES extraction_cache (id),
    ordinal        INTEGER NOT NULL CHECK (ordinal >= 1),
    statement_key  TEXT NOT NULL,
    quote          TEXT NOT NULL,
    speaker        TEXT,
    language       TEXT NOT NULL CHECK (language IN ('exploratory', 'conditional', 'firm')),
    quote_location TEXT CHECK (quote_location IS NULL OR json_valid(quote_location)),
    UNIQUE (extraction_id, ordinal)
);

CREATE TRIGGER statements_immutable_u BEFORE UPDATE ON statements
BEGIN SELECT RAISE(ABORT, 'statements are immutable'); END;
CREATE TRIGGER statements_immutable_d BEFORE DELETE ON statements
BEGIN SELECT RAISE(ABORT, 'statements are immutable'); END;

-- 9 ---------------------------------------------------------------------------------------------
-- Which commitment a kept statement belongs to lives in review_statement_commitments (many-to-many).
CREATE TABLE review_statements (
    review_id         INTEGER NOT NULL REFERENCES reviews (id),
    statement_id      INTEGER NOT NULL REFERENCES statements (id),
    source_version_id INTEGER NOT NULL REFERENCES source_versions (id),
    kept              INTEGER NOT NULL CHECK (kept IN (0, 1)),
    filter_rule       TEXT,
    PRIMARY KEY (review_id, statement_id, source_version_id),
    FOREIGN KEY (review_id, source_version_id) REFERENCES review_sources (review_id, source_version_id),
    CHECK (kept = 1 OR filter_rule IS NOT NULL)
);

-- The statement must come from the extraction this review used for that source version.
CREATE TRIGGER review_statements_identity BEFORE INSERT ON review_statements
WHEN NOT EXISTS (
    SELECT 1
    FROM review_sources rsrc
    JOIN statements s ON s.extraction_id = rsrc.extraction_id
    WHERE rsrc.review_id = NEW.review_id
      AND rsrc.source_version_id = NEW.source_version_id
      AND s.id = NEW.statement_id
)
BEGIN SELECT RAISE(ABORT, 'statement is not from the extraction this review used for that source version'); END;

-- An already-linked statement cannot be changed to dropped. (Changing its key columns is blocked by the
-- link table's foreign key.)
CREATE TRIGGER review_statements_linked_stay_kept BEFORE UPDATE OF kept ON review_statements
WHEN OLD.kept = 1 AND NEW.kept = 0 AND EXISTS (
    SELECT 1 FROM review_statement_commitments l
    WHERE l.review_id = OLD.review_id AND l.statement_id = OLD.statement_id AND l.source_version_id = OLD.source_version_id
)
BEGIN SELECT RAISE(ABORT, 'a statement linked to a commitment cannot be dropped'); END;

-- 10 --------------------------------------------------------------------------------------------
CREATE TABLE commitments (
    id                INTEGER PRIMARY KEY,
    deal_id           INTEGER NOT NULL REFERENCES deals (id),
    commitment_key    TEXT NOT NULL,
    created_review_id INTEGER NOT NULL REFERENCES reviews (id),
    note              TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (deal_id, commitment_key)
);

CREATE TRIGGER commitments_same_deal BEFORE INSERT ON commitments
WHEN (SELECT deal_id FROM reviews WHERE id = NEW.created_review_id) IS NOT NEW.deal_id
BEGIN SELECT RAISE(ABORT, 'commitment and its creating review must belong to the same deal'); END;

CREATE TRIGGER commitments_only_note_changes BEFORE UPDATE OF id, deal_id, commitment_key, created_review_id, created_at ON commitments
BEGIN SELECT RAISE(ABORT, 'only commitments.note can change'); END;
CREATE TRIGGER commitments_no_delete BEFORE DELETE ON commitments
BEGIN SELECT RAISE(ABORT, 'commitments are never deleted'); END;

-- 9b: statement -> commitment links (many-to-many) ----------------------------------------------
-- Only kept = 1 statements can be linked, and the commitment must belong to the review's deal.
CREATE TABLE review_statement_commitments (
    review_id         INTEGER NOT NULL,
    statement_id      INTEGER NOT NULL,
    source_version_id INTEGER NOT NULL,
    commitment_id     INTEGER NOT NULL REFERENCES commitments (id),
    PRIMARY KEY (review_id, statement_id, source_version_id, commitment_id),
    FOREIGN KEY (review_id, statement_id, source_version_id)
        REFERENCES review_statements (review_id, statement_id, source_version_id)
);

CREATE TRIGGER rsc_requires_kept BEFORE INSERT ON review_statement_commitments
WHEN NOT EXISTS (
    SELECT 1 FROM review_statements rs
    WHERE rs.review_id = NEW.review_id AND rs.statement_id = NEW.statement_id
      AND rs.source_version_id = NEW.source_version_id AND rs.kept = 1
)
BEGIN SELECT RAISE(ABORT, 'only a kept statement can be linked to a commitment'); END;

CREATE TRIGGER rsc_same_deal BEFORE INSERT ON review_statement_commitments
WHEN (SELECT deal_id FROM commitments WHERE id = NEW.commitment_id)
     IS NOT (SELECT deal_id FROM reviews WHERE id = NEW.review_id)
BEGIN SELECT RAISE(ABORT, 'commitment and review must belong to the same deal'); END;

CREATE TRIGGER rsc_append_only_u BEFORE UPDATE ON review_statement_commitments
BEGIN SELECT RAISE(ABORT, 'statement-commitment links are append-only'); END;
CREATE TRIGGER rsc_append_only_d BEFORE DELETE ON review_statement_commitments
BEGIN SELECT RAISE(ABORT, 'statement-commitment links are append-only'); END;

-- 11 --------------------------------------------------------------------------------------------
-- authorisation: NULL means not applicable (exploratory/conditional only). 'not_assessed' means the
-- rules have not run yet. contractual_presence is never NULL; 'not_assessed' is its unassessed value.
-- Rules must handle 'not_assessed' explicitly and never treat it as absent.
CREATE TABLE commitment_assessments (
    id                     INTEGER PRIMARY KEY,
    review_id              INTEGER NOT NULL REFERENCES reviews (id),
    commitment_id          INTEGER NOT NULL REFERENCES commitments (id),
    name                   TEXT NOT NULL,
    language               TEXT NOT NULL CHECK (language IN ('exploratory', 'conditional', 'firm')),
    authorisation          TEXT DEFAULT 'not_assessed' CHECK (
        authorisation IS NULL
        OR authorisation IN ('standard_authorised', 'exception_approved', 'no_approval_evidence', 'unknown_needs_review', 'not_assessed')
    ),
    authorisation_evidence TEXT,
    evidence_refs          TEXT CHECK (evidence_refs IS NULL OR json_valid(evidence_refs)),
    contractual_presence   TEXT NOT NULL DEFAULT 'not_assessed'
        CHECK (contractual_presence IN ('absent', 'included_in_draft_contract', 'not_assessed')),
    presence_detail        TEXT,
    support_state          TEXT NOT NULL CHECK (support_state IN ('supported', 'unsupported')),
    rationale              TEXT,
    -- Consolidation snapshot: the group key (null when incomplete), terms_incomplete and what is missing, each
    -- member's term set and attributes (dates, cadence, go-live date), and the hash of the rules that built it.
    terms                  TEXT CHECK (terms IS NULL OR json_valid(terms)),
    UNIQUE (review_id, commitment_id)
);

CREATE TRIGGER commitment_assessments_same_deal BEFORE INSERT ON commitment_assessments
WHEN (SELECT deal_id FROM commitments WHERE id = NEW.commitment_id)
     IS NOT (SELECT deal_id FROM reviews WHERE id = NEW.review_id)
BEGIN SELECT RAISE(ABORT, 'commitment and review must belong to the same deal'); END;

CREATE TRIGGER commitment_assessments_append_only_u BEFORE UPDATE ON commitment_assessments
BEGIN SELECT RAISE(ABORT, 'commitment_assessments are append-only'); END;
CREATE TRIGGER commitment_assessments_append_only_d BEFORE DELETE ON commitment_assessments
BEGIN SELECT RAISE(ABORT, 'commitment_assessments are append-only'); END;

-- 12 --------------------------------------------------------------------------------------------
CREATE TABLE commitment_links (
    id                 INTEGER PRIMARY KEY,
    review_id          INTEGER NOT NULL REFERENCES reviews (id),
    from_commitment_id INTEGER NOT NULL REFERENCES commitments (id),
    to_commitment_id   INTEGER NOT NULL REFERENCES commitments (id),
    link_type          TEXT NOT NULL CHECK (link_type IN ('contract_side_of', 'supersedes', 'related')),
    basis              TEXT,
    UNIQUE (review_id, from_commitment_id, to_commitment_id, link_type),
    CHECK (from_commitment_id <> to_commitment_id)
);

CREATE TRIGGER commitment_links_same_deal BEFORE INSERT ON commitment_links
WHEN (SELECT deal_id FROM commitments WHERE id = NEW.from_commitment_id)
         IS NOT (SELECT deal_id FROM reviews WHERE id = NEW.review_id)
  OR (SELECT deal_id FROM commitments WHERE id = NEW.to_commitment_id)
         IS NOT (SELECT deal_id FROM reviews WHERE id = NEW.review_id)
BEGIN SELECT RAISE(ABORT, 'both commitments and the review must belong to the same deal'); END;

CREATE TRIGGER commitment_links_append_only_u BEFORE UPDATE ON commitment_links
BEGIN SELECT RAISE(ABORT, 'commitment_links are append-only'); END;
CREATE TRIGGER commitment_links_append_only_d BEFORE DELETE ON commitment_links
BEGIN SELECT RAISE(ABORT, 'commitment_links are append-only'); END;

-- 13 --------------------------------------------------------------------------------------------
-- No state column: state is derived in issue_current_state.
CREATE TABLE issues (
    id                  INTEGER PRIMARY KEY,
    commitment_id       INTEGER NOT NULL REFERENCES commitments (id),
    issue_type          TEXT NOT NULL CHECK (issue_type IN ('approval', 'contract_gap', 'conflicting_terms', 'missing_condition', 'insufficient_evidence')),
    subject_key         TEXT NOT NULL,
    owner_function      TEXT NOT NULL CHECK (owner_function IN ('Product', 'Commercial', 'Delivery', 'Customer Success', 'Support')),
    note                TEXT,
    raised_review_id    INTEGER NOT NULL REFERENCES reviews (id),
    raised_by           TEXT NOT NULL CHECK (raised_by IN ('rules', 'agent')),
    raised_config_sha256 TEXT CHECK (raised_config_sha256 IS NULL OR (length(raised_config_sha256) = 64 AND raised_config_sha256 NOT GLOB '*[^0-9a-f]*')),
    closure_criteria    TEXT NOT NULL CHECK (json_valid(closure_criteria)),
    criteria_version    INTEGER NOT NULL,
    absolute_limit      INTEGER NOT NULL DEFAULT 0 CHECK (absolute_limit IN (0, 1)),
    created_at          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (commitment_id, issue_type, subject_key)
);

-- Only owner_function and note are editable: closure criteria cannot be loosened after the fact.
CREATE TRIGGER issues_only_owner_and_note_change BEFORE UPDATE OF
    id, commitment_id, issue_type, subject_key, raised_review_id, raised_by, raised_config_sha256,
    closure_criteria, criteria_version, absolute_limit, created_at
ON issues
BEGIN SELECT RAISE(ABORT, 'only issues.owner_function and issues.note can change'); END;
CREATE TRIGGER issues_no_delete BEFORE DELETE ON issues
BEGIN SELECT RAISE(ABORT, 'issues are never deleted'); END;

-- 14 --------------------------------------------------------------------------------------------
CREATE TABLE fixes (
    id                INTEGER PRIMARY KEY,
    deal_id           INTEGER NOT NULL REFERENCES deals (id),
    fix_key           TEXT NOT NULL,
    version_no        INTEGER NOT NULL CHECK (version_no >= 1),
    supersedes_fix_id INTEGER REFERENCES fixes (id),
    route             TEXT NOT NULL CHECK (route IN ('align_documents', 'allowed_exception', 'change_or_withdraw_promise')),
    owner_function    TEXT NOT NULL CHECK (owner_function IN ('Product', 'Commercial', 'Delivery', 'Customer Success', 'Support')),
    rationale         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'approved')),
    approved_at       TEXT,
    approved_by       TEXT,
    created_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (deal_id, fix_key, version_no),
    CHECK (status = 'draft' OR (approved_at IS NOT NULL AND approved_by IS NOT NULL))
);

-- A fix is created as a draft and approved by an update; approval needs its issues and evidence.
CREATE TRIGGER fixes_insert_as_draft BEFORE INSERT ON fixes
WHEN NEW.status <> 'draft'
BEGIN SELECT RAISE(ABORT, 'a fix is created as a draft and approved afterwards'); END;

CREATE TRIGGER fixes_approval_needs_issue BEFORE UPDATE OF status ON fixes
WHEN OLD.status = 'draft' AND NEW.status = 'approved'
 AND NOT EXISTS (SELECT 1 FROM fix_issues WHERE fix_id = NEW.id)
BEGIN SELECT RAISE(ABORT, 'approval needs at least one issue'); END;

CREATE TRIGGER fixes_approval_needs_evidence BEFORE UPDATE OF status ON fixes
WHEN OLD.status = 'draft' AND NEW.status = 'approved'
 AND NEW.route <> 'change_or_withdraw_promise'
 AND NOT EXISTS (SELECT 1 FROM fix_evidence WHERE fix_id = NEW.id)
BEGIN SELECT RAISE(ABORT, 'approval needs at least one piece of evidence for this route'); END;

CREATE TRIGGER fixes_approved_immutable_u BEFORE UPDATE ON fixes
WHEN OLD.status = 'approved'
BEGIN SELECT RAISE(ABORT, 'approved fixes are immutable; add a new version'); END;
CREATE TRIGGER fixes_approved_immutable_d BEFORE DELETE ON fixes
WHEN OLD.status = 'approved'
BEGIN SELECT RAISE(ABORT, 'approved fixes are immutable'); END;

-- 15 --------------------------------------------------------------------------------------------
CREATE TABLE fix_issues (
    fix_id   INTEGER NOT NULL REFERENCES fixes (id),
    issue_id INTEGER NOT NULL REFERENCES issues (id),
    PRIMARY KEY (fix_id, issue_id)
);

CREATE TRIGGER fix_issues_frozen_i BEFORE INSERT ON fix_issues
WHEN (SELECT status FROM fixes WHERE id = NEW.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_issues of an approved fix are immutable'); END;
CREATE TRIGGER fix_issues_frozen_u BEFORE UPDATE ON fix_issues
WHEN (SELECT status FROM fixes WHERE id = OLD.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_issues of an approved fix are immutable'); END;
CREATE TRIGGER fix_issues_frozen_d BEFORE DELETE ON fix_issues
WHEN (SELECT status FROM fixes WHERE id = OLD.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_issues of an approved fix are immutable'); END;

-- 16 --------------------------------------------------------------------------------------------
CREATE TABLE fix_evidence (
    id                INTEGER PRIMARY KEY,
    fix_id            INTEGER NOT NULL REFERENCES fixes (id),
    source_version_id INTEGER NOT NULL REFERENCES source_versions (id),
    locator           TEXT,
    note              TEXT
);

CREATE TRIGGER fix_evidence_frozen_i BEFORE INSERT ON fix_evidence
WHEN (SELECT status FROM fixes WHERE id = NEW.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_evidence of an approved fix is immutable'); END;
CREATE TRIGGER fix_evidence_frozen_u BEFORE UPDATE ON fix_evidence
WHEN (SELECT status FROM fixes WHERE id = OLD.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_evidence of an approved fix is immutable'); END;
CREATE TRIGGER fix_evidence_frozen_d BEFORE DELETE ON fix_evidence
WHEN (SELECT status FROM fixes WHERE id = OLD.fix_id) = 'approved'
BEGIN SELECT RAISE(ABORT, 'fix_evidence of an approved fix is immutable'); END;

-- 17 --------------------------------------------------------------------------------------------
CREATE TABLE closure_checks (
    id                INTEGER PRIMARY KEY,
    issue_id          INTEGER NOT NULL REFERENCES issues (id),
    review_id         INTEGER NOT NULL REFERENCES reviews (id),
    check_kind        TEXT NOT NULL CHECK (check_kind IN ('raised', 'recheck')),
    outcome           TEXT NOT NULL CHECK (outcome IN ('open_action', 'open_evidence', 'met')),
    evidence_checked  TEXT NOT NULL CHECK (json_valid(evidence_checked) AND json_type(evidence_checked) = 'array'),
    reason            TEXT NOT NULL,
    unmet             TEXT CHECK (unmet IS NULL OR json_valid(unmet)),
    re_raised         INTEGER NOT NULL DEFAULT 0 CHECK (re_raised IN (0, 1)),
    fix_id            INTEGER REFERENCES fixes (id),
    checked_at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    UNIQUE (issue_id, review_id),
    CHECK (outcome = 'met' OR unmet IS NOT NULL),
    CHECK (NOT (check_kind = 'raised' AND outcome = 'met')),
    CHECK (outcome <> 'met' OR json_array_length(evidence_checked) > 0)
);

-- An absolute limit is never closed by an allowed exception.
CREATE TRIGGER closure_checks_absolute_limit BEFORE INSERT ON closure_checks
WHEN NEW.outcome = 'met' AND NEW.fix_id IS NOT NULL
 AND (SELECT absolute_limit FROM issues WHERE id = NEW.issue_id) = 1
 AND (SELECT route FROM fixes WHERE id = NEW.fix_id) = 'allowed_exception'
BEGIN SELECT RAISE(ABORT, 'an absolute limit cannot be closed by an allowed exception'); END;

CREATE TRIGGER closure_checks_append_only_u BEFORE UPDATE ON closure_checks
BEGIN SELECT RAISE(ABORT, 'closure_checks are append-only'); END;
CREATE TRIGGER closure_checks_append_only_d BEFORE DELETE ON closure_checks
BEGIN SELECT RAISE(ABORT, 'closure_checks are append-only'); END;

-- Views -----------------------------------------------------------------------------------------
-- State follows the latest closure check. A `met` whose evidence now includes an excluded source version
-- shows Needs evidence, so removing a source never closes anything. An issue with no check yet is open.
CREATE VIEW issue_current_state AS
SELECT
    i.id AS issue_id,
    i.commitment_id,
    cc.id AS closure_check_id,
    cc.outcome AS latest_outcome,
    cc.re_raised,
    CASE
        WHEN cc.id IS NULL THEN 'Needs action'
        WHEN cc.outcome = 'met' AND EXISTS (
            SELECT 1
            FROM json_each(cc.evidence_checked) je
            JOIN source_versions sv ON sv.id = json_extract(je.value, '$.source_version_id')
            WHERE sv.included = 0
        ) THEN 'Needs evidence'
        WHEN cc.outcome = 'met' THEN 'Resolved'
        WHEN cc.outcome = 'open_action' THEN 'Needs action'
        ELSE 'Needs evidence'
    END AS state
FROM issues i
LEFT JOIN closure_checks cc
       ON cc.id = (SELECT MAX(id) FROM closure_checks WHERE issue_id = i.id);

-- Status comes from the latest assessment and the states of the commitment's issues. Open issues win:
-- an unsupported commitment (or one whose source was removed) never hides an open issue. In order:
-- Needs action, Needs evidence, Not in current documents, Resolved, No issues raised.
-- Resolved means the documented gap is closed, not that the work is operationally ready.
CREATE VIEW commitment_status AS
SELECT
    c.id AS commitment_id,
    a.id AS assessment_id,
    a.support_state,
    CASE
        WHEN a.id IS NULL THEN NULL
        WHEN EXISTS (
            SELECT 1 FROM issue_current_state s WHERE s.commitment_id = c.id AND s.state = 'Needs action'
        ) THEN 'Needs action'
        WHEN EXISTS (
            SELECT 1 FROM issue_current_state s WHERE s.commitment_id = c.id AND s.state = 'Needs evidence'
        ) THEN 'Needs evidence'
        WHEN a.support_state = 'unsupported' THEN 'Not in current documents'
        WHEN EXISTS (SELECT 1 FROM issues WHERE commitment_id = c.id) THEN 'Resolved'
        ELSE 'No issues raised'
    END AS status
FROM commitments c
LEFT JOIN commitment_assessments a
       ON a.id = (SELECT MAX(id) FROM commitment_assessments WHERE commitment_id = c.id);
