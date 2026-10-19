# Brief: simplify the deal page and handover record (19 Oct 2026)

**For Claude Code.**
- Inspect first, then list the files you will change and wait for Lina's OK before editing.
- No git commands.
- **Scope:** front end, plus small additive API fields only. Detection, verification, closure rules and stored data stay exactly as they are.
- **Done means:** all Python tests and all front-end tests pass, with new tests for the new helpers.

## Why

Two outside reviews and Lina's rehearsal agree on the same things:
- A first-time viewer has to work too hard: repeated counts, five blocks before the first promise, rows that don't say what's wrong, and a name box that blocks every action.
- "Resolve" makes the tool feel like issue management. It is a visibility tool.
- A note must never make an uncomfortable commitment disappear from the handover story.

**The test after the change:** a new viewer can say, within 10 seconds of opening Alder Bank,
1. what we're delivering,
2. which commitments need attention and why, in one line each,
3. what has already been agreed,
4. which documents were checked, and when.

## 1. Deal page: new order, top to bottom

1. **Header (one block):** deal name · stage chip · target go-live · "Checked [date] against N documents". Remove the "Live deal view" chip. Keep "Check again" when the review is out of date. Keep the Product catalogue button.
2. **What we're delivering:** the existing brief, shown open.
   - The summary and deliverables, then "Confirmed by [name] from [document]".
   - Keep the re-confirmation warning.
3. **Commitments needing attention** (renamed from "Promises"):
   - **One count only**, in the heading, for example: "3 need attention · 1 addressed by note · 1 closed by documents". Remove the summary box with its three pills, and the open/resolved chips beside the heading.
   - **Stage history:** replace the 7-step bar above the list with one line, "Stage: Contracting · gaps first made at Proposal / RFP · Show history". "Show history" expands the existing bar in place, collapsed by default.
4. **Handover:** both notes, the signing date, and Complete handover. Keep the logic. The disabled button must list what's missing, in words, under it.
5. **Footer scope line:** "Lists commitments where the customer's expectation, the contract and what we can sell don't line up. Checked against the documents listed and the product catalogue."
6. **Right column:**
   - Keep "Documents checked".
   - Replace the permanent "How a gap closes" box with a "How closing works" link that opens the same text in a small pop-up.
   - Put a one-line version inside each action dialog.

## 2. Each commitment row

**Collapsed, the row must tell the story without opening it:**

```
Coaching-scam detection live at launch                 [Needs attention]
Not approved internally · Not in the contract
First promised in the RFP response, 29 Sep
```

- **Title:** a plain title if the deal profile sets one (see section 5), otherwise the extracted name.
- **Mismatch line:** built only from verified finding labels and stored terms, never from AI text. The finding-to-phrase mapping is in section 4.
- **First promised:** the earliest statement's source label and date.
- **Status chip**, three states:
  - **Needs attention** (amber);
  - **Addressed by note** (outlined, not solid). Rename "Resolved by note" everywhere in the UI;
  - **Closed by documents** (solid green).

**Expanded:**
- Keep the three columns, renamed "Customer was told" · "Contract says" · "What we found".
- If a plain title is shown, show "Extracted as: [original name]" under the columns.
- Keep the AI label on the explanation paragraph: "AI-written summary · the quotes behind it are checked against the documents".
- Keep "already closed by the documents" and note blocks as they are, with the new wording.
- **Footer actions** replace "Resolve…" with two explicit buttons, plus a quiet link:
  - **Add updated document** opens the existing Add-a-document form, with the suggested file pre-selected as now;
  - **Record a note** opens the note form;
  - **Mark as seen** stays a quiet text link. It must not look like a button that closes anything.

## 3. Notes

- **The default option is "Keep it open, add context"** (stays Needs attention, note shown inside the row).
- **The second option is "Mark as addressed by note"**, with the helper text: "The documents still differ. It moves to 'Addressed by note', stays in the handover record, and reopens if the documents change."
- The button reads "Save note".
- Wherever a note is shown, attribute it as **"Recorded by [name] · [date]"**.

**Name handling: no gate.**
- Actions are enabled without a name.
- On the first action with no stored name, the dialog shows a "Your name" field (required for saving), stored in the browser as now.
- Remove the top-right name box. Replace it with a small "Recording as [name] · change" link once a name exists.

## 4. Wording

| Now | New (detail) | Chip / short form |
| --- | --- | --- |
| No approval recorded | No approval found in the supplied documents | Not approved internally |
| Missing from contract | Not in the draft contract or SOW | Not in the contract |
| Contract says something different | The contract says something different: "[contract term]" | Contract differs |
| Not offered | Not offered: no exception can fix this; only changing the promise can | Not offered |
| Resolved by note | Addressed by note · not in the documents · reopens if the documents change | Addressed by note |
| Resolve… | Add updated document · Record a note | — |
| Promises | Commitments needing attention | — |
| The deal in brief | What we're delivering | — |

**Mismatch line:** join the short forms of each open finding with " · ".
- For "Contract differs", append the stored contract term when it is short, for example "Contract differs: AWS Sydney".
- **Unit test this builder** with Alder's three commitments.

## 5. Plain titles (Alder Bank only, set by the deal owner)

Add an optional `titles` map to `data/profiles/<deal>.json`, keyed by the stable commitment key. The register returns `display_name` next to `name`; the UI shows `display_name` when present. This is owner-confirmed wording, like the brief. It is never generated.

| Extracted name (now) | Plain title |
| --- | --- |
| BioCatch-based coaching detection live from 1 February 2027 launch | Coaching-scam detection live at launch |
| Real-time scoring of 750,000 outbound instant payments per day by end of first year | 750,000 payments a day by the end of year one |
| Hosting Alder's environment on Microsoft Azure in Australia East | Hosting on Microsoft Azure |

## 6. Frozen handover record

Order, top to bottom:
1. **Quiet banner:** "Handover complete · locked on [date] by [name]". Light grey, not dark.
2. **Heading:** "[Deal]: what Delivery inherits".
3. **What we're delivering:** the brief from the snapshot, shown open in the main column, not the side.
4. **Verdict line, honest:** "Handed over with N needing attention, M addressed by note, K closed by documents." Never say "no open gaps" when anything was addressed by note. Use "no open gaps; M addressed by note" instead.
5. **Commitments:** the same rows and wording as the live page, read-only.
6. **Both handover notes.**
7. **Record details**, folded at the bottom: documents at handover and the fingerprint with Copy.

Print or save as PDF stays, and expands every row first.

## 7. Home

- Remove the three summary tiles.
- Keep the title, filters, search, sort and table.
- Rename the column "Open gaps" to "Need attention".

## 8. Don't change

- Detection, verification, closure rules, the freeze middleware, the hash definitions and the snapshot format. The added `display_name` is a read-time field, not part of any hash.
- The visual system (Geist, teal, amber, green). Google Stitch restyles after this structure is in.
- The pre-revamp detailed view behind `?detailed`.

## 9. After building

1. Run `.venv/bin/python -m unittest discover -s tests` and `cd frontend && node --test tests/*.mjs`.
2. Report the counts.
3. List every changed file.
