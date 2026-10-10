# From Promise to Delivery — Build & Learning Plan v3

*Lina Mockeliunaite · 30 September 2026 · v3.4 · replaces v2.6 · product revised before Day 8 into a local deal workspace with resolution checking · technical checkpoint 16 Oct, target completion 21 Oct, hard stop 22 Oct · Days 1–7 unchanged*

## Start here

**In one sentence:** you are building a small working deal workspace that reads a deal's paperwork before signature, catches promises that became stronger than the company authorised and promises that disappeared from the contract without being withdrawn, and then checks whether the fixes people record actually close those gaps. You are learning agentic AI hands-on while you build it.

**Why you're doing it.** Two reasons, equally weighted:

1. **To learn to build.** Not to become a software engineer, but to understand AI systems well enough to design, direct and defend one.
2. **To have evidence.** A working product a business leader understands in thirty seconds, plus a public repo, honest results and the ability to explain every choice.

**What changed in v3 (30 Sep).** After Day 7 the product was revised for a business and leadership audience. The evaluation story stays; a usable workspace sits on top of it. The distinctive behaviour is the **recheck**: after someone records a fix, the system shows which issues closed, which remain open and the evidence behind each. Scope grew, so the timeline grew with it: **50 committed hours including learning and logging (the 4 contingency hours pulled forward to 1–2 Oct are already inside this), plus 2 spare hours on 16 Oct and up to 4 on 22 Oct: 56 hours maximum, excluding optional work during 6–11 Oct**, technical checkpoint **Fri 16 Oct**, completion **Wed 21 Oct**, **hard stop Thu 22 Oct**. Nothing technical was cut.

**How to use this plan.**

- Lost? Read **The product on one page** and **Where you are now**.
- Starting a day? Go to that date in **Remaining schedule**, then open a new conversation in this project titled with the date.
- Not sure how deep to go? Look for the label: **understand**, **recognise** or **just do**.
- The revision brief is saved in the repo as `docs/REVISION_BRIEF_2026-09-30.md`. This plan is the schedule; the brief is the detailed specification.

## The product on one page

**Working title:** Promise to Delivery (repository name unchanged). Final brand name is follow-on work.
**Tagline, to test with reviewers:** "Catch deal surprises before you sign."
**Product line:** "A simple workspace that shows what was promised, what needs resolving, and whether the fixes close the gaps."
**Demonstrated scope (say this everywhere):** "Demonstrated on fictional deals with a complete capability catalogue." Other uploads can compare promises with contractual terms, but their accuracy is unvalidated, and authorisation shows *Needs evidence* without suitable internal evidence.

**Audience.** B2B software and services teams, of any size, whose commitments are scattered across calls, proposals, contracts and internal approvals, whether they use spreadsheets, a CRM or an internal system. The shared handoff serves Delivery, Customer Success and Support.

**The user journey.**
Create or open a deal → upload or select sources → **Review deal** → inspect evidence → record a fix → recheck → save and export the handoff.

**The problem: drift.** As a promise moves from sales call to RFP response, proposal, SOW and draft contract, it can become firmer, broader or more contractual than anyone approved, or a specific term can quietly turn vague. Nobody sees the whole chain, so Delivery inherits it at kickoff.

| Source | What it says |
| --- | --- |
| Discovery call | "We're exploring whether Elva's pre-built connector to a blockchain analytics provider can return real-time screening results for Polygon wallets in time for your launch." |
| Technical call | Real-time Polygon screening could run as a limited beta, if Product grants named approval; planned GA in Singapore 31 March 2027. |
| RFP response | "Elva will return real-time wallet-screening results for Ethereum and Polygon before every NUSD payout is released." |
| Proposal | Every NUSD payout on Polygon screened in real time before release, from the 1 December launch. |
| Draft SOW | Screening "in accordance with the Wallet Screening Specification in Annex A". Annex A: Polygon wallets screened in hourly batches. |
| Draft contract | Incorporates the SOW and Annex A; clause 3.4 points to SOW section 3 — so, two references deep, hourly batch. |
| Customer email | "Our 1 December launch depends on Elva's real-time screening result clearing every recipient wallet before release." |
| Catalogue | Polygon batch screening: GA. Polygon real-time: beta in Singapore, requires named approval, planned GA 31 March 2027. |
| Pricing/services note | No named exception approved for Harbour Bank. |

*Finding: a firm, dated promise went beyond the catalogue with no approval evidence (an approval issue), and the contract, through its references, commits to hourly batch instead with nothing withdrawing the real-time promise (a contract gap). Two separate issues on one commitment.*

**What the review looks for.** Material commitments Delivery, CS or Support need to know: capability, scope, quantity, effort, dates, conditions, customer dependencies, service obligations. It checks for:

- firm promises beyond authorised capabilities or commercial limits
- material terms that conflict across documents
- conditions or approval requirements that disappeared
- firm promises absent, reduced or unresolved in the contract/SOW
- insufficient evidence to reach a reliable conclusion

**The core model (behind the interface): three attributes per commitment.**

