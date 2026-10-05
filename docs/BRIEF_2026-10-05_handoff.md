# Brief: handoff view and exports (Sunday 4 Oct Outcome 2, built Mon 5 Oct)

*Drafted by Claude (project) for Lina's approval. Claude Code builds it as ONE change set: propose files and approach first, wait for Lina's go-ahead.*

## Boundaries (non-negotiable)

- Do not change the evaluated pipeline: `extract.py`, `schema.py`, `sales_filter.py`, `ledger_consolidate.py`, `terms.py`, `references.py`, `rules.py`, `agent.py`. Read from the ledger only.
- No model calls. No new extraction. If a handoff section cannot be filled from what the ledger already holds, leave it out rather than infer it.
- Never read `data/coral_pay/`. Only path parameter stays `{deal}`; same deal allowlist; any write route uses `write_guard`.
- Exports never contain the API key, file-system paths or internal IDs.

## What to build

**1. Saved handoff record (backend).**
- Saving creates an immutable snapshot of one specific review (review id plus source-set and decision-evidence hashes). A new save is a new version; earlier versions are never overwritten (database trigger, like approved fixes).
- Saving is refused while the review is *Review out of date* (plain message: "Rerun the review before saving the handoff").
- Reviewer decision, one of:
  - **Ready for handoff**: allowed only when no issue is open.
  - **Proceed with open items**: allowed only when every open issue has an owner.
  - **Not ready**.
  Plus reviewer name, date, note. The decision never changes any issue's state.

**2. Handoff view (frontend), for Delivery, CS and Support.** Plain language, calm style as in the existing workspace.
- Header: deal, review date, freshness, reviewer decision, scope line: "Demonstrated on fictional deals with a complete capability catalogue."
- **Open items first**: commitment, what needs attention, owner, next step, evidence quote with source.
- All commitments, clean ones included: the promise, status, where it sits in the contract.
- Approved exceptions with the approving evidence.
- Fix and decision history (route, owner, date, rationale, evidence version).
- Reviewed sources: document, type, version, date, included or excluded.

**3. Exports.**
- **CSV**: one row per issue, plus one row for each clean commitment. Columns: Commitment, What needs attention, Status, Owner, Note, Evidence quote, Source document, Source version.
- **Readable summary**: a printable HTML page of the handoff view (browser "Save as PDF" is enough). Unresolved items stay visible at the top.
- Both export a *saved* handoff version, not the live screen.

**4. Remove internal keys** such as "C07" and statement IDs from all on-screen text and both exports.

## Checks Claude Code adds and runs

- Tests: save refused when out of date; "Ready for handoff" refused with an open issue; "Proceed with open items" refused with an unowned open issue; saved versions immutable; CSV includes clean commitments and open issues; no "C0"/"S0"-style internal keys in exports; non-allowlisted deal → 404; write without the header → refused.
- Full test suite passes (399 before this change).
- Browser walk-through on Harbour Bank: review → approval-only fix → recheck → save with "Proceed with open items" → contract gap and conflict appear at the top of both exports.

## Decisions for Lina (defaults above; change any before go-ahead)

1. "Ready for handoff" blocked while any issue is open. Why: a reviewer cannot erase a system finding.
2. Readable export as printable HTML, not a generated PDF/DOCX file. Why: no new dependency, same content.
3. Milestones, dependencies and service obligations appear only as commitments already in the ledger, not as separate extracted sections. Why: anything more needs pipeline changes before the freeze.
