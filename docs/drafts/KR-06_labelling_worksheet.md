# KR-06 security questionnaire — labelling worksheet (for Lina)

*Draft fixture written by Claude on 9 Oct, development only: Kestrel Remit world, Singapore, no Australian market, no Solana, nothing from the sealed deal (written from `data/hard_cases/BRIEF.md`, DECISIONS and the catalogue only). **Not in `data/` yet, on purpose:** adding it changes the hard-case label hash, so the labels must be yours and the move is your decision.*

**Why this fixture exists:** on 3 Oct `security_questionnaire` became extractable with no development example, so it would enter the sealed run untested. This gives it one run on development data before the 12 Oct freeze.

## Label each row yourself

For each row, write: **extract or not**, and if extracted, **language** (exploratory / conditional / firm) and the **exact quote**.

| Row | What it is designed to test | Your label |
|---|---|---|
| 1 | Firm promise after a bare "Yes." — should the quote include "Yes."? | |
| 2 | Plain firm security promise | |
| 3 | Firm, technical | |
| 4 | Data residency — firm | |
| 5 | Roadmap/expectation, not a promise | |
| 6 | One firm sentence with two parts (annual test is a fact; sharing on request is a promise) | |
| 7 | A **capability** promise hidden in a security form (Arbitrum is an absolute limit in SG — same as H9) | |
| 8 | Customer's own obligation — never Elva's commitment | |
| 9 | Pointer only | |
| 10 | **"Yes." alone** — the promise is in the question. The quote checker needs words from the document; what should happen? | |
| 11 | Firm promise that duplicates KR-02's audit-history promise — should consolidate with it | |

Design answers are in `KR-06_design_answers.md`. **Open it only after you've labelled every row.**

Expected downstream: rows 1–4 and 6 have no catalogue capability, so they reach review as *Needs evidence* (DECISIONS 3 Oct: no security section in the catalogue yet).

## To adopt it (JUST DO, after labelling)

1. Move `KR-06_security_questionnaire.md` into `data/hard_cases/docs/`, add it to `manifest.json` (`"doc_type": "security_questionnaire"`, `"date": "2026-11-05"`).
2. Add your labels to `data/hard_cases/labels/statements.json`; record the old and new label hash in DECISIONS (labels change → new hash, old score reported alongside).
3. One extraction run on hard cases (about $0.01, needs the key), then `regression.py`. Record the result before the freeze.

---
**Superseded 10 Oct:** adopted as a separate extraction-only deal, `data/questionnaire_cases/` (labels written by Claude at your request). Not added to hard cases, so their labels and hash are unchanged.
