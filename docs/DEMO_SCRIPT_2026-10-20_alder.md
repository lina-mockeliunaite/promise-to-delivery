# Dealshape demo script: Alder Bank (20 Oct 2026)

**About 4 minutes. Desktop, browser at full width. Everything is fictional.**

## Before the demo (5 minutes, JUST DO)

1. **Stop anything old that is still running.** Run these two lines, one after the other:
   ```
   lsof -ti :8000 | xargs kill
   lsof -ti :5173 | xargs kill
   ```
   If a line prints a short usage message (`usage: kill …`), nothing was running on that port, which is what you want. Anything else is fine too: it was an old server and it has now been stopped.
2. **Window 1:**
   ```
   cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
   source .venv/bin/activate
   unset ANTHROPIC_API_KEY
   .venv/bin/python reset_demo.py
   .venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```
3. **Window 2:** `cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery/frontend && npm run dev`. Then open http://127.0.0.1:5173/#welcome, which always shows the landing page.
4. **Files ready:** keep a Finder window open on `data/scenarios/`, showing `AB-05_v2_named_exception.md`, `AB-06_v2_coaching_added.md` and `AB-09_signed_contract.md`.
5. **Your name** is set in the app ("Recording as …").
6. **Close every other tab.** Turn off notifications.

## The script

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | Home page | "When a deal is signed, Delivery inherits the contract. But the customer remembers the proposal, the RFP answers and the calls. Dealshape reads that whole paper trail and shows the shape of the deal: what we're delivering, and where what the customer was told doesn't match what the contract says or what we can sell." |
| 0:20 | Open **Alder Bank**. Pause. | "This is a fictional bank buying scam protection for instant payments. In ten seconds you can see what we're delivering, here, and that three commitments need attention. The stage, Contracting, comes from the documents on the right. Nobody sets it by hand." |
| 0:45 | Click **Coaching-scam detection live at launch** | "Here's the comparison. The RFP response promised coaching-scam detection live at launch, in the exact wording of the source document. The contract and SOW have no matching wording, and the catalogue says it needs a named approval, which nobody recorded. That's two separate gaps on one promise." |
| 1:10 | Point at the AI label | "The model reads the paperwork and finds these. But every quote is checked against the documents by code, and the gaps themselves are verified facts. The AI's summary is labelled as AI. It never closes anything." |
| 1:25 | Coaching row → **Add updated document** → choose the file `AB-05_v2_named_exception.md` → check the form reads **This is: A new version of: Pricing and services note (currently v1)** (it is pre-selected; if it says "A new document", choose the version) → **Add and check** | "Product has approved a named exception. I add the new pricing note and the check runs again." *Point at What changed:* "The approval gap closed. The contract gap is still open, because an approval doesn't put a promise into the contract. A partial fix stays visibly partial." |
| 2:00 | Coaching row → **Add updated document** → choose the file `AB-06_v2_coaching_added.md` → check the form reads **This is: A new version of: Draft SOW (currently v1)** → **Add and check** | "Now the SOW is updated. The contract side changed, so a model reading is needed. The demo uses a saved reading, and the app still verifies every finding." *Point:* "Closed by documents, in solid green, with the document that closed it. One document closed one gap, and the app shows why." |
| 2:35 | **Hosting on Microsoft Azure** → **Record a note** → **Mark as addressed by note** → "Customer agreed AWS Sydney on the 14 Oct call." → **Save note** | "Sometimes the answer is a conversation, not a document. A note is a person's word, so it looks different: outlined grey, not green. It stays in the handover record and reopens if the documents change." |
| 3:00 | Sidebar **+ Add** → choose the file `AB-09_signed_contract.md` → **This is: A new document**, **Type: Signed contract** (leave Dated as today) → **Add and check** | "The signed contract arrives. The stage moves to Signed because of the document, not because someone clicked a button." **Then point at the coaching row, which is back under Needs attention:** "The revised SOW added coaching, but the signed contract incorporates the 9 October SOW — the fix never reached the signed agreement, so Dealshape reopens it. The earlier closure stays visible beneath it." *This is the closing moment: a fix in a draft is only as good as what was signed.* |
| 3:15 | Add both handover notes, then **Complete handover** | "Sales and Delivery each write their note. The checklist shows what's missing, and completing locks the record." |
| 3:35 | Locked record, then **Print or save as PDF** | "This is what Delivery inherits: two needing attention, the 750,000 volume and the coaching detection that never made it into the signed contract, and one addressed by note. Nothing is closed by documents, because the one fix we made didn't survive signing. The record never says 'no open gaps' while something rests on a note. And it can't be edited." *The locked record reads "Handed over with 2 needing attention, 1 addressed by note."* |
| 3:50 | Stop | "Demonstrated on fictional deals with a complete capability catalogue. The detection was tested on two sealed deals, each run once per configuration. I'm happy to go into how." |

## If something goes wrong

| It happens | Say, and do |
| --- | --- |
| "Method Not Allowed", or the page won't load | "Old server, give me ten seconds." Stop it with `lsof -ti :8000 \| xargs kill`, then restart window 1 |
| "This review needs the model…" | "Nothing was added; that's the safety rule." Skip to the note step, or reset and refile as **A new version of: …** |
| The form says "This looks like a new version of …" | You chose "A new document" for a revised file. It would be dated today and sit beside the original. Click the primary button **Use "A new version of …"**. The quiet "Add as a new document anyway" is the only way past it |
| "This review needs the model…" and the message names a document "added earlier as a new document" | An earlier step was filed as a new document, not a new version. Reset the demo and add it as **A new version of: …** |
| Wrong file picked | The app warns you ("This looks like a…"). "And it catches me if I pick the wrong file." Cancel, then pick the right one |

## Likely questions (short answers)

- **"Where does the AI come in?"** "The model reads the paperwork and proposes each gap with exact quotes. Code checks every quote and citation, and only code can close a gap. The model never closes anything."
- **"Why can't someone just mark it resolved?"** "They can record a decision, and it's shown as exactly that: a typed note, visibly different from documentary support, kept in the record. It reopens if a document in its checking fingerprint changes; signed paperwork doesn't reopen it."
- **"How do you know it works?"** "Two deals were written and sealed before the code that tested them. Each configuration ran once. Version 2 found 8 of 8 labelled issues with no false flags on Atlas Remit. That's a small sample, and I say so in the README."
- **"Why did coaching reopen after the signed contract?"** "Because the signed contract says the services are those in the Statement of Work dated 9 October, which is the original SOW without coaching. A fix in a draft only counts if the signed paperwork has it. Dealshape looks for the exact wording in the signed document, so it reopened the gap. If the signed contract repeated the clause, it would say 'Confirmed in the signed contract'. One limit: it errs toward attention, so a signed contract that incorporates a revised SOW by reference, without repeating it, would also reopen."
- **"What doesn't it do?"** "It doesn't read scanned PDFs. It checks wording, not legal meaning. And it's demonstrated on fictional deals only."
