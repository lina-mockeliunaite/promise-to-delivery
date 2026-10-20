# Dealshape

**See the deal as it was actually promised.**

When a deal is signed, Delivery inherits the contract. But the customer remembers the proposal, the RFP answers and the calls. Dealshape reads a deal's paper trail and shows the shape of the deal: what we're delivering, which commitments need attention and why, what people have agreed about them, and which documents were checked.

It flags two kinds of mismatch:
- **promises stronger than the company authorised;**
- **promises that never made it into the contract.**

It is a **visibility tool, not a workflow tool.** It has no tasks, assignees, approvals or risk scores.

*Demonstrated on fictional deals with a complete capability catalogue.* It is a local prototype, built in October 2026 to learn how to design, build and evaluate an AI system end to end.

![Alder Bank deal page](docs/screens/2026-10-20/alder_deal.png)

## What it shows (Alder Bank, the fictional demo deal)

| Commitment | What the customer was told | What the paperwork says |
| --- | --- | --- |
| Coaching-scam detection live at launch | Promised in the RFP response | The contract has no matching wording, and the catalogue needs a named approval that nobody recorded |
| Hosting on Microsoft Azure | Promised in the RFP response | The contract says Amazon Web Services in the Sydney region, and Azure isn't offered |
| 750,000 payments a day by the end of year one | Promised in the proposal | No matching wording in the contract, and no approval found |

One commitment can carry several gaps, and they close independently. An approval does not put a promise into the contract.

## How it works

1. **Read.** The deal's documents (Markdown, text, PDF, Word, Excel, PowerPoint) are grouped by deal stage. **The stage comes from the documents:** a signed contract marks the deal Signed. Nobody sets the stage by hand.
2. **Detect (the model).** One model call reads the paper trail with the capability catalogue. It proposes each gap with the promise quoted word for word, the catalogue entry, and the contract clause or the missing wording.
3. **Verify (code).** Every quote and citation is checked mechanically. A finding that fails a check is kept on record and never shown. On screen, **"What we found" shows only what code verified.** The model's own explanation is labelled "AI-written summary".
4. **Recheck (code).** Add an updated document, such as a named exception or an aligned SOW, and the check runs again. A gap closes only when the new paperwork shows it no longer holds, and the screen says which document closed it. A failed check stores nothing.
5. **Notes are a person's word, not proof.** A note can keep a commitment open with context, or mark it "Addressed by note". Either way it looks different from "Closed by documents", stays in the record, and reopens if the documents change.
6. **Hand over.** Sales and Delivery each write a note, the signed contract is uploaded, and completing the handover locks a read-only record. The record states honestly what is still open.

## Where the AI comes in, and where it doesn't

The model does the reading. It maps sales wording to the catalogue and the contract, which hand-written rules could not do on unseen deals (see the results below). Code does the deciding: a finding exists only if its quotes and citations check out, and it closes only when code can show the claim no longer holds. **The model never closes anything.** What code cannot check is the model's reading of a paraphrase. That is what the sealed runs measure.

**Alder Bank is a demo deal. It was not part of either sealed evaluation.** The published results below describe the versions that were tested.

## Results, version 1 (rules decide): first sealed deal, 10 Oct 2026

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

## Results, version 2 (model detects, code verifies): second sealed deal, 10 Oct 2026

After the Coral Pay result, detection was rebuilt: one model call proposes each finding with exact quotes and catalogue or contract citations, and code rejects any finding whose quotes or citations do not check out. Tuned on the four development deals (including Coral Pay, now seen), frozen and committed, then run once on **Atlas Remit**, a deal written and sealed by an isolated agent that never saw v2's code. Full analysis: [`docs/RESULTS_atlas_remit_v2_2026-10-10.md`](docs/RESULTS_atlas_remit_v2_2026-10-10.md).

| | Pre-registered target | v2 | One-call baseline |
| --- | --- | --- | --- |
| Labelled issues found | ≥ 80% | **8 of 8** | 8 of 8 |
| False flags | ≤ 1 | **0** | 1 (a real timing point outside the labels) |
| Reply complete and parsed | required | **yes** | truncated at the token limit |
| Every finding mechanically checked | — | **yes** | no (free text, scored by hand) |

**Read it straight:** v2 did not out-detect a single prompt; it matched it, and its findings are verifiable and structured enough for the app to recheck and close. One deal and eight targets is a small sample.

## Known limitations (stated plainly)

- **Paraphrase and unseen wording.** The v1 rules found 1 of 3 planted issues on the first sealed deal. v2 found 8 of 8 on the second, but one deal with 8 targets is a small sample.
- **The results describe detection v2 as tested** (`v2_version` 2, 10 Oct). Any later change to the detection prompt or verifier raises the version, and those results would then no longer describe the running version.
- **Wording, not legal meaning.** "No matching wording found" means exactly that. It is not a legal reading of the contract.
- **A recheck does not re-read unchanged documents** when extraction settings change. Each review records which settings every document was read under.
- **Adding a capability to the catalogue marks every deal "Review out of date"** until it is checked again. That is safe, but noisy on many deals.
- **Signed paperwork.** A signed contract marks the deal Signed; its wording is not compared with the drafts.
- **Formats.** PDF text layer only (no OCR); Excel by stored values only; PowerPoint slide text only.
- **Synthetic data.** Every deal is fictional and was written for this build.
- **Not in this build:** live Drive or CRM connectors (documents carry a Drive link field), user accounts, post-signature tracking, legal advice.

## How it was tested

- **Sealed evaluation.** Two deals were written and sealed before the code that tested them, and each configuration ran once. The labels, documents and seals are never edited, and nothing was tuned on them.
- **Automated tests:** 677 Python tests and 57 front-end tests. They include regression checks on extraction, five resolution scenarios, "a failed check stores nothing", and "no internal key reaches any screen".
- **Reviewers:** a Head of Growth (6 Oct), a COO (15 Oct) and a Delivery lead (16 Oct), plus one outside UI review. Two reviewers in different roles asked for visibility, not workflow, and the product was rebuilt around that. **Not yet done: an unaided test** with someone who has never seen the product.

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

The demo opens on the deals list with no API key. Reading a new or changed contract or customer document needs `ANTHROPIC_API_KEY` in the server's terminal. The browser never sees it.

## Where to look

| File | What it is |
| --- | --- |
| `DECISIONS.md` | Every design choice, the alternative rejected, and why |
| `LEARNING_LOG.md` | What I learned, got stuck on and got wrong |
| `docs/RESULTS_*.md` | The two sealed runs in full |
| `docs/DEMO_SCRIPT_2026-10-20_alder.md` | The four-minute demo |
| `docs/` | Briefs, the integrity inspection, specs, design references |

## Credits and honesty

All companies, people, products and deal terms are fictional. TRM Labs, Chainalysis, BioCatch, Microsoft Azure and Amazon Web Services are real names, used in the fictional catalogue and deals for realism only. No partnership is claimed.

Built with Claude Code as build partner. Claude drafted the fictional documents, fixtures and briefs from my direction, and the screen designs started in Google Stitch. The product decisions, labels and evaluation design are mine.
