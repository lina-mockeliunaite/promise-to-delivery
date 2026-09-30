# Where I stopped

*Written 30 September 2026, close of Day 7. Read this first on 12 October (or before any work-ahead day).*

## Revision v3 (30 Sep, same day)

The product was revised before Day 8 into a local deal workspace with resolution checking. Days 1–7 below are unchanged. `docs/PLAN_v3.3.md` is the schedule and governs; `docs/REVISION_BRIEF_2026-09-30.md` is the specification; DESIGN.md ("Revision v3") and DECISIONS.md (2026-09-30, Revision v3) record the design and choices. Completion Wed 21 Oct, hard stop Thu 22 Oct. Work is now planned by date, not Day number.

**Open items from the revision**

- **Decision due 4 Oct:** the `security_questionnaire` document type (Coral Pay uses it; `config.py` does not list it). Part of the evaluated configuration, so it must be settled before the 12 Oct candidate freeze.
- **Open for 4 Oct:** whether PDF or DOCX pricing notes count as approval evidence, and how the rules parse the note.
- **Approved in principle, for later:** the `text=` parameter on `extract_document`, with a fake-client test proving the request is byte-identical to the file-read request. No model run.
- **Design due 2 Oct, after Checkpoint 1 feedback is logged:** the SQLite ledger schema, the adapter interface and snapshot columns, and the Excel and PowerPoint canonical-text specification (a document only).
- **Filter and consolidation:** deterministic first; any rule-based filter is checked on `hard_cases` as well as Harbour Bank.
- **Freeze scope:** the 12 Oct candidate freeze covers extraction, filter, consolidation, rules and agent only. Plan v3.3 still says "candidate backend freeze" and needs a matching edit.
- **Cut order at the 22 Oct hard stop (reported unfinished, not deleted):** PowerPoint, then visual refinement, then Excel.
- **Actual build hours:** log per block from 1 Oct. Formal re-plan at the close of 5 Oct.
- **Environment:** Node v26.10.0 and npm 11.19.1 are installed. Web and adapter dependencies are not yet installed.
- **Local app launch:** added here once the step-two scaffold exists. There is no web layer yet.

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

1. Thu 1 Oct: step two of the revision — the local UI/API scaffold showing the permitted Harbour Bank source list and saved extraction results, labelled as intermediate. Needs its own go-ahead.
2. Fri 2 Oct, Checkpoint 1 (revised): a paper test of the pivot, not a walk through extraction scores. Show the three Harbour Bank steps (real-time promise conflicts with the hourly-batch SOW and needs approval; approval recorded, SOW discrepancy stays open; both supported, the finding closes). Log objections and acceptance criteria.
3. Check actual API spend (credit was $19.79 on 30 Sep; today's runs cost about $0.10). Re-check on 12 Oct.
4. Sat 3 Oct onwards: see the plan's remaining schedule.

## First commands on 12 October

```
cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
source .venv/bin/activate
git pull
cat WHERE_I_STOPPED.md
.venv/bin/python -m unittest discover tests
```

Then set the key with `read -s` (Setup reference in the plan) only when a step makes API calls.