| Attribute | Values | Comes from |
| --- | --- | --- |
| Language | exploratory · conditional · firm | The words themselves (the model extracts it) |
| Authorisation evidence | standard-authorised · exception-approved · no approval evidence · unknown / needs review. Firm commitments only; null (not applicable) for exploratory and conditional | Catalogue and pricing/services note only |
| Contractual presence | absent · included in draft contract (with partial/uncertain coverage preserved in the consolidated record) | Document terms and traced references |

**Key rules.** Approval is never inferred from confident language or from appearing in a proposal, SOW or draft contract. Absolute limits apply only to the complete fictional catalogue; an incomplete uploaded reference cannot prohibit by omission. Pointer-only sentences are not standalone commitments, but their references count for coverage. Absence from a selected subset of documents is never a confident claim of absence from the whole deal.

**Results the user sees.** One card per consolidated commitment, with every related issue on it: the promise, what needs attention and why, quotes with source links, the next decision or missing evidence, owner, notes and status. An editable register above it: **Commitment | What needs attention | Owner | Status**, showing clean commitments as well as flagged ones. Issue states: *Needs action*, *Needs evidence*, *Resolved*. Review freshness is separate: changing sources or decision evidence marks the result *Review out of date* until rerun; changing an owner or a note does not.

**Resolution and recheck: the distinctive behaviour.** Three routes, one shared form:

1. Align the documents.
2. Record an allowed exception.
3. Change or withdraw the promise.

The form records the affected issue, owner, rationale and supporting evidence. Choosing a route or typing "resolved" is not proof. The recheck re-evaluates every issue on that commitment with the same rules. **What closes is an individual issue; a commitment shows Resolved only when every issue on it is closed.** An exception needs permitted evidence for the exact terms and cannot override an absolute limit. Approval alone does not close a contract gap. Approved decisions are immutable; a change creates a new version. A reviewer cannot erase a system finding, only record an evidenced disposition.

**Recheck must be deterministic where inputs haven't changed.** Extraction results are cached under a key built from everything that can change the output: the document's content hash, its document type and any document context passed to extraction, plus the extraction configuration (system-prompt, template and schema hashes, model ID, thinking mode, max tokens). ~~A recheck reuses a cached result only when the whole key matches; any change re-extracts that document.~~ *(Corrected 10 Oct, see DECISIONS 2026-10-06: a cache lookup hits only when the whole key matches. A recheck reuses the extraction its previous review used for an unchanged source version, whatever configuration made it; a new or re-included version is looked up by the whole key. Each review records the key every source used.)* Otherwise model variation, not evidence, could open or close a finding. Source-set and decision-evidence hashes drive *Review out of date*.

Three kinds of run, kept separate:

- **Recheck after a fix (what the app does).** A fix changes the inputs, so this is not an unchanged-input run. Reuse cached extraction for every document whose cache key is unchanged; re-extract only changed eligible documents; update the affected commitments in the ledger; then reassess every issue attached to those commitments against its closure criteria.
- **Unchanged-input rerun.** Nothing changed: cached extraction plus deterministic rules gives the same result, with no model call. This is the reproducibility check.
- **Fresh model run.** Bypasses the cache and calls the model again. Used for the repeatability measurements and the sealed evaluation. Caching extraction does not make the agent deterministic: each of the three agent measurements makes its own agent calls over the same ledger.

**Issues never disappear because the checker changed.** Every issue records which configuration found it (rules or agent). If the agent found an issue and the recheck runs on rules, that issue stays open and visible until its own closure criteria are satisfied with evidence; the recheck cannot drop it because the rules would not have raised it. Closure is a decision about evidence, not about which checker ran last.

**Five resolution scenarios on Harbour Bank** (separate, labelled; original fixtures and labels untouched):

| Scenario | Expected result |
| --- | --- |
| Approval added; hourly-batch SOW remains | Contract gap stays open |
| SOW aligned; required approval still missing | Approval issue stays open |
| Both issues supported with evidence | Finding closes |
| Absolute limit plus an attempted exception | Remains blocked |
| Insufficient evidence | Remains *Needs evidence* |

**Three views** (may share one layout):

| View | Essential content |
| --- | --- |
| Deals | Create or reopen a deal; last review; outstanding items |
| Deal workspace | Selected sources (include/exclude), **Review deal**, commitment register, evidence and fix panel |
| Handoff | Shared record for Delivery, CS and Support; reviewer decision; CSV and readable export; unresolved items stay visible |

Visual style: calm and professional. Readable type, neutral surfaces, one accent colour, compact tables, status shown by text and icon as well as colour. Conflicting terms and exact quotes side by side. Upload, processing, empty, incomplete, failed and out-of-date states all visible. No AI jargon or decorative dashboards on screen.

**The pipeline (behind the interface).**

1. **Ingest** — uploaded or selected documents, each tagged with one of the seven existing document types (plain-language names in the UI); content hash recorded.
2. **Extract** — frozen extraction v1, cached by content hash.
3. **Filter** — remove sales-process housekeeping; keep genuine service obligations (S15).
4. **Consolidate** — one record per promise with history, in the SQLite ledger.
5. **Find conflicts** — evidence and coverage rules; capability and authorisation built twice, rules vs agent.
6. **Resolve and recheck** — manual fixes with evidence, issue-level closure.
7. **Handoff** — saved record and export.

