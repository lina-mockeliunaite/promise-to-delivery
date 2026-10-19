# Promise to Delivery: the current UI and workflow (for Google Stitch, 19 Oct 2026)

**How to use this file**
1. Paste the **"Paste into Stitch first"** block below as your opening prompt.
2. Attach screenshots of the live app (cmd + shift + 4, then drag) for the screen you're working on: home, deal page, one promise opened, the Resolve pop-up, and the frozen record.
3. Ask for one screen at a time, then add your changes.
4. Export each screen as HTML and paste the code back to Claude. Claude maps it onto the real data and keeps the rules in section 5.

Everything here is fictional. The data comes from a fictional vendor (Elva) and fictional deals (Alder Bank, Harbour Bank, Coral Pay, Atlas Remit).

---

## Paste into Stitch first

> I'm redesigning an existing desktop web app called **Promise to Delivery**. I want it **simpler**: fewer elements on screen, one clear thing to look at first, and a short, obvious workflow. Keep the calm, light, professional style (Geist font, teal accent #0f766e, amber for open, green for closed, warm light-grey surfaces, 1440 px wide). Screenshots of the current screens are attached.
>
> **What it does:** it reads a B2B software deal's paperwork (sales calls, RFP answer, proposal, customer emails, draft SOW, draft contract, internal pricing note) and shows the Delivery team every **promise the customer was told that the contract doesn't back**: missing from the contract, different in the contract, or never approved internally. It is a **visibility tool, not a workflow tool**: no tasks, no approvals, no assignments.
>
> **Who reads it:** Delivery, Customer Success and Support leads inheriting a deal from Sales. Also used by the Sales deal owner, who adds documents and notes.
>
> **The flow today:**
> 1. Deal list.
> 2. Open a deal.
> 3. See the promises with gaps.
> 4. Open one promise to compare what the customer was told with what the contract says.
> 5. Fix it by adding a document, or record a note.
> 6. Sales and Delivery each write a handover note.
> 7. Record the signing date.
> 8. Complete the handover, which freezes a read-only record.
>
> **Rules any design must keep:**
> - A gap closed **by a document** (proof) must look different from a gap resolved **by a person's note** (their word).
> - "Mark as seen" must never look like it closes anything.
> - AI-written text is labelled as AI-written.
> - The frozen record has no buttons except Print.
>
> My changes: [write yours here]

---

## 1. The product in three lines

- **Problem:** Delivery inherits the contract, but the customer remembers the proposal. Gaps between the two surface at kickoff, as escalations.
- **What it shows:** each promise in the customer's words with where it was made, what the contract says, and what's wrong (the gap type).
- **The distinctive behaviour:** add a corrected document and the check runs again. A gap closes only when the new paperwork shows it no longer holds, and the app says why.

**Gap labels on screen**
- **No approval recorded:** needs a named approval (or exceeds a limit), and none is recorded.
- **Not offered:** not in the product catalogue at all. Only changing the promise fixes it.
- **Missing from contract:** a firm promise appears nowhere in the draft contract or SOW.
- **Contract says something different:** same subject, different terms.

## 2. The current workflow (what a user actually does today)

**A. Home: "Deals in handover"**
1. See the list of deals (Contracting stage or later).
2. Click a deal to open it.
3. Optional:
   - **Product catalogue** opens a pop-up of what Elva can sell. You can also add a capability there.
   - **New deal** creates an empty deal.

**B. Deal page (live)**
1. **Type your name** in the top-right "Your name" box. Every action is disabled until you do. It is stored in the browser; there is no login.
2. Read the header: deal name, "Live deal view", stage, target go-live, last checked. If the review is stale, a "Check again" link appears.
3. Read the summary: "N promises have open gaps", with counts for Open, Closed by documents and Resolved by note.
4. Read the 7-step stage bar: Discovery → Evaluation → Proposal / RFP → Shortlisted → Contracting → Signed → Handover. Each step shows its document count and date, and "N gaps started here".
5. Read "The deal in brief": a two-line summary, the deliverables, and "Confirmed by [name] from [document]".
6. **Promises:** one row per promise, collapsed by default (title plus a status chip). Click a row to open it:
   - three columns: **Customer was told** · **Contract says** · **What we found** (one paragraph per gap, a catalogue link, and the AI-written label);
   - if already closed: the gaps closed by documents, and any note;
   - footer: "Seen by: name (date)…", **Mark as seen**, **Resolve…**
7. **Resolve…** opens a pop-up with two tabs:
   - **Add a document.** The new version of the right document is pre-selected, with a hint for this gap type. Pick a file, then **Add and check**. The check runs again (a model call only if a contract or customer document changed), and a **"What changed"** panel appears at the top: what closed, why and by which document; what is still open; anything new.
   - **Record a note.** A choice between:
     - **Resolve it with this note** (the default): the promise moves to "Resolved by note", marked "not in the documents", and reopens if the documents change;
     - **Keep it open, note for the record.**
     Then type the reason and press **Resolve as [name]** or **Record note as [name]**.
8. **Right column:**
   - **Documents checked:** click a name to read the exact text used; a link icon saves a Drive link; **+ Add** adds a document or a new version.
   - **How a gap closes:** a permanent explainer of three steps plus caveats.
