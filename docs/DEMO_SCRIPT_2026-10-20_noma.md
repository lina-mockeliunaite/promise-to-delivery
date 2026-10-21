# Dealshape demo script: Noma Journeys (20 Oct 2026)

**About 4 minutes. Desktop, browser at full width. Everything is fictional.** Same engine as the Alder Bank demo, a different vendor: Aivuna, an AI customer-support platform, selling to Noma Journeys, a Singapore travel company. Dealshape reviews this software sale, not the assistant.

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
   read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
   [ -n "$ANTHROPIC_API_KEY" ] && echo "key set" || echo "key missing"
   .venv/bin/python reset_demo.py
   .venv/bin/python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```
3. **Window 2:** `cd frontend && npm run dev`. Then open http://127.0.0.1:5173. To see the landing page again, clear this site's storage (or use a private window).
4. **Files ready:** keep a Finder window open on `data/scenarios/`, showing `NJ-05_v2_named_exception.md`, `NJ-07_v2_languages_aligned.md` and `NJ-09_signed_contract.md`.
5. **Your name** is set in the app ("Recording as …").
6. **Close every other tab.** Turn off notifications.

## What the live rehearsal showed (20 Oct, 17:14)

It matched the design: the pricing note closed the approval gap only, and the live recheck of the revised contract closed the languages gap. One thing to expect: the model's re-read of the revised contract also reports **a third gap on the phone commitment**, "Missing from contract" for "phone calls" (the commitment now has three: not offered, differs from the SOW, missing from the contract). On that row the drawer shows the contract wording first, then "No matching wording found for “phone calls”". Say it as a feature: a new document can surface a new gap.

## The facts behind it (run 1, 20 Oct)

The model read the eight starting documents once, against Aivuna's ten-capability catalogue: **5 findings shown, 0 refused, $0.0755** (7,868 tokens in, 5,972 out). That is the designed set plus one legitimate extra: the phone promise also conflicts with the SOW's "chat and email". It is a demonstration, not an accuracy measurement. The detection prompt still names the original vendor (Elva); the run gave no sign it mattered. Full log: `data/noma_journeys/BRIEF.md`.

## The script

| Time | Do | Say |
| --- | --- | --- |
| 0:00 | Landing page: point at the two cards, then click **Open this sample deal** on **AI support assistant** | "Same engine, two vendors. This one is an AI support platform selling to a travel company. Dealshape compares what the customer was promised with the contract and this vendor's catalogue." |
| 0:20 | Noma Journeys deal page. Pause. | "Three commitments need attention. The stage, Contracting, comes from the documents on the right. The brief at the top is the owner's words, not the model's." |
| 0:40 | Click **AI answers customers' phone calls at launch** | "The RFP response promised that the assistant answers phone calls. The SOW says chat and email, and the catalogue lists chat and email only. Two gaps on one promise, and one of them can't be fixed with an approval: voice isn't offered." *Point at the origin line:* "Where it was first found, worked out from the exact sentence in the documents." |
| 1:00 | Click **Catalogue: CAP-003 · SG** | "This opens this deal's own catalogue: Aivuna's. It says plainly that voice isn't offered. Elva's deals open Elva's catalogue." Close it. |
| 1:15 | Back to the row list → **Dedicated launch specialist…** | "A launch specialist for 30 days at no charge. Two gaps: the catalogue says it needs a named approval, and nobody recorded one. And it's not in the contract or the SOW at all." |
| 1:30 | Launch specialist row → **Add updated document** → choose the file `NJ-05_v2_named_exception.md` → check the form reads **This is: A new version of: Pricing and services note (currently v1)** (it is pre-selected; if it says "A new document", choose the version) → **Add and check** | "The head of Customer Success approved a named exception, and I add the new pricing note." *Point at What changed:* "**Approval found, and the contract gap is still open.** An approval doesn't put a promise into the contract. This is the moment to notice: a partial fix stays visibly partial." (No model call is needed for this step; the footer says so.) |
| 2:05 | **Support in 12 languages at launch** → **Add updated document** → choose the file `NJ-07_v2_languages_aligned.md` → check the form reads **This is: A new version of: Draft contract (currently v1)** (not the Draft SOW) → **Add and check** | "Sales promised 12 languages, the draft contract said four. Aivuna's catalogue supports 12, so the fix is the contract. The contract changed, so the model reads it. That takes a few seconds. The reading is cached on this machine from the 20 Oct rehearsal, so it runs even with no API key; on another machine it needs the key." *Point:* "Closed by documents, in solid green, with the document that closed it. The line says the contract changed and the SOW was checked with it, unchanged." *Then glance at the phone row* (it now shows a third gap): "**A new document can also surface a new gap — here, phone calls appear nowhere in the revised contract.**" |
| 2:40 | **AI answers customers' phone calls** → **Record a note** → **Mark as addressed by note** → "Noma agreed on 19 Oct to launch on chat and email; voice is not offered." → **Save note** | "Here the answer is a conversation, not a document. Noma accepted a launch without voice. A note is a person's word, so it's outlined grey, not green. It settles all three gaps on the promise (not offered, differs from the SOW, and the new missing-wording gap), they all stay visible, and it reopens if the documents change." |
| 3:05 | Sidebar **+ Add** → choose the file `NJ-09_signed_contract.md` → **This is: A new document**, **Type: Signed contract** (leave Dated as today) → **Add and check** | "The signed contract arrives, 12 languages, no launch specialist. The stage moves to Signed because of the document." *Point at the languages row:* "Confirmed in the signed contract: Dealshape looked for the exact sentence that closed the gap, and it is in the signed agreement. A fix in a draft only counts if it survives signing." |
| 3:20 | Add both handover notes (suggestions below), then **Lock handover record** | "Sales and Delivery each write their note. The checklist shows what's missing, and locking freezes the record." |
| 3:40 | Locked record | "One commitment still needs attention: the specialist, because the contract never got it. One is addressed by note, one closed by documents. The record never says 'no open gaps' while something rests on a note, and it can't be edited." |
| 3:55 | Stop | "Demonstrated on fictional deals. Two vendors' catalogues, one pipeline; the detection prompt still names the original vendor, and I say so in the README." |

**Handover notes to paste.** Sales (Liam Hart, deal owner): "Signed with the launch specialist still missing from the contract. The exception covers 30 days at no extra charge. Noma launches on chat and email; voice isn't offered. Raise the specialist at kickoff." Delivery (Sam Lee): "Accepted. We start on chat and email as contracted; the specialist's contract commitment goes on the kickoff agenda."

## If something goes wrong

| It happens | Say, and do |
| --- | --- |
| "Method Not Allowed", or the page won't load | "Old server, give me ten seconds." Stop it with `lsof -ti :8000 \| xargs kill`, then restart window 1 |
| "This review needs the model…" on the contract step | "That needs the API key on the server. Nothing was added, and that's the safety rule working." Skip to the note step |
| The form says "This looks like a new version of …" | You chose "A new document" for a revised file. It would be dated today and sit beside the original. Click the primary button **Use "A new version of …"**. The quiet "Add as a new document anyway" is the only way past it |
| "This review needs the model…" and the message names a document "added earlier as a new document" | An earlier step was filed as a new document, not a new version. Reset the demo and add it as **A new version of: …** |
| Wrong file picked | The app warns you ("This looks like a…"). Cancel, then pick the right one |
| The landing page doesn't show | It shows once per browser. Clear this site's storage, or use a private window |

## Likely questions (short answers)

- **"Is this tuned to one vendor?"** "Two vendors' catalogues run through one pipeline. The detection prompt still names the original vendor, Elva. I didn't change it, because changing it would invalidate every saved reading. The Aivuna run read the right promises anyway, once. That's a demonstration, not a proof for any vendor."
- **"Why is one finding not offered, with no exception possible?"** "Because the catalogue lists chat and email only. A channel that isn't there can't be approved into existence. Only changing the promise, or an agreement to launch without it, resolves it."
- **"Where does the AI come in?"** "The model reads the paperwork and proposes each gap with exact quotes. Code checks every quote and citation, and only code can close a gap."
- **"Why does the specialist still need attention after the approval?"** "Because the approval and the contract are separate gaps. Delivery inherits a promise the contract doesn't contain."
- **"How do you know it works?"** "Two sealed deals, each run once per configuration. Version 2 found 8 of 8 labelled issues with no false flags on Atlas Remit. Small sample, and the README says so. Noma and Alder are demos, not evaluations."
- **"What doesn't it do?"** "It doesn't read scanned PDFs. It checks wording, not legal meaning. And the verifier matches words, so a loosely worded finding can be refused: Alder shows one."
