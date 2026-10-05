# Brief: decision integrity, before any signing-brief layout (6 Oct)

*Drafted by Claude (project) for Lina's approval, from DECISIONS.md 2026-10-05 ("Simulated reviews, integrity rules and signing-brief hypotheses"). Claude Code works in TWO change sets. Part A is a written inspection with no code changes. Part B is implemented only after Lina has read Part A and given the go-ahead. Propose files and approach before each part.*

## Why this brief exists

Planned additions (accepted risks, impact assessments, named accountability, a signing brief) are human records sitting on top of system findings. They are only trustworthy if three things hold:

1. **No human record changes a finding.** Accepting a risk, assessing an impact or naming a person never closes, reopens or recounts an issue.
2. **Every decision is bound to the evidence it was made against.** If that evidence changes, the decision shows "Needs re-confirmation". It is never silently current, and never rewritten.
3. **Ownership follows an issue only when it is verifiably the same issue.**

The layout, consequence categories and founder-as-recipient are **not** in this brief. They wait for the real Checkpoint 1 (Tue 6 Oct).

## Boundaries (non-negotiable)

- Do not change the evaluated pipeline: `extract.py`, `schema.py`, `sales_filter.py`, `ledger_consolidate.py`, `terms.py`, `references.py`, `rules.py`, `agent.py`. Read them; do not edit them.
- `recheck.py` is not frozen, but the five resolution scenarios depend on it. Any change to it must keep **5/5 scenarios** and the full downstream checks passing. Prefer to change nothing in it.
- No model calls. No new extraction. No layout or screen work beyond what a test needs.
- Additive schema only, applied on demand like `handoff_schema.sql`. The existing database keeps its data. `schema_version` does not change.
- Never read `data/coral_pay/` or `data/coral_pay.sha256`. No repository-wide scans. No Git commands.

## What Claude (project) already read (confirm or correct in Part A)

This is a reading of the code on 5 Oct, not a verified result. Confirm each point with file and line, or correct it.

| Topic | Current behaviour, as read |
| --- | --- |
| `source_set_sha256` (`ledger_fixes.py`) | Hashes included source versions: source key, version, canonical text hash, doc type, doc date. The pricing and services note is a source (`pricing_services_note`), so a change to it **is** covered when it is included. |
| `decision_evidence_sha256` (`ledger_fixes.py`) | Hashes evidence rows of **approved fixes only**. Owners and notes excluded. |
| Catalogue | **Not** in either hash above. It is in `config_sha256` (`ledger_consolidate.rules_sha256`: rule files plus `catalogue.json`), recorded on each review. |
| Handoff staleness (`handoff.py`) | Compares only source-set and decision-evidence hashes. **A catalogue change, or a rules-code change, does not mark a saved handoff as out of date.** This is the gap the decision entry predicted. |
| Hash level | All three are deal-level, not issue-level. |
| Commitment identity across rechecks (`recheck._assign_identities`) | A new group inherits a previous commitment if it shares at least one (source, quote hash) member; largest overlap wins; each previous commitment used once. The same commitment can therefore carry changed terms. |
| Issue identity | `UNIQUE (commitment_id, issue_type, subject_key)`. `subject_key` is coarse: `authorisation`, `contract`, or `conflict:<other commitment key>`. A conflict whose terms change (e.g. hourly batch → 15-minute batch) stays the **same issue row**. An issue that closes and reappears reuses the same row (`re_raised`). |
| Ownership today | `issues.owner_function` (a team) is editable on the issue row, so it carries forward automatically whenever the row identity holds, including when the terms behind it changed. |

## Part A — inspection report (no code changes)

Write `docs/INTEGRITY_INSPECTION_2026-10-06.md` answering, with file and line references:

1. **Hash coverage.** For each input that can change a finding or a decision, say which hash covers it, or "none": each source document; the pricing and services note; `catalogue.json`; rule files; extraction configuration; excluded sources; approved fixes and their evidence; issue owner and note fields. Name every gap.
2. **Freshness today.** Exactly what marks the workspace "Review out of date" and what marks a saved handoff out of date. Do they use the same inputs? If not, list the difference.
3. **Issue identity.** For each case, say what happens today, with a test or a traced example on Harbour Bank development data:
   - a. same promise, unchanged terms;
   - b. same commitment, changed terms in the conflict (e.g. a revised SOW with a different batch interval);
   - c. a different issue type on the same commitment;
   - d. an issue that closed, then reappeared;
   - e. a commitment split or merged by regrouping;
   - f. a genuinely new commitment.
