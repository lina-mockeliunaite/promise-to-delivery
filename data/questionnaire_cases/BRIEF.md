# Questionnaire fixture deal (development only)

Created 10 Oct 2026, before the 12 Oct candidate freeze. Fictional (Kestrel Remit, Singapore). One document: a vendor security questionnaire answered by Elva.

**Why it exists.** On 3 Oct `security_questionnaire` became an extracted document type, with no development example. Without this fixture the sealed run would be the first time extraction ever read one. This is one development run to catch format problems (question/answer tables, bare "Yes." answers) before 14 Oct.

**Scope.** Extraction only: `python extract.py questionnaire_cases`, then `python evaluate.py <run file>`. In `ALLOWED_DEALS` only — deliberately **not** in `LEDGER_DEALS` or `UI_DEALS`, so the ledger, the demo, the hard-case labels and their hash are untouched. Written from `data/hard_cases/BRIEF.md`, DECISIONS and the catalogue only; nothing from the sealed deal.

**Labels.** Written by Claude at Lina's request (10 Oct), who also wrote the document — so the labels are not independent of the design. Treat the result as a smoke test of the document type, not as evidence of accuracy.

| Row | Case | Label |
|---|---|---|
| 1 | Promise after a bare "Yes." | firm; quote starts "Elva supports…" |
| 2 | Plain security promise | firm |
| 3 | Technical promise | firm |
| 4 | Data residency | firm |
| 5 | Expectation, not a promise ("working towards… expects") | conditional |
| 6 | Fact plus promise in one sentence | firm (whole sentence) |
| 7 | Capability promise inside a security form (Arbitrum: absolute limit in SG) | firm |
| 8 | Customer's own obligation | excluded |
| 9 | Pointer only | excluded |
| 10 | Bare "Yes." — the promise is in the question | not labelled: a known limitation; if extracted it shows as a false positive and is recorded, not fixed |
| 11 | Audit history (same promise as KR-02 in hard cases) | firm |

Expected: 8 labelled statements, 7 firm. Rows 1–4 and 6 have no catalogue capability, so in a full review they would reach *Needs evidence*.