9. **Handover notes:**
   - two panels: **Deal owner's handoff note** (Sales) and **Delivery acceptance note**, each with Add / Update note;
   - **Contract signed? Record the date**: a date field and **Record signature**;
   - **Complete handover**, enabled only when your name, both notes and the signature date are all in. It asks "Complete as [name]? Yes, complete / Cancel".
10. Footer: "Lists only promises that the paperwork doesn't back. Checked against the draft contract, SOW and product catalogue."

**C. Frozen handover record** (replaces the deal page once complete)
- Top bar: **← All deals**, **Print or save as PDF**.
- Dark banner: "Frozen record · Handover complete · frozen on [date] by [name] · this record does not change".
- Heading: "[Deal] — what Delivery inherits", stage at handover, go-live.
- Verdict box: "Handed over with N promises still open. Delivery inherits these gaps." It also says how many documents were checked and the scope.
- **Promises at handover:** the same rows, with their status at handover. Expanding a row shows told / contract / found, what was closed earlier, and notes. Each row also shows "Seen by ✓ names" and a lock.
- **Handover notes:** both notes, read-only.
- **Right column:**
  - the deal in brief;
  - the documents at handover;
  - the record fingerprint (SHA-256, with Copy).

**D. Product catalogue pop-up**
- Contents: one block per capability, with a row per region showing status (Generally available / Beta / Roadmap), how it can be sold (Standard / Needs a named approval / Not sellable), limits and the planned availability date.
- Tools: search box and region chips.
- **+ Add a capability** opens a form with an amber warning: adding one marks every deal "Review out of date" until it is checked again.

## 3. Screen inventory: how much is on screen now

| Screen | Elements, top to bottom |
| --- | --- |
| Home | Eyebrow, title, deal count, subtitle · 2 header buttons · **3 summary tiles** with bars · 3–4 filter tabs with counts · search · sort · table (6 columns) · footer with paging |
| Deal page | Back link and name box · header with 2–4 chips and a meta line · summary box with 3 count pills · 7-step stage bar · brief card · promise list (each open row has 3 columns, a footer, and 2 buttons) · notes card (2 panels, signature form, complete button, hint) · footer · right column (documents, explainer) |
| Resolve pop-up | 2 tabs · document tab: hint, explainer, 2–4 fields, 2 buttons · note tab: 2 radio choices with long descriptions, a text box, 2 buttons |
| Frozen record | Top bar · banner · heading block · verdict box · promise list · notes · right column with 3 cards |

**Where it feels heavy (Claude's reading of the code; your rehearsal notes take priority):**
- **The open count appears four times on the deal page:** the summary sentence, the "Open" pill, the "N open" chip on the Promises heading, and each row's chip.
- **There are five blocks above the first promise:** header, summary, stage bar, brief, and possibly the "What changed" panel.
- **The name box blocks every action**, and the only sign of this is a tooltip.
- **The "Record a note" choice depends on reading two long sentences.**
- **"How a gap closes" is always open**, even after the first visit.
- **The home tiles repeat what the filter tabs already count.**

## 4. Visual system now

- Font: Geist, with JetBrains Mono for dates and numbers. Base size 13 px.
- Colours:
  - ink #18181b, body #3f3f46, muted #71717a;
  - lines #e5e5e9, page #fafafa, cards #ffffff;
  - brand teal #0f766e;
  - amber: background #fffbeb, line #fde68a, dot #d97706, text #92400e;
  - green: background #ecfdf5, line #a7f3d0, dot #059669, text #047857.
- Shapes: cards with 12 px radius and 1 px border; pill chips; dark (ink) primary buttons; light secondary buttons.
- Dark mode exists (via prefers-color-scheme).

## 5. What the app can show (don't design beyond this)

| Area | Data available |
| --- | --- |
| Deal list | name, stage, number of promises with open gaps, owner (may be empty), last updated, in handover yes/no, handover complete yes/no |
| Stage bar | per stage: label, done / current / to do, documents (name, date, link), gaps started here, note |
| Brief | summary, deliverables, confirmed by, from which document, go-live, needs re-confirmation plus note |
| Promise | name, what the customer was told (short) and where/when, what the contract says, a detail line, gaps (label, reason, open / closed by document / resolved by note, what closed it), catalogue entry, seen by (names, dates), notes (who, when, reason) |
| After a document | closed (promise, gap, why, which document), still open, newly found, whether the model was called |
| Documents | name, type, version, date, Drive link, readable text |
| Handover | both notes (text, who, when), signing date and who recorded it, completed by / at, fingerprint |
| Catalogue | capability, region and variant, status, how it can be sold, limits, planned date, integrations, who added it |

**Must stay true in any redesign**
1. **Closed by documents** (solid green, proof) looks different from **Resolved by note** (outlined, a person's word, "not in the documents").
2. **Mark as seen** never looks like it closes or approves anything.
3. AI-written sentences carry a label. The quotes behind them are checked by code.
4. The frozen record is read-only: no actions except Print / PDF.
5. Complete handover needs both notes and a signing date, and the screen says what's missing.
6. No new workflow: no assigning, approving, deadlines, risk scores or AI-suggested impact.

**Not available (don't design):** login or user accounts, connectors to a CRM or Drive (only a pasted link), notifications, comments, editing existing catalogue entries.
