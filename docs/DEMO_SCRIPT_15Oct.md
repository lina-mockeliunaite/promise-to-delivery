# Demo script, 3 minutes (v2, rewritten 15 Oct from the live walk-through)

*Audience: CRO, founder, heads of growth, delivery and support. Say it in your words; the clicks are fixed. Rehearse twice before recording. Replaces the 10 Oct v1 script.*

## Before you press record (10 min)

1. Stop both terminals. `.venv/bin/python reset_demo.py`. Harbour Bank should show **6 unresolved, 6 awaiting decision**.
2. Terminal 1: set the key (`read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY`, paste, Enter), then `.venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000`.
3. Terminal 2: `cd frontend && npm run dev`. Browser at http://127.0.0.1:5173, about 1440×900, zoom 100%.
4. Finder window with `data/scenarios/HB-05_v2_named_exception.md` and `HB-06_v2_annex_aligned.md`.
5. Close other tabs and notifications. **Click Save & check once and wait.**

## The script

| Time | Click | Say |
| --- | --- | --- |
| 0:00 | Overview, nothing clicked | "When a deal is signed, Delivery inherits the contract, but the customer remembers the proposal and the calls. This is Harbour Bank, a fictional deal. The tool has read every document and lists the promises that the paperwork doesn't back up." |
| 0:20 | Click the **Polygon** row (second) | "Let's take the one where the contract contradicts the customer. They were told real-time screening; the draft contract says hourly batch." |
| 0:35 | Point at the two findings, at the bold **Checked against** lines | "Two separate problems: nobody approved it, and the contract says something different. Each line in bold is what the code checked, word for word, against the documents." |
| 1:00 | **No approval recorded** → attach `HB-05_v2_named_exception.md` → Pricing and services note → sign off → **Save & check** | "Product approves a named exception. I attach it and check." *(Point at the result.)* "The approval closed. The contract problem is still open, because an approval doesn't change the contract. A partial fix stays visibly partial." |
| 1:30 | **Contract says something different** → attach `HB-06_v2_annex_aligned.md` → Draft SOW → **Save & check** | "Now the SOW is aligned to real time. The conflict closes, and the tool spots one more gap: the 1 December launch date the customer was promised isn't in the SOW. Fixing one problem surfaces the next." |
| 2:00 | Open the **1 December** finding → **Okay to proceed** → reason: *Date depends on the customer's sandbox access, now confirmed for 10 Nov. Commercial to confirm the SOW timeline before signing.* → back to overview | "Some things need a judgement. I record it with my name and a reason." *(Point at the counts: 5 unresolved, 4 awaiting decision.)* "Unresolved didn't move. A decision is not a fix." |
| 2:30 | Close | "Where does the AI come in? The model reads all the paperwork and proposes problems, with exact quotes. Code checks every quote and the product catalogue before anything is shown, and only code can close a finding. I tested it on a deal it had never seen: it found all 8 planted issues, with no false alarms." |

## If something goes wrong on camera

- **"Nothing was saved … API key":** the key isn't set in Terminal 1. Stop, set it, restart the server, record again.
- **Counts aren't 6 and 6 at the start:** you didn't reset. Stop, reset, start again.
- **A pricing note shows "version 3":** Save & check was clicked twice. Reset and record again.

## What not to say

- Don't read the grey sentence above the bold line: it is the model's summary and is not checked (it says "signed SOW"; the SOW is a draft).
- Don't call it validated or accurate on real deals: "demonstrated on fictional deals; tested on one sealed deal".
- Don't say rules decide: in v2 the model finds, code checks and closes, people decide.
- Don't promise integrations.
