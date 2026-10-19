# Dealshape: brief for Google Stitch (19 Oct 2026, v2)

**How to use this file**
1. Start a new Stitch project.
2. Paste **Prompt 0** to set the context.
3. Then use one screen prompt at a time (Prompts 1–4). Attach fresh screenshots of that screen from the app: ⌘ + Shift + 4 and drag.
4. **One round per screen.** Pick the version you like, export the HTML, and paste it to Claude, who maps it onto the real data.
5. **The structure below is decided. Stitch's job is the visual style:** type, colour, spacing, composition, icons and states. It is not the information order.

All companies, people and deals are fictional.

---

## Prompt 0: the context (paste first)

> Design a modern, calm, premium desktop web app (1440 px) called **Dealshape**, tagline **"See the deal as it was actually promised."** It is used at the handover from Sales to Delivery in B2B software deals.
>
> **What it does:** it reads a deal's paper trail (sales calls, RFP response, proposal, customer emails, the internal pricing note, draft SOW, draft contract, signed contract) and shows the shape of the deal:
> - what we're delivering;
> - which commitments need attention, because what the customer was told, what the contract says and what the company can sell don't line up;
> - what people have agreed about them;
> - where the deal stands.
>
> **What it isn't:** a workflow tool. There are no tasks, assignees, approvals, deadlines or risk scores. The readers are Delivery, Customer Success and Support leads, plus the Sales deal owner.
>
> **Style:**
> - Confident, editorial and quiet, like Linear, Stripe or Notion, not a dashboard.
> - Generous white space, strong type hierarchy, one accent colour.
> - Status colours used sparingly:
>   - amber = needs attention;
>   - solid green = closed by documents (proof);
>   - outlined or neutral = addressed by a person's note (their word, not proof).
> - Status is always shown with text, not colour alone.
> - Light theme first.
> - You may propose a new accent colour and typeface, but keep it professional and readable.
>
> **Rules the design must keep:**
> 1. "Closed by documents" must look clearly different from "Addressed by note".
> 2. "Mark as seen" is a quiet text link and never looks like it closes or approves anything.
> 3. AI-written sentences carry a small label: "AI-written summary · the quotes behind it are checked against the documents".
> 4. The deal's stage comes from the documents. Nobody sets it by hand, so there is no "set stage" or "record signature" control.
> 5. The locked handover record has no actions except Print / save as PDF.

---

## Prompt 1: the deal page (the most important screen)

