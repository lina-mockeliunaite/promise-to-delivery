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
