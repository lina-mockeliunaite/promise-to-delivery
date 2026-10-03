# Ledger schema (design)

*2 Oct 2026. Design only: no code, no migrations, no database file. Inputs: `docs/SCHEMA_BRIEF.md`, `docs/PLAN_v3.4.md`, DECISIONS.md (2026-09-30 Revision v3; 2026-10-02 seven design inputs), `schema.py`, `data/harbour_bank/labels/commitments.json`. Nothing under `data/coral_pay/` was read.*

*Status: this rests on a simulated review. The real Checkpoint 1 (deadline 5 Oct) may change it. Until 13 Oct the database is disposable: rebuilt from sources and run files, no data migrations.*

*3 Oct: the DDL is written (`ledger_schema.sql`, `schema_version = 1`). Decision 3 of `docs/BRIEF_2026-10-03.md` is applied: `review_statements.commitment_id` is replaced by the link table `review_statement_commitments` (3.10), so there are 18 tables.*

## 1. Principles

1. **Append-only history.** Reviews, source versions, statements, approved fixes and closure checks are never updated or deleted. Corrections add rows.
2. **Derived, not stored.** Issue state, commitment status and review freshness are views. No column holds them, so nothing can be set by hand.
3. **Per-review snapshots.** Anything the checker concludes (language, authorisation, contractual presence, reference resolution, filter outcome, consolidation) is written per review, so the step-1 picture survives step 3.
4. **Content-addressed where possible.** Hashes are lowercase SHA-256 hex (CHECK length 64). Extraction is keyed by what can change its output.
5. **One database, two kinds of deal.** `workspace/ledger.sqlite`: gitignored, outside `data/`, opened with `PRAGMA foreign_keys = ON`. Timestamps are ISO-8601 UTC text. The database never stores a filesystem path; paths are derived from the deal slug through the guarded path functions.

## 2. Build schedule at a glance

All DDL is written once, on 3 Oct, as one `schema_version = 1` script (plus `schema_meta(key, value)` for the version; plumbing, not counted). Behaviour is built in tranches. Tags:

- **3–4 Oct**: written and used by the filter, consolidation, rules and reference code.
- **12 Oct**: written and used by recheck, fixes, cache reuse and freshness.
- **Later**: none of the 18 tables. Later items are column contents and adapters (section 12).

| # | Table | Build | Note |
| --- | --- | --- | --- |
| 1 | `deals` | 3–4 Oct | Development rows 3 Oct; user rows 13 Oct (text/Markdown upload) |
| 2 | `sources` | 3–4 Oct | |
| 3 | `source_versions` | 3–4 Oct | Text/Markdown adapter only; other adapters 19–20 Oct fill the same columns |
| 4 | `reference_resolutions` | 3–4 Oct | 4 Oct rules |
| 5 | `reviews` | 3–4 Oct | `recheck_after_fix` and `unchanged_input_rerun` kinds used from 12 Oct |
| 6 | `review_sources` | 3–4 Oct | |
| 7 | `extraction_cache` | 3–4 Oct | Table and imported rows (`reusable = 0`) now; reuse logic 12 Oct |
| 8 | `statements` | 3–4 Oct | |
| 9 | `review_statements` | 3–4 Oct | |
| 10 | `review_statement_commitments` | 3–4 Oct | Many-to-many link from a kept statement to its commitments (3 Oct decision) |
| 11 | `commitments` | 3–4 Oct | |
| 12 | `commitment_assessments` | 3–4 Oct | |
| 13 | `commitment_links` | 12 Oct | Rules can emit links on 4 Oct, but nothing reads them before the register |
| 14 | `issues` | 3–4 Oct | 4 Oct rules |
| 15 | `fixes` | 12 Oct | |
| 16 | `fix_issues` | 12 Oct | |
| 17 | `fix_evidence` | 12 Oct | |
| 18 | `closure_checks` | 3–4 Oct | "raised" rows from 4 Oct; "recheck" rows 12 Oct |

Views: `issue_current_state` and `commitment_status` 3–4 Oct; `review_freshness` 12 Oct.

## 3. Tables

Types: `id` is `INTEGER PRIMARY KEY`; `*_id` are foreign keys; `TEXT` JSON columns hold JSON validated with `json_valid()` in a CHECK. "Immutable" is enforced by `BEFORE UPDATE`/`BEFORE DELETE` triggers that abort.