> Screen: **Deal page, live**, for the deal "Alder Bank". Two columns: a main column (about 65%) and a right sidebar (about 35%).
>
> **Top bar:** "← All deals" on the left. On the right: "Recording as Lina Mockeliunaite · change" (small, muted) and a "Product catalogue" button.
>
> **Main column, in this order:**
>
> 1. **Header:**
>    - "Alder Bank" (large);
>    - a clear stage pill: "Stage: Contracting";
>    - a meta line: "Target go-live: 1 Feb 2027 · Checked 19 Oct 2026 against 8 documents";
>    - a quiet line: "Gaps first made at Proposal / RFP".
>
> 2. **What we're delivering** (a calm card, shown open):
>    - summary: "Elva provides scam protection for Alder Bank's outbound instant payments, holding each payment until Elva returns a decision, from a 1 February 2027 launch. Go-live depends on Alder providing sandbox access to its payments platform by 1 December.";
>    - deliverables as a compact list:
>      - Dedicated environment on AWS, Sydney region
>      - Real-time scoring for instant payments of AUD 1,000 or more; hourly batches below that
>      - Up to 200,000 payments a day at launch
>      - Case management workspace with full case audit history
>      - Weekly project status meeting during implementation;
>    - a small line: "Confirmed by Tom Fraser (Account Executive) from draft SOW, 9 Oct".
>
> 3. **Commitments needing attention.** Heading, with one count on the right: "3 need attention". Each commitment is a row that tells its story while collapsed:
>    - **title** (strong), e.g. "Coaching-scam detection live at launch";
>    - **mismatch line** (amber text), e.g. "No approval found · Not in the contract";
>    - **origin line** (muted), e.g. "First promised in the RFP response, 29 Sep";
>    - **status chip** on the right: "Needs attention" (amber).
>
>    The other two rows:
>    - "Hosting on Microsoft Azure" · "Not offered · Contract differs: Amazon Web Services in the Sydney region" · "First promised in the RFP response, 29 Sep"
>    - "750,000 payments a day by the end of year one" · "No approval found · Not in the contract" · "First promised in the proposal, 2 Oct"
>
>    **Show the first row expanded:**
>    - three columns:
>      - **Customer was told:** a quote, "Through its connector to BioCatch, Elva will use behavioural signals… to flag customers who appear to be coached by a scammer, live from the 1 February 2027 launch." Source: RFP response, 29 Sep.
>      - **Contract says:** "No matching wording found in the draft contract or SOW."
>      - **What we found:** two short findings, each with a one-line reason, plus a small "Catalogue: CAP-027 · AU" link and the AI-written label.
>    - footer: "Seen by: nobody yet" with a quiet "Mark as seen" link, then two buttons: **Add updated document** (primary) and **Record a note** (secondary).
>
>    Also show the other two status styles as example rows below: one "Addressed by note" (outlined/neutral) and one "Closed by documents" (solid green), each with its one-line reason.
>
> 4. **Handover:**
>    - two side-by-side note cards: "Sales · Deal owner's handoff note" and "Delivery · Delivery acceptance note", each showing "Not written yet" and an "Add note" link;
>    - a primary "Complete handover" button, disabled, with the helper text "To complete: upload the signed contract · add the Sales note · add the Delivery note".
>
> 5. **Footer:** "Lists commitments where the customer's expectation, the contract and what we can sell don't line up. All companies, people and deals are fictional."
>
> **Right sidebar: "Deal journey".** A vertical timeline of the seven stages, each with its documents underneath as clickable links with short dates:
> - **Discovery:** Call transcript, 15 Sep
> - **Evaluation:** Call transcript, 22 Sep
> - **Proposal / RFP:** RFP response, 29 Sep · Proposal, 2 Oct · Pricing and services note, 6 Oct. Amber marker: "3 gaps started here".
> - **Shortlisted:** "No documents" (faint)
> - **Contracting (current stage):** Draft SOW, 9 Oct · Draft contract, 12 Oct · Customer email, 14 Oct. Note: "Last point to fix gaps cheaply". It is clearly highlighted: a tinted band, a larger accent dot and the label "Current stage". Contract documents are subtly marked as contract.
> - **Signed:** "Not yet" (hollow dot, greyed)
> - **Handover:** "Not yet" (hollow dot, greyed)
>
> The sidebar header reads "Deal journey · 8 documents", with a small "+ Add" button. Below it is a quiet "How closing works" link.
>
> **The 10-second test:** within ten seconds, a first-time viewer should be able to say what we're delivering, which commitments need attention and why, and where the deal stands.

---

## Prompt 2: "What changed" after adding a document, and the two dialogs

> Same app and style. Show three states of the Alder Bank deal page.
>
> **A. The "What changed" panel**, which appears at the top of the main column after a document is added:
> - title: "After adding Draft SOW, new version";
> - a small line: "No model call was needed: code checked every finding again.";
> - **Closed (1):** "Coaching-scam detection live at launch: Not in the contract". Reason: "The new SOW version now includes coaching detection (section 5)."
> - **Still needs attention on the same commitment:** "No approval found".
> - footer: "Nothing else changed. 3 commitments still need attention." and a "Done" button.
>
> **B. The "Add updated document" dialog:**
> - a one-line hint: "A contract gap closes when the SOW or contract includes the promise as made.";
> - "This is: [A new version of: Draft SOW ▾]";
> - a file picker;
> - buttons "Add and check" and "Cancel";
> - a quiet line: "The check runs again on all the deal's documents. A gap closes only if the new paperwork shows it no longer holds."
>
> **C. The "Record a note" dialog**, with two choices as large selectable cards:
> 1. **Keep it open, add context** (selected by default). "The commitment stays in 'Needs attention' with your note."
> 2. **Mark as addressed by note.** "The documents still differ. It moves to 'Addressed by note', stays in the handover record, and reopens if the documents change."
>
> Then a text box ("What was agreed, and who will act on it"), a "Your name" field shown only if no name is stored yet, and the buttons "Save note" and "Cancel".

