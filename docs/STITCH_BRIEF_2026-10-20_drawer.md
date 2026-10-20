# Dealshape: Stitch brief v3, the drawer layout (20 Oct 2026)

**What's new since v2 (19 Oct)**
- **A commitment opens in a right-hand drawer** instead of expanding in place. The list stays visible, and documents open in the same drawer.
- **The visual references are named:** the Revolut web app, Cal.com, the Attio / Command property panel, and Mercury for mood.
- **The mismatch line is a sentence:** key terms are dark and the connecting words are muted, in the style of Stellate's alerts.

**How to use this file**
1. Start a new Stitch project.
2. Paste **Prompt 0**, then one screen prompt at a time (Prompts 1 to 4).
3. Attach the reference screenshots to Prompt 0: the Revolut Highlight home and drawer, Cal.com's list, the Command/Attio property panel, and Mercury. Don't attach the landing or sign-up pages.
4. **One round per screen.** Export the HTML and paste it to Claude, starting with the deal page.
5. **The structure is decided. Stitch's job is the visual style.**

All companies, people and deals are fictional.

---

## Prompt 0: context and style (paste first)

> Design a calm, premium, modern desktop web app (1440 px) called **Dealshape**, tagline **"See the deal as it was actually promised."** It is used at the handover from Sales to Delivery in B2B software deals. It reads the deal's paper trail (sales calls, RFP response, proposal, customer emails, internal pricing note, draft SOW, draft contract, signed contract) and shows where what the customer was told, what the contract says and what the company can sell don't line up.
>
> **It is a visibility tool, not a CRM or workflow tool.** No tasks, owners, assignees, activity feeds, deadlines, priorities, risk scores or KPI tiles.
>
> **Visual references (attached):**
> - **Revolut web app:** light grey page; white cards with a large radius and very soft shadow; soft tinted pill buttons; and a **right-hand detail drawer** of label-and-value rows with a note block.
> - **Cal.com:** a single list card with hairline dividers between rows and small grey chips.
> - **Attio / Command property panel:** a list of facts, each with a small line icon, a quiet label and a value.
> - **Mercury:** the mood. Quiet, fine lines, restrained colour, fintech calm.
>
> **Style rules:**
> - Inter. Few sizes, with clear weight contrast between title, body and muted text.
> - One accent colour. You may propose it; keep it calm (deep teal, ink-blue or violet).
> - Generous spacing and few borders. No gradients, no illustrations, no mascots.
> - Small line icons (Lucide style).
> - Status is shown with a dot plus text, never colour alone:
>   - **Needs attention:** amber.
>   - **Closed by documents:** solid green (proof).
>   - **Addressed by note:** outlined grey (a person's word, not proof).
>
>   These three must never look alike.
>
> **Rules the design must keep:**
> 1. "Mark as seen" is a quiet text link and never looks like it closes or approves anything.
> 2. AI-written sentences carry a small label: "AI-written summary · quotes checked against the documents".
> 3. The deal's stage comes from the documents. There is no "set stage" or "record signature" control.
> 4. The locked handover record has no actions except Print / save as PDF.

---

## Prompt 1: deal page, with the drawer closed and then open

> Screen: **Deal page** for "Alder Bank". Light grey page background. Main column about 65%, right sidebar about 35%.
>
> **Top bar (flush, minimal):** "← All deals" on the left. On the right: "Recording as Lina Mockeliunaite · change" (small, muted) and a quiet "Product catalogue" pill.
>
> **Main column:**
>
> 1. **Header card:**
>    - "Alder Bank" (large);
>    - a property list with icons, in two columns:
>      - Stage: **Contracting** (pill)
>      - Target go-live: 1 Feb 2027
>      - Last checked: 19 Oct 2026
>      - Documents: 8
>    - a quiet line: "Gaps first made at Proposal / RFP".
>
> 2. **What we're delivering** (card):
>    - summary: "Elva provides scam protection for Alder Bank's outbound instant payments, holding each payment until Elva returns a decision, from a 1 February 2027 launch. Go-live depends on Alder providing sandbox access to its payments platform by 1 December.";
>    - deliverables as a compact list with small check icons:
>      - Dedicated environment on AWS, Sydney region
>      - Real-time scoring for instant payments of AUD 1,000 or more; hourly batches below that
>      - Up to 200,000 payments a day at launch
>      - Case management workspace with full case audit history
>      - Weekly project status meeting during implementation
>    - muted line: "Confirmed by Tom Fraser (Account Executive) from draft SOW, 9 Oct".
>
> 3. **Commitments needing attention:** heading with one count on the right, "3 need attention". One card, rows divided by hairlines (Cal.com style). Each row:
>    - **title** (medium weight);
>    - a **sentence-style mismatch line**: key terms in dark ink, connecting words muted;
>    - a muted origin line;
>    - a status chip (dot plus text) on the right, and a chevron.
>
>    The rows:
>    - **Coaching-scam detection live at launch**
>      - Told *live at the 1 Feb 2027 launch* · contract has *no matching wording* · *no approval found*
>      - First promised in the RFP response, 29 Sep · Needs attention
>    - **Hosting on Microsoft Azure**
>      - Told *Microsoft Azure, Australia East* · contract says *AWS, Sydney region* · *not offered*
>      - First promised in the RFP response, 29 Sep · Needs attention
>    - **750,000 payments a day by the end of year one**
>      - Told *750,000 a day by end of year one* · contract has *no matching wording* · *no approval found*
>      - First promised in the proposal, 2 Oct · Needs attention
>
> 4. **Handover** (card):
>    - two side-by-side note blocks, "Sales · Deal owner's handoff note" and "Delivery · Delivery acceptance note", each showing "Not written yet" with an "Add note" link;
>    - a "Complete handover" button, disabled, with the helper text "To complete: upload the signed contract · add the Sales note · add the Delivery note".
>
> 5. **Footer:** "Lists commitments where the customer's expectation, the contract and what we can sell don't line up. All companies, people and deals are fictional."
>
> **Right sidebar: "Deal journey · 8 documents"**, with a small "+ Add" pill. A vertical timeline of seven stages with fine connecting lines, each stage's documents listed underneath as links with short dates:
> - **Discovery:** Call transcript, 15 Sep
> - **Evaluation:** Call transcript, 22 Sep
> - **Proposal / RFP:** RFP response, 29 Sep · Proposal, 2 Oct · Pricing and services note, 6 Oct. A small amber marker: "3 gaps started here".
> - **Shortlisted:** "No documents" (faint)
> - **Contracting (current):** Draft SOW, 9 Oct · Draft contract, 12 Oct · Customer email, 14 Oct. A tinted band, a larger accent dot, the label "Current stage", and a muted note: "Last point to fix gaps cheaply".
> - **Signed** and **Handover:** "Not yet" (hollow dots, greyed)
>
> A quiet "How closing works" link sits at the bottom.
>
> **Now show the same page with the drawer open** for "Coaching-scam detection live at launch". The page behind dims slightly. The drawer slides in from the right, about 520 px wide, Revolut style:
> - **Top:** the title, the status chip, and a close ×.
> - **Customer was told:** the quote "Through its connector to BioCatch, Elva will use behavioural signals… to flag customers who appear to be coached by a scammer, live from the 1 February 2027 launch." Source: RFP response, 29 Sep (a link that opens the document in this drawer).
> - **Contract says:** "No matching wording found in the draft contract or SOW." Below it, small muted text: "Searched for: coaching, BioCatch, behavioural".
> - **What we found:** two label-and-value rows:
>   - "No approval found": "Needs a named approval; none in the pricing and services note."
>   - "Not in the contract": "A firm promise appears nowhere in the draft contract or SOW."
>
>   A small "Catalogue: CAP-027 · AU" link. A short summary paragraph with the label "AI-written summary · quotes checked against the documents".
> - **Notes:** an empty state, "No notes yet".
> - **Bottom of the drawer, sticky:**
>   - two pill buttons, **Add updated document** (accent tint, primary) and **Record a note** (neutral tint);
>   - on the left, the muted text "Seen by: nobody yet · Mark as seen".
>
> **The 10-second test:** within ten seconds of the page loading, a first-time viewer can say what we're delivering, which commitments need attention and why, and where the deal stands.

---

## Prompt 2: the drawer in its other states

> Same app and style. Show the drawer in four states, side by side.
>
> **A. A document, opened from the sidebar or a source link.**
> - Header: "RFP response · 29 Sep · Proposal / RFP stage", with a "← Back to commitment" link when it was opened from a quote.
> - The document's text in a readable column, with the quoted sentence highlighted in soft amber.
> - A small "Drive link" icon. No editing.
>
> **B. Add updated document, inside the drawer.**
> - A one-line hint: "A contract gap closes when the SOW or contract includes the promise as made."
> - "This is: [A new version of: Draft SOW ▾]", then a file drop area.
> - Buttons "Add and check" and "Cancel".
> - Muted line: "The check runs again on all the deal's documents. A gap closes only if the new paperwork shows it no longer holds."
>
> **C. Record a note, inside the drawer.** Two selectable cards:
> 1. **Keep it open, add context** (selected by default): "Stays in 'Needs attention' with your note."
> 2. **Mark as addressed by note:** "The documents still differ. It moves to 'Addressed by note', stays in the handover record, and reopens if the documents change."
>
> Then a text box ("What was agreed, and who will act on it"), a "Your name" field (only if none is stored), and the buttons "Save note" and "Cancel".
>
> **D. What changed, at the top of the main column after a document is added** (a calm card, not a toast):
> - title: "After adding Draft SOW, new version";
> - muted line: "No model call was needed: code checked every finding again.";
> - **Closed (1):** "Coaching-scam detection live at launch: Not in the contract". Reason: "The new SOW version now includes coaching detection (section 5)." Shown with the solid green chip.
> - **Still needs attention on the same commitment:** "No approval found".
> - footer: "Nothing else changed. 3 commitments still need attention." and a "Done" link.
>
> Also show two example rows in the list: one **Addressed by note** (outlined grey chip; muted line "Recorded by Priya Nair · 19 Oct") and one **Closed by documents** (solid green chip; "Closed by Draft SOW v2, 16 Oct").

---

## Prompt 3: the locked handover record

> Same app and style. Screen: **Handover record (locked)** for Alder Bank. It should read like a beautifully set one-page brief that Delivery reads before kickoff. The only actions are "← All deals" and "Print or save as PDF".
>
> 1. **A quiet grey banner** with a lock icon: "Handover complete · locked on 20 Oct 2026 by Sam Lee (Delivery)".
> 2. **Heading:** "Alder Bank: what Delivery inherits". A property row: Stage **Signed** · Go-live 1 Feb 2027.
> 3. **What we're delivering:** the same summary and deliverables as on the deal page.
> 4. **An honest verdict line:** "Handed over with 2 needing attention, 1 addressed by note, 0 closed by documents." It never says "no open gaps" while anything is addressed by note.
> 5. **Commitments at handover:** the same rows and sentence-style mismatch lines, read-only. Clicking a row opens the same drawer, read-only: no buttons, and no "Mark as seen".
>
>    Show one drawer open with a note block: "Recorded by Priya Nair · 19 Oct: 'Customer agreed AWS Sydney on the 14 Oct call.' · Addressed by note · not in the documents".
> 6. **Handover notes:** both notes as quotes, each with author and date.
> 7. **Record details**, folded at the bottom: the documents at handover, and a record fingerprint (a long hash in a mono font, with Copy).

---

## Prompt 4: deals list (home)

> Same app and style. Screen: **Deals in handover**. A supporting screen, so keep it very simple.
>
> - **Header:** the "Dealshape" wordmark and tagline; title "Deals in handover"; pills "Product catalogue" and "+ New deal".
> - **Segmented filter** (Revolut style): All in handover · Need attention · Handover complete. Then a search field and a sort control.
> - **One list card with hairline rows** (not a heavy table). Each row shows the deal name, a stage pill, need attention (an amber count, or "Nothing needs attention · 1 addressed by note"), the deal owner (initials and name) and last updated (relative). A locked deal shows "Handover complete" with a lock and "Open record".
>   - Alder Bank · Contracting · 3 need attention · Tom Fraser · 2 hours ago
>   - Harbour Bank · Handover complete · 1 needs attention at handover · Grace Tan · 3 days ago
>   - Coral Pay · Contracting · 2 need attention · Marcus Chen · 9 days ago
>   - Atlas Remit · Proposal / RFP · 4 need attention · Not set · 9 days ago
> - **No summary tiles or charts.**

---

## Checking Stitch's output (for Lina and Claude)

**Reject a design that adds** assignees, due dates, priorities, risk scores, activity feeds, avatars from photos, notifications, comments, AI-suggested impact, a "set stage" control or a "record signature" control.

**Mapping notes for Claude Code:**
- **The sentence-style mismatch line** is built only from verified finding labels and the stored short "told" and "contract" terms. It is never built from AI text. For "no matching wording", the line uses that phrase, not a paraphrase.
- **The drawer replaces in-place expansion** on the live page and on the locked record. The locked record's drawer has no actions.
- **`?detailed` stays** as the old view.
- **Tests:** update the front-end tests for the drawer. Python stays as it is.
- **Decision log:** the drawer reverses the in-place layout of 19 Oct, so it needs a DECISIONS.md entry.
