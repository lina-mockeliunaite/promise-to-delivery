# Checkpoint 2 — Question pack (Wed 21 Oct)

*Drafted 15 Oct. The likely questions and a short answer for each, in plain words. Say them in your own voice; learn the idea, not the sentence. The starred ones are the most likely.*

---

## A. What it is

**1. What does it do, in one sentence?**
It reads a deal's paper trail and shows Delivery which promises the contract doesn't back up, then checks each fix against the documents until the gap is actually closed.

**2. Who is it for?**
Delivery, Customer Success and Support, who inherit the deal at handoff. Pre-signature review by Commercial is the upgrade, not the pitch.

**3. Why would anyone use this instead of the AE's handoff notes?**
Notes say what the AE remembers. This shows what the customer was told, word for word, beside what the contract says, and it keeps track of what has been fixed and who decided what.

---

## B. How it works

**4. ★ Where does the AI come in?**
The model reads all the documents and proposes problems, each with exact quotes. Code then checks every quote exists word for word and checks the product catalogue. Only findings that pass are shown. Only code can close a finding. People make the judgement calls.

**5. ★ Why can't a reviewer just mark something resolved?**
Because "resolved" has to mean the documents now say the right thing. A fix only closes a finding when the code re-checks the original problem and it no longer holds. A person can record a decision, such as *Okay to proceed*, but that is kept separate and the finding still counts as unresolved. A decision is not a fix.

**6. ★ The model is inconsistent. Couldn't a different run make a problem disappear?**
No. When a finding is raised, the exact claim is stored. A recheck re-tests that stored claim against the current documents. If the model doesn't mention it next time, it stays open. I saw this happen on 15 Oct: the model re-worded one gap in a way the code rejected, and the finding stayed open.

**7. What can the code not check?**
Whether the model's description is right. It checks the quotes and the catalogue, not the sentence the model writes about them. Example: the model called a draft SOW "signed". The bold "Checked against" line is what to trust.

**8. Why not use an agent?**
I tested one. On the sealed Coral Pay deal the agent added nothing that passed validation. The design that worked is simpler: one model call to find, code to verify. An agent adds steps and failure points without adding accuracy here.

**9. What happens when someone removes a document?**
Nothing closes. If a finding cites a document that is excluded, it moves to *Needs evidence* until the document is back or replaced. Removing evidence must never look like fixing a problem.

---

## C. Does it work?

**10. ★ How do you know it works?**
I tested it on a deal it had never seen, written and sealed by a separate agent, with the pass criteria fixed before the run. It found all 8 planted issues with no false alarms. It's one deal and 8 issues: evidence, not proof.

**11. ★ Is it better than just asking a model in one prompt?**
On finding problems, no: a single prompt also found 8 of 8. The difference is what you can do next. A single prompt gives you text. This gives structured, verified findings the app can recheck and close, and it never lets the model's inconsistency close anything.

**12. What failed along the way?**
My first version used hand-written rules. On the first sealed deal it found 1 of 3 problems with 2 false alarms; a single prompt found all 3. I didn't demo a known failure. I rebuilt it as model-finds, code-checks, and tested that on a fresh sealed deal.

**13. Your development scores were perfect. Doesn't that prove it?**
No. Those are the deals I tuned against, so a perfect score only shows the fixes did what I intended. The sealed deal is the only test that counts.

---

## D. Real world

**14. ★ What happens at 500 deals?**
Cost is fine: about $0.15 per full review of a deal, and nothing is re-run if the documents haven't changed. What isn't built is the rest: it's a single-user local app with a local database, no logins, no integrations. At 500 deals you'd need a proper database, user accounts, and a connection to the CRM and document store.

**15. Would it work on real deals?**
Not shown yet. It's demonstrated on fictional deals with a complete product catalogue. Real deals have messier documents and an incomplete catalogue. Uploading real documents works, and the app says plainly what it couldn't check (for example, no pricing note means no approvals can be found).

**16. Who puts the documents in? Would Sales do it?**
That's the weak point and still open. The realistic answer is a deal desk or Commercial owner at signature, or a connector that pulls from the document store.

---

## E. Say this before they ask: what isn't finished

- Only promises with problems are listed; a full list of every promise is the next step, and it needs a fresh sealed test.
- The model's summary sentence isn't checked; only the bold line is.
- Uploading an identical file twice creates a new version instead of "no change".
- Rows with the same number of findings are not ranked by severity.
- No integrations, no logins, single user.
- Validated on fictional deals and one sealed deal only.

---

## F. One question to ask them back

"If this landed on your desk at handoff, what would you check first — and would you miss the promises that have no problems?"
