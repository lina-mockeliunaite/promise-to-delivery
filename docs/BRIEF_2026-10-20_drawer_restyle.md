# Brief: drawer layout and v3 restyle (20 Oct 2026)

**For Claude Code.**
- Inspect first. Then list the files you'll change and the plan, and wait for Lina's OK before editing.
- No git commands.
- **Scope:** front end only. Detection, verification, closure rules, the freeze middleware, hash definitions, snapshot format and API are unchanged. If you believe an API field is needed, stop and say why.
- **Done means:**
  - all Python tests and all front-end tests pass, with new tests for new helpers;
  - every changed file is listed;
  - you report what you checked in the browser.

**References:** `docs/stitch/v3_*.html` and `docs/STITCH_BRIEF_2026-10-20_drawer.md`.

**Take the visual style and the layout from the references. Take every word and number from the stored data or this brief, never from the mock.** The mocks contain invented data. Section 6 lists what must not be built.

## Why

The deal page expands commitments in place, so the page grows and the viewer loses the list. A right-hand drawer keeps the deal's shape visible while one commitment is read, and lets documents open in context. This **reverses the in-place expansion of 19 Oct.** Lina will write the DECISIONS.md entry, so draft it for her at the end (chose, rejected, why).

## 1. Visual system (replace the deep-green tokens in `DealPage.css`; apply the same tokens to `Deals.css`)

| Token | Light | Note |
| --- | --- | --- |
| Canvas | `#f8fafc` | page background |
| Card | `#ffffff`; radius 14px; no border; shadow `0 1px 3px rgba(15,23,42,.05), 0 10px 25px -5px rgba(15,23,42,.04)` | soft cards, no outlines |
| Ink / body / muted | `#0f172a` / `#475569` / `#64748b` | **muted must stay ≥ 4.5:1 on white. Don't use `#94a3b8` for text** |
| Hairline | `#f1f5f9` | row dividers |
| Accent (brand) | `#4f46e5`, hover `#4338ca`; tint `#eef2ff` | buttons, links, current stage. Indigo also separates the brand from the green status colour, which deep green did not |
| Needs attention | bg `#fffbeb`, dot `#f59e0b`, **text `#b45309`** | Stitch's `#f59e0b` text fails contrast |
| Closed by documents | **solid** bg `#ecfdf5`, dot `#10b981`, text `#047857` | **green is used only for this** |
| Addressed by note | **outlined:** transparent bg, 1px `#cbd5e1` border, dot `#94a3b8`, text `#475569` | must not look like either of the above |

- **Type:** Inter (already bundled), base 14px, nothing under 11px. Headline 28 to 32px, semibold, tracking -0.02em.
- **Buttons:** pill-shaped. Primary is solid accent; secondary is a soft grey tint (`#f1f5f9`). Quiet actions are text links.
- **No** gradients, pulsing dots, animation beyond the drawer slide, or hidden scrollbars.
- **Dark mode:** keep it working. Derive the dark values in the same way as the current file.

## 2. Deal page (`DealPage.jsx`, `DealPage.css`)

**Layout:** a flush top bar, then a main column (about 65%) and a right sidebar (about 35%). The order of the main column is unchanged from 19 Oct:

1. **Header card:**
   - deal name;
   - the stage pill, from the documents;
   - a property list with small line icons: **Target go-live · Last checked · Documents (N)**;
   - muted line: "Gaps first made at [stage]";
   - "Check again" when the review is out of date.

   **Four properties at most, all existing data.**
2. **What we're delivering:**
   - the summary as plain text: **no quotation marks and no grey box**;
   - the deliverables with **neutral grey bullets**, not green checks;
   - "Confirmed by …".
3. **Commitments needing attention:**
   - one count in the heading;
   - one card, rows divided by hairlines;
   - each row: title, the **sentence-style mismatch line** (section 4), the origin line, a status chip, and a plain chevron;
   - clicking a row opens the drawer and gives the row a soft accent tint.