**Local architecture.** React frontend built to static files; a thin Python HTTP layer that calls the existing modules (no second pipeline, no builder-default model); both served locally; SQLite for deals, snapshots, findings and decisions. Credentials stay server-side. User-created deals live in their own gitignored folder outside `data/`, reached through their own guarded path function; `ALLOWED_DEALS` and `deal_dir()` stay unchanged. No public model-backed endpoint in this build.

**The world it runs on (all fictional).** Elva, an AML platform with transaction monitoring, screening, case management, SAR drafting, a payout ledger connector and digital-asset wallet screening through pre-built analytics integrations (TRM Labs and Chainalysis named for realism only; no partnership claimed). 25-capability catalogue, region → network → asset → mode; anything unlisted is an absolute limit.

| Deal | Buyer | Role |
| --- | --- | --- |
| Harbour Bank | Singapore digital bank, HarbourPay Global NUSD payouts, launches 1 December | Development: build, tune, break; resolution scenarios |
| Kestrel Remit | Fictional hard-case fixtures | Regression and hard cases |
| Coral Pay | Sydney payments company, NUSD on Ethereum and Solana | **Sealed.** Runs exactly once, 14 Oct |

**Not in this build:** post-signature tracking, margin modelling, live connectors (Google Drive first, later), generated resolution suggestions, OCR for scanned documents, per-role dashboards, a customer-facing view, name/domain research, automatic contract editing or legal advice.

## How to talk about it

Lead with what exists, then where it could go.

| Moment | What you say |
| --- | --- |
| Opening (spoken) | "I built a deal review workspace. It catches promises that got stronger than the company authorised, and promises that disappeared from the contract but not from the deal. Then, when someone records a fix, it checks whether the fix actually closes the gap." |
| Product line (written) | "A simple workspace that shows what was promised, what needs resolving, and whether the fixes close the gaps." |
| Scope, always | "Demonstrated on fictional deals with a complete capability catalogue." |
| Why it matters | "Commitments changed across documents without every affected function consciously agreeing to them. Flagging that isn't enough; teams also mark things resolved that aren't." |
| The design insight | "What someone said, what the company approved and what's in the contract move independently. Fixing one doesn't fix the others, so a partial fix has to stay open." |
| How you tested it | "I rerun a fixed set of labelled cases, certain rows must never break, and the test deal was sealed until one final run." |
| After explaining how it works | "The longer-term vision is a shared commitment record from the first promise through contract and delivery." |

## Where you are now

**Day 7 closed Wed 30 Sep. Extraction v1 is frozen. Product revised to v3 the same day.** Checkpoint 1 is Fri 2 Oct, now a paper test of the revised product. Read `WHERE_I_STOPPED.md` first.

| Done | Evidence |
| --- | --- |
| Python 3.12, git, Homebrew, Claude Code (Pro login) | Working on your Mac |
| Public repo | github.com/lina-mockeliunaite/promise-to-delivery |
| Project venv with the Anthropic library | `.venv`, excluded by `.gitignore` |
| API key on prepaid credit ($19.79 remaining on 30 Sep) | Set with `read -s` (rotated twice after exposure, Day 1 and Day 5) |
| Design, decisions, learning log | `DESIGN.md`, `DECISIONS.md`, `LEARNING_LOG.md` |
| Catalogue (25 capabilities) | `data/catalogue.json` |
| Harbour Bank pack and labels | `data/harbour_bank/`: 8 documents, 15 statements, 8 commitments |
| Coral Pay pack, **sealed 29 Sep** | Hashes in `data/coral_pay.sha256`; four deny rules in `.claude/settings.json`; `ALLOWED_DEALS` guard; path containment |
| Naive baseline (Day 4) | `results/baseline_harbour_bank.md`: 3 of 3 conflicts, 6 of 7 issue labels, 0 false flags |
| Extraction v1 (Day 5) | `extract.py`, `schema.py`, `config.py`, `check_quotes.py`; ~$0.068 per run |
| Eval harness and model choice (Day 6) | `evaluate.py`; Sonnet 5 with default thinking kept |
| Regression, hard cases, freeze (Day 7) | `regression.py` 6/6; precision 75% (15/20), recall 15/15; hard cases 9/9; 75 tests pass; hashes in `WHERE_I_STOPPED.md` |

**Repo as of 30 Sep:** ~1,100 lines of Python, command-line scripts only, dependencies `anthropic` and `pydantic`. No web layer yet.

**Open going into the revised build:**

- Sales-process steps extracted as firm (all 5–6 false positives). Filter downstream before conflict rules.
- "thirty thousand" (KR-02) and "30,000" (KR-03) must consolidate.
- C08 and KC3 must return *needs review* where the internal note is silent.
- Repeatability untested (one run per configuration).
- Known v1 gap: an Elva promise reported only in a customer email is missed.
- New: user-created deal storage, document-type mapping for uploads, extraction cache key (content, doc type, context and extraction configuration) (design on 1 Oct).
- New: confirm Node is installed on the Mac (`node -v`; if missing, `brew install node`, just do).

