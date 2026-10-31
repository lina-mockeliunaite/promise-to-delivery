# Learning log

## Day 1 — Friday 25 September 2026

**Learned:** When my code calls the model, it sends a key, a model name and my message, and gets back an envelope of blocks — the model's thinking first, then the text answer. I pay per token for both, including the thinking I never see: about 65 in, 380 out, half a cent per run. The first real output also showed me the prompt decides what the system finds — it ignored "our go-live depends on it", the line that makes the promise risky.

**Stuck on:** Setup took most of the day — Claude Code not found (PATH), a placeholder API key, git not knowing who I was, GitHub refusing passwords. I followed the steps but couldn't yet explain all of them.

**Failure:** I pasted my real API key into the chat and had to revoke it. My script also crashed because it read the thinking block instead of the answer, and then printed nothing because of one stray colon — valid code that silently did the wrong thing.

**Still unclear:** Much of the setup felt too technical; I wouldn't yet know how to fix a PATH problem on my own. I spent time on three rounds of design changes after saying the design was frozen — worth watching from Day 2.

**Open question for Day 3:** Should extraction capture customer statements — reliance ("our go-live depends on it") and obligations — alongside vendor commitments?


## 2026-09-27 — Day 2

**Learned:** A region's catalogue record can hold its status, approval rule, limits and GA date together, so I can check a promise against the right market.

**Stuck on:** reading the exercise instructions (what "predict what it will print" meant; where to run commands vs edit files). Pasted file contents into Terminal once.

**Failure:** typo "reqiures" and "2027-o3-31" passed as valid JSON. Removed a comma on purpose: error reported line 5, mistake on line 4.

**Still unclear:** How to reliably extract one commitment spread across several turns of a conversation.

**Scorecard 25 Sep:** 2, 2, 1, 1, 1, 1, 1, 1, 1, 1

**Scope:** Harbour Bank drift storyline moved to Day 3 (time ceiling).


## 2026-09-28/29 — Day 3

**Learned:** A statement records exactly what was said and how firmly; a commitment groups statements with the same material terms. Contract references have to be followed to their actual terms before I decide what is included.

**Stuck on:** Whether SOW §3 and contract clause 3.4 should both produce rows. I resolved it by asking whether each sentence states material terms of its own or only points to them elsewhere.

**Failure:** The brief initially called C05 and C06 overcommitments but missed that both also meet my written expectation-gap rule. I corrected the labels rather than scoring against the brief's intended summary.

**Still unclear:** I can apply authorisation to C01, but I want to explain more crisply why it attaches to the consolidated terms once a firm promise exists, without implying that its earlier exploratory and conditional statements became firm. How to label an authorised training promise omitted from Coral Pay's contract also remains open.


## 2026-09-29 — Day 4

**Learned:** A fair baseline needs the same evidence as the later system. Catching all three planted conflicts in one run is impressive, but it does not show that every issue was found or that the result will repeat.

**Stuck on:** Separating a standard service that Elva is authorised to sell from a service actually allocated to Coral Pay's deal.

**Failure:** I initially thought 3 of 3 would be the whole story. The baseline missed C06's expectation gap even though it found C06's overcommitment, which taught me to score issues as well as cases.

**Still unclear:** Whether the rules can give a useful verdict for every commitment without producing noise when the internal note is silent, as it is for Coral Pay.


## 2026-09-29 — Day 5

**Learned:** Structured output checks the shape of an answer, while code must check its source and quote. The first run produced 23 valid quotes, but that tells me nothing yet about whether all 23 should have been extracted.

**Stuck on:** I had to work through the boundary between a possible customer outcome, a planned delivery and a bare next step. The rejected `DESIGN.md` edit also made me check the exact scope: HB-08 is customer-authored, but the general rule that an Elva-authored email can contain a promise is still right.

**Failure:** I pasted my full API key into the chat — the second time after Day 1. I revoked it and created a new one straight away, and now set the key with `read -s` so it never appears on screen or in shell history.

