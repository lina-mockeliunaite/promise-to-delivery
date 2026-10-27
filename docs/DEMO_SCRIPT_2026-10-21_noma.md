# Dealshape demo script: Noma Journeys (21 Oct 2026)

**About 4 minutes is a rehearsal target, not a timed result: time a complete run before quoting a length. Desktop, browser at full width. No API key needed. Every company, person, document and deal is fictional.**

**Not yet rehearsed in this order.** The fresh-clone run on 21 Oct used the earlier order (note before the signed contract). Run this sequence end to end once before presenting it. Order for an interview: slide 1 → this demo → slide 2 for the technical discussion. Alder Bank stays as the second demo (`docs/DEMO_SCRIPT_2026-10-20_alder.md`) for the "fix didn't survive signing" story.

**The spine of the demo: three business decisions.**

- **Languages:** align the agreed scope with the paperwork.
- **Launch specialist:** an internal authorisation is not a customer-facing commitment.
- **Phone calls:** a capability boundary, settled by clarifying the customer's expectations.
- Then: a correction has to survive into the signed agreement.

## Before the demo (5 minutes)

1. **Window 1** (Terminal):
   ```
   lsof -ti :8000 | xargs kill
   lsof -ti :5173 | xargs kill
   cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
   source .venv/bin/activate
   unset ANTHROPIC_API_KEY
   .venv/bin/python reset_demo.py
   .venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```
   A `usage: kill …` line just means nothing was running. Check the prompt ends in `promise-to-delivery %`.
2. **Window 2** (Cmd + N): `cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery/frontend && npm run dev`
3. **Browser:** open `http://127.0.0.1:5173/#welcome`. It always shows the landing page.
4. **Finder** on `data/scenarios/` (Cmd + Shift + G), showing `NJ-05_v2_named_exception.md`, `NJ-07_v2_languages_aligned.md`, `NJ-09_signed_contract.md`.
5. **Your name** set in the app ("Recording as …"). Close other tabs; notifications off.
6. **Have ready to paste:** the note and the two handover notes (below the script).

## The script

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | **Landing page.** Point at the two cards | "When a deal is signed, Delivery inherits the contract. But the customer remembers the proposal, the RFP answers and the calls. Dealshape compares customer promises, contractual wording and the vendor's catalogue, and flags mismatches with linked source evidence. AI surfaces gaps, code checks sources, and teams decide the response." |
| 0:20 | **Open this sample deal** on **AI support assistant**. Pause | "An AI support platform, Aivuna, selling to a travel company. What we're delivering is here, confirmed by the deal owner. Three commitments need attention, and each needs a different business decision." |
| 0:35 | Click **AI answers customers' phone calls at launch** | "The RFP response promised phone calls. The SOW says chat and email, and Aivuna's catalogue lists chat and email only. Every quote is exact wording from the source, linked. The model reads; code checks each quote against its document. And this one is a capability boundary: no exception can make voice exist." |
| 1:00 | Close the drawer. **Dedicated launch specialist…** → **Add updated document** → `NJ-05_v2_named_exception.md` → check **This is: A new version of: Internal approvals note** → **Add and check** | "A launch specialist for 30 days at no charge. Two gaps: it needs a named approval, and it isn't in the contract. The head of Customer Success has now authorised an exception." *Point at What changed, then* **pause**: "The approval gap closed. The contract gap is still open. An internal authorisation is not a customer-facing contractual commitment; someone still has to put it in the agreement." |
| 1:45 | **Support in 12 languages at launch** → **Add updated document** → `NJ-07_v2_languages_aligned.md` → check **A new version of: Draft contract** (not the SOW) → **Add and check** | "Sales promised 12 languages; the draft contract said four. Here the fix is aligning the paperwork with the agreed scope." *Point:* "Closed by documents, naming the version that closed it." *Glance at the phone row:* "And the revised contract surfaces a new gap: phone calls appear nowhere in it." |
| 2:15 | Sidebar **+ Add** → `NJ-09_signed_contract.md` → **This is: A new document**, **Type: Signed contract** → **Add and check** | "The signed contract arrives, and the stage moves to Signed because of the document." *Open the languages row:* "Earlier fixes are checked against the signed text. This one is confirmed. If it weren't, it would come back for review." |
| 2:40 | **AI answers customers' phone calls** → **Record a note** → **Mark as addressed by note** → paste the note → **Save note** | "Phone calls are a capability boundary, and the answer was a conversation, not a document. This note records the customer's agreement of 19 October to launch on chat and email; it doesn't mean the scope was decided after signing. It's a recorded decision, so it looks different from documentary support: outlined grey, not green, and every gap stays visible." |
| 3:05 | Paste both handover notes → **Lock handover record** | "Sales and Delivery each write their note, and locking freezes the record." |
| 3:20 | **Locked record.** Point at the summary line | "What Delivery inherits: one commitment closed by documents; one addressed by note; and one still needing attention, the launch specialist the contract never got. Signing and locking the handover don't authorise or resolve that omission. Dealshape keeps the open commitment explicit in the handover; what to do about it is a business decision." |
| 3:50 | Stop | "Fictional deals, two vendors' catalogues, one pipeline. Happy to go into how it's built and tested, or what it can't do." |