## How every day works

Same loop, about 4 hours: **learn it, build it, check it.**

| Block | Time | What you do |
| --- | --- | --- |
| Learn | 45–60 min | The day's concept in plain language, then a small typed exercise for **understand** items |
| Build | ~150 min | Claude Code builds; you direct, read every change and run it |
| Check | 30 min | Commit, log the decision and the learning, close-of-day quiz |

**Depth labels.** **Understand**: explain it without notes, under questioning. **Recognise**: know the symptom and where to look. **Just do**: follow the steps. Claude takes on most recognise and just-do work; the understand items stay yours.

**Habits.** Type first, then delegate. Explain before you accept. Predict, then run. Break it on purpose once a day.

**Daily evidence (about 10 minutes at the close):**

- ☐ One commit, with a message you wrote
- ☐ One DECISIONS.md entry: chose, rejected, why
- ☐ One LEARNING_LOG.md entry (dictate it; Claude saves it word for word)
- ☐ Three quiz questions, answered without scrolling back; at least one out loud from 12 Oct

## Working with Claude

| Tool | Role | Use it for | Not for |
| --- | --- | --- | --- |
| Claude in this project | Tutor, reviewer, interviewer | Explaining, reviewing code and decisions, writing Claude Code instructions, drafting fixtures and docs for your sign-off, quizzes, saving your log | Running git in your repo; deciding design for you |
| Claude Code (Terminal, in the repo) | Build partner | Writing and changing project code you've directed, one agreed change set at a time (per `CLAUDE.md`) | Deciding the design |

Claude Code cannot see chat attachments. Put briefs in the repo (`docs/`) and point to the file.

**Daily prompts:**

| When | What to say |
| --- | --- |
| Start of day | "[Date]. Read my learning log. Ask me yesterday's quiz miss first, then teach me [concept] with labels." |
| Stuck | Paste the exact error plus one line on what you expected. |
| Before accepting a big change | "Claude Code made this change. Walk me through it, then ask me to explain it back." |
| Close of day | "Close of day. Review my commit and decision, save my log, then quiz me." |
| Before a checkpoint | "Run a mock Checkpoint [1 or 2]. Be hostile." |

## Learning agentic AI: the courses

Anthropic Academy (anthropic.skilljar.com) inside the Learn blocks.

| Date | Course | Section | Why then |
| --- | --- | --- | --- |
| Days 2–7 ✓ | Building with the Claude API; Claude Code 101 | As in v2 | Done |
| Thu 1 Oct | — | Plain-language: what an HTTP API is; frontend vs backend | Defend the architecture |
| Sun 4 – Mon 5 Oct | Building with the Claude API | Tool Use; Anthropic Apps & Agents (chaining, routing, parallelisation) | Rules vs agent |
| Mon 12 Oct | — | Human-in-the-loop design; idempotence and caching | Recheck and closure |
| After 22 Oct | Intro to MCP; agent skills; subagents | Whole courses | Breadth |

**Agentic concepts to explain by 16 Oct (understand):** the agent loop · workflow vs agent · tool use · evaluating agents · human in the loop · when not to use an agent.
**Recognise only:** MCP, subagents, RAG.

## Phase 1 (complete): 25 – 30 Sep

| Day | Date | Build | Status |
| --- | --- | --- | --- |
| 1 | Fri 25 Sep | Setup, first model call | ✓ |
| 2 | Sun 27 Sep | Capability catalogue | ✓ (rebuilt Day 3 for the stablecoin world) |
| 3 | Mon 28 – Tue 29 Sep | Harbour Bank brief, documents, labels; lean pack | ✓ |
| 4 | Tue 29 Sep | Coral Pay drafted, labelled, **sealed**; naive baseline | ✓ |
| 5 | Tue 29 Sep | Extraction v1: language, quote, speaker; quote checker | ✓ |
| 6 | Wed 30 Sep | Eval harness; model comparison | ✓ |
| 7 | Wed 30 Sep | Regression, hard cases, **extraction frozen** | ✓ |

## Remaining schedule: 1 – 22 Oct

**50 hours committed in the dated schedule, within the four-hour ceiling on every day.** This already includes the 4 contingency hours pulled forward to 1–2 Oct. Remaining spare capacity: 2 hours on 16 Oct and up to 4 hours on 22 Oct, so **56 hours maximum**, excluding optional work during 6–11 Oct. The hours include everything, not only building: each 4-hour day is roughly 45–60 minutes of learning, about 2.5 hours of directing and reviewing Claude Code, and 30 minutes of commit, decision log, learning log and quiz. That leaves roughly **30 hours of actual build time**. The 1 Oct audit tests whether that is enough, especially the single 4-hour Excel/PowerPoint block.

**How the contingency works.** There are 6 spare hours inside the ceiling: 2 each on 1, 2 and 16 Oct. Spare hours cannot absorb an overrun on a day that is already at four hours, so they are used in two specific ways:

- **Pulled forward (1 and 2 Oct):** the local UI/API scaffold moves to 1 Oct, and the ledger schema design moves to 2 Oct, once Checkpoint 1 feedback is logged. Both lighten 3 Oct before it starts.
- **Absorbed afterwards (16 Oct):** the 2 hours after Checkpoint 2 take any overrun from 12–15 Oct that does not affect the sealed run.

