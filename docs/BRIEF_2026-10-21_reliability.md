# Brief: demo reliability and the signed-contract check (21 Oct 2026)

**For Claude Code.**
- Inspect first. Report your plan and the files you'll change, and wait for Lina's OK.
- Git is denied in your settings; if a command is blocked, stop and say so.
- **Scope:** the two items below. Nothing else.
- **Done means:**
  - both test suites pass;
  - the four Elva deals are unchanged against the baseline (hashes, freshness, findings);
  - a DECISIONS draft.

## Why

Outside review, 21 Oct:
1. The Noma demo can't run through the screens offline. With no API key on the server, the revised-contract step is refused even though its model reading is cached.
2. **A correction made in a draft is never checked against the signed contract.** The locked record says the languages gap was "Closed by Draft contract, version 2". If the signed contract went back to four languages, the record would still say closed.

Item 2 matters most. It sits exactly where Delivery places its trust.

## 1. The cached-step bug

**Cause, from the 20 Oct screenshot run:** the add-and-check guard looks the cache up with an empty date, while the real review uses the stored date, so the guard reports a miss.

**Fix:** the guard and the review must build the cache key with **one shared function**, so the two can never disagree. Don't duplicate the key logic.

**Tests:**
- **Offline replay:** a fresh reset with no API key, then the Noma demo steps through the add-and-check route itself, not a script. Every step whose reading is cached succeeds with no model call.
- **A changed document with no key** is still refused, with "Nothing was added".
- **The cache folder** holds the same files before and after the test suite.

## 2. Check that a draft's fix survives into the signed paperwork (UNDERSTAND for Lina)

**The rule:** a gap closed by a draft contract or SOW is only as good as the signed agreement. When a signed contract or signed SOW is added, code checks **every gap that is closed by documents and whose closure relies on contract or SOW wording.**

**The check is deterministic, with no model call:**
- **What it looks for:** the closing wording, the contract sentence that now matches (the stored lookup sentence or the closing evidence), in the signed document.
- **How it matches:** with the verifier's normalisation (whitespace collapsed, lower-case).

**The outcomes:**
- **Found:** the closed row and the drawer add "Confirmed in the signed contract (Signed contract, 20 Oct)".
- **Not found:** the closure is no longer supported by the paperwork that counts. Show the commitment as **Needs attention**, with the reason "The fix in Draft contract, version 2 was not found in the signed contract." Keep the history of the earlier closure visible.
- **Approval-only closures** (from the pricing note) are not affected by signed paperwork. Skip them.
- **No signed document yet:** show nothing.

**Assess before building:**
- **Where this lives.** Prefer files outside the configuration hash, as a layer computed when the page is read, over changing `recheck.py`, `ledger_v2.py` or `detect_v2.py`. If reopening a gap properly needs a change to a hashed file, say so and stop. We decide that together, because it would make every existing review stale.
- **The locked record.** New records store the confirmation result, as an additive field. Records locked earlier stay untouched.
- **The data.** Does the existing `NJ-09_signed_contract.md` contain the 12-languages sentence verbatim? It should be confirmed. Tell me the exact sentence.
- **The negative test.** It needs a scratch signed contract that says four languages, created in a test fixture only, never in `data/` or the demo. The languages gap must show as Needs attention with the reason above.
- **Out of scope:** a signed contract that newly contains wording for an open gap does **not** close it in this change. Note it as a possible later step.

## 3. After building

1. Run both suites and the four-deal regression check.
2. Do the offline replay of the full Noma flow through the add-and-check route: reset, pricing note, revised contract, note, signed contract, lock. Report each step's result and whether the model was called.
3. **README:** replace the limitation "A signed contract marks the deal Signed; its wording is not compared with the drafts" with what is now true, and keep any part that is still not checked.
4. **DECISIONS draft** `docs/DECISIONS_DRAFT_2026-10-21_reliability.md`:
   - **Chose:** one shared cache-key function; the signed-paperwork confirmation and its rule.
   - **Rejected:** trusting draft closures at lock time; re-reading signed paperwork with the model.
   - **Why:** the outside review, 21 Oct.