**Text to paste**

- **Note (phone row):** "Noma agreed on 19 Oct to launch on chat and email; voice is not offered."
- **Sales (deal owner):** "Signed with the launch specialist still missing from the contract. The exception covers 30 days at no extra charge. Noma launches on chat and email; voice isn't offered. Raise the specialist at kickoff."
- **Delivery:** "Accepted. We start on chat and email as contracted; the specialist's contract commitment goes on the kickoff agenda."

**Why the note comes after the signed contract.** It makes the sequence easier to follow: the paperwork first, then the decision that rests on a conversation. It does not remove the underlying limitation. Notes reopen when documents in their checking fingerprint change, and signed paperwork is currently excluded, so a signed clause contradicting a note could go undetected. Reconfirming notes at signing is a **future improvement**, not built behaviour.

## If asked: show, don't narrate
- **Hashes:** in the locked record, scroll to **Documents at handover** → click **Signed contract** → *Matches the text shown*. "Each document is stored with a SHA-256 of the exact text Dealshape read; the record's fingerprint covers them all."
- **Print:** tick **Include full document text** → **Print or save as PDF**.
- **Stage:** "The stage comes from the documents on the right; nobody sets it by hand."
- **Refused findings:** on Alder, "1 proposed finding couldn't be verified against the documents and isn't shown."

## If something goes wrong

| It happens | Say, and do |
| --- | --- |
| The landing page doesn't show | Open `http://127.0.0.1:5173/#welcome`, or click **About Dealshape** in the home footer |
| The page won't load, or "Method Not Allowed" | "Old server, ten seconds." Ctrl + C in Window 1, run the two `lsof` lines, restart Window 1 |
| The form says "This looks like a new version of …" | You chose "A new document" for a revised file. Click the primary button **Use "A new version of …"**. "And it catches me when I file the wrong way." |
| "This review needs the model…" | A revision was filed as a new document earlier. "Nothing was added; that's the safety rule." Skip ahead, or reset and refile |
| Wrong file picked | The app warns you ("This looks like a…"). Cancel, pick the right one |

## Likely questions (short answers)

- **"Where does the AI come in?"** "The model proposes potential gaps from the documents and the catalogue. Code checks the quoted wording and references, rechecks stored claims and controls status changes. People clarify expectations, set capability boundaries, authorise exceptions, update agreements and decide how to proceed. At runtime it's an AI-powered review workflow, not an agent: the model doesn't choose tools or plan steps."
- **"Is it agentic?"** "The way I built it was. I used Claude Code as an agentic development partner: I defined the problem, the product rules and the acceptance criteria, and directed the implementation through tasks, review and testing. Inside Dealshape, the model identifies potential gaps, code checks the evidence, and people make the commercial decisions."
- **"Give me one concrete example of working with Claude Code."** *Prepare one: the task you gave it, what it changed, how the result was checked, and where you intervened.* (See the primer, section 16.)
- **"Why can't someone just mark it resolved?"** "They can record a decision, and it's shown as exactly that: a typed note, visibly different from documentary support, kept in the record. It isn't an authenticated approval."
- **"Why was the specialist still open at signing?"** "The scenario doesn't say why, and I don't invent a reason. Signing and locking don't resolve it. Dealshape keeps it explicit in the handover; the decision stays with the business."
- **"What does the signed-contract check do?"** "It attempts to confirm earlier draft fixes in the signed text, and anything it can't confirm returns for review. It doesn't review all new or conflicting clauses, or resolve legal precedence or incorporation by reference."
- **"Does matching the source prove it's true?"** "No. It shows the wording is where the finding says it is. It doesn't establish truth, legal meaning, completeness or whether we can actually deliver."
- **"What does the hash prove?"** "That the text you're viewing is the text Dealshape read when the record was locked. It covers the text, not the original file, and the browser check trusts the server. Tamper evidence comes from the record fingerprint kept outside the system, for example on the printout."
- **"How do you know it works?"** "My first, rules-based version found 1 of 3 planted issues on a held-out deal, so I rebuilt it. The rebuilt version, v2, found 8 of 8 labelled issues on a different held-out fictional deal, matching a single-prompt baseline. So what it adds isn't better detection; it's findings you can check and close. It's a small, synthetic sample, and today's demo deals aren't part of that evaluation."
- **"What happens without an API key?"** "The demo uses saved model readings. The app still verifies every finding and rechecks every stored claim; only the model call is skipped."
- **"Is it tuned to one vendor?"** "Two vendors' catalogues run through one pipeline. The prompt still names the original vendor; I didn't change it because that would invalidate every saved reading."
- **"What doesn't it do?"** "It checks wording, not legal meaning. No scanned PDFs. No CRM or Drive connectors. And it hasn't yet been tested unaided by someone who's never seen it."