Be clear about what this means: pulling work forward spends 4 of the 6 contingency hours before 3 Oct. From 3 Oct onwards, the only real buffer is the 2 hours on 16 Oct.

**If a day still overruns, the work moves to the next day and the dates behind it move.** 3 Oct → 4 Oct → 5 Oct; anything left from 5 Oct moves to 12 Oct, and 12–14 Oct shift with it, including the unsealing. Time during 6–11 Oct may take light tasks (reading a diff, copy, explanations) but is never counted on. The ceiling does not move; the date does.

| Date | Hours | Work | Evidence by close | Understand |
| --- | --- | --- | --- | --- |
| Thu 1 Oct | 4 (2 + 2 pulled forward) | Save the brief to `docs/`. Claude Code step one: read-only audit and proposal (doc updates, architecture, user-deal storage outside `data/`, doc-type mapping, extraction cache key, `.gitignore`, estimate changes). Approve, then apply doc updates. Then step two: the local UI/API scaffold showing the permitted Harbour Bank source list and saved extraction results, labelled as intermediate. | DESIGN/DECISIONS/WHERE_I_STOPPED updated; approved architecture note; scaffold runs locally | Frontend vs backend; why user deals live outside `data/` |
| Fri 2 Oct | 4 (2 + 2 pulled forward) | **Checkpoint 1**, paper test of the pivot (below). Log feedback. Then, only after feedback is logged: design the SQLite ledger schema (deals, source snapshots, commitments, findings, decisions) with Claude Code, no pipeline code. | Feedback and acceptance criteria in DECISIONS.md; approved schema | — |
| Sat 3 Oct | 4 | Sales-housekeeping filter; consolidation ("thirty thousand" = "30,000", terms and conditions preserved); ledger built to the approved schema; score grouping. | Grouping score vs labels; S15 preserved | How one promise worded three ways becomes one record |
| Sun 4 Oct | 4 | **Decide `security_questionnaire`** (extract, reference-only or skip) and whether PDF/DOCX pricing notes count as evidence; log both. Write the rules-vs-agent decision rule **first**, with explicit cost and latency bounds. Material conflict, coverage and authorisation rules; citations; silent-note cases (C08, KC3 → needs review); incomplete/missing-reference handling. | Rule-based findings on Harbour Bank with citations | Why rules are enough for some conflicts |
| Mon 5 Oct | 4 | Bounded catalogue-search agent; three fresh agent runs over the same Harbour Bank ledger (three sets of real agent calls); case-by-case comparison with rules. **Formal re-plan at close,** using actual build hours logged since 1 Oct. | Variation, cost, latency recorded; comparison table | Workflow vs agent; the agent loop |
| Tue 6 – Thu 8 Oct | Optional | Light tasks only: review screen copy, learn, read a prepared diff, practise explanations. No milestone. | — | — |
| Fri 9 – Sun 11 Oct | 0 | Unallocated | — | — |
| Mon 12 Oct | 4 | Resolution and recheck logic: three routes, one form; issue-level closure; extraction cache with the full key; source snapshots; five scenarios as labelled fixtures. **Candidate freeze of the evaluated pipeline at close** (extraction, filter, consolidation, rules, agent), recorded with hashes. Recheck, cache, UI and adapter work may continue after today without delaying unsealing, provided it does not change evaluated modules. | 5/5 scenarios behave as expected; candidate freeze recorded | Why a partial fix stays open; why the cache key makes recheck trustworthy |
| Tue 13 Oct | 4 | Wire the UI to the live pipeline through the API: text/Markdown upload, doc-type selection, include/exclude, Review deal, saved results, freshness. **Integration checks on development data;** fix any backend bug they expose, then rerun regression and the downstream checks. **Record the final evaluated configuration** (commit and hashes). If the checks fail and can't be fixed today, **delay unsealing Coral Pay** rather than evaluate a known-broken pipeline. Check API credit; top up if needed. | A fictional deal runs end to end in the browser with live results, no mock data; final configuration recorded, or unsealing delayed with the reason logged | API/frontend separation, under questioning |
| Wed 14 Oct | 4 | Verify Coral Pay hashes; unseal; run baseline, rules and agent **once each** on the final evaluated configuration. Change nothing afterwards. | Exact-case results, cost, failure log, commit/config recorded | What the test deal showed |
| Thu 15 Oct | 4 | Demonstrable review → partial fix → full fix in the UI; technical README; record the demo. | Recorded demo; README with scope caveat and results | The whole system in 3 minutes, including what fails |
| Fri 16 Oct | 2 (+2 contingency) | **Checkpoint 2** (technical): working journey, results, design defence, explicit list of unfinished items. Spare 2 hours absorb overrun from 12–15 Oct. | Recording; hesitations logged | Any design choice, under pressure |
| Mon 19 Oct | 4 | Text-based PDF and DOCX adapters with failure reporting; handoff view with CSV and readable export. | Adapters with separate development checks; both exports work | — |
| Tue 20 Oct | 4 | Excel (.xlsx) and PowerPoint (.pptx) adapters within the agreed boundary (below); Excel/PowerPoint variants of the Harbour Bank RFP response and proposal as new development fixtures (originals untouched); quote validity and source locations checked on both. | Both adapters with development checks; quotes trace to sheet/cell and slide | Why a spreadsheet needs a canonical text form before extraction |
| Wed 21 Oct | 4 | Acceptance checks (below); reopen/export verification; final DECISIONS/WHERE_I_STOPPED; draft *What We Promised*. **Target completion.** | Acceptance list passed | — |
| Thu 22 Oct | Reserve only | **Hard stop.** Not planned work: absorbs overrun from 19–21 Oct only. Anything unfinished at the close of 22 Oct is reported as unfinished, with the reason; the date does not move again. | Final state recorded honestly | — |