4. **Handover:**
   - the title is "Handover" (not "readiness", no "gate");
   - both note blocks;
   - the disabled button, with the missing items listed in words (the existing `missingForHandover`).
5. **Footer:** the existing scope line plus "All companies, people and deals are fictional."

**Right sidebar: "Deal journey · N documents".** A vertical timeline of the seven stages with a fine connecting line:
- **under each stage, its real documents** as links with short dates (the existing `groupByStage`, `docLabel`);
- an amber marker "N gaps started here" where it applies;
- the current stage in an accent tint with the label "Current stage";
- future stages hollow and grey;
- "+ Add" at the top and "How closing works" at the bottom.

Clicking a document opens it in the drawer (section 3A).

**Top bar:** "← All deals", the Dealshape wordmark and tagline, "Recording as [name] · change", and "Product catalogue". **No global navigation:** there are no Commitments or Discrepancies pages.

## 3. The drawer (new component; replaces in-place expansion)

- **Shape:** fixed to the right, 520 px wide (full width under 640 px), below the top bar.
- **Behaviour:**
  - slides in over 200 ms and dims the page behind;
  - closes with ×, Esc or a click on the backdrop;
  - focus moves into it and returns to the row on close;
  - `role="dialog"` and `aria-labelledby`.
- **Address bar:** opening a commitment puts it in the URL hash (`#c=<commitment key>`), so a reload or a shared link reopens it.

**Commitment view (the default).**
- **Header:** title, status chip, ×. Nothing else: no reference IDs, no source counts.
- **Customer was told:** the checked quotes (`toldQuotes`), each with "Source: [label], [date]". The source opens that document in the drawer (3A) with "← Back to commitment".
- **Contract says:** the contract wording (`contractSide`), or "No matching wording found in the draft contract or SOW." with "Searched for: …" when stored.
- **What we found:** one row per open finding, as a label (`findingDetail`) plus the code's reason (`cleanReason`). Also the catalogue link, the "Extracted as …" line when a plain title is shown, and the closed findings with what closed them.
- **AI-written summary:** the stored AI explanation directly under the label "AI-written summary · quotes checked against the documents". **If there is no AI text, show no label.**
- **Notes:** existing notes as "Recorded by [name] · [date]" with the note text. When empty: "No notes yet". No "+ New" button.
- **Sticky footer:**
  - a muted line, "Seen by: … · Mark as seen" (a text link, never a button);
  - below it, two pill buttons on one line, "Record a note" (secondary) and "Add updated document" (primary).

**3A. Document view.** The header shows the document label, date and stage, with "← Back to commitment" when it was opened from a quote. Below it, the stored readable text in a reading column, **with the quoted sentence highlighted in soft amber** when opened from a quote. Show a Drive link icon if a link is stored. Read-only.

**3B. Add updated document.** Move the existing Add-a-document form into the drawer as is:
- the hint;
- "This is:" with the existing document-type choices only;
- the file picker;
- "Add and check" / "Cancel";
- the existing explainer line.

**After the check, close the drawer** and show the existing **What changed** card at the top of the main column, restyled as in `v3_what_changed.html` (the card only):
- a solid green chip on closed items;
- an amber block for "still needs attention";
- "Done" as a link.

**3C. Record a note.** Move the existing note form into the drawer, matching `v3_drawer_states.html` C:
- two selectable cards, "Keep it open, add context" (the default) and "Mark as addressed by note", with the 19 Oct helper text;
- the text box and its label;
- the "Your name" field only if none is stored;
- "Save note" / "Cancel".

## 4. Sentence-style mismatch line (new helper in `dealpage.js`, with unit tests)

