# Where I stopped

*Written 30 September 2026, close of Day 7. Read this first on 12 October (or before any work-ahead day).*

## Revision v3 (30 Sep, same day)

The product was revised before Day 8 into a local deal workspace with resolution checking. Days 1–7 below are unchanged. `docs/PLAN_v3.4.md` is the schedule and governs; `docs/REVISION_BRIEF_2026-09-30.md` is the specification; DESIGN.md ("Revision v3") and DECISIONS.md (2026-09-30, Revision v3) record the design and choices. Completion Wed 21 Oct, hard stop Thu 22 Oct. Work is now planned by date, not Day number.

**Open items from the revision**

- **Decision due 4 Oct:** the `security_questionnaire` document type (Coral Pay uses it; `config.py` does not list it). Part of the evaluated configuration, so it must be settled before the 12 Oct candidate freeze.
- **Open for 4 Oct:** whether PDF or DOCX pricing notes count as approval evidence, and how the rules parse the note.
- **Approved in principle, for later:** the `text=` parameter on `extract_document`, with a fake-client test proving the request is byte-identical to the file-read request. No model run.
- **Design due 2 Oct, after Checkpoint 1 feedback is logged:** the SQLite ledger schema, the adapter interface and snapshot columns, and the Excel and PowerPoint canonical-text specification (a document only).
- **Filter and consolidation:** deterministic first; any rule-based filter is checked on `hard_cases` as well as Harbour Bank.
- **Freeze scope:** the 12 Oct candidate freeze covers extraction, filter, consolidation, rules and agent only. Plan v3.3 still says "candidate backend freeze" and needs a matching edit.
- **Cut order at the 22 Oct hard stop (reported unfinished, not deleted):** PowerPoint, then visual refinement, then Excel.
- **Actual build hours:** log per block from 1 Oct. Formal re-plan at the close of 5 Oct.
- **Environment:** Node v26.10.0 and npm 11.19.1 are installed. Web dependencies are installed (fastapi, uvicorn, httpx in `.venv`; react and vite in `frontend/`). Adapter dependencies are not.
- **Local app launch:** see the "Local app launch" section below. The step-two scaffold is read-only, makes no model calls and shows Harbour Bank only.

## What works

**Extraction v1 is frozen.** Sonnet 5, default thinking, `MAX_TOKENS = 8000`.

| Frozen item | SHA-256 (first 8) |
| --- | --- |
| System prompt | `db9e892a` |
| User-message template | `2afd3f1e` |
| Output schema | `a4debfaf` |
| Harbour Bank labels (statements) | `dbdc17a3` |
| Hard-case labels (statements) | `1f434f93` |
| Catalogue | `11826c96` |

**Harbour Bank, frozen run** (`results/extract_harbour_bank_20260930T061113Z.json`): 15/15 labelled statements found, 75% precision (15/20), 0 language errors, all quotes valid, $0.068. Regression: 6/6 must-hold checks pass (`results/regression_extract_harbour_bank_20260930T061113Z.json`).

**Hard cases** (`data/hard_cases/`, Kestrel Remit, fictional, development only): 9/9 labels found, 100% language accuracy, 1 false positive. 11 of 12 cases pass: the hedge, roadmap, future-date, number-in-words, pointer, customer-obligation, split-turn, absolute-limit, authorised-but-absent, injection and pointer-only-contract cases all behave as labelled.

**Tooling:** `extract.py`, `evaluate.py` (now lists language mismatches), `regression.py` (six must-hold checks, never overwrites), `check_quotes.py`; 75 tests pass. Coral Pay is still sealed and `ALLOWED_DEALS` excludes it.

## What's fragile

1. **Sales-process steps are extracted as firm commitments.** All 6 remaining false positives are one type: "I'll bring our Product team to the next call", "We'll respond to your RFP within the window", "Priya can walk your architects through the options", "Elva follows a phased methodology", "A draft Statement of Work will follow", "We'll send our security pack by Friday". Harmless to extraction scores, but on Day 9 each is firm and absent from the contract, so the expectation-gap rule would flag it. **Day 8 or 9 must filter these before the decision screen.** Not fixed on Day 7: the one permitted revision was used on pointer sentences, and these add noise rather than hide a conflict.
2. **One run per configuration.** 6/6 shows the fix can work, not that it always will.
3. **Hard cases were written after seeing the prompt**, so they are likely easier than real documents. Coral Pay on 14 October is the honest test.
4. **Regression gaps:** no warning line when a document is not `complete` (planned, not built). Check 6 for HB-05 and HB-08 guards configuration, not the model: the code never sends those documents.
5. **Known v1 gap:** an Elva promise reported only in a customer email is missed.

## Rules for any change from here

- Any change to the prompt, template, schema, model or thinking setting must pass `python regression.py <new run>` on Harbour Bank and be logged in DECISIONS.md with old and new hashes.
- Label changes produce a new label hash; report the old score alongside any adjudicated one.
- Coral Pay: no code reads `data/coral_pay/` before 14 October; verify hashes with `shasum -a 256 -c data/coral_pay.sha256` on the day, before the run.

## Working ahead (weekend of 3–4 October)

- Start Sat 3 Oct work only after Checkpoint 1 feedback (Fri 2 Oct) is logged in DECISIONS.md.
- Four-hour ceiling applies on weekend days too.
- Sat 3 Oct = sales-housekeeping filter, consolidation and the SQLite ledger, built to the schema approved on 2 Oct. Its first known hard cases: "thirty thousand" (KR-02) and "30,000" (KR-03) must merge into KC4; the sales-process false positives above must not become commitments; S15 must survive the filter.