4. **Existing guarantees.** Show the tests (or say none exist) for:
   - "Proceed with open items" never changing an issue state or the open count;
   - saved handoffs unchanged after later fixes and rechecks;
   - owner edits not changing `source_set_sha256` or `decision_evidence_sha256`.
5. **Migration risk.** If the hash definitions were widened, what happens to existing reviews and saved handoffs? List the records that would appear changed for reasons that have nothing to do with evidence.

End Part A with a short list: **gaps found**, and **proposed fixes**, each one line. Stop for Lina.

## Part B — integrity changes (after Lina's go-ahead on Part A)

Defaults below. Lina may change any of them before go-ahead.

**B1. Bind decisions to all three hashes.** Every saved decision (today: handoff versions; later: accepted risks, signing decisions and impact assessments) records `source_set_sha256`, `decision_evidence_sha256` **and** `config_sha256` of the completed review it concerns.

- Freshness compares all three.
- The reason is shown in plain words: "Documents changed", "Approval or fix evidence changed", "Catalogue or rules changed".
- Do not merge the catalogue into the source-set hash. That would mark every review out of date for a reason that has nothing to do with the documents.

**B2. Version the hash definitions.** Each stored binding records a `hash_definition` number.

- A record is compared only against a hash computed under the same definition.
- If the definition has changed, show "Needs re-confirmation: checking rules updated". Do not show "Documents changed".
- Existing saved handoffs are never rewritten.

**B3. No current brief against an out-of-date review.** Any signing or handoff decision is refused, and any decision summary declines to show a current list, while the review is out of date: "Review out of date: rerun before a signing decision." This extends the existing save refusal.

**B4. Ownership carry-forward is explicit.** If accountable person and deadline fields are added later, they attach to the issue but are stamped with the evidence context of the closure check that was current when they were set.

- They carry forward automatically **only** when the issue row is the same **and** its terms are unchanged (case 3a).
- In cases 3b, 3d and 3e they show "Confirm owner still applies" and need a named person to confirm.
- New issues (3f) start with no accountable person.
- Carrying ownership forward never makes an accepted risk or an impact assessment current.
- *Part B builds only the mechanism and tests. The fields' screen design waits for Checkpoint 1.*

**B5. Human records never touch findings.** Records for accepted risk, impact assessment ("no material impact" included) and accountable person live in their own append-only tables with immutability triggers, like `fixes` and `handoff_versions`. They never write to `issues` or `closure_checks`, and they are excluded from `decision_evidence_sha256`, so recording one does not mark the review out of date.

## Checks Claude Code adds and runs (predicted results, from DECISIONS.md)

| Check | Predicted result |
| --- | --- |
| Accept a risk | Finding stays open; open count unchanged. |
| Record an impact (including "no material impact") or an accountable person | Metadata changes; no finding status changes; review freshness unchanged. |
| Make later decisions after saving a handoff | Earlier handoff retains its original contents and state. |
| New contract version | Earlier decisions and accepted risks show "Needs re-confirmation"; originals still readable. |
| Change `catalogue.json` (development copy, in a test) | Earlier decisions show "Catalogue or rules changed"; nothing appears current. |
| Change the hash definition (test) | Old records show "checking rules updated", not "Documents changed". |
| Recheck cases 3a, 3b, 3f | Ownership carries forward for 3a only; 3b asks for confirmation; 3f has none. |
| Change an issue's evidence after its impact was assessed | Assessment shows "Needs reassessment"; original preserved; no finding closed. |
| Regression | Full test suite passes (502 Python + 5 Node before this change); **5/5 resolution scenarios**; downstream checks pass. |

## Decisions for Lina (defaults above; change any before go-ahead)

1. **B1, three hashes rather than two.** Why: the catalogue decides approval findings but sits only in `config_sha256`. Cost: a rules-code edit also marks decisions for re-confirmation. That is arguably correct, since the findings could have changed.
2. **B4, carry forward only on case 3a.** Why: a coarse `subject_key` means the "same issue" can hold different terms; silent inheritance would attach a person to a commitment they never saw. Cost: more confirmation clicks after every material revision.
3. **B5, human records excluded from the decision-evidence hash.** Why: an opinion about consequences should not make the findings look stale. Cost: none known; confirm in Part A.

## For Lina to understand (UNDERSTAND)

- Why "same issue row" is not the same as "same issue", using case 3b.
- Why the catalogue lives in a different hash from the documents, and what that meant for saved handoffs before this change.
- Why changing a hash definition needs a version number, or every old record lies about why it changed.