`mismatchParts(row)` returns segments `[{text, strong}]`, rendered with dark strong terms and muted connecting words:
- **"Told" segment:** "Told " plus the stored short `told`, strong, **only if it is 60 characters or fewer**. Otherwise omit the segment.
- **Contract segment:**
  - for "Contract says something different": " · contract says " plus the stored short contract term (the existing `shortTerm` rule);
  - for "Missing from contract": " · contract has " plus "no matching wording".
- **The remaining open findings:** " · " plus each finding's short form, lower-case (the existing `FINDING_SHORT`), without repeating the contract finding.
- **Built only from verified finding labels and stored terms. Never from AI text.**
- Keep `mismatchLine` (plain text), used by print and CSV.
- **Tests:** Alder's three commitments, a long `told` (the segment is omitted), and a commitment with only a contract finding.

## 5. Locked record (`FrozenRecord.jsx`) and home (`Deals.jsx`)

**Locked record.** The order is unchanged from 19 Oct:
1. quiet grey banner with a lock;
2. heading;
3. What we're delivering;
4. honest verdict line (`verdictLine`);
5. the same rows and mismatch lines;
6. both notes as quotes, each with author and date;
7. "Record details" folded at the bottom.

**Rows open the same drawer, read-only:** no buttons, no "Mark as seen", no note form. The **stage pill uses the neutral or accent style, not green.** Print / PDF expands every commitment inline (the drawer is not printed).

**Home:**
- the list card with hairline rows and the segmented filter from `v3_home.html`;
- **"Handover complete" is a neutral chip with a lock, not green;**
- no pulsing dots;
- column labels "Deal · Need attention · Deal owner · Last updated";
- no subtitle about audits and no sync line.

**Catalogue pop-up:** apply the new tokens so it matches (no structural change).

## 6. Do not build (it appears in the mocks but isn't real)

**Invented data and labels:**
- ACV or any money figure;
- "Readiness Score", "Unresolved Gaps … Detected", "Stage 5 of 7";
- "Enterprise Deal / SaaS", "Jurisdiction", the product subtitle;
- "Rev 3", "v2.4", "Draft SOW v0.9", "REF: C-019", "Commercial Scope";
- page or section numbers on quotes, invented filenames, file-size limits, MSA or side-letter options, .mp3 recordings.

**Claims the product can't back:**
- "Audit ready", "Audit Validated", "Immutable Archive", "ISO/IEC 27001";
- "syncs to delivery and deal audit logs", "Auto-synced from Salesforce & Ironclad", "3 reviewers synced", "confidence intervals";
- "Deterministic Rule Check · 0 API Tokens", the "Audit Log" button.

**Workflow the product deliberately doesn't have:**
- "Escalate to Tech Lead", "Requires Solutions Architect Approval", "Delivery Handover Protocol", "Prerequisite: 0 unaddressed blockers", "Gate incomplete";
- a "Status Verification" timeline;
- invented stage names. **Use the seven real stages.**

**Wording and status:**
- the words "Resolved", "Settlement", "Discrepancy" in the UI;
- red text for findings;
- a row showing two status chips at once;
- the top navigation (Deals / Commitments / Discrepancies / Catalogue);
- "Dealshape 2025".

**Handover notes** come only from stored notes. Never show sample note text.

## 7. Keep unchanged

- The `?detailed` view.
- The rules for closure, notes and handover.
- Status wording: Needs attention, Addressed by note, Closed by documents.
- All existing front-end helpers' behaviour (`mismatchLine`, `verdictLine`, `missingForHandover` and the rest).

## 8. After building

1. Run `.venv/bin/python -m unittest discover -s tests`, then `cd frontend && node --test tests/*.mjs`.
2. Report the counts and list every changed file.
3. **Regression check:** confirm that the verdict line, counts, mismatch text (plain form), print output and locked record content are unchanged for Alder Bank and Harbour Bank. List anything that did change.
4. Draft the DECISIONS.md entry for Lina: "Drawer replaces in-place expansion; v3 visual system (indigo accent, soft cards); green reserved for Closed by documents".
