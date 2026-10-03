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

*Updated 3 Oct, close. 3 Oct block done in about 2 h 10 (all five change sets of `docs/BRIEF_2026-10-03.md`). Commits 1137e4c (ledger DDL, LEDGER_DEALS, seal tests), import, parser and filter, 04065c2 (consolidation), 20d2216 (grouping score). 297 tests pass.*

**State of the ledger.** `workspace/ledger.sqlite` (gitignored; rebuild with `.venv/bin/python ledger_import.py --rebuild` then `.venv/bin/python ledger_consolidate.py`): Harbour Bank 10 commitments, hard cases 8; all assessments `not_assessed` for authorisation and contractual presence; no issues yet. Grouping score: HB 14/15 statements, 6/8 commitments; hard cases 8/9, 6/7; misses S11 (no mode, needs Annex A) and K01 (Arbitrum, no mode).

1. **4 Oct block (Day 10).** Start with the quiz retry (below). Then, per the plan:
   - Decide `security_questionnaire` (extract / reference-only / skip) and whether PDF/DOCX pricing notes count as approval evidence; log both.
   - Write the rules-vs-agent decision rule first, with explicit cost and latency bounds.
   - Rules: material conflict, coverage (reference resolution through the draft contract → SOW → Annex A; S11 should gain its mode and join the Ethereum real-time and Polygon batch commitments), authorisation with citations, absolute limit for unlisted networks (`in_catalogue = false`), silent-note cases (C08, KC3 → needs review), `terms_incomplete` → needs review never a confirmed gap, `not_assessed` handled explicitly.
   - Issue creation must write its `raised` closure check in the same transaction (tested).
2. **Quiz retry for 4 Oct:** the two seal tests are different. Route rule (negative control: wrong-directory mount is flagged) vs canary/traversal (negative control added 3 Oct: a decoy-serving app makes the canary check fail). Explain both without mixing them.
3. Book a real Checkpoint 1 reviewer before 5 Oct (still not booked as of 3 Oct).
4. Check actual API spend before 12 Oct (credit was $19.79 on 30 Sep; 3 Oct used no model calls).

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
