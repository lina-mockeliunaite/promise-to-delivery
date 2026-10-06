# Brief: deal workspace layout after Checkpoint 1 (6 Oct)

*Drafted by Claude (project) for Lina's approval. **Do not start until Part B of `BRIEF_2026-10-06_integrity.md` is merged**: the decision statuses below depend on it. Claude Code proposes files and approach first, then works in one change set per section. No Git commands.*

## Why

At the real Checkpoint 1 (Head of Growth, 6 Oct) neither the reviewer nor Lina could follow the fix flow: evidence was uploaded in one place, selected from a dropdown in another, and the result appeared away from the finding. The main page did not update in a way either could read. Reviewer: "too much text"; "evidence and status need to be on the same line as the issue"; "a quick summary at the top: what the deal is, the key deliverables, where the conflicts are". Audience for the first screen: CRO, founder, heads of growth, delivery and support.

Reference mocks (simulation only, not the app): `docs/mock/mock_polygon_after_check.png`. `mock_overview_v1_superseded.png` shows the earlier card layout that this brief **replaces** with compact rows.

## Boundaries

- Frontend and `workspace.py`/`api.py` read models only. Do not edit the evaluated pipeline (`extract.py`, `schema.py`, `sales_filter.py`, `ledger_consolidate.py`, `terms.py`, `references.py`, `rules.py`, `agent.py`). `recheck.py`: no changes; 5/5 scenarios must still pass.
- No model calls. No new statuses in the backend beyond what integrity Part B provides.
- Never read `data/coral_pay/`. Never seed Coral Pay in the UI.

## Level 1 — Deal overview (fits one desktop screen for Harbour Bank)

1. **Header:** deal name; source versions in use (e.g. "Draft contract v1 · SOW v2 · Pricing note v1"); one **deal decision deadline** (date field, deal-level only).
2. **About this deal:** one or two lines, **typed by a person**, labelled "Deal note · entered by <name>". Never generated.
3. **Two counts, never merged:** "N findings unresolved" and "N findings awaiting decision". A decision ("Okay to proceed", "Must fix before signing") never reduces the unresolved count.
4. **Commitments with open findings, one compact row each:** commitment name · *Told:* short term · *Contract:* short term · finding types in plain words (*No approval recorded*, *Missing from contract*, *Contract says something different*, *Needs evidence*) · open count · accountable person (amber **Unassigned** if none) · decision status.
5. **Sort:** open findings, descending; ties A–Z. Label it ("Sorted by open findings"). No severity or impact sort.
6. **Collapsed below:** Resolved findings (n) · Other commitments (no issues raised / not checked) · Review coverage & saved handoff.
7. Any **Needs re-confirmation** decision shows on its row and in the counts line ("2 decisions need re-confirmation").

## Level 2 — Commitment detail (opens from a row)

1. Told vs contract side by side, short terms. Exact quotes, sources and dates sit behind "Promise trail · n sources" (timeline, oldest first).
2. **One block per finding**, open first: plain-language title; status badge; what would close it; responsible team; accountable person (name field); decision status; business impact "Not assessed" until a person records it.
3. **Fix inside the finding block — one flow, in order:**
   1. *Attach evidence* (file picker in the block).
   2. *Confirm document type* — shown as a required, pre-selected but visible choice, with the plain-language consequence ("Counts as approval evidence" / "Replaces SOW v1"). This step exists because the wrong file and the wrong type were both chosen in the live demo.
   3. Note (optional) and signed-off by.
   4. **Save & check.**
   The result appears **in that block, immediately**, and once in a banner at the top. Do not repeat it a third time.
4. **Cross-finding effects are stated.** If one document closes or changes another finding, the result says so: "This document also resolved: Contract says something different."
5. **Resolved findings name their evidence:** "Resolved by SOW v2 (Annex A), 6 Oct, signed off by <name>", with a link that opens the document. "Resolved by evidence" alone is not enough.
6. **Record a decision on this finding** (collapsed): *Okay to proceed* or *Must fix before signing*, each with name and reason. The finding stays open. A *Must fix* flag stays visible if the finding later resolves or the decision goes stale, until a named person reviews and clears it.

## Re-confirmation (Lina's decision, 6 Oct)

Deal-wide for this prototype: when any bound hash changes (sources, decision evidence and — per integrity B1 — catalogue/rules config), **every** active decision shows "Needs re-confirmation" with the plain-language reason. Original decisions stay readable. Known limitation to state in the README: on a large deal this creates re-confirmation noise; narrower carry-forward needs tested dependency tracking (catalogue inputs and missing evidence included). Later list.

## Checks (predict before running)

| Check | Expected |
| --- | --- |
| Harbour Bank overview at 1440×900 | All commitments with open findings visible without scrolling |
| Polygon: attach `HB-05_v2_named_exception.md` as pricing note → Save & check | Approval finding resolves; two contract findings stay open; result shown in the block |
| Polygon: attach `HB-06_v2_annex_aligned.md` as SOW → Save & check | Missing-from-contract and contract-says-different resolve; result names both |
| Attach a file with the wrong document type | Type step visible before save; wrong type does not silently count as approval |
| Record "Okay to proceed", then any new source | Unresolved count unchanged; decision shows Needs re-confirmation |
| Mark "Must fix before signing", then resolve the finding | Flag still visible until cleared by a named person |
| Regression | Full test suite; 5/5 scenarios; downstream checks |

## For Lina to understand (UNDERSTAND)

- Why a decision is shown next to a finding but never changes its status.
- Why re-confirmation is deal-wide here, and what it would take to narrow it.
- Why the document-type step is a safety check, not a formality.
