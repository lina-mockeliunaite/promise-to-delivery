# Rules for Claude Code in this repo

## Sealed test set
- Until Lina explicitly releases the test set for the 14 October 2026 evaluation, do not read, list, search, hash, edit or otherwise inspect `data/coral_pay/` or `data/coral_pay.sha256`, including through scripts, Git history or tool output.
- Exclude both paths from every repository-wide search or script that traverses the repository. If a task appears to require either path, stop and ask Lina.
- Before starting, read `.claude/settings.json` to confirm the four deny rules are present. Never test the seal by attempting to access either path. This file is an instruction, not the access control.

## Development data
- `data/harbour_bank/` is the development deal. Extraction may read its source documents, but not its labels.
- Evaluation code may read `data/harbour_bank/labels/` to score runs and report errors. Use those errors to improve general rules; do not put gold labels or Harbour Bank sentences into an extraction prompt as examples.

## How we work
- Work on one agreed, bounded change set at a time. State the files and intended change, wait for Lina's go-ahead, then show what changed and what you checked.
- Do not run Git commands. Lina handles Git.
- Read the API key only from `ANTHROPIC_API_KEY`; never print, log or write its value.
- Keep model IDs in one config file; other code reads them from there.
