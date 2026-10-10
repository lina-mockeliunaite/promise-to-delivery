-- v2 detections (10 Oct 2026): what the model proposed for each v2 review and what the code accepted or rejected.
-- Additive: created with IF NOT EXISTS, never alters an existing table. Append-only.
CREATE TABLE IF NOT EXISTS v2_detections (
    review_id      INTEGER PRIMARY KEY REFERENCES reviews (id),
    input_sha256   TEXT NOT NULL CHECK (length(input_sha256) = 64 AND input_sha256 NOT GLOB '*[^0-9a-f]*'),
    origin         TEXT NOT NULL CHECK (origin IN ('model_call', 'cache', 'seed', 'previous_review')),
    v2_version     INTEGER NOT NULL,
    findings_json  TEXT NOT NULL CHECK (json_valid(findings_json)),
    accepted_json  TEXT NOT NULL CHECK (json_valid(accepted_json)),
    rejected_json  TEXT NOT NULL CHECK (json_valid(rejected_json)),
    cost_usd       REAL,
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS v2_detections_append_only_u BEFORE UPDATE ON v2_detections
BEGIN SELECT RAISE(ABORT, 'v2_detections are append-only'); END;
CREATE TRIGGER IF NOT EXISTS v2_detections_append_only_d BEFORE DELETE ON v2_detections
BEGIN SELECT RAISE(ABORT, 'v2_detections are append-only'); END;