---

## Prompt 3: the locked handover record

> Same app and style. Screen: **Handover record (locked)** for Alder Bank. It is read-only: something Delivery would actually read before kickoff, like a well-designed one-page brief. The only actions are "← All deals" and "Print or save as PDF".
>
> **In this order:**
> 1. **A quiet grey banner:** "Handover complete · locked on 20 Oct 2026 by Sam Lee (Delivery)".
> 2. **Heading:** "Alder Bank: what Delivery inherits", with the stage "Signed" and "Go-live 1 Feb 2027".
> 3. **What we're delivering:** the same summary and deliverables as on the deal page.
> 4. **An honest verdict line:** "Handed over with 2 needing attention, 1 addressed by note, 0 closed by documents." It must never say "no open gaps" while anything is addressed by note.
> 5. **Commitments at handover:** the same rows as the live page, read-only, each with its status at handover. One is expanded to show the evidence and a note block: "Recorded by Priya Nair · 19 Oct: 'Customer agreed AWS Sydney on the 14 Oct call.' · Addressed by note · not in the documents".
> 6. **Handover notes:** both notes, shown as quotes with author and date.
> 7. **Record details**, folded at the bottom: the documents at handover, plus a record fingerprint (a long hash, with Copy).

---

## Prompt 4: deals list (home)

> Same app and style. Screen: **Deals in handover** (home). Keep it simple, as this screen plays a supporting role.
>
> - **Header:** "Dealshape" wordmark and tagline, the page title "Deals in handover", and the buttons "Product catalogue" and "+ New deal".
> - **Filter tabs:** All in handover · Need attention · Handover complete. Then a search box and a sort control.
> - **Table** with the columns: Deal · Stage (pill) · Need attention (amber count, or "Nothing needs attention · 1 addressed by note") · Deal owner (avatar and name) · Last updated (relative). A locked deal shows "Handover complete" with a lock icon and "Open record".
> - **Rows:**
>   - Alder Bank · Contracting · 3 need attention · Tom Fraser · 2 hours ago
>   - Harbour Bank · Handover complete · 1 needs attention at handover · Grace Tan · 3 days ago
>   - Coral Pay · Contracting · 2 need attention · Marcus Chen · 9 days ago
>   - Atlas Remit · Proposal / RFP · 4 need attention · Not set · 9 days ago
> - **No summary tiles or charts.**

---

## What the app can and can't show (for checking Stitch's output)

| Can show | Can't show (don't accept designs that need it) |
| --- | --- |
| Deal name, stage (from the documents), go-live, last checked, document count | User accounts, avatars from photos, login |
| Brief: summary, deliverables, who confirmed it and from which document | Notifications, comments, @mentions |
| Per commitment: title, mismatch line, first-promised source and date, quotes, contract wording or "no matching wording", findings with reasons, catalogue link, seen-by names and dates, notes (who, when, what) | Assignees, due dates, priorities, risk scores, AI-suggested impact |
| "What changed" after a document: closed, still open, new, whether the model was called | Editing documents in the app; contract redlining |
| Documents grouped by stage, with dates, versions and Drive links | Connectors to CRM, Drive or DocuSign (only a pasted link) |
| Handover notes, locked record, fingerprint | Setting the stage or signature by hand |

**After Stitch:** export the HTML for each screen and paste it to Claude, one screen at a time, starting with the deal page.
