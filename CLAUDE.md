# Rules for Claude Code in this repo

## Sealed test set
- Until Lina explicitly releases the test set for the 14 October 2026 evaluation, do not read, list, search, hash, edit or otherwise inspect `data/coral_pay/` or `data/coral_pay.sha256`, including through scripts, Git history or tool output.
- Exclude both paths from every repository-wide search or script that traverses the repository. If a task appears to require either path, stop and ask Lina.
- Before starting, read `.claude/settings.json` to confirm the four deny rules are present. Never test the seal by attempting to access either path. This file is an instruction, not the access control.

## Second sealed test set (10 Oct, v2)
- `data/atlas_remit/` and `data/atlas_remit.sha256`: sealed for the single v2 run, which took place on 10 Oct 2026 (08:44 UTC). Released from then on as development data; still never edit the documents, labels or seal.

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
- `detect_v2.py` prompt and verifier logic are frozen at v2_version 2 (sealed run passed); changing them needs a new sealed check.
