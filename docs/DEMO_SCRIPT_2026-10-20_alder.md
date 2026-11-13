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
4. **Files ready:** keep a Finder window open on `data/scenarios/`, showing `AB-05_v2_named_exception.md`, `AB-06_v2_scam_alerts_added.md` and `AB-09_signed_contract.md`.
5. **Your name** is set in the app ("Recording as …").
6. **Close every other tab.** Turn off notifications.

## The script

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | Home page | "When a deal is signed, Delivery inherits the contract. But the customer remembers the proposal, the RFP answers and the calls. Dealshape reads that whole paper trail and shows the shape of the deal: what we're delivering, and where what the customer was told doesn't match what the contract says or what we can sell." |
| 0:20 | Open **Alder Bank**. Pause. | "This is a fictional bank buying scam protection for instant payments. In ten seconds you can see what we're delivering, here, and that two commitments need attention. The stage, Contracting, comes from the documents on the right. Nobody sets it by hand." |
| 0:45 | Click **Scam-call alerts live at launch** | "Here's the comparison. The RFP response promised scam-call alerts, which warn the bank when a customer seems to be on a call with a scammer while making a payment, live from the 1 February launch, in the exact wording of the source document. The contract and statement of work have nothing about it, and the catalogue says the feature is in beta and needs a named approval, which nobody recorded. That's two separate gaps on one promise." |
| 1:10 | Point at the AI label | "The model reads the paperwork and finds these. But every quote is checked against the documents by code, and the gaps themselves are verified facts. The AI's summary is labelled as AI. It never closes anything." |
| 1:25 | Scam-call alerts row → **Add updated document** → choose the file `AB-05_v2_named_exception.md` → check the form reads **This is: A new version of: Internal approvals note (currently v1)** (it is pre-selected; if it says "A new document", choose the version) → **Add and check** | "Product has approved it, but only from 1 May. I add the new approvals note and the check runs again." *Point at the result dialog ("Rechecked after adding …"; **Got it** closes it and highlights the rows that changed):* "The approval was found, but it starts later than the promised date, and the gap stays open. The promise was live from 1 February; the approval starts on 1 May. Open the row: Why it's open, with the two clauses and their dates. And the contract gap is still open too, because an approval doesn't put a promise into the contract." |
| 2:00 | Scam-call alerts row → **Add updated document** → choose the file `AB-06_v2_scam_alerts_added.md` → check the form reads **This is: A new version of: Draft SOW (currently v1)** → **Add and check** | "Now the statement of work is updated. The contract side changed, so a model reading is needed. The demo uses a saved reading, and the app still verifies every finding." *Point:* "The contract gap is closed by documents, in solid green, with the document that closed it. The approval gap is still open, and now the reason names the contract: the contract start date is earlier than the approved start date." |
| 2:35 | **Hosting on Microsoft Azure** → **Record a note** → **Mark as addressed by note** → "Customer agreed AWS Sydney on the 14 Oct call." → **Save note** | "Sometimes the answer is a conversation, not a document. A note is a person's word, so it looks different: outlined grey, not green. It stays in the handover record and reopens if the documents change." |
| 3:00 | Sidebar **+ Add** → choose the file `AB-09_signed_contract.md` → **This is: A new document**, **Type: Signed contract** (leave Dated as today) → **Add and check** | "The signed contract arrives. The stage moves to Signed because of the document, not because someone clicked a button." **Then point at the scam-call alerts row:** "The signed statement of work repeats the revised sentence, so the contract fix is confirmed in the signed contract. But the approval still starts on 1 May, and the signed start date is 1 February: the signed start date is earlier than the approved start date. The commitment still needs attention." **Open the row:** "Why it's open: the signed clause, 1 February, and the Product approval, 1 May, each with its source link." *This is the closing moment: an approval has to start when the promise does.* |
| 3:15 | Add both handover notes, then **Complete handover** | "Sales and Delivery each write their note. The checklist shows what's missing, and completing locks the record." |
| 3:35 | Locked record, then **Print or save as PDF** | "This is what Delivery inherits: one needing attention, the scam-call alerts, whose approval starts after the signed launch date, and one addressed by note, the hosting. The contract fix is closed and confirmed in the signed contract. The record never says 'no open gaps' while something rests on a note. And it can't be edited." *The locked record reads "Handed over with 1 needing attention, 1 addressed by note."* |
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
- **"Why do scam-call alerts still need attention after the approval and the signed statement of work?"** "Because the approval starts on 1 May 2027 and the promise, in the signed statement of work, starts on 1 February. Dealshape reads two explicit dates from quotes it has already verified: the approval's effective date, which it finds after 'from', 'effective' or 'starting', and the commitment's start date, from the signed contract first, then the draft, then the customer's promise. If the approval starts later, the approval gap stays open and says which source the start date comes from. If either date is missing it behaves as before."
- **"And if a fix in a draft is not in the signed paper?"** "Then the signed check reopens it: Dealshape looks for the closing wording in the signed document's own text. It does not compare dates or terms there. In this deal the signed statement of work repeats the revised sentence, so it says 'Confirmed in the signed contract'. One limit: it errs toward attention, so a signed contract that incorporates a revised statement of work by reference, without repeating it, would reopen."
- **"What doesn't it do?"** "It doesn't read scanned PDFs. It checks wording, not legal meaning. And it's demonstrated on fictional deals only. On approvals: it ignores an approval's end date, so an approval that expires early is not caught; it reads only day-month-year dates, so a quarter or a month on its own counts as no date; and with no date on either side it does nothing extra."