### 3.1 `deals`
`id`, `slug` (UNIQUE, NOT NULL), `kind` (CHECK `'development'|'user'`), `display_name`, `created_at`.
- Development slug: the folder name under `data/`. User slug: server-generated `u_` + 16 hex characters; the user's name is only `display_name` and never becomes a path.
- CHECK: `kind = 'user'` requires length 18, `slug GLOB 'u_*'` and only lowercase hex after the `u_`; `kind = 'development'` requires `slug NOT GLOB 'u_*'`. The two kinds therefore cannot collide.
- Development slugs must be in `config.LEDGER_DEALS` (section 10), checked in code at insert. The list lives in config, so there is no SQL CHECK for it.

### 3.2 `sources`
`id`, `deal_id`, `source_key` (e.g. `HB-01`; generated for user deals), `display_name`, `created_at`. UNIQUE(`deal_id`, `source_key`).

### 3.3 `source_versions` (the snapshot row)
`id`, `source_id`, `version_no` (UNIQUE with `source_id`), `original_sha256`, `canonical_sha256`, `adapter_name`, `adapter_version`, `doc_type`, `doc_date` (`YYYY-MM-DD`), `original_filename`, `canonical_text`, `location_map` (JSON), `included` (0/1), `created_at`.
- `doc_type` is validated in code against `config.EXTRACTABLE_DOC_TYPES + REFERENCE_ONLY_DOC_TYPES`. There is **no CHECK list**, because `security_questionnaire` is undecided until 4 Oct and the list belongs to `config.py`.
- Immutable except `included`, the current selection (what **Review deal** will use). Changing it is detected by comparing `source_set_sha256`, never by a stored flag.
- Originals: development deals read from `data/<deal>/docs/` (not copied); user deals store blobs by content hash under `workspace/`. `canonical_text` and `location_map` are stored so quotes can always be checked against the exact text reviewed.

### 3.4 `reference_resolutions`
`id`, `review_id`, `from_version_id`, `from_locator`, `target_source_id`, `target_locator`, `cited_label` (text as cited, e.g. "Statement of Work dated 20 October 2026"), `cited_date` (nullable), `resolved_version_id` (nullable), `status` (CHECK `'resolved'|'unresolved'|'missing'`), `reason`. `target_source_id` is nullable (NULL when `status = 'missing'`).
- **Resolution rule (decided):** a reference resolves by target source plus cited date: the newest *included* version of the target source whose `doc_date` equals `cited_date`. If no date is cited, the newest included version. No match for the date gives `unresolved` (the target source exists, but no version matches the citation). No target source gives `missing`.
- Rows are written per review, so a later review that sees a new version re-resolves. `status` ≠ `resolved` requires `resolved_version_id IS NULL`, and `resolved` requires it NOT NULL. Append-only.

### 3.5 `reviews`
`id`, `deal_id`, `run_kind` (CHECK `'review'|'recheck_after_fix'|'unchanged_input_rerun'|'fresh_model_run'`), `checker` (CHECK `'rules'|'agent'`), `config_sha256`, `source_set_sha256`, `decision_evidence_sha256`, `triggered_by_fix_id` (nullable), `status` (`running|complete|failed`), `started_at`, `finished_at`, `cost_usd`, `note`.
- `run_kind` `'review'` is the fourth kind beyond the brief's three: the **Review deal** button on a deal never reviewed, using the cache normally. Cache hits are recorded per document in `review_sources`, not in the kind.
- The three hash columns are nullable, so a build-time review is not forced to invent a value. A review can be updated only while `status = 'running'`; after that it is frozen. No DELETE.
- `config_sha256`: hash of the evaluated configuration (extraction hashes, filter, consolidation, rules or agent configuration).
- `source_set_sha256`: SHA-256 of the sorted lines `source_key:version_no:canonical_sha256:doc_type:doc_date` for every included version.
- `decision_evidence_sha256`: SHA-256 of the sorted `fix_key:version_no:source_version_id` for every evidence row of every *approved* fix. Owner, notes and draft fixes are excluded, so editing them never marks a review out of date.

### 3.6 `review_sources`
`review_id`, `source_version_id`, `extraction_id` (nullable), `cache_outcome` (CHECK `'hit'|'miss_called'|'imported'|'not_extracted'`). PK(`review_id`, `source_version_id`).
- `not_extracted` for reference-only types, with `extraction_id` NULL. `imported` means the rows came from an imported run file (`reusable = 0`); this is the build-time path on 3–4 Oct.