**Agreed completion scope.** Supported upload formats: text/Markdown, text-based PDF, DOCX, Excel (.xlsx) and PowerPoint (.pptx). The CSV export and the readable handoff summary are also agreed deliverables. Only visual refinement beyond the basic calm, usable design is optional.

**Excel and PowerPoint boundary for this build.** Excel: cell text with sheet and cell references; question and answer rows kept together as one line; formula results read as values; charts ignored. PowerPoint: slide text and speaker notes with slide numbers; images, charts and embedded objects ignored. Authorisation evidence (catalogue and pricing/services note) stays in its current format: a pricing note uploaded as a spreadsheet is accepted as a source but does not count as approval evidence. Scanned or image-only files need OCR and are outside this build. None of these formats is validated by the Markdown-only sealed run.

**Hard stop: Thu 22 Oct.** The date may move within 21–22 Oct; it does not move past 22 Oct. Anything unfinished then is reported as unfinished, in this order: **PowerPoint first** (a deck saved as PDF goes through the PDF adapter), **then visual refinement** beyond the basic design, **then Excel**. Never cut: PDF, DOCX, both exports, recheck, the full evaluation.

**Log actual build hours per block from 1 Oct** (in LEARNING_LOG.md). Claude Code's 1 Oct audit estimated 43–52 build hours against about 30 available (judgement, not measurement; table in DECISIONS.md). The formal re-plan is at the close of 5 Oct.

**Never cut:** the sealed run, the rules-vs-agent comparison, regression, the decision log. On 16 Oct, report the actual state; do not imply 19–21 Oct features exist.

## Checkpoint 1, Fri 2 Oct: test the pivot on paper

Reviewer: a CS, implementation or pre-sales leader who has lived through a bad handoff. Show Harbour Bank:

1. Real-time promise conflicts with the hourly-batch SOW and needs internal approval.
2. Approval is recorded; the SOW discrepancy stays open.
3. Both discrepancies receive sufficient evidence; the finding closes.

Ask:

- Which remaining discrepancy would affect your handoff?
- Would you trust this before signing, and what evidence is missing?
- Is checking the fix materially more useful than a flagged-items spreadsheet?
- What is the minimum shared record Delivery, CS and Support need?
- Does "Catch deal surprises before you sign" land?

Record objections and acceptance criteria. A positive reaction is early qualitative feedback, not market validation.

## Measuring the build

Headline result: the single sealed run on Coral Pay, baseline vs rules vs agent, reported as exact cases. Keep extraction scores, complete-product findings and resolution correctness separate. Metrics live in the README and results page, not on product screens.

| Metric | Question | Target |
| --- | --- | --- |
| Recall, firm commitments | Found the promises that matter? | ≥ 90% |
| Precision | Invented promises? | ≥ 85% after the housekeeping filter (extraction alone 75%) |
| Language accuracy | Exploratory / conditional / firm right? | ≥ 85% |
| Quote validity | Every quote word for word? | 100% |
| Grouping accuracy | Consolidation matches labels? | Record it |
| Authorisation citations | Every verdict cites catalogue or pricing note; unknowns record the search | 100% |
| Conflict recall | Planted conflicts reach review with evidence | 3 of 3 |
| False flags on clean commitments | Clean items flagged? | 0 per deal |
| Resolution correctness | Five scenarios behave as expected | 5 of 5 |
| Repeatability | Same inputs, same findings (rules); agent variation across 3 runs | Record it |
| Cost, latency, review effort per deal | Could it run for real? | Record it |

**Extraction regression (frozen, six must-hold checks):** all 15 labelled firm statements found; S08 and S09 firm; S12–S14 extracted; 100% quote validity; precision ≥ 60%; no statements from HB-05, HB-07 or HB-08. Any change to prompt, template, schema, model or thinking must pass and be logged with old/new hashes.

**Downstream checks (new):** S15 survives the housekeeping filter; "thirty thousand" and "30,000" match with original quotes kept; conflicting terms survive grouping; partial fixes stay open; unsupported exceptions refused; absolute limits not overridden; missing references never produce confident conclusions; an unchanged-input rerun makes no model call and returns the same result; after a fix, only documents with a changed cache key are re-extracted and every issue on the affected commitments is reassessed; an agent-found issue stays open under a rules recheck until its closure criteria are met.

