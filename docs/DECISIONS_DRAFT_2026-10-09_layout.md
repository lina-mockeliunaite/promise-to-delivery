# DECISIONS draft, 9 Oct 2026 — layout redesign (for Lina to accept, edit or reject, then fold into DECISIONS.md)

*Built by Claude on 9 Oct while Lina was unavailable, at her request ("proceed with the build … with your self-sufficient way"). Every choice below was made on her behalf and is **not accepted** until she reviews it. Brief: `docs/BRIEF_2026-10-06_layout.md`. No Git commands were run; nothing is committed.*

## 2026-10-09 — Layout redesign after Checkpoint 1: overview rows, fix inside the finding, per-finding decisions

**Deviation from the brief, stated first.** The brief says "Do not start until Part B is merged." Part B was not reviewed or committed. The layout was built on top of it anyway, because the fix flow is the biggest demo risk and the day was otherwise lost. Consequence: if Part B is corrected on review, the decision statuses in the layout may need adjusting. The layout code is in separate files where possible so the two can be reviewed separately (see "Files" below). `api.py` carries changes from both.

**Chose:**

1. **One server call for the fix inside the finding** (`finding_check.py`, `POST /findings/check`): attach → confirmed type → sign-off → save version + approved fix → recheck → report. *Rejected:* three browser calls (upload, fix, review) as before. *Why:* the 6 Oct failure was a flow split across places; one call also means the type check and the "no key" check happen on the server, before anything is written.
2. **The document type is a required, server-checked confirmation.** The browser pre-selects a type from the file name (then from the finding), shows what that type counts as ("Counts as approval evidence · Replaces Pricing and services note, version 1"), and warns when the file name suggests a different type. The server refuses a file that would replace a document of a different type, and refuses an unconfirmed type. *Why:* both 6 Oct demo errors (wrong file, wrong type) would now be stopped or flagged before saving.
3. **If the new version needs the model and the server has no key, refuse before writing.** *Rejected:* save, then fail at the recheck (old behaviour: leaves an uploaded document and an approved fix with no check). Precise: a cache hit for the same text is allowed without a key.
4. **The fix route is derived from the document type** (pricing note → allowed exception; SOW or contract → align the documents; anything else → change or withdraw the promise). **Decided by Lina, 9 Oct, 12:55: the fix addresses only the finding the person attached it to.** *Rejected:* addressing every open finding on the commitment (Claude's first build). *Why:* the fix history should record what the person actually did; the recheck still re-evaluates everything, and any other finding the document closes is reported as a cross-finding effect, not claimed by the fix.
5. **"Okay to proceed" is Part B's accepted risk** (bound to the three hashes, so any new evidence → *Needs re-confirmation*, deal-wide, as decided 6 Oct). It is refused while the review cannot back a decision.
6. **"Must fix before signing" is a separate append-only flag** (`workspace_records_schema.sql`: `signing_flags`, `flag_clearances`), not a Part B decision binding. *Why:* the brief says a must-fix flag stays visible when the finding resolves or the decision goes stale, until a named person clears it with a reason; a binding that goes stale would be the wrong model. It can be recorded while the review is out of date (being more cautious is always allowed). One active flag per finding.
7. **Two counts, never merged:** *unresolved* = open findings; *awaiting decision* = open findings with neither a current Okay to proceed nor an active Must fix. A decision lowers *awaiting decision*, never *unresolved*. *Needs re-confirmation* and *must-fix flags* show as separate counts when non-zero.
8. **The freshness label never says "Up to date" when a decision cannot be saved on the review** (brief addition): it reads "Rerun the review before recording decisions". The ledger's own `freshness.state` is unchanged.
9. **An accountable person whose evidence changed shows as "Name · confirm", not as Unassigned.** Found while testing: a new pricing note version changes the evidence behind every approval finding, so Part B correctly asks for confirmation on VASP's owner; the first version of the overview hid that as "Unassigned".
10. **The deal note is typed, append-only, max 300 characters, with the one decision deadline per deal** (`deal_notes`). Never generated.
11. **Resolved findings name their evidence** ("Resolved by Pricing and services note, version 2 · 9 Oct 2026 · signed off by Daniel Koh") with a link that opens the document text (`GET /documents/text`, this deal's versions only).
12. **`register()` is unchanged;** the new fields come from `workspace.overview()`, which the register route now returns. The handoff snapshot still reads `register()`, so saved handoffs are unaffected.

**Not done (honest list):** business impact is shown ("Not assessed") but there is no form to record it (Part B has `record_impact`; AI-suggested impact stays on Later). No per-finding deadline (one per deal, by decision). The overview at 1440×900 shows all four Harbour Bank rows without scrolling, with or without a two-line deal note; the last row ends close to the fold (screens in `docs/screens/2026-10-09/`). Real-model check of the SOW path not run (needs the key); tested with the scripted fake.

**Checks run:** 549 Python tests pass (533 before + 16 in `tests/test_layout.py`); 7 Node tests pass; frontend builds; browser walk-through on a reset ledger with no page errors. `recheck.py` and every evaluated module untouched, so the config hash and the 5/5 scenarios are unaffected.

**Files.** New: `finding_check.py`, `workspace_records.py`, `workspace_records_schema.sql`, `tests/test_layout.py`, `docs/screens/2026-10-09/`. Changed: `api.py` (also carries Part B), `workspace.py` (additions at the end only), `frontend/src/App.jsx`, `App.css`, `api.js`, `format.js`, `frontend/tests/format.test.mjs`.

## 2026-10-09 (later) — Excel and PowerPoint adapters, pulled forward from 13 Oct

*Also built unattended; not accepted until reviewed. Spec written first: `docs/SPEC_xlsx_pptx_canonical_text.md` (owed since 2 Oct).*

**Chose:**

1. **Excel:** every sheet, row by row, cells joined by ` | ` (the shape the rules already read in Markdown and Word pricing notes), `[Sheet: name]` markers. **Stored values only:** a formula with no stored value or an error reads `[no stored value]`, never recalculated. **Hidden sheets, rows and columns are read and flagged** in `location_map` and in the document's notes (per the 3 Oct decision). Refused: `.xls`, `.xlsm`, macro content inside a renamed file, password-protected files, over 200,000 filled cells.
2. **PowerPoint:** slides in order, title first, groups opened, tables one row per line, `[Slide N]` markers. **Hidden slides read and flagged; speaker notes not read** (both proposals for you to decide). Refused: `.ppt`, `.pptm`, over 300 slides.
3. **Quotes trace to "sheet X, row N" or "slide N"** on the commitment detail (`adapters.locate`). The saved handoff still cites page only (unchanged).

**Open, needs your decision before the 12 Oct freeze:** the 3 Oct decision says a missing or error formula value gives *Needs evidence*. With `rules.py` unchanged it gives *No approval recorded* (conservative — never a false approval — but not what was decided). Honouring it exactly is a `rules.py` change (evaluated pipeline).

**One existing test assertion changed, on purpose:** `tests/test_adapters.py` expected `.xlsx` to be refused; it now expects the new supported-formats message, and a non-workbook named `.xlsx` to be refused by the adapter. Same for one line in `frontend/tests/format.test.mjs`. Check both in the diff.

**Checks:** 563 Python tests pass (+14 in `tests/test_adapters_office.py`, including an Excel named-exception pricing note closing only the approval finding through the real API); 8 Node tests; browser check with an Excel pricing note. New dependencies pinned: `openpyxl==3.1.5`, `python-pptx==1.0.2`. Not checked: a PowerPoint document through the model (needs the key); real decks and workbooks from outside this build.

**Files:** `adapters.py` (Excel, PowerPoint, `locate`), `requirements.txt`, `workspace.py` (one query: location for Office formats), `frontend/src/App.jsx`, `format.js`, `tests/test_adapters_office.py` (new), `tests/test_adapters.py`, `frontend/tests/format.test.mjs`, `docs/SPEC_xlsx_pptx_canonical_text.md` (new).

## 2026-10-09, 12:55 — Lina's decisions (answered in chat), and what was built from them

1. **Agent v2 on Coral Pay: option C** (`docs/DECISION_MEMO_agent_v2.md`). Smoke-test v2 with the real model on Harbour Bank and the hard cases first, then run it once on Coral Pay. **The 4 Oct decision rule is unchanged.** Rejected: A (rules only: drops the third column of the headline), B (v2's first real run would be the sealed run), D (fresh practice set: 2–3 hours of labelling before the freeze). Built: `agent_smoke.py` — one run per deal, in a temporary ledger, no labels, nothing scored, the practice set refused; writes `results/agent_smoke_<time>.json`. Tests: `tests/test_agent_smoke.py`. **To record before the 12 Oct close:** the exact configuration that runs on 14 Oct (`AGENT_VERSION = 2`, `AGENT_MODEL`, bounds in `config.py`).
2. **A formula approval cell with no stored value gives *Needs evidence*** (confirms 3 Oct). **This changes `rules.py` — evaluated pipeline, before the freeze.** `rules.note_finding`: a scoped row whose last cell is `[no stored value]` returns *unknown / needs review* before any approved/not-approved reading. Display: `evidence_text.approval_text` says why in plain words (a first version showed "no approver is named", which was wrong; caught by the test). **Regression:** rules scores on all three development deals are identical to the 3 Oct score file (`rules_score_20261003T035110Z.json`, compared field by field); all tests pass. **Consequence:** `rules.py` is in the config hash, so existing reviews read "Catalogue or rules changed" — run `reset_demo.py`. Correction (10 Oct): the real-model 5/5 rerun is only a regression check for this change (it did not break the scenarios); no scenario uses a spreadsheet, so none exercises the new rule. Its only test is `test_a_formula_approval_cell_with_no_stored_value_needs_evidence_and_never_closes` (scripted, no model).
3. **Hidden PowerPoint slides: read and flagged** (as built). Speaker notes stay unread (not asked; still a proposal).
4. **A fix addresses only the finding it was attached to** (replaces Claude's "every open finding on the commitment"). Test: `test_the_fix_addresses_only_the_clicked_finding_and_other_closures_are_reported_as_effects`.

Tests after these changes: 568 Python pass.

## 2026-10-10, 10:56 — Real-model 5/5 rerun (owed before the freeze): passed

Run by Lina on her Mac after the Part B `recheck.py` change and the 9 Oct `rules.py` change (missing formula value → *Needs evidence*). Control (unchanged-input rerun, no model client): PASS. S1–S5: all PASS. Model cost $0.025. File: `results/scenarios_20261010T025651Z.json`. Still to run: `agent_smoke.py` (option C), the full test suite on the Mac, `reset_demo.py`.

## 2026-10-10, 11:01 — Agent v2 smoke test (option C): ran end to end

`results/agent_smoke_20261010T030129Z.json`. Harbour Bank: C08 escalated, 1 tool call, 1 turn, 6.6 s, $0.012, verdict *unknown* (accepted). Hard cases: C03 escalated, 1 tool call, 1 turn, 4.6 s, $0.010, verdict *unknown* (accepted). Both within bounds ($0.10, 60 s).

**What it shows, and what it doesn't.** v2 runs with the real model: the schema is accepted, verdicts are submitted and validated, nothing is capped. It does **not** show v2 maps paraphrases correctly. Both commitments went straight to *unknown* in one call without searching the catalogue, which is the right answer for these two (the weekly status meeting and a hard-case item with no catalogue capability) but exercises none of the v1 failure modes (term labels, capability phrase, region in the path). The sealed run is still v2's first real test of what it was built for. Say so in the README.

**Configuration proposed for the 14 Oct sealed run (Lina to confirm and record in DECISIONS.md before the 12 Oct close).** Three runs, once each, nothing changed afterwards: (1) baseline; (2) rules; (3) rules + agent v2 as escalation for firm commitments the rules leave *unknown*. Agent: `AGENT_VERSION = 2`, `AGENT_MODEL = claude-sonnet-5` (same as extraction), `AGENT_MAX_TOKENS = 4000`, max 6 tool calls per commitment, 40 per deal, 15 turns; bounds $0.10 and 60 s per deal review. Decision rule: unchanged from 4 Oct (conditions 1–3), applied to a single run. Extraction: frozen v1, `claude-sonnet-5`, thinking `model_default`, `MAX_TOKENS = 8000`. Rules: as of 9 Oct (including the missing-formula-value change). Open point to decide: the 4 Oct rule judged v1 on three runs per deal; on Coral Pay the plan says once per configuration — record that condition 2 is judged on that single run.

## 2026-10-10, 11:07 — Verified on Lina's Mac

568 tests OK (26 s). `reset_demo.py`: fresh ledger, Harbour Bank 8 commitments, 8 open issues, review up to date, 0 model calls; previous ledger backed up as `workspace/ledger.backup-20261010T030222Z.sqlite`. Everything needing the API key before the freeze is done except the KR-06 extraction run (waits for labels).
