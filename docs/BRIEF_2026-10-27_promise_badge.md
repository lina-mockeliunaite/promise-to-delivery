# Brief: promise findings beside the promise, contract wording on its own line (27 Oct 2026)

*Written by Claude (reviewer) for Lina. Front-end display only: no data, no model calls, no change to findings, labels, seals or results. Do not run any git command; Lina handles git.*

## Why
On the landing cards and deal rows, one line joins everything with " · ", contract wording first:
"Contract says **chat and email** · **not offered**". "Not offered" describes the *promise* (phone calls), but it sits against the contract wording, so it reads as "chat and email are not offered". Alder has the same flaw ("Amazon Web Services in the Sydney region · not offered"). This is on the first screen of the public video.

**Rule:** a finding about the promise sits with the promise; what the contract says sits on its own line.
- About the promise: `Not offered`, `No approval found` -> a badge beside the title.
- About the contract: `Contract says something different`, `Missing from contract` -> the contract line ("Contract says **chat and email**", "Contract has **no matching wording**").

Lina's decision (27 Oct): option A, badge beside the title. Rejected: reordering the joined line (still one line, still joined); naming the vendor in the label ("Aivuna doesn't offer this"; the vendor is already named above, and it changes the label everywhere).

## Required reading order
```
AI answers customers' phone calls at launch   [Not offered]
Contract says chat and email
```
- The badge sits beside the title when there is room and wraps **directly beneath the title** when there isn't. It never squeezes or truncates the title.
- The contract statement always has its own line. It is never joined to a badge with " · ".
- Several promise findings -> several badges, in the existing finding order.
- No contract finding -> no contract line. No promise finding -> no badge.
- The badge must not look like the row's status chip (status and finding are different things), and its meaning must not rely on colour alone (the text carries it).
- Closed rows: unchanged (they show no mismatch today).

## Where (all in `frontend/src`)
1. `dealpage.js`: `mismatchParts` returns the contract part only; add a small helper returning the promise findings' short labels (from `FINDING_SHORT`). The landing pick in `landing.js` passes both.
2. `Landing.jsx`: the sample-deal cards.
3. `DealPage.jsx`: `CommitRow`.
4. `Drawer.jsx`: the `dr-mismatch` line in `CommitmentView` (title and badge in the drawer head, or directly above the contract line; propose which in the plan).
5. `FrozenRecord.jsx`: the locked-record row (line ~39) and the plain **Mismatch:** line (line ~60), which also prints.
6. `mismatchLine` (plain text, used by the locked record and print): make the relationship explicit, for example `Promise: Not offered. Contract says: chat and email.` Propose the exact form in the plan.
7. Check and report: any other place that renders `mismatchParts` / `mismatchLine` or the joined line, including `handoff.py` exports. Change only what has the same ambiguity; list the rest as unchanged with the reason.

## Ground rules
- **First reply with a plan only:** files, the exact new strings, the badge style (class names, using existing CSS variables), and where the badge goes in the drawer. Wait for Lina's go-ahead.
- Never touch `data/`, `results/`, labels, seals, catalogues, `LEARNING_LOG.md`, or any Python finding logic. Finding labels in `FINDING_SHORT` keep their wording.
- Demo scripts and README: report any line that quotes the old joined wording; do not edit them in this change set.

## Checks, then report
1. Both suites: `.venv/bin/python -m unittest discover -s tests -b` and `cd frontend && node --test tests/*.mjs`, quoting the last lines. Update `frontend/tests/dealpage.test.mjs` for the new shape, and add tests for: a not-offered + contract-differs commitment (Noma phone calls), a no-approval + missing-from-contract commitment (Noma launch specialist), contract-only, and promise-only.
2. **Regression check:** before/after screenshots, desktop full width, of the landing page, the Noma deal page, the phone-calls drawer and the locked record after the Noma script is run. State what changed and what didn't.
3. **390px check:** the landing page and the Noma deal page at 390px wide, including the longest title in either sample deal and the `No approval found` badge. Open each image and describe what it shows; confirm the badge wraps beneath the title and the contract line stands alone.
4. Save screenshots to `docs/screens/2026-10-27/`. Stop any servers you started.
5. **DECISIONS.md:** one entry dated 27 Oct: promise findings shown as a badge beside the promise, contract wording on its own line; this reverses the 19 Oct single sentence-style mismatch line; rejected options and why (above).
6. List every file changed. Then stop.