**Rules-vs-agent decision rule** (capability and authorisation only), written on 4 Oct before any comparison. Keep the agent for the app only if all hold: (1) it catches at least one additional material conflict the rules miss; (2) no unsupported findings or uncited verdicts; (3) extra cost and latency within the bounds written that day. Both implementations stay in the repo; the README says which powers the demo and why.

**Test-set discipline.** Coral Pay is never read by code before 14 Oct; the seal must hold across every new entry point (API routes, uploads, static serving). It runs once per configuration; nothing is tuned afterwards. Work after 14 Oct on UI, adapters or persistence uses development data; any material pipeline change is versioned and disclosed, and sealed scores belong to the evaluated configuration only. PDF/DOCX support is not validated by the Markdown-only sealed run.

**Acceptance examples (21 Oct):**

- A user creates a deal, selects readable documents and runs a review without editing JSON or using a terminal.
- Findings show the conflicting material terms and traceable evidence.
- A missing annex leaves the affected conclusion incomplete.
- A partial fix leaves the remaining issue open; a fully supported fix closes the relevant issues.
- Changing evidence marks the old result out of date until rerun.
- The saved record reopens and exports for Delivery, CS and Support, including unresolved items.

**Honest framing.** Results are performance on a small synthetic set. They show design and technical judgement, not an effect on real deals. Publish what still fails, with the reason.

## Measuring your learning

Score yourself on twelve skills on 25 Sep, 5 Oct, 16 Oct and 21 Oct (the two new skills start from 1 Oct). Reviewers score the starred skills.

**Scale:** 1 = never done it · 2 = with heavy help · 3 = with a reference · 4 = alone and can explain · 5 = can teach it

| Skill | 25 Sep | 5 Oct | 16 Oct | 21 Oct |
| --- | --- | --- | --- | --- |
| Terminal, Python and Git | 2 |  |  |  |
| Calling a model from code; tokens and cost | 2 |  |  |  |
| Prompt design and structured outputs ★ | 1 |  |  |  |
| Designing an eval set and ground truth ★ | 1 |  |  |  |
| Measuring honestly ★ | 1 |  |  |  |
| Working with data: JSON, SQLite | 1 |  |  |  |
| Tool use and agents; rules vs agent ★ | 1 |  |  |  |
| Human-in-the-loop and resolution design | 1 |  |  |  |
| Directing Claude Code while staying in control | 1 |  |  |  |
| Explaining the architecture under pressure ★ | 1 |  |  |  |
| Frontend/backend separation (new) | — |  |  |  |
| Product framing for a business audience (new) | — |  |  |  |

| Checkpoint | Date | Reviewer | Tests |
| --- | --- | --- | --- |
| 1 | Fri 2 Oct | CS, implementation or pre-sales leader | The pivot on paper: does checking the fix beat a spreadsheet? |
| 2 | Fri 16 Oct | Engineer or solutions architect who has shipped LLM features | "Why an agent?", "How do you know the judge is right?", "Why can't a reviewer just mark it resolved?", "What happens at 500 deals?" Record with permission. |

## Ground rules

- **Scope is set by this plan (v3).** New ideas go on the Later list. No design review rounds once a day's design is committed.
- **Four-hour ceiling,** weekends and 6–11 Oct included.
- **Extraction is frozen.** Changes only through regression with logged hashes.
- **Freeze for the sealed evaluation covers the evaluated pipeline only** (extraction, filter, consolidation, rules, agent): candidate freeze at close of 12 Oct; integration fixes on development data on 13 Oct, rechecked by regression and downstream checks; final evaluated configuration recorded before unsealing. If it isn't sound, unsealing waits.
- **Seal across every entry point.** Deny rules, `ALLOWED_DEALS`, path containment. Serve only frontend build assets, never the repo or `data/`. No repository-wide scans. Do not connect or upload the repo to any UI builder before 14 Oct. Never seed Coral Pay in the UI.
- **No public model-backed endpoint.** Local app for demo and recording.
- **Secrets.** Key never in chat, committed files, browser code, exports or shared Terminal output. Set with `read -s`.
- **Confidentiality.** Nothing from any employer. Everything is fictional.
- **No regulatory claims.** Launch rules are the customer's own internal policy.
- **Spend.** $19.79 prepaid credit on 30 Sep. Log cost per run; check on 13 Oct and top up before 14 Oct.
- **Honest credit.** Built with Claude Code as build partner; Claude drafted the fictional documents, fixtures and resolution scenarios from your brief and rules; frontend built by Claude Code under your direction. Then show you can explain every decision.

## Setup reference

**Start of every build day (just do):**

```
cd ~/Desktop/"From Promise to Delivery"/promise-to-delivery
source .venv/bin/activate
read -s ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY
[ -n "$ANTHROPIC_API_KEY" ] && echo "key set" || echo "key missing"
```

The check reports only whether the key is set; it prints no part of it.

**Claude Code window (just do):**

```
unset ANTHROPIC_API_KEY
claude
```

Check `/status` shows your subscription, not an API key.

**Once, before 1 Oct (just do):** `node -v`. If "command not found": `brew install node`.

**Local app launch:** added to `WHERE_I_STOPPED.md` once the scaffold exists.