## Next

*Updated 3 Oct, late morning. The 4 Oct block was built early on 3 Oct, by Claude at Lina's request (fast-forward day: Claude built, Lina monitored). Brief: `docs/BRIEF_2026-10-04.md`. Decisions: DECISIONS.md 2026-10-03 (working ahead). Not yet committed.*

**What now exists.** `references.py` (contract chain: the draft contract plus everything it incorporates, by cited date; Annex/Schedule/section headings; resolved / unresolved / missing). `rules.py` (authorisation with citations, absolute limits, quantity limits, silent-note cases → unknown, contractual presence through the chain, contract gap, conflicting terms with a `contract_side_of` link, insufficient evidence). Consolidation now fills a pointer's missing terms from the section it cites (S11). `ledger_consolidate.py` runs the rules in the same review and transaction. `score_rules.py` scores the rules against the labels. 356 tests pass.

**State of the ledger.** `workspace/ledger.sqlite`: 16 commitments, 16 issues (13 Needs action, 3 Needs evidence), 16 raised closure checks, 7 reference resolutions, 1 link. Rebuild: `.venv/bin/python ledger_import.py --rebuild && .venv/bin/python ledger_consolidate.py`. Scores: grouping HB 15/15 and 8/8, hard cases 8/9 and 6/7 (`results/grouping_score_20261003T025653Z.json`); rules 100% on both deals (`results/rules_score_20261003T025653Z.json`) — designed with these documents in view, so not evidence of generalisation.

1. **Decisions settled (3 Oct, 10:40):** security questionnaires are extracted; Excel, PDF and DOCX pricing notes all count as approval evidence (Excel from 20 Oct: hidden cells kept with a visibility flag and assessed like any other; missing or error formula values need evidence); decision rule and `terms_incomplete` interpretation confirmed. **Open:** a fictional security-questionnaire fixture in `hard_cases`, its labels (Lina) and one extraction run (about $0.01, needs the API key), before the 12 Oct candidate freeze.
2. **Verify on the Mac:** `.venv/bin/python -m unittest discover tests` (expect 399 OK); rebuild the ledger with the two commands above; `.venv/bin/python score_rules.py`.
3. **Commit** (Lina; files listed in the chat).
4. **Before agent code on 5 Oct:** practice set `data/practice_cases/` (Tidewater Pay, 12 commitments) signed off by Lina and frozen in `data/practice_cases.sha256` (verify with `shasum -a 256 -c data/practice_cases.sha256`). Extracted once on 3 Oct (`results/extract_practice_cases_20261003T034401Z.json`, 15 statements, $0.031) and pinned; in `LEDGER_DEALS`. **5 Oct starts with:** rebuild the ledger, score extraction and rules on this deal against the frozen labels (the rules baseline), then the agent. Labels never change after results. Catalogue hash is now 2d2d96a0 (explicit `unlisted_rule`).
5. **5 Oct block (built 3 Oct):** `agent.py` and `agent_compare.py` built and tested with a fake client (`docs/BRIEF_2026-10-05.md`). Rules baseline on the practice set: 0 of 5 approval issues. **Result (3 Oct, 12:24):** the rules power the demo. The agent judged all 7 practice commitments correctly in substance but failed the evidence contract in every run (condition 2); see DECISIONS. **Open:** decide before 12 Oct whether a versioned agent v2 (fixed tool schema) runs on Coral Pay; the formal re-plan from actual hours (1 Oct onwards).
6. **Checkpoint 1:** real reviewer booked for Monday 5 Oct. Use the Harbour Bank register now in the ledger for the paper test.
7. **12 Oct block built early (3 Oct):** fixes, full-key cache, recheck, five scenarios (`docs/BRIEF_2026-10-12.md`); 5/5 with the real model too (`results/scenarios_20261003T045108Z.json`, $0.029). Candidate freeze still at 12 Oct close.
8. **13 Oct, first part built (3 Oct):** workspace API and screens; freshness; fix-and-recheck works in the browser. Launch: see Local app launch. **After pulling on the Mac run `cd frontend && npm ci`** (Claude's side reinstalled `node_modules` for Linux on 3 Oct). Open: integration checks and final evaluated configuration on 13 Oct.
9. The frontend has a new label for `security_questionnaire`; rebuild `frontend/dist` before the next built-mode run.
10. Check actual API spend before 12 Oct (credit was $19.79 on 30 Sep; 3 Oct used no model calls).

## Local app launch

Read-only scaffold: `api.py` (FastAPI, GET routes only) and `frontend/` (React with Vite). Both bind to `127.0.0.1`. No API key is needed and no model is called.

First time only, from the repo root:

```
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm ci && cd ..
```

**Dev mode** (two terminals; the page hot-reloads):

```
# terminal 1, repo root
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000

# terminal 2
cd frontend && npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` to port 8000.

**Built mode** (one server; FastAPI serves `frontend/dist/`):

```
cd frontend && npm run build && cd ..
.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Rebuild after any frontend change; the server notices `frontend/dist/` only at start-up, so restart it after the first build.

Check: `.venv/bin/python -m unittest discover tests` runs the API seal tests with the rest.

## First commands on 12 October

```
cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
source .venv/bin/activate
git pull
cat WHERE_I_STOPPED.md
.venv/bin/python -m unittest discover tests
```

Then set the key with `read -s` (Setup reference in the plan) only when a step makes API calls.