**Still unclear:** Which of the nine statements above the gold count are actual extraction errors, especially the process promises and HB-07 reference, and whether the extra thinking tokens improve accuracy enough to justify their cost.

## 2026-09-30 — Day 6

**Learned:** I can explain why a better headline score may still be the worse product choice. The cheaper models called S08 and S09 conditional, which would skip the authorisation checks and hide two of the conflicts I built this tool to find.

**Stuck on:** I slowed down when choosing how partial quotes should match labels, and when deciding whether the weekly SOW meeting was a real commitment. I needed to draw a clearer line between delivery under the deal and steps taken to sell it.

**Failure:** My labels missed the weekly implementation meeting, so one reported false positive is a gap in the answer key. The detail-lost check also treated Annex A section numbers as missing commitment details; I kept the original score and recorded both problems.

**Still unclear:** I cannot yet explain how to authorise the weekly meeting if the permitted internal evidence is silent. I also do not know whether Sonnet’s advantage on Harbour Bank will hold on the sealed deal.

## 2026-09-30 — Day 7

**Learned:** A regression test is a fixed set of labelled cases rerun after every change, with named rows that must never break, because a better headline score can hide the exact failure the product exists to catch. When a model keeps breaking a rule it has already been given, the rule usually lacks a boundary; defining "material term" fixed the pointer sentences where repeating the rule would not have.

**Stuck on:** Keeping track of why each of the four code changes existed while Claude Code worked through them; I needed the map of the day restated before the runs.

**Failure:** My own check 6 failed on every Day 6 run before I had changed anything — HB-07's two pointer sentences had been there all along. The only hard case the model got wrong was a sales-process step, the same type as all five remaining Harbour Bank false positives.

**Still unclear:** Whether one clean run proves the pointer fix holds, and how Day 9 should keep sales-process steps off the decision screen without a second prompt change. The hard cases were written after the prompt, so I don't yet know how much 11 of 12 is worth.

## 2026-09-30 — Revision v3 (product and plan revision, before Day 8)

**Learned:** A fix must resolve each issue attached to a commitment. Internal approval can be settled while the contractual gap remains open, so completing one action cannot clear the whole finding.

**Stuck on:** I needed help understanding how a web frontend connects to the Python pipeline, and how to add the workspace while preserving evaluation and learning time.

**Failure:** The earlier schedule understated committed hours and described already allocated contingency as spare capacity. Reviewing it exposed those planning errors before implementation.

**Still unclear:** I still need to understand how the API, ledger and cache fit together in working code, especially how an agent-found issue retains its identity and is closed with evidence.

## 2026-10-02 — Scaffold, simulated Checkpoint 1 and ledger schema design

**Hours (build log):** 1 Oct — 2.5 h total (mostly learning: HTTP APIs, frontend vs backend, scratch server). 2 Oct — about 2 h (about 0.5 learning, 1.5 build and review); about 2 h of the ceiling unused.

**Learned:** The seal has two layers. Deny rules protect my build workflow; the running app is protected by design — it only answers routes I wrote, no route takes a path, and each layer has its own allowlist. Tests use a decoy deal with a canary so they check content, not just status codes.

**Stuck on:** Reading Claude Code's proposals fast enough to spot what was wrong, and knowing which of its questions were mine to decide.

**Failure:** The 1 Oct block slipped a day, so the contingency hours were spent without lightening 3 Oct. My Checkpoint 1 review was simulated, so it confirmed my design instead of testing it.

**Still unclear:** Whether a real reviewer will find rechecking more useful than a spreadsheet, and how the 17-table schema will feel when I have to explain it under pressure.

## 2026-10-02 (evening) — 3 Oct block started early: consolidation, link table, seal test

**Hours:** 2 Oct evening, about 1 h 10: approximately 20 minutes learning and 50 minutes building, reviewing and drafting tomorrow’s brief.

**Learned:** Consolidation needs the material terms pulled out of a quote, not a comparison of whole sentences. Missing required terms must lead to `terms_incomplete` and needs review, while the link table lets one exact statement support several commitments without losing contract coverage.

