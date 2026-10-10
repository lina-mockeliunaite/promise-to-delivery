# Promise to Delivery

**Hand over the deal as it was promised.**

When a deal is signed, Delivery inherits the contract — but the customer remembers the proposal, the RFP answers and the calls. Promise to Delivery reads a deal's paper trail and builds the handoff record: each promise in its exact words and source, flagged where the customer was told more than the contract includes, or more than the company approved. People fix those gaps with evidence, and a recheck shows which ones actually closed.

*Demonstrated on fictional deals with a complete capability catalogue.* A local prototype built in October 2026 to learn how to design, build and evaluate an AI system end to end.

![Deal overview](docs/screens/2026-10-09/1_overview_fresh.png)

## What it catches

| | Example (Harbour Bank, fictional) |
| --- | --- |
| **A promise stronger than the company authorised** | The proposal promises real-time Polygon wallet screening from launch; the catalogue says it is in beta and needs named approval; the pricing note records none. |
| **A promise that disappeared from the contract without being withdrawn** | The contract, through the SOW it incorporates, commits to hourly batch screening. Nothing withdraws the real-time promise. |
| **Terms that conflict across documents** | Real-time in the proposal, batch in Annex A. |

One commitment can carry several of these at once, and they close independently: an approval does not put a promise into the contract.

## How it works

1. **Read.** Upload the deal's documents (Markdown, text, PDF, Word, Excel, PowerPoint), each with its type confirmed by a person.
2. **Detect (the model).** One call reads the whole paper trail with the capability catalogue and proposes findings: a promise that needs an approval nobody recorded, one the catalogue does not offer at all, one above a catalogue limit, one missing from the contract, or one the contract states differently. Each finding cites the promise word for word, the catalogue entry, and the contract clause or the missing words.
3. **Verify (code).** Every citation is checked mechanically: the quote is in the named document, the catalogue entry exists and says what the finding claims, the missing words really are absent from the contract and SOW. A finding that fails any check is kept on record and never shown.
4. **Fix and recheck (code).** Attach evidence inside a finding — a named exception, an aligned SOW, a withdrawn promise. The code re-checks the claim the finding was raised on against the new documents; it closes only when that claim no longer holds, and the reason says why. The model never closes a finding. *Okay to proceed* and *Must fix before signing* are recorded beside a finding and never change it.
5. **Hand over.** A saved, versioned handoff for Delivery, Customer Success and Support, with CSV and readable exports; unresolved items stay visible.

## Where the AI comes in — and where it doesn't

The model does the reading: it maps sales wording ("instant risk check", "thirty thousand a day") to the catalogue and the contract, which hand-written rules could not do on unseen deals (v1 found 1 of 3 planted issues on the first sealed deal). Code does the deciding: a finding exists only if its quotes and citations check out, and it closes only when the code can show the claim no longer holds. What code cannot check is the model's reading of a paraphrase and whether a statement is firm; that is what the sealed runs measure. The first version (rules decide, model extracts) is kept in the repository with its measured results.

## Results (sealed deal, run once on 10 Oct 2026)

Coral Pay was written before the build and sealed: no code read it until a single run per configuration. Full analysis: [`docs/RESULTS_coral_pay_2026-10-10.md`](docs/RESULTS_coral_pay_2026-10-10.md).

| | Target | Result |
| --- | --- | --- |
| Extraction recall, firm commitments | ≥ 90% | **14/14** |
| Language (exploratory / conditional / firm) | ≥ 85% | **14/14** |
| Quote validity | 100% | **100%** |
| Precision after the housekeeping filter | ≥ 85% | **74%: missed** |
| Planted issues found exactly by the rules | 3 of 3 | **1 of 3** (the other 2 reached review as *Needs evidence*) |
| False flags on clean commitments | 0 | **2 of 4** |
| Agent v2 earns a place (pre-registered rule) | — | **No**: right in substance on 2 cases, unsupported in form, over the time and cost bounds |
| Resolution scenarios (development deal, real model) | 5 of 5 | **5 of 5** |

