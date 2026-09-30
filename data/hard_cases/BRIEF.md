# Hard-case fixture deal: Kestrel Remit (development only)

Created Day 7, 30 September 2026. Fictional. Singapore market. Used only for development: to break extraction on purpose and, from Day 9, to give the rules their first development cases for two paths.

Designed from the general labelling rules (DESIGN.md, DECISIONS.md) and `data/catalogue.json` only. Not modelled on the sealed test deal: no Australian market, no Solana, no training services.

| Case | What it tests | Where | Expected |
|---|---|---|---|
| H1 | Hedge inside a firm-sounding sentence | KR-02 | conditional |
| H2 | "On our roadmap" | KR-01 | conditional, never firm |
| H3 | Future date alone | KR-02 | firm |
| H4 | Number in words; same promise in digits in the SOW | KR-02, KR-03 | firm (Day 8: merge 30,000 and thirty thousand) |
| H5 | Pointer sentence with no material terms | KR-03 | excluded |
| H6 | Sales-process step | KR-01 | excluded |
| H7 | Customer's own obligation | KR-01 | excluded |
| H8 | Promise split across two call turns | KR-01 | firm, speaker Ravi Menon |
| H9 | Absolute limit: Arbitrum is not in the SG catalogue | KR-01, KR-02 | firm; Day 9: no_approval_evidence, reason absolute_limit |
| H10 | Authorised but absent: CAP-014 in proposal, missing from SOW | KR-02 | firm; Day 9: standard_authorised, expectation_gap |
| H11 | Prompt injection next to a real promise | KR-02 | injection ignored; K07 still extracted |
| H12 | Contract with only pointers and boilerplate | KR-04 | 0 statements |

KR-05 (pricing/services note) is reference-only and must never be extracted.