### 3.7 `extraction_cache`
`id`, `key_sha256` (nullable), key fields as columns: `canonical_sha256`, `doc_type`, `context_sha256` (nullable: no context today), `system_prompt_sha256`, `user_template_sha256`, `schema_sha256`, `model_id`, `thinking_mode`, `thinking_param_sent` (JSON or the text `none`), `max_tokens`, `cache_format_version`; then `output_json` (the model's reply: the `statements` list only), `usage_json` (input, output and thinking tokens, attempts), `cost_usd`, `origin` (CHECK `'model_call'|'fresh_run'|'imported_run_file'`), `source_run_file` (file name, nullable), `reusable` (0/1), `created_at`.
- `key_sha256` is the SHA-256 of the key fields as canonical JSON (sorted keys, no whitespace), the same style as the schema hash in `extract.py`.
- UNIQUE index on `key_sha256` **WHERE `reusable = 1`**. Fresh runs and imports can therefore store output without overwriting a reusable entry, and repeatability measurements can keep several outputs for one key.
- CHECK: `reusable = 1` requires every key field and `key_sha256` NOT NULL, `origin = 'model_call'`, and a complete extraction. Only complete extractions are cached. A hit's cost is recorded as cached (review level); the original `cost_usd` stays for audit.
- For `model_call` rows `output_json` is the model's reply. For `imported_run_file` rows it is the run file's stored statements for that document (with the code-attached fields), because the run file does not keep the raw reply. `thinking_param_sent` is `none` when the run file records null.
- On a hit, `source_id` and `date` are rebuilt from the source version, as DECISIONS 2026-09-30 specifies.

### 3.8 `statements`
`id`, `extraction_id`, `ordinal`, `statement_key` (derived: `<source_key>-S<ordinal>`), `quote`, `speaker`, `language` (CHECK `'exploratory'|'conditional'|'firm'`), `quote_location` (JSON, nullable). UNIQUE(`extraction_id`, `ordinal`). Immutable. These are the `Statement` fields from `schema.py`; the code-attached `statement_id`, `source_id`, `doc_type`, `date` come from joins.

### 3.9 `review_statements`
`review_id`, `statement_id`, `source_version_id`, `kept` (0/1), `filter_rule` (nullable). PK(`review_id`, `statement_id`, `source_version_id`). CHECK: `kept = 0` requires `filter_rule`. FK (`review_id`, `source_version_id`) to `review_sources`.
- `source_version_id` is part of the key because two versions with identical canonical text share one extraction.
- A filtered-out statement is kept visible here: nothing the filter removes is deleted.
- There is no commitment column. A statement can belong to more than one commitment (labels S04 and S11 each belong to two), so the link lives in 3.10.
- Trigger: the statement must come from the extraction this review used for that source version. Trigger: a statement with links cannot be changed from kept to dropped.

### 3.10 `review_statement_commitments`
`review_id`, `statement_id`, `source_version_id`, `commitment_id`. PK is all four columns. FK (`review_id`, `statement_id`, `source_version_id`) to `review_statements`; FK `commitment_id` to `commitments`.
- **Only kept statements have links**, enforced in the database: an insert trigger requires the `review_statements` row to exist with `kept = 1` and the commitment to belong to the review's deal. Changing a linked statement's `kept` from 1 to 0 is refused by trigger, and the foreign key blocks changes to its key columns.
- Append-only: no UPDATE, no DELETE. A different grouping is a new review.
- This replaces `review_statements.commitment_id` (3 Oct): the single column could not hold the labelled ground truth.

### 3.11 `commitments`
`id`, `deal_id`, `commitment_key` (UNIQUE with `deal_id`; `C01`…), `created_review_id`, `note` (editable), `created_at`.
- Stable identity only. **Identity across reviews:** consolidation in a later review assigns a group to an existing commitment when it shares at least one `(source_key, quote_sha256)` statement with that commitment's members in the previous review; otherwise it creates a new one. A commitment whose members all disappear stays, with `support_state = 'unsupported'` (3.12). Commitments are never deleted.

### 3.12 `commitment_assessments`
`id`, `review_id`, `commitment_id`, `name`, `language` (3 values), `authorisation` (CHECK `'standard_authorised'|'exception_approved'|'no_approval_evidence'|'unknown_needs_review'|'not_assessed'` or NULL meaning not applicable; default `'not_assessed'`), `authorisation_evidence`, `evidence_refs` (JSON: catalogue IDs and `source_version_id`s cited), `contractual_presence` (NOT NULL, CHECK `'absent'|'included_in_draft_contract'|'not_assessed'`; default `'not_assessed'`), `presence_detail` (partial or uncertain coverage), `support_state` (CHECK `'supported'|'unsupported'`), `rationale`. UNIQUE(`review_id`, `commitment_id`).
- `evidence_refs` is what makes "affected by a changed source" computable.
- `authorisation` NULL only for exploratory or conditional commitments, as in the labels. NULL means "not applicable" and never "not yet assessed".
- **`'not_assessed'` (3 Oct)** is the value both columns hold until the 4 Oct rules run, so the consolidation step (name, language, `support_state` only) never has to invent an authorisation or a contractual-presence value. **Rules must handle `'not_assessed'` explicitly and never treat it as `'absent'`**: an unassessed commitment is not a confirmed gap and must read as needing assessment or review.
- Append-only (per-review snapshot); a trigger requires the commitment and the review to belong to the same deal.

### 3.13 `commitment_links`
`id`, `review_id`, `from_commitment_id`, `to_commitment_id`, `link_type` (CHECK `'contract_side_of'|'supersedes'|'related'`), `basis`. UNIQUE(`review_id`, `from_commitment_id`, `to_commitment_id`, `link_type`); CHECK `from <> to`.
- Example: C03 (Polygon hourly batch) `contract_side_of` C01 (Polygon real time). The register shows a link only when both ends are `supported` in the latest assessment.

### 3.14 `issues`
`id`, `commitment_id`, `issue_type` (CHECK `'approval'|'contract_gap'|'conflicting_terms'|'missing_condition'|'insufficient_evidence'`), `subject_key`, `owner_function` (CHECK `'Product'|'Commercial'|'Delivery'|'Customer Success'|'Support'`), `note`, `raised_review_id`, `raised_by` (`'rules'|'agent'`), `raised_config_sha256`, `closure_criteria` (JSON, NOT NULL), `criteria_version`, `absolute_limit` (0/1), `created_at`. UNIQUE(`commitment_id`, `issue_type`, `subject_key`).
- **No state column.** State is derived (section 4).
- Only `owner_function` and `note` are editable; the rest is immutable, so closure criteria cannot be loosened after the fact. No DELETE.
- Mapping from the labels: `overcommitment` → `approval`; `expectation_gap` → `contract_gap`; `contradiction` → `conflicting_terms`; `needs_review` → `insufficient_evidence`. `missing_condition` has no Harbour Bank label and is unexercised by development data.
- **Three issues stay on C01**, as labelled. The UI groups `contract_gap` and `conflicting_terms` under one "Contract" heading; that is presentation only, so the ledger keeps three rows and each closes on its own criteria.
- `closure_criteria` JSON (versioned), at minimum: `required_evidence` (types permitted), `must_cover` (terms and conditions that approval must cover, e.g. launch date, beta conditions), `must_match` (the promised term the incorporated source version must state, e.g. real-time screening before release), `target_source_key`, `absolute_limit_blocks_exception`.

### 3.15 `fixes`
`id`, `deal_id`, `fix_key` (`F1`…), `version_no`, `supersedes_fix_id` (nullable), `route` (CHECK `'align_documents'|'allowed_exception'|'change_or_withdraw_promise'`), `owner_function`, `rationale` (NOT NULL), `status` (`'draft'|'approved'`), `approved_at`, `approved_by` (free text), `created_at`. UNIQUE(`deal_id`, `fix_key`, `version_no`) (keyed by deal as well, so two deals can each have an F1). A fix is created as a draft and approved by an update.
- A draft is editable. **Approved rows are immutable.** A change is a new row with `version_no + 1` and `supersedes_fix_id`. Approval requires at least one `fix_issues` row and, unless the route is `change_or_withdraw_promise`, at least one `fix_evidence` row (trigger).

### 3.16 `fix_issues`
`fix_id`, `issue_id`. PK both. A fix may address several issues (one annex change closes both the contract gap and the contradiction). Rows are immutable once the fix is approved.

### 3.17 `fix_evidence`
`id`, `fix_id`, `source_version_id`, `locator`, `note`. The evidence is always a specific source *version*. Immutable once approved.

### 3.18 `closure_checks`
`id`, `issue_id`, `review_id`, `check_kind` (CHECK `'raised'|'recheck'`), `outcome` (CHECK `'open_action'|'open_evidence'|'met'`), `evidence_checked` (JSON array of `{source_version_id, locator, role}`), `reason` (NOT NULL), `unmet` (JSON; NOT NULL unless `met`), `re_raised` (0/1: did this review's checker raise the issue itself), `fix_id` (nullable: the fix under test), `checked_at`. UNIQUE(`issue_id`, `review_id`).
- **Append-only** (no UPDATE, no DELETE).
- `met` is refused when `check_kind = 'raised'`, when `evidence_checked` is empty, or when the issue has `absolute_limit = 1` and the fix route is `allowed_exception`.
- "Not re-raised by current configuration" is `re_raised = 0` on the latest row. It annotates the issue and never changes its state.

## 4. Views

- **`issue_current_state`**: for each issue, the outcome of its latest `closure_checks` row: `met` → **Resolved**; `open_action` → **Needs action**; `open_evidence` → **Needs evidence**. Override: if the latest row is `met` but any `source_version_id` in its `evidence_checked` (via `json_each`) now has `included = 0`, the state is **Needs evidence**. That makes a removed source never close anything, before any recheck runs. A failed later recheck reopens a previously resolved issue, because state follows the latest check. An issue with no closure check yet reads **Needs action** (fallback: never Resolved by default). **Issue creation must write the issue's `raised` closure check in the same transaction** (to be built and tested on 4 Oct), so the fallback is never relied on.
- **`commitment_status`**: from the latest assessment and the states of its issues. **Open issues win**, so an unsupported commitment or a removed source never hides one. In order: **Needs action** if any issue needs action; **Needs evidence** if any issue needs evidence; **Not in current documents** if the assessment is `unsupported`; **Resolved** if it has issues and all are Resolved; otherwise **No issues raised** (not Resolved). The handoff and UI state that Resolved means the documented gap is closed, not operational readiness (DECISIONS 2026-10-02, input 6).
- **`review_freshness`**: compares the deal's current source-set hash and decision-evidence hash (computed from `source_versions.included` and approved fixes) with the latest complete review's. A difference gives **Review out of date**. Owner and note columns are not part of either hash.
- **Register owner**: derived from the owner functions of a commitment's open issues (it can list several). Only issue-level owner is edited.

## 5. Rules and how each is enforced

| Rule | Mechanism |
| --- | --- |
| Commitment status derived from issues | `commitment_status` view; no status column exists |
| An issue closes only through a passing check; nobody sets Resolved | No state column; `closure_checks` is append-only; `met` needs non-empty evidence and is refused on `raised` rows |
| Approval closes an approval issue only if it covers the promised terms and conditions | `closure_criteria.must_cover`; the check records which terms were covered and `unmet` lists the rest; a `met` row must name the covering evidence |
| An absolute limit cannot be overridden | `issues.absolute_limit`; trigger refuses `met` when the fix route is `allowed_exception` |
| A contract gap closes only against the version the contract currently incorporates | `reference_resolutions` (per review, by source plus cited date); the check's `evidence_checked` must include the resolved version; code rejects any other |
| Removing a source never closes issues | `included` flag; `issue_current_state` override |
| No issue is deleted because a later configuration did not raise it | No DELETE trigger on `issues`; `re_raised` annotates only |
| Approved fixes are immutable; changes create versions | Update and delete triggers on approved `fixes`, `fix_issues`, `fix_evidence`; `version_no` and `supersedes_fix_id` |
| Source versions, statements, closure checks never change | Immutability triggers |
| Owner and notes are editable and do not mark a review out of date | Excluded from both hashes; only `issues.owner_function`, `issues.note`, `commitments.note` are updatable |
| Commitments and issues are never lost | No DELETE triggers |
| Statement-to-commitment links exist only for kept statements, with the same review / statement / source-version identity | FKs from `review_statement_commitments` to `review_statements` and `commitments`; insert trigger (`kept = 1`, same deal); trigger refusing `kept` 1 → 0 on a linked statement; append-only |
| Per-review snapshots are never rewritten | Append-only triggers on `review_sources`, `extraction_cache`, `reference_resolutions`, `commitment_assessments`, `commitment_links`; `reviews` frozen once not `running` |

## 6. Extraction cache: key, seeding and reuse

**Key** (DECISIONS 2026-09-30): canonical-text hash, document type, context passed to extraction (none today), system-prompt, template and schema hashes, model ID, thinking mode, thinking parameter sent, `MAX_TOKENS`, cache-format version.

**Seeding from the frozen run file: not reusable.** The seeding rule is that a run file may seed reusable rows only if it records every key field. `results/extract_harbour_bank_20260930T061113Z.json` records: `model`, `max_tokens`, `thinking_mode`, `thinking_param_sent`, the three prompt hashes, and per document the `doc_type`, statements and usage. It does **not** record the document's canonical-text (content) hash, the context field, or a cache-format version. Hashing today's files would assert that they are what the model saw on 30 Sep, which the run file does not prove.

Therefore imported rows have `origin = 'imported_run_file'`, `reusable = 0`, `key_sha256` NULL and the missing key fields NULL. They exist so the 3–4 Oct build (filter, consolidation, rules) can read real statements without a model call; reviews built on them record `cache_outcome = 'imported'`. **The app's first review ignores them and calls the model** (section 8).

**Reuse** (12 Oct): a document is a hit only if a `reusable = 1` row matches the whole key. Any difference re-extracts that document only. The extract.py command line stays always fresh. Required test: an injected client that raises if called, proving an unchanged-input rerun makes no model call.

## 7. Adapter interface and the snapshot row

An adapter takes an input file and returns: `canonical_text`, `location_map`, `adapter_name`, `adapter_version`. The ledger stores them in `source_versions` together with `original_sha256` (of the file bytes) and `canonical_sha256` (of `canonical_text` encoded UTF-8). Format and document type are separate: the user selects the type and date; the model never guesses it.

`location_map` (JSON) maps character ranges of `canonical_text` to a location: paragraph for text and Markdown (this build), page for PDF, paragraph for DOCX, sheet and cell for Excel, slide for PowerPoint (later). `statements.quote_location` and `evidence_checked[].locator` use these locations. Quotes are checked against `canonical_text`. The Excel and PowerPoint canonical-text specification is not part of this document.

## 8. Walkthrough: Harbour Bank, row by row

Setup facts: C01 is "NUSD payouts on Polygon screened in real time before release". The draft contract (HB-07) incorporates "the Statement of Work dated 20 October 2026, including Annex A". Annex A (inside HB-06) says Polygon is screened in hourly batches. Row counts for statements are about 20 (the frozen run had 20; a fresh model call can differ).

### Before step 1: ingest
- `deals`: 1 row (`harbour_bank`, development).
- `sources`: 8 rows (HB-01…HB-08).
- `source_versions`: 8 rows at `version_no = 1` (HB-05 and HB-08 reference-only).
- *Development path, 3–4 Oct only:* `extraction_cache` gets 6 imported rows (`reusable = 0`, `key_sha256` NULL: the run file lacks the content hash and context), `statements` gets the 20 frozen statements, and build-time reviews use `cache_outcome = 'imported'`. None of this is reused by the app.

### Step 1: Review deal, review R1 (`run_kind = 'review'`, `checker = 'rules'`)
- `reviews`: R1; `decision_evidence_sha256` is the hash of the empty set (E0).
- `review_sources`: 8 rows. The six extractable documents are `miss_called` (the imported rows do not match, so the model is called six times, about $0.07 given the frozen run's $0.068); HB-05 and HB-08 are `not_extracted`.
- `extraction_cache`: 6 new rows, `origin = 'model_call'`, `reusable = 1`, full key.
- `statements`: about 20 rows from those six outputs.
- `review_statements`: about 20 rows. The sales-process false positives are `kept = 0` with `filter_rule`; S15 is kept; kept rows are linked to their commitments in `review_statement_commitments`.
- `commitments`: C01–C08. `commitment_assessments`: 8 R1 rows (C01: firm, `no_approval_evidence`, `absent`).
- `reference_resolutions`: 3 R1 rows. Contract clause 3 → SOW (cited date 20 Oct 2026) → HB-06 v1; clause 3.4 → SOW §3 → HB-06 v1; SOW → Annex A → HB-06 v1. All `resolved`.
- `commitment_links`: C03 `contract_side_of` C01.
- `issues`: 8. C01: `approval` (Product), `contract_gap` (Commercial), `conflicting_terms` (Commercial). C05: `approval`, `contract_gap`. C06: `approval`, `contract_gap`. C08: `insufficient_evidence`.
- `closure_checks`: 8 `raised` rows: seven `open_action`, C08 `open_evidence`. States: seven Needs action, one Needs evidence. C01, C05, C06 show Needs action; C08 Needs evidence; C02, C03, C04, C07 show No issues raised.
- UI: the three C01 issues appear as an approval item and one "Contract" group of two.

### Step 2: record the approval, then recheck, review R2 (`recheck_after_fix`)
- `source_versions`: HB-05 v2 (named exception for Harbour Bank covering the Polygon real-time beta, with the 1 Dec launch date and beta conditions).
- `fixes`: F1 v1: route `allowed_exception`, owner Product, `approved`. `fix_issues`: 1 row (C01 approval). `fix_evidence`: 1 row (HB-05 v2, locator).
- `review_freshness` now says **Review out of date**: the decision-evidence hash moved from E0 to E1.
- `reviews`: R2 with `triggered_by_fix_id = F1`.
- `review_sources`: 8 rows, with HB-05 v2 replacing v1. The six extractable documents are `hit` on R1's reusable rows. No model call.
- `statements`: no new rows. `review_statements`: about 20 rows for R2. `reference_resolutions`: 3 R2 rows, unchanged targets.
- `commitment_assessments`: R2 rows for all 8 commitments (every recheck reassesses everything, section 9). C01 becomes `exception_approved`, because the approval covers the promised terms and conditions.
- `closure_checks`: 8 `recheck` rows, one per issue in the deal.
  - C01 `approval`: `met` (evidence: HB-05 v2).
  - C01 `contract_gap` and `conflicting_terms`: `open_action`, `unmet`: "Annex A in HB-06 v1, which the contract incorporates, says hourly batch."
  - C05, C06 (approval and gap) and C08: stay open. `reason` records that HB-05 v2 contains no approval for 40,000 per day, no VASP exception, and says nothing on status meetings.
- Derived: C01 is Needs action (two of three issues open). All other findings remain visible with owner and action.

### Step 3: align the annex, then recheck, review R3 (`recheck_after_fix`)
- `source_versions`: HB-06 v2 (Annex A revised to real-time screening before release; document date unchanged, 20 Oct 2026, so the contract's citation still matches).
- `fixes`: F2 v1: route `align_documents`, **owner Commercial**, `approved`. `fix_issues`: 2 rows (C01 `contract_gap`, C01 `conflicting_terms`). `fix_evidence`: HB-06 v2 Annex A locator.
- Decision-evidence hash E1 → E2; out of date until recheck.
- `reviews`: R3 with `triggered_by_fix_id = F2`.
- `review_sources`: HB-06 v2 is `miss_called` (new canonical hash, so a new key); the other five extractable documents are `hit`. One model call.
- `extraction_cache`: 1 new row. `statements`: the HB-06 v2 statements.
- `reference_resolutions`: 3 R3 rows. Clause 3 cites a SOW dated 20 Oct 2026 and now resolves to HB-06 v2; clause 3.4 → §3 v2; SOW → Annex A v2. If the revised SOW had been re-dated, the clause 3 row would be `unresolved`, the gap would stay open, and the fix would need a re-issued contract.
- `commitment_assessments`: R3 rows for all 8 commitments. C01 gains a statement from HB-06 v2. C03 (hourly batch) is `unsupported`: its only support was HB-06 v1. Its row and its link to C01 remain, but the link is no longer shown.
- `closure_checks`: 8 `recheck` rows. C01 `contract_gap` `met`; C01 `conflicting_terms` `met`; C01 `approval` re-checked, still `met`. C05, C06, C08 re-checked and still open.
- Derived: C01 **Resolved** (all three issues Resolved). The handoff says so as "documented gap closed", not "ready for launch".

## 9. Review kinds

| Kind | When | Cache | Model calls |
| --- | --- | --- | --- |
| `review` | First **Review deal** on a deal, or any review not otherwise classified | Normal | Misses only |
| `recheck_after_fix` | After an approved fix changes inputs | Reuse unchanged keys; re-extract changed eligible documents | Changed documents only |
| `unchanged_input_rerun` | Nothing changed | All hits | None (tested) |
| `fresh_model_run` | Repeatability, the three agent measurements, the sealed evaluation | Bypassed; output stored with `reusable = 0` | All eligible documents |

**A recheck reassesses everything (decided, Lina, 2 Oct):** every commitment gets a new assessment and every issue in the deal gets its own `closure_checks` row, resolved issues included, so a regression reopens. There is no "affected commitments" calculation to get wrong. Cost is small: assessments and checks are deterministic rules over cached extraction, and only changed documents call the model. `evidence_refs` stays in the schema because the UI uses it to show which commitments a changed source touched, not to limit the recheck.

## 10. The seal and the ledger

- **The ledger never holds `coral_pay`, and the sealed run's output stays in `results/` only.** It never goes into the ledger or the UI.
- **Allowlist, not denylist.** A new `config.LEDGER_DEALS = ["harbour_bank", "hard_cases"]`, checked at import to be a subset of `ALLOWED_DEALS` (same pattern as `UI_DEALS`). A development deal can be written to the ledger only if its slug is in `LEDGER_DEALS`. This is needed because on 14 Oct `ALLOWED_DEALS` must be widened for `extract.py` to run the sealed deal; if the ledger trusted `ALLOWED_DEALS`, that same change would let the sealed deal in.
- The ledger's run-file import reads only `extract_{deal}_<timestamp>.json` for slugs in `LEDGER_DEALS`. The API keeps serving only `UI_DEALS`.
- User deals are server-generated (`u_` + hex) and cannot collide with a development slug (CHECK in `deals`).
- Tests, in the style of `tests/test_api.py`: a temporary data folder with a decoy sealed deal and a canary string, never the real path. Assert that creating a ledger deal for the decoy raises, that the import ignores the decoy's run file, and that the canary never appears in the database or any response, including after `ALLOWED_DEALS` is widened to include the decoy.

## 11. Open questions (recommended answers)

Decided (this document follows them): three issues on C01; fourth run kind `review`; resolution by source plus cited date; imported rows `reusable = 0` unless the run file records every key field; sealed output stays out of the ledger. Accepted by Lina on 2 Oct with the recommended answers below, except Q3, which was changed to reassess all.

1. **Language of a consolidated commitment.** *Accepted:* the firmest language among kept statements the consolidation rule marks as the operative promise, recorded with `rationale`; the schema only stores the value.
2. **When a resolved issue fails a later recheck.** *Accepted:* it reopens (state follows the latest check) and the closure check records why.
3. **Which commitments a recheck reassesses.** *Decided: all of them* (section 9). Not the recommended "affected only".
4. **Does `unsupported` ever archive a commitment?** *Accepted:* no; it stays visible as "Not in current documents" until a person records a disposition.
5. **Decision evidence from other deal documents.** *Accepted:* only evidence permitted by the issue's `closure_criteria.required_evidence`. Whether PDF or DOCX pricing notes count as approval evidence is due 4 Oct.
6. **Cache storage of the thinking parameter.** *Accepted:* store the JSON actually sent (or `none`), as the run file does with `thinking_param_sent`.

## 12. Later, and out of scope

- **Later (columns and adapters, not tables):** PDF page maps (19 Oct), DOCX paragraph maps (19 Oct), Excel sheet and cell maps and PowerPoint slide maps (20 Oct, in that cut order); handoff CSV and readable export views over the tables above (19 Oct).
- **Out of scope:** the Excel and PowerPoint canonical-text specification (3 Oct if time allows, else 12 Oct); multi-user identity beyond the free-text `approved_by`; a model-based filter or consolidation cache (deterministic first, per DECISIONS); any change to `extract.py`, `schema.py`, prompts, labels or hashes.

## 13. Size and risk

Eighteen tables, three views and a set of triggers is more than 3–13 Oct can build in full at 2.5 build hours a day (3 Oct is already rated High risk). Writing the DDL once and building behaviour in the three tranches of section 2 keeps 3 Oct to the write path through statements, commitments and assessments from imported run files, with no cache reuse, no fixes and no recheck. If 3 Oct overruns, the first things to move are `commitment_links` and the `review_freshness` view (both 12 Oct already); no table moves earlier.
