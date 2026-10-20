# Rules for Claude Code in this repo

## Released test sets
- `data/coral_pay/` and `data/coral_pay.sha256`: sealed for the single v1 run of 10 Oct 2026 (06:12 UTC). Released from then on as development data (19 Oct): code and tools may read the documents.
- Never edit the sealed results or labels of Coral Pay or Atlas Remit, and never rerun the sealed evaluation. Never edit the documents or the seal files either.
- `.claude/settings.json` still carries the old Coral Pay read/edit deny rules. They are access control, not this file's instruction; Lina decides when to drop them. Never test them by attempting access.

## Atlas Remit (10 Oct, v2)
- `data/atlas_remit/` and `data/atlas_remit.sha256`: sealed for the single v2 run, which took place on 10 Oct 2026 (08:44 UTC). Released from then on as development data; the rule above still applies: never edit the documents, labels, results or seal.

## Development data
- `data/harbour_bank/` is the development deal. Extraction may read its source documents, but not its labels.
- Evaluation code may read `data/harbour_bank/labels/` to score runs and report errors. Use those errors to improve general rules; do not put gold labels or Harbour Bank sentences into an extraction prompt as examples.

## How we work
- Work on one agreed, bounded change set at a time. State the files and intended change, wait for Lina's go-ahead, then show what changed and what you checked.
- Do not run Git commands. Lina handles Git.
- Read the API key only from `ANTHROPIC_API_KEY`; never print, log or write its value.
- Keep model IDs in one config file; other code reads them from there.

## v2 in the app (10 Oct)
- The app runs v2 only (`ledger_v2.py`); the v1 rules pipeline stays for evaluation. `python reset_demo.py` rebuilds the app ledger from `config.V2_DEALS` with the saved v2 output (no model call).
- Closure is by re-verifying a stored claim; never let model output close an issue directly.
- `detect_v2.py` may change (19 Oct: nothing is frozen). Any change to its prompt or verifier must raise v2_version; the published sealed results describe v2_version 2 only. Never re-run the sealed evaluation.
