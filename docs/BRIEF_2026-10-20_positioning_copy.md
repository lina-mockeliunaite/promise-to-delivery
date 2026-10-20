# Brief: positioning and copy pass (20 Oct 2026)

**For Claude Code.**
- Inspect first. List the files and your plan, and wait for Lina's OK.
- No git.
- **Scope:** copy and front end, plus at most two small read-only API fields (items 3 and 9). Detection, verification, closure, hashes, the snapshot format and stored data stay unchanged.
- **Done means:**
  - both test suites pass, with tests for any new helper;
  - a regression check on Alder Bank and Harbour Bank, saying what changed and what didn't;
  - a DECISIONS draft for Lina.

## Why

The outside review (20 Oct) recommends leading with **catching deal surprises before signing**, rather than the handover moment, and tightening the trust language. **This reverses the 5 Oct positioning,** where the handover record was the pitch and pre-signature review was the upgrade. The handover record stays as an important output.

## 1. Messaging (`brand.js`, top bar, home, README)

**Tagline:**
- **Now:** "See the deal as it was actually promised."
- **New:** "Catch deal surprises before you sign."

**Description, used on the landing page and home only:**
> "Dealshape compares what the customer was promised with the contract and your product catalogue. See which commitments are missing, different or unsupported, with the source evidence."

**Audience line:** "For B2B Sales and Delivery teams."

**Remove the repeated taglines and explanations.**
- The tagline appears once, in the top bar.
- The page footers keep only the scope line and "All companies, people and deals are fictional."
- Remove "shows the shape of the deal" and "visibility tool" wherever they appear on screen.

**README:** update the tagline and the opening paragraph to match. Keep "visibility, not workflow" as a design principle in the body, not as the headline.

## 2. Landing page (new, small)

The first visit to `/` shows:
- the wordmark and tagline;
- the description and the audience line;
- one primary button, **"Open a sample deal"**, which opens Alder Bank;
- a quiet secondary link, "See all deal reviews", which opens the home list.

**Beside the introduction, show one concrete mismatch,** taken from Alder's stored data (not hand-written):
- the commitment's title and its mismatch line;
- for example, "Hosting on Microsoft Azure · Contract says Amazon Web Services in the Sydney region · not offered".

Repeat visits go straight to the home list. Remember this per browser in localStorage, wrapped in try/catch; if storage fails, show the landing page.

**No "Log in" and no "Review your deal" button.** There are no accounts, and uploading belongs to "+ New deal".

## 3. Home: "Deal reviews"

- **Rename the title** from "Deals in handover" to **"Deal reviews"**, with the eyebrow "Before signing and at handover".
- **Under each deal name, show one scope line.** It comes from a new optional, owner-confirmed `scope` field in `data/profiles/<deal>.json` (Alder only), returned as a read-time field like `display_name`. Never generate it. If the field is absent, show nothing.
  - Alder: "Scam protection for outbound instant payments"
- **Filter counts must say what they count.** Tabs count deals ("4 deals"); the column counts commitments ("3 commitments need attention"). Keep the wording consistent.

## 4. Wording across all screens

| Now | New |
| --- | --- |
| First promised in the RFP response, 29 Sep | First found in the checked documents: RFP response, 29 Sep |
| What was agreed, and who will act on it | Note or recorded agreement |
| Complete handover | Lock handover record |
| AI-written summary · the quotes behind it are checked against the documents | AI-written summary · quotes checked against the supplied documents |

## 5. Drawer: lead with the mismatch

Directly under the title and status chip, show the row's mismatch line (`mismatchParts`, the same styling as the row). This is the issue in one line, before any scrolling.

The order below it stays the same: Customer was told · Contract says · What we found · AI-written summary · Notes.

## 6. What changed: lead with the result

- **First line:** the result, for example "Approval found · the contract gap on this commitment is still open."
- **"No model call was needed: code checked every finding again."** moves to a small muted footer line.
- Everything else stays as it is.

## 7. Locked record: open items first

The new order:
1. banner;
2. heading;
3. verdict line;
4. **Commitments at handover;**
5. What we're delivering, including any re-confirmation notice (keep it: a lock must not make a stale brief look current);
6. handover notes;
7. record details.

## 8. Shorter sidebar

"Deal journey · N documents" stays visible. Each stage shows its name, its document count and any "N gaps started here" marker.
- **The documents under a stage are collapsed,** except the current stage, which is expanded.
- **Clicking a stage expands its documents in place.**
- **"Which documents were checked" must still be answerable at a glance,** from the total plus the per-stage counts.

## 9. Check coverage (UNDERSTAND for Lina: an honest review shows what it couldn't check)

If the current review has proposed findings that failed verification and are therefore not shown, show **one muted line under the Commitments heading:**

> "N proposed findings couldn't be verified against the documents and aren't shown."

- Use the existing stored rejected-finding records; add one read-only count field if needed.
- Show nothing when N is 0.
- **Neutral styling, not a status.** It changes no count or verdict.
- **Show the same line in the locked record** if the snapshot holds the count. If not, leave saved records untouched and tell Lina.

## 10. Don't change

- The status colours and their meanings.
- The two card rules (indigo brief, amber commitments).
- The drawer behaviour.
- Notes vs documents.
- The engine, the hashes, the sealed sets, the `?detailed` view.

## After building

1. Run both test suites.
2. Regression check on Alder Bank and Harbour Bank.
3. List the changed files.
4. Draft `docs/DECISIONS_DRAFT_2026-10-20_positioning.md`:
   - **Chose:** pre-signature positioning, the tagline, the landing page, check coverage and the wording changes.
   - **Rejected:** a "Log in" button (no accounts); collapsing the documents entirely (it would fail the 10-second test); fewer card rules (they are a two-colour system).
   - **Reverses:** the 5 Oct positioning.
