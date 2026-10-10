# Sealed v2 run: Atlas Remit, 10 Oct 2026

Run once at 08:44 UTC (`results/sealed_v2_atlas_remit_20261010T084453Z.json`), after v2 was frozen and committed (`d539f5e`). The deal was written and sealed by an isolated agent that never saw v2's code; nobody building v2 read it before the run. Seal verified 12/12. Total cost $0.248 (v2 $0.145, baseline $0.103).

## Against the pre-registered criteria

| Criterion (fixed 15:30, confirmed 16:45) | Result |
| --- | --- |
| ≥ 80% of labelled (commitment, issue) targets found | **8 of 8 (100%)**: pass |
| ≤ 1 false flag | **0**: pass |
| No parse error or truncated reply | **end_turn, parsed**: pass |

7 findings accepted, 0 rejected, 0 duplicates. Every planted case (P1–P5) found; none of the 7 commitments that must not be flagged was flagged, including the approved Polygon exception (AC07) and the exploratory anomaly-detection remark (AC11).

| Planted case | v2 finding(s) |
| --- | --- |
| P1 Tron real-time screening (network not in catalogue) | absolute limit + contract gap |
| P2 Behavioural-signals connector, "approved in principle", approver not recorded | approval required + contract gap |
| P3 STR drafting promised, never in SOW/contract | contract gap |
| P4 Sanctions 60,000/day (proposal) vs 30,000/day (SOW) | conflicting terms (scores contradiction + expectation gap) |
| P5 Ledger 30,000/day above the 25,000 limit, carried into SOW | over limit |

## The one-call baseline on the same deal (scored by hand)

Same task and model as on Coral Pay. It also found **all 8 targets**. It raised **1 finding outside the labels**: Polygon real-time was promised in the proposal (16 Oct) two days *before* the named exception was approved (18 Oct). The label treats AC07 as clean because the exception exists before the contract; the baseline's point is a real timing observation, but under the frozen labels it counts as a false flag. Its reply was **cut off at the token limit** (`max_tokens`) in the middle of the last item; nothing was lost that affected scoring, but under the criteria applied to v2 that would be a failed run.

## What this does and does not show

- **v2 did not out-detect a single prompt.** Both found 8/8. The case for v2 is not recall: it is that every v2 finding is structured, quote-exact and mechanically checked against the catalogue and the contract chain, so it can drive recheck and closure in the app; the baseline is free text that a person must score.
- **Small sample.** One deal, 8 targets, 7 clean commitments. 8/8 is consistent with a true rate well below 100% (a 95% lower bound is about 63%). It is evidence that v2 generalises beyond the deals it was tuned on, not a measured accuracy.
- **Same fictional world.** The test deal uses the same catalogue and vendor, and its writer used the development deals for format. It is unseen wording, not a new domain.
- **AC02 depends on a scoring rule set before the run.** A verified conflict is scored as contradiction *and* expectation gap (DECISIONS 15:30). Without that rule the score would be 7 of 8 (88%), still a pass.
- **The verifier did not earn the AC07 result.** The approved exception is recorded as "Approver: Gabriel Tan". The verifier's approval guard recognises "approved by <Name>" only, so had the model reported AC07 the verifier would have accepted a false flag. The model got it right; the guard is narrower than real note wording. Recorded as a limitation; not changed after the run.
- **P2 shows the guard working as intended:** "approved in principle… Approver: not recorded" is not an approval, and the finding was accepted.

Nothing in v2 was changed in response to this run.