**The finding that matters:** a single model call over all the documents found **all 3** planted issues with no false flags; the rules found 1. The rules' vocabulary was tuned on development wording and did not generalise. What the pipeline adds is not better detection but evidence-bound findings, recheck, decisions that never change findings, and a handoff record. The next design is model-led detection with rule-checked evidence.

## Version 2 (model detects, code verifies): second sealed deal, 10 Oct 2026

After the Coral Pay result, detection was rebuilt: one model call proposes each finding with exact quotes and catalogue or contract citations, and code rejects any finding whose quotes or citations do not check out. Tuned on the four development deals (including Coral Pay, now seen), frozen and committed, then run once on **Atlas Remit**, a deal written and sealed by an isolated agent that never saw v2's code. Full analysis: [`docs/RESULTS_atlas_remit_v2_2026-10-10.md`](docs/RESULTS_atlas_remit_v2_2026-10-10.md).

| | Pre-registered target | v2 | One-call baseline |
| --- | --- | --- | --- |
| Labelled issues found | ≥ 80% | **8 of 8** | 8 of 8 |
| False flags | ≤ 1 | **0** | 1 (a real timing point outside the labels) |
| Reply complete and parsed | required | **yes** | truncated at the token limit |
| Every finding mechanically checked | — | **yes** | no (free text, scored by hand) |

**Read it straight:** v2 did not out-detect a single prompt; it matched it, and its findings are verifiable and structured enough for the app to recheck and close. One deal and eight targets is a small sample.

## Known limitations (stated plainly)

- **Paraphrase and unseen wording.** The rules found 0 of 5 reworded approval issues in a practice set, and 1 of 3 planted issues on the sealed deal; the misses reached review as *Needs evidence*, not as findings.
- **A recheck does not re-read unchanged documents** when extraction settings change: an unchanged version keeps the extraction it already had. Each review records which settings every document was read under and says so when they differ.
- **Re-confirmation is deal-wide.** Any new evidence asks for every earlier decision to be re-confirmed. Safe, but noisy on a large deal; narrowing it needs dependency tracking.
- **Synthetic data, small set.** Results describe performance on fictional deals written for this build, not generalisation.
- **Formats.** PDF text layer only (no OCR); Excel by stored values only; PowerPoint slide text only (not speaker notes). Office formats are checked on development documents only.
- **Not in this build:** post-signature tracking, live CRM or Drive connectors, AI-suggested business impact, legal advice.

## How it was tested

- A labelled development deal, hard cases written to break extraction, and a practice set for rules vs agent.
- A sealed test deal (Coral Pay) that no code read before one final run per configuration.
- Regression checks on extraction; five resolution scenarios; 568 automated tests; a seal on every entry point that keeps the test deal out of the app.
- One real reviewer session (Head of Growth). It showed the idea landed and the first interface did not; the screens were redesigned from it.

## Run it locally

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm ci && cd ..
python reset_demo.py
python -m uvicorn api:app --host 127.0.0.1 --port 8000
# second terminal
cd frontend && npm run dev     # open http://127.0.0.1:5173
```

The demo opens on Harbour Bank with no API key. Reading a new or changed document needs `ANTHROPIC_API_KEY` in the server's terminal; the browser never sees it.

## Where to look

| File | What it is |
| --- | --- |
| `DESIGN.md` | Users, the three-attribute model, the pipeline |
| `DECISIONS.md` | Every design choice, the alternative rejected, and why |
| `LEARNING_LOG.md` | What I learned, got stuck on and got wrong |
| `docs/` | Briefs, the integrity inspection, specs, screens |

## Credits and honesty

All companies, people, products and deal terms are fictional. TRM Labs, Chainalysis and BioCatch are real providers named in the catalogue for realism only; Elva's integrations with them are fictional and no partnership is claimed. Built with Claude Code as build partner; Claude drafted the fictional documents, fixtures and briefs from my direction. The product decisions, labels and evaluation design are mine.
