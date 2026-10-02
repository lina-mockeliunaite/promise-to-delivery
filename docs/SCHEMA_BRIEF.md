# Ledger schema design (brief for Claude Code)

*Written 2 Oct 2026. Design only: the output is a document, `docs/LEDGER_SCHEMA.md`. No code, no migrations, no database file.*

## Read first

- `docs/PLAN_v3.4.md`: "Resolution and recheck", "Recheck must be deterministic", "Issues never disappear because the checker changed", "Three views".
- `DECISIONS.md`: 2026-09-30 Revision v3 (user-deal storage, findings record configuration and closure criteria, owner function, document types, extraction cache) and 2026-10-02 (the seven design inputs).
- `schema.py` and `data/harbour_bank/labels/commitments.json` for the existing statement and commitment shapes. Do not read `data/coral_pay/`.

## What the schema must hold

SQLite tables (propose names, columns, keys and constraints) for:

1. **Deals**: development deals and user-created deals, kept apart (user deals live under `workspace/`, never `data/`).
2. **Sources and versions**: a source document has versions. Each version records original-file hash, canonical-text hash, adapter version, document type (one of the seven), document date, and whether it is included in the current review.
3. **References between versions**: e.g. contract clause 3.4 → SOW section 3 → Annex A. A reference records which *version* it resolves to, and whether it is unresolved or missing.
4. **Reviews (runs)**: run kind (recheck after fix, unchanged-input rerun, fresh model run), configuration hash, source-set hash, decision-evidence hash, timestamp. Drives *Review out of date*.
5. **Statements** extracted from a source version (existing extraction output).
6. **Commitments**: one consolidated promise, linked to its statements; language, authorisation evidence, contractual presence.
7. **Links between commitments**: e.g. "Polygon hourly batch" is the contract side of "Polygon real time". Typed relationship.
8. **Issues**: belong to one commitment; type (approval, contract gap, conflicting terms, missing condition, insufficient evidence); state (*Needs action*, *Needs evidence*, *Resolved*); owner function (Product, Commercial, Delivery, Customer Success, Support); which configuration and review raised it; structured closure criteria; annotation "not re-raised by current configuration".
9. **Fixes (decisions)**: route (align documents, allowed exception, change or withdraw the promise), affected issue, owner, rationale, evidence references to specific source versions. Approved fixes are immutable; a change creates a new version.
10. **Closure checks**: each recheck's evaluation of each issue's criteria: which evidence was checked, pass or fail, reason, what remains unmet.
11. **Extraction cache**: the full key from DECISIONS 2026-09-30 (canonical-text hash, document type, context, prompt/template/schema hashes, model ID, thinking mode and parameter, MAX_TOKENS, cache-format version), stored output and usage.

Owner and notes are editable and do not mark a review out of date; sources and decision evidence do.

## Rules the design must make enforceable

- Commitment status is **derived** from its issues (Resolved only when every issue is Resolved), never stored independently.
- An issue closes only through a closure check that passes against evidence; no column lets a person set *Resolved* directly.
- Approval closes an approval issue only if it covers the promised terms and conditions; an absolute limit cannot be overridden.
- A contract gap closes only against the source version the contract currently incorporates.
- Removing a source makes affected issues *Needs evidence*, never closed.
- No issue is deleted because a later configuration did not raise it.

## Also in the document (short)

- **Adapter interface**: input file → canonical text + location map + adapter version; what a snapshot row stores.
- **Walkthrough**: the three Harbour Bank steps from the reviewer pack, row by row through the tables (review → approval fix → recheck: approval closes, contract gap open → annex aligned → recheck: closed).
- **Open questions** for Lina, each with a recommended answer.

Out of scope today: the Excel and PowerPoint canonical-text specification (moved to 3 Oct if time allows, else 12 Oct).

## Process

Per CLAUDE.md: propose the table list and the walkthrough first, in chat, before writing the document. Wait for Lina's go-ahead. Keep it to what 3 Oct–13 Oct will build; mark anything beyond that as later.
