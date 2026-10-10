# Demo script — 3 minutes (for the 15 Oct recording and Checkpoint 2)

*Drafted by Claude, 10 Oct. Audience: CRO, founder, heads of growth, delivery and support. Say it in your words; the clicks are fixed. Rehearse twice before recording.*

## Before you press record (10 min)

1. Stop both terminals. `.venv/bin/python reset_demo.py` (a clean deal: 8 open findings).
2. Terminal 1: set the key (`read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY`), then start the server. The key is needed only for step 6 (the SOW is read by the model, about $0.01).
3. Terminal 2: `cd frontend && npm run dev`. Browser at http://127.0.0.1:5173, window about 1440×900, zoom 100%.
4. Add the deal note beforehand (one line, your name, a deadline), so the first screen is complete.
5. Have the two files ready in a Finder window: `data/scenarios/HB-05_v2_named_exception.md` and `HB-06_v2_annex_aligned.md`.
6. Close other tabs and notifications.

## The script

| Time | Click | Say (your words) |
| --- | --- | --- |
| 0:00 | Overview, nothing clicked | "When a deal is signed, Delivery inherits the contract — but the customer remembers the proposal, the RFP answers and the calls. This is Harbour Bank, a fictional deal. The tool has read every document and built the deal as it was actually promised." |
| 0:20 | Point at the rows and the two counts | "Four promises have open findings. Top one: the customer was told **real-time** wallet screening; the contract says **batch**. Eight findings unresolved, eight awaiting a decision — two different numbers, on purpose." |
| 0:40 | Click the Polygon row; open **Promise trail** for two seconds, close it | "Here's how it drifted: exploratory on the first call, a firm promise by the proposal, and the contract quietly says batch. Every line is a word-for-word quote from a document." |
| 1:00 | Point at the three finding blocks | "One promise, three separate problems: nobody approved it, it's missing from the contract, and the contract says something different. They're separate because fixing one doesn't fix the others." |
| 1:15 | **No approval recorded** → attach `HB-05_v2_named_exception.md` → point at the confirm line → Signed off by → **Save & check** | "Product approves a named exception. I attach it to the finding, confirm what it is — this step exists because I attached the wrong file in my first live demo — and check." |
| 1:35 | Read the result banner | "The approval closed. The contract problems are still open — an approval doesn't put anything into the contract. That's the point of the tool: a partial fix stays visibly partial." |
| 1:50 | **Missing from contract** → attach `HB-06_v2_annex_aligned.md` (Draft SOW) → **Save & check** | "Now Delivery aligns the SOW to real-time." *(The model reads the new SOW: a few seconds.)* "Both contract findings close, and it tells me this one document closed both." |
| 2:15 | Back to overview; open **Resolved findings** | "Every resolved finding names the evidence that closed it and who signed it off." |
| 2:25 | VASP row → a finding → **Record a decision** → **Okay to proceed** with a reason → back to overview | "Sometimes the business decides to go ahead anyway. That's recorded with a name and a reason — and look: unresolved didn't move. A decision is not a fix." |
| 2:45 | Close | "Where does the AI come in? The model reads the paperwork and pulls out every promise with an exact quote. Rules make the decisions, because their verdicts can be checked. Demonstrated on fictional deals with a complete catalogue; tested on a sealed deal it had never seen." |

## If something goes wrong on camera

- **"Nothing was saved … API key":** the key isn't set in Terminal 1. Stop, set it, restart the server, and record again.
- **Wrong file attached:** the red warning shows it; say "this is exactly why the type step exists" and choose again.
- **Counts look different:** you didn't reset first. Stop, reset, start again.

## What not to say

- Don't call it validated or accurate on real deals: "demonstrated on fictional deals".
- Don't say the agent decides anything: it doesn't.
- Don't promise integrations: they're on the Later list.