**Stuck on:** I initially treated normalisation as if it solved matching. Turning “thirty thousand” into “30000” helps, but I still need to identify the volume, unit and period before deciding whether two promises are the same.

**Failure:** The seal test had been passing because nothing had been built that could leak, so the pass gave false reassurance. I learned why it needs decoy content, checks that the canary never appears in responses, and a negative control that demonstrates the test can detect a leak.

**Still unclear:** I still need to work through which terms are required for each capability and how to preserve explicit network/asset pairings. I also need to understand how reference resolution supplies S11’s missing mode from Annex A while preserving the original quote and its provenance.

## 2026-10-03 — Ledger, parser, filter, consolidation, grouping score

*Rewritten by Lina in her own words, 3 Oct 13:48 (replaces Claude's draft).*

**Hours:** 3 Oct, about 2 h 10 (07:41–09:51): about 15 minutes of quiz and learning, the rest directing and reviewing five change sets. Plus about 1 h 10 on 2 Oct evening.

**Learned:** The same promise can appear in different words, so grouping has to compare its material terms, not the whole sentence. One statement can support several commitments, so the ledger needs a link table while preserving the original quote.

**Stuck on:** I needed help deciding when the parsed terms were complete enough to group statements. S11 names Ethereum and Polygon but leaves the screening mode to an annex, so the quote alone cannot establish the full match.

**Failure:** I skipped predicting the results before running the code and moved on without explaining the changes myself. The build progressed faster than my understanding.

**Still unclear:** I still need to explain which missing terms require `terms_incomplete` and needs review, and when the available evidence supports a conclusion anyway. I also want to walk one statement through the filter, parser, grouping and ledger links without notes.

## 2026-10-03 (late morning) — 4 Oct block built early: rules, references, evidence decisions

*Rewritten by Lina in her own words, 3 Oct 13:50 (replaces Claude's draft).*

**Hours:** 3 Oct, about 10:05–11:10, roughly 1 h 05, all directing and reviewing; no separate learning block. Day total about 3 h 15, inside the ceiling.

**Learned:** The contract’s wording is not the whole story: an incorporated SOW and annex can supply the actual terms, so the reference chain matters. Approval is a separate question, answered from the catalogue and pricing note—not from how confidently something was promised.

**Stuck on:** I needed help understanding when missing terms prevent a verdict. A missing detail should block the conclusion it could change; a volume check can still pass if the promise fits every relevant limit.

**Failure:** The initial evidence boundary excluded security questionnaires and Excel pricing notes. That could hide customer promises or approval evidence, so we corrected the scope.

**Still unclear:** I still need to explain how missing or ambiguous references become needs review rather than confirmed gaps. I also need to defend why an unlisted capability can be prohibited by our complete fictional catalogue, while omission from an incomplete uploaded catalogue proves nothing.

## 2026-10-03 (afternoon) — 5, 12 and 13 Oct blocks built early: agent result, recheck and scenarios, workspace screens

*Dictated by Lina, 3 Oct 13:52.*

**Hours:** About 2 hours (rough estimate).

**Learned:** An agent identifying the right problem is not enough: its evidence must also be valid and traceable. Recheck tests each issue separately, so fixing approval alone leaves the contract gap open.

**Stuck on:** I could follow fix-and-recheck on screen more easily than I could explain the steps underneath it. I still needed help tracing how the recorded evidence, cached extraction and issue states fit together.

**Failure:** The agent was right in substance but failed the evidence checks in every run, so the rules power the demo. Browser testing also exposed a threading bug despite the automated checks passing; it was fixed.

**Still unclear:** I need to understand the threading fix well enough to explain it myself. The five scenarios passed with the real model, but I still need to explain what they establish about resolution correctness and what remains untested on new deals.

## 2026-10-05 (evening) — Simulated checkpoint, signing-brief hypotheses, decision integrity

*Dictated by Lina, 5 Oct 23:17, as answers to three close-of-day questions. Saved word for word.*

**Why accepting a risk leaves the finding open:** Accepting a risk records a choice to proceed; it doesn't fix the missing approval or conflicting contract terms. The finding stays open so the handoff still shows what remains unresolved.

**Why the same issue row isn't enough to carry the accountable person forward:** Reusing the row is a storage decision, not proof that the issue and responsibility are unchanged. I need to check whether the revised terms still represent the same issue before carrying the accountable person forward.

**Why a saved handoff looks current after a catalogue edit:** Catalogue changes aren't covered by the current freshness check, so the handoff can look current even though its authorisation basis has changed. The saved snapshot should remain unchanged, but its currentness status needs to reflect that change.

## 2026-10-06 — Checkpoint 1 (real reviewer), integrity inspection and Part B

Today’s checkpoint showed me how much the UI was getting in the way of understanding the product. I struggled with selecting the right evidence myself, and the recheck didn’t make it obvious what had closed and what was still open. I understand why we chose deal-wide re-confirmation: a new pricing note could affect other commitments, so we can’t assume their earlier decisions still apply. In the next demo I’ll let the reviewer find the issues without helping, then show the evidence upload and check result together beside the issue.

## 2026-10-07 to 2026-10-20 — Sealed results, the move to visibility, and building the UI with AI

*Drafted by Claude on 20 Oct from the build record, at Lina's request; Lina to edit any line that isn't true for her.*

**The sealed run taught me the most.** My rules found 1 of the 3 planted issues on Coral Pay. A single model call over all the documents found all three. The rules had been tuned on my development wording and did not generalise. So I rebuilt detection: now the model proposes each gap with exact quotes, and code rejects anything it can't verify. On the second sealed deal, Atlas Remit, that found 8 of 8 issues with no false flags. What the pipeline adds is not better detection. It's evidence-bound findings, a recheck, and a record you can trust.

**Reviewers.** The COO and the Delivery lead both said "visibility, not workflow", so I took the workflow off the screen. Twice, though, I explained the app before the reviewer had tried it alone. That means I still don't know whether a first-time viewer understands it unaided. Praise for a mockup is not a test of it.

**Today, building the UI with AI:**
- Design tools fill gaps with plausible detail. Some of it was false: approvals, compliance claims, money figures. In a product about evidence, I have to strip out everything the data can't back up.
- "What the code verified" and "what the model wrote" can look alike in the data, so the label matters.
- One user action should either succeed completely or leave nothing behind. A failed check had been saving document versions. The fix was to check before writing, and to set a version aside rather than delete it.
- Tests protect earlier rules: a test that no internal key ever reaches the screen stopped a later change.
- **Practical:** each Terminal window starts at home, an environment variable lives only in the window where it was set, and a server left running from a closed window keeps serving old code.

## 2026-10-20 (afternoon) — Outside review, a second vendor, and safeguards from my own mistakes

*Drafted by Claude at close on 20 Oct from the session record, at Lina's request. Lina to edit any line that isn't true for her.*

- **An outside review is useful only after I filter it.** I accepted the pre-signature positioning, the trust wording and the idea of showing check coverage. I rejected a login button with no accounts behind it, hiding the documents that answer "which documents were checked", and dropping the two-colour card rules. I also had to correct my own overclaim: two demos show "two vendors' catalogues, one pipeline", not "any vendor".
- **Honest coverage.** The verifier refused a real concern because the model added three words, "with no exceptions", that aren't in the documents. Hiding that silently would make a review look cleaner than it is, so the screen now says when proposed findings couldn't be verified.
- **Adding a second vendor without breaking the first.** Before promising compatibility, I checked what goes into the hash. The four existing deals kept identical hashes because nothing hashed changed, not because anything was left out. The prompt still names the original vendor, and the claim says so.
- **"First found" has to mean what it says.** It showed the document the model quoted, not the earliest document containing that wording. Now code finds the earliest exact match, and the locked record and the sidebar use the same answer.
- **I misfiled two documents in my own demo,** and one false closure followed. I had clicked straight through a warning. So warnings now state the consequence and put the right action first, and the form pre-selects the document the evidence actually came from.
- **Rules versus enforcement.** "No git" written as an instruction was broken three times. A deny rule in the settings enforces it, the same principle as the product itself: don't rely on someone's word.
- **Practical:** a 502 means the front end is up but the server isn't; I need the right folder before any `.venv` command; and the API key is mine to run, never Claude Code's.

## 2026-10-21 — Demo reliability, a handover record you can check, and keeping the promise specific

*Drafted by Claude at close on 21 Oct from the session record, at Lina's request. Lina to edit any line that isn't true for her.*

- **The offline refusal was not a date bug.** Each cached reading is keyed partly on the document's date. A revision filed as "A new document" gets today's date, so its key changes and the app needs the model. Filed as "A new version of …", it keeps the original date and hits the cache. Now the app questions that filing before adding anything, and both demos run with no API key.
- **Draft fixes are checked against the signed contract.** A gap closed by a draft is confirmed or reopened by whether the signed paperwork still contains the fixing sentence. The check forgives formatting (curly quotes, number words) but not wording, because a reworded clause can change what it commits to. It errs toward attention.
- **One definition of an open gap.** Several counts each had their own SQL and had to be patched one by one. Now every count goes through one function, and a test stops new ones bypassing it.
- **What my document hashes prove, and what they don't.** The hash covers the text Dealshape read, not the original file, so a changed logo or signature image isn't caught. The browser check trusts the server; tamper evidence comes from the record's fingerprint kept outside the system, for example on the printed record.
- **"Locked" means the contents, not the wording.** The stored record and its fingerprint never change. The sentences around them are built from those stored facts and can improve, so old records show the new wording.
- **Keep the promise specific.** I nearly swapped "Catch deal surprises before you sign" for "One deal. Every team aligned." The new line described an outcome every collaboration tool claims, and it would have reversed an outside reviewer's recommendation one day later with no new evidence. I kept the tagline and let the description line carry the cross-functional message.
- **A quiet bug in plain sight.** The count beside "Deal reviews" showed only deals in handover. In the demo both numbers were 5, so nothing looked wrong.
- **Practical:**
  - `git add -A` stages whatever is in the folder, including files Claude Code is still writing. Read `git status` first and name the files.
  - `--ff-only` makes git refuse a merge rather than quietly combine branches.
  - "No module named pytest" and "Missing script: test" are errors about how the tests were started, not failed tests.
  - The last line of a test run decides it: `OK` or `fail 0`. The noise above is tests breaking things on purpose.

## 2026-10-27 — Findings belong to what they describe

*Drafted by Claude at close on 27 Oct from the session record, at Lina's request. Lina to edit any line that isn't true for her.*

- **A layout can make a true finding read as false.** The landing card said "Contract says chat and email · not offered". "Not offered" described the promise (phone calls), but it sat against the contract's wording, so it read as "chat and email aren't offered". Alder had the same flaw. The rule I set: a finding about the promise sits with the promise, as a badge beside the title; what the contract says gets its own line. It now applies to the cards, the deal rows, the drawer, the locked record and the print.
- **Fixing one thing exposes the next.** Once the line was clean, the gaps around it stood out: the two landing cards laid out differently, the languages row said only "Contract differs" because of a 45-character limit set for the old joined sentence, and the drawer repeated "Contract says chat and email" twice. Each fix was its own plan, review, tests and screenshots.
- **Check whether it's wording or logic before fixing.** "Not in the draft contract or SOW" next to a quote from the SOW looked like a contradiction. Both findings were true: the SOW names chat and email, and the words "phone calls" appear in neither document. The label just didn't say which words. Naming the missing phrase fixed it, without touching the check.
- **The reviewer gets corrected too.** Claude proposed "None of the contract documents mention…". Claude Code pointed out that the check never reads signed paperwork, so that would claim more than was checked. The original "draft contract or SOW" was accurate; only the phrase was missing.
- **Colour means urgency, nothing else.** I asked whether "Not offered" should be red or orange. It would compete with the orange status chip, and in the locked record the badge stays on a row already addressed by note, where red would say danger about something the customer has agreed. A light grey fill made the badge easier to find without turning it into a warning. I tried it live before deciding.
- **Why the RFP matters if the contract is right.** The contract decides what we owe; the RFP decides what the customer expects. RFP responses are often attached to the contract, and a misrepresentation can survive an entire-agreement clause. Dealshape doesn't say which document is right. It makes sure the difference is fixed or knowingly agreed before Delivery inherits it.
- **Practical:**
  - This project's tests run with `python -m unittest discover -s tests -b`. Without `-b`, a test's own printed output can hide the summary line.
  - One commit took three changes again, the same lesson as 21 Oct: commit each working change before starting the next.
  - Before/after screenshots at desktop, 390px, light and dark caught what tests can't: a badge that wraps, a fill that disappears on hover.

## 2026-10-28 to 2026-10-31 — Making every screen say exactly what is true, before the video

*Drafted by Claude at close on 31 Oct from DECISIONS.md and the session record, at Lina's request. Lina to edit any line that isn't true for her.*

- **Both sides of a mismatch get the same shape.** A row used to say what the contract says but only where the customer heard the promise. Now the two lines match: "Customer was told phone calls · RFP response, 28 Sep" and "Contract says chat and email · Draft SOW". If one side is shown without its source, it reads as the stronger side.
- **A summary must not pretend to be a quote.** On the landing cards I shortened the terms ("12 languages", "4 languages"). That meant the label had to change too: "Contract says" signals exact wording, so the cards say "Contract has" and the evidence stays on the deal page word for word. The same reason led me to replace "shows every mismatch" with "flags mismatches": the product flags what it finds and says what it couldn't check.
- **Wording can promise completeness by accident.** "Know exactly what you inherit" became "understand what you're taking on". No checking tool can honestly promise "exactly".
- **Show only what the reader needs at this stage.** The deliverables list is folded behind "Show deliverables (5)". The Handover card is folded until the deal is Signed, because the lock can't be used before then. It opens by itself once the signed contract arrives or a note exists, so nothing written is ever hidden. The stage that drives this is the same one the stage bar shows, calculated from the documents.
- **I tried a cleaner idea and reverted it.** Replacing the "Needs attention" chip with a dot looked tidier, because the heading already gives the count. In practice the row lost its words, and a reader had to work out what the dot meant. I brought the chip back, kept the title at 14px, and separated rows with space rather than lines. Trying it live and reverting was cheaper than arguing about it.
- **A results card should report what the document changed, not repeat the page.** "What changed" now says what the added document closed, opened, reopened or confirmed in the signed contract. Unchanged gaps elsewhere stay in the list below it. It also names documents in plain words ("Draft contract, new version (v2, 19 Oct)") and takes the date from the file itself, not the upload day.
- **Display fixes stay out of the engine.** Every change in these four days was display or wording only. The hashed engine files were checksummed before and after and didn't change. The one backend file touched, `workspace.py`, only changes how names are shown when they're read. Keeping that boundary is what lets the sealed results stay honest.
- **Known effect, written down rather than hidden.** After the first new review in the demo, the specialist row's source moves from "RFP response, 28 Sep" to "Call transcript, 14 Sep". The saved starting reading holds one statement, and a fresh review finds the earliest of three. The screen is faithful to what is stored. I'll see it in the video and can explain it if asked.
- **Practical:**
  - Again, one commit took many changes (21 Oct, 27 Oct, now 30–31 Oct), and this time I committed and pushed before the test result was back. The tests passed (781 Python, 176 front-end), but the order was wrong. The rule from here: run the tests, read the summary line, commit, then start the next change.
  - `git merge --ff-only revamp` moves `main` forward without creating a merge; GitHub shows `main` by default, so it has to be current before anything is shared.
