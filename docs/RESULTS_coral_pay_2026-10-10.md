# Sealed evaluation results — Coral Pay (run once, 10 Oct 2026)

*Run by Lina on her Mac after verifying the seal (12/12 files OK). Configuration as recorded in DECISIONS.md before the run. Nothing in the evaluated pipeline was changed afterwards. Files: `results/sealed_coral_pay_20261010T061256Z.json`, `results/extract_coral_pay_20261010T061136Z.json`, `results/eval_extract_coral_pay_20261010T061136Z_t0.8_L08dce2d9.json`. Total model cost $0.25. Analysis by Claude; baseline scored by hand against the commitment labels.*

## Headline, plainly

**On finding the problems, the one-call baseline beat the structured pipeline on this deal.** The deal had three planted issues: Solana screening, which isn't offered in AU; Azure hosting, which isn't a supported cloud; and two training sessions that were promised in the proposal but dropped from the SOW.

| | Found the 3 planted issues | False flags on the 4 clean commitments | Verifiable |
| --- | --- | --- | --- |
| **Baseline** (one model call, all documents and the catalogue) | **3 of 3**, with correct reasoning | 0 | 12 of 13 quotes verbatim (1 elided with "…"). One run, no structure, no recheck |
| **Rules** (extraction → grouping → rules) | **1 of 3 exactly** (Solana, including the absolute limit). The other 2 reached review only as *Needs evidence* | **2** | Every finding cites a quote, catalogue path or pricing-note line |
| **Rules + agent v2** | No change: the agent added nothing that passed validation | — | — |

## Extraction (frozen v1) — met its targets

- Recall 14/14; firm recall 14/14 (target ≥ 90%). Language 14/14 correct (target ≥ 85%). All quotes valid.
- Precision 14/20 = 70%. After the housekeeping filter it's 14/19 = 74%, against a target of ≥ 85%. **Missed the target.**
  - The filter caught 1 of the 3 sales-process lines.
  - It kept "I'll bring our implementation lead to the next call … path to go-live", because "go-live" counts as a material term.
  - Other false positives: a penetration-test summary "available on request", the weekly status meeting, and the contract's term clause.

## Rules — why they missed, case by case

| Commitment | Label | Rules | Cause |
| --- | --- | --- | --- |
| Solana wallet screening | Approval issue, absolute limit | **Same** ✓ | — |
| Azure production hosting | Approval issue, absolute limit | *Needs evidence* | The term parser didn't map "deploy … on Microsoft Azure" to CAP-019, so the promise went unclassified. The catalogue's `supported_clouds` was never checked. |
| Training sessions | Contract gap (service-menu item) | *Needs evidence* | Services aren't catalogue capabilities, so terms were incomplete. The contract was correctly searched and found absent, but an incomplete promise can't raise a confident gap (by design). |
| 25,000 sanctions screenings/day (clean) | No issue | **False flag**: contract coverage uncertain | "Payer and beneficiary names" wasn't recognised as the volume unit, so presence was uncertain. |
| 15 Jan go-live, conditional (clean) | No issue | **False flag**: contract gap | The unfiltered sales line ("…path to go-live") grouped with the conditional promise and made the group firm. |

Every miss traces to the same root: **the vocabulary, meaning the term parser and filter written on development data, doesn't generalise to unseen wording.** This is the paraphrase limitation recorded on 3 Oct (0 of 5 on the practice set), now confirmed on the sealed deal. Grouping matched 3 of 7 commitments exactly, and 10 of 14 statements.

## Agent v2 — decision rule: rules power the demo

- Condition 1, adds a material issue: **no**.
- Condition 2, no unsupported or uncited verdict: **no**. Three verdicts were rejected and one was uncited.
- Condition 3, within the cost and time bounds: **no**. It took 80 s against a 60 s bound and cost $0.128 against a $0.10 bound, on 8 escalated commitments.
- **Right in substance, again:** it judged Azure as not approved (CAP-019) and training as standard-authorised. Both match the labels and both are things the rules missed. Neither passed validation, because the validator can't express a cloud or a service-menu item. That's an interface limit, the same pattern as v1. Kept out under the pre-registered rule, as written.

## What this means (for the README and Checkpoint 2)

1. **Detection:** on this deal, a single well-prompted model call found more than the rules. Claiming otherwise would be false.
2. **What the pipeline gives that the baseline doesn't:**
   - findings tied to verifiable evidence;
   - a state that changes only on evidence;
   - recheck after a fix, with partial fixes kept open;
   - decisions that never alter findings;
   - repeatable verdicts;
   - a saved handoff.
   The baseline is one answer, run once. There's no way to track it, close it or prove it next week.
3. **The honest product conclusion:** the strongest design is likely **model-led detection with rule-checked evidence**. The model proposes findings; code verifies each one against quotes and the catalogue; the workflow manages them. That's the agent's direction, minus its brittle validator. It's a next build, not a claim about this one.
4. **The sealed run did its job:** it exposed overfitting to development data that development scores (100% rules on Harbour Bank) hid.
