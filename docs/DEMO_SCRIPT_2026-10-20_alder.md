# Dealshape demo script: Alder Bank (20 Oct 2026)

**About 4 minutes. Desktop, browser at full width. Everything is fictional.**

## Before the demo (5 minutes, JUST DO)

1. **Check nothing old is running.** `lsof -ti :8000 :5173` must print nothing. If it prints numbers, run `lsof -ti :8000 :5173 | xargs kill`.
2. **Window 1:**
   ```
   cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
   source .venv/bin/activate
   read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
   [ -n "$ANTHROPIC_API_KEY" ] && echo "key set" || echo "key missing"
   .venv/bin/python reset_demo.py
   .venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```
3. **Window 2:** `cd frontend && npm run dev`. Then open http://127.0.0.1:5173.
4. **Files ready:** keep a Finder window open on `data/scenarios/`, showing `AB-05_v2_named_exception.md`, `AB-06_v2_coaching_added.md` and `AB-09_signed_contract.md`.
5. **Your name** is set in the app ("Recording as …").
6. **Close every other tab.** Turn off notifications.

## The script

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | Home page | "When a deal is signed, Delivery inherits the contract. But the customer remembers the proposal, the RFP answers and the calls. Dealshape reads that whole paper trail and shows the shape of the deal: what we're delivering, and where what the customer was told doesn't match what the contract says or what we can sell." |
| 0:20 | Open **Alder Bank**. Pause. | "This is a fictional bank buying scam protection for instant payments. In ten seconds you can see what we're delivering, here, and that three commitments need attention. The stage, Contracting, comes from the documents on the right. Nobody sets it by hand." |
| 0:45 | Click **Coaching-scam detection live at launch** | "Here's the comparison. The RFP response promised coaching-scam detection live at launch, in the customer's exact words. The contract and SOW have no matching wording, and the catalogue says it needs a named approval, which nobody recorded. That's two separate gaps on one promise." |
| 1:10 | Point at the AI label | "The model reads the paperwork and finds these. But every quote is checked against the documents by code, and the gaps themselves are verified facts. The AI's summary is labelled as AI. It never closes anything." |
| 1:25 | **Add updated document** → `AB-05_v2_named_exception.md` → Pricing and services note → **Add and check** | "Product has approved a named exception. I add the new pricing note and the check runs again." *Point at What changed:* "The approval gap closed. The contract gap is still open, because an approval doesn't put a promise into the contract. A partial fix stays visibly partial." |
| 2:00 | Coaching row → **Add updated document** → `AB-06_v2_coaching_added.md` → Draft SOW → **Add and check** | "Now the SOW is updated. This one needs the model, because the contract side changed." *Point:* "Closed by documents, in solid green, with the document that closed it. One document closed one gap, and the app shows why." |
| 2:35 | **Hosting on Microsoft Azure** → **Record a note** → **Mark as addressed by note** → "Customer agreed AWS Sydney on the 14 Oct call." → **Save note** | "Sometimes the answer is a conversation, not a document. A note is a person's word, so it looks different: outlined grey, not green. It stays in the handover record and reopens if the documents change." |
| 3:00 | Sidebar **+ Add** → `AB-09_signed_contract.md` | "The signed contract arrives. The stage moves to Signed because of the document, not because someone clicked a button." |
| 3:15 | Add both handover notes, then **Complete handover** | "Sales and Delivery each write their note. The checklist shows what's missing, and completing locks the record." |
| 3:35 | Locked record, then **Print or save as PDF** | "This is what Delivery inherits: one needing attention, one addressed by note, one closed by documents. The record never says 'no open gaps' while something rests on a note. And it can't be edited." |
| 3:50 | Stop | "Demonstrated on fictional deals with a complete capability catalogue. The detection was tested on two sealed deals, each run once per configuration. I'm happy to go into how." |

## If something goes wrong

| It happens | Say, and do |
| --- | --- |
| "Method Not Allowed", or the page won't load | "Old server, give me ten seconds." Stop it with `lsof -ti :8000 \| xargs kill`, then restart window 1 |
| "This review needs the model…" | "That needs the API key on the server. Nothing was added, and that's the safety rule working." Then skip to the note step |
| Wrong file picked | The app warns you ("This looks like a…"). "And it catches me if I pick the wrong file." Cancel, then pick the right one |

## Likely questions (short answers)

- **"Where does the AI come in?"** "The model reads the paperwork and proposes each gap with exact quotes. Code checks every quote and citation, and only code can close a gap. The model never closes anything."
- **"Why can't someone just mark it resolved?"** "Because a note is a person's word, not proof. It's shown differently, stays in the record, and reopens if the documents change."
- **"How do you know it works?"** "Two deals were written and sealed before the code that tested them. Each configuration ran once. Version 2 found 8 of 8 labelled issues with no false flags on Atlas Remit. That's a small sample, and I say so in the README."
- **"What doesn't it do?"** "It doesn't read scanned PDFs. It checks wording, not legal meaning. And it's demonstrated on fictional deals only."