**Regression after any extraction change:**

```
python extract.py harbour_bank
python regression.py results/extract_harbour_bank_<new timestamp>.json
```

**End of every build day:**

```
git status
git add <files you changed>
git diff --cached --stat
git commit -m "<date>: what you did"
git push
```

Never commit a key, the SQLite database, uploaded documents, `node_modules` or the frontend build.

**Common symptoms (recognise):**

| You see | It means | Do this |
| --- | --- | --- |
| `command not found` after installing | Not on PATH | Look for a PATH line in the installer output |
| `No module named ...` | venv not active, or new dependency not installed | `source .venv/bin/activate`, then `pip install -r requirements.txt` |
| `authentication_error` | Key missing, mistyped or revoked | Run the key check; if "key set", create a new key in the Console and set it again |
| Browser shows "connection refused" | Local server not running, or wrong port | Check the server Terminal window for errors |
| `Unable to create index.lock` | Git lock left behind | Close other git users, then `rm .git/index.lock` |
| "file changed on disk" in Claude Code | Something else edited the file | `git diff --stat` |

## After 22 October

| When | What |
| --- | --- |
| Week of 19 Oct | Publish *What We Promised* with the repo, demo and results. |
| From 21 Oct | Validation conversations with 5–6 implementation, professional-services and pre-sales leaders: would you use this before signing, who could require it, is checking the fix worth more than a spreadsheet? |
| Next build, if it holds | Post-signature tracking against the approved baseline. |

**Later, not in this build:** brand name and domain research · Google Drive selected-file connector, then CRM connectors (HubSpot as an audience example, not a promise) · generated resolution suggestions · OCR · per-role dashboards · margin modelling · a customer-facing view · Kickoff Sparring Partner · Elva promises reported only in customer emails · regression warning for incomplete documents.

## What changed from v2

| Area | v2.6 | v3.0 (30 Sep) |
| --- | --- | --- |
| Product | Pre-signature review; decision screen with five actions | Local deal workspace: Review deal, register, three resolution routes, **recheck with issue-level closure**, saved handoff and export |
| Audience | Implicitly technical reviewers | Business and leadership first; technical evidence kept behind the interface |
| Scope claim | Not stated | "Demonstrated on fictional deals with a complete capability catalogue"; other uploads unvalidated, authorisation needs evidence |
| Input | Fixed deal folders | Upload of text/Markdown, then PDF, DOCX, Excel and PowerPoint, into user deals stored outside `data/`; seven existing doc types in the UI |
| Recheck | — | Extraction cached under a full key (content, doc type, context, extraction configuration); unchanged-input rechecks separated from fresh model runs |
| Frontend | Streamlit decision screen; Lovable demo reading exported JSON | One React frontend built by Claude Code, thin Python API, run locally; Lovable dropped for this build |
| Schedule | Days 8–12 on 12–16 Oct | 50 h committed including learning, logging and the pulled-forward contingency, 56 h maximum with 16 and 22 Oct, 1 – 22 Oct; contingency pulled forward to 1–2 Oct plus 2 h on 16 Oct; overruns move dates, not the ceiling; completion 21 Oct, hard stop 22 Oct |
| Freeze | Extraction only | Plus candidate backend freeze 12 Oct, integration fixes 13 Oct, final evaluated configuration recorded before unsealing; unsealing waits if unsound |
| Checkpoint 1 | Walk through extraction scores | Paper test of the pivot |
| Metrics | Extraction and conflicts | Added resolution correctness, repeatability, downstream checks, explicit cost/latency bounds in the decision rule |
| Kept unchanged | — | Days 1–7, extraction v1 and hashes, regression, rules vs agent with three dev runs, the sealed single run, the learning record |

**v3.1 (30 Sep, same day):** freeze timing corrected (candidate freeze, 13 Oct fixes, delay unsealing if unsound); cache key extended beyond content hash; fresh agent runs separated from cached rechecks; contingency made explicit (pulled forward to 1–2 Oct); PDF/DOCX and both exports are agreed scope, date moves instead of cutting; Day 1 date corrected to Fri 25 Sep; scorecard twelve skills; key check prints no part of the key.

**v3.2 (30 Sep, same day):** Excel and PowerPoint upload added as agreed scope with a defined boundary (+4 h on Tue 20 Oct); completion moved to Wed 21 Oct; hard stop Thu 22 Oct, after which unfinished items are reported, not rescheduled.

**v3.3 (30 Sep, same day):** hours corrected (50 committed, 56 maximum; about 30 of actual build); recheck after a fix defined as partial re-extraction plus reassessment of every related issue, separate from unchanged-input reruns; agent-found issues stay open under a rules recheck until closure criteria are met.

**v3.4 (30 Sep, after the repo audit):** freeze narrowed to the evaluated pipeline; `security_questionnaire` and pricing-note evidence decisions scheduled for 4 Oct; cut order fixed for the hard stop; actual hours logged from 1 Oct with a formal re-plan at the close of 5 Oct, after Claude Code's estimate of 43–52 build hours against about 30.

Earlier version history (v2.1–v2.6) is preserved in `DECISIONS.md` and the v2 plan.
