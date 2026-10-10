# Atlas Remit deal brief — Atlas Direct (SEALED v2 test deal)

**Purpose:** Sealed second test deal for From Promise to Delivery. Written on 10 October 2026 by an isolated agent that never saw the system under test, the Coral Pay deal or any Python code. Inputs used: `data/catalogue.json` and the Harbour Bank / hard-case files for format and labelling conventions only. Do not open, tune against or edit this folder before the evaluation run; the seal is `data/atlas_remit.sha256`.

All companies, people, tokens, dates and terms are fictional. No document states what a regulator requires.

## The deal

**Elva** (fictional Singapore AML platform) is selling to **Atlas Remit Pte. Ltd.**, a fictional Singapore major payment institution sending SGD remittances to Indonesia and the Philippines. Atlas is launching **Atlas Direct** on **1 February 2027**: recipients take payouts in **NUSD** straight into their own wallets. Most payouts run on Polygon, larger ones on Ethereum, and Indonesian partners are pushing for Tron. Atlas brings its own blockchain-analytics provider licence and credentials; Elva supplies the connector and workflow. Market: Singapore (SG) throughout.

## Documents

| ID | Date | doc_type | Document | Role in the trail |
|---|---|---|---|---|
| AR-01 | 1 Oct 2026 | call_transcript | Discovery call | Context, reliance, clean Ethereum promise, exploratory Tron and anomaly-detection remarks |
| AR-02 | 7 Oct 2026 | call_transcript | Solution deep-dive | Conditional Polygon real-time, ledger volume in words, STR drafting, hedged behavioural connector, customer key-loading obligation |
| AR-03 | 12 Oct 2026 | security_questionnaire | Security and deployment questionnaire | Two firm answers (hosting, case audit history); the rest are pointers to appendices |
| AR-04 | 16 Oct 2026 | proposal | Proposal | Main firm promises, including all planted overcommitments |
| AR-05 | 19 Oct 2026 | pricing_services_note | Internal deal-desk note | Approval evidence and priced services; reference only, never extracted |
| AR-06 | 26 Oct 2026 | draft_sow | Draft SOW No. 1 with Annex 1 | Contract-chain terms |
| AR-07 | 29 Oct 2026 | draft_contract | Draft master agreement | Incorporates SOW No. 1 and Annex 1 by reference; pointers and boilerplate only (0 statements) |
| AR-08 | 2 Nov 2026 | customer_email | Customer email | Reliance on the missing promises; no Elva statements |

## Planted cases and expected results

| # | Case | Commitment | Expected authorisation | Contract | Expected issues |
|---|---|---|---|---|---|
| P1 | Absolute limit: real-time wallet screening on Tron (network not in catalogue) | AC01 | no_approval_evidence, reason absolute_limit | absent | overcommitment, expectation_gap |
| P2 | Behavioural-signals connector (CAP-027 beta): exception "approved in principle", approver not recorded | AC03 | no_approval_evidence | absent | overcommitment, expectation_gap |
| P3 | STR drafting (CAP-015, standard) promised twice, never in SOW/contract, never withdrawn | AC04 | standard_authorised | absent | expectation_gap |
| P4 | Sanctions screening volume: proposal 60,000/day vs SOW 30,000/day | AC02 (AC08 is the SOW side, clean) | standard_authorised | absent | expectation_gap, contradiction |
| P5 | Ledger volume 30,000/day above CAP-023 SG limit 25,000, carried into SOW | AC05 | no_approval_evidence | included_in_draft_contract | overcommitment |

## Must NOT be flagged

| Case | Commitment | Expected |
|---|---|---|
| Approved exception: Polygon real-time (CAP-021 beta), named approver recorded in AR-05 | AC07 | exception_approved, included, no issues |
| Clean: Ethereum real-time screening | AC06 | standard_authorised, included, no issues |
| Clean: AWS Singapore hosting | AC09 | standard_authorised, included, no issues |
| Clean: case workspace with audit history | AC10 | standard_authorised, included, no issues |
| Clean: 30 days hypercare (priced service) | AC12 | standard_authorised, included, no issues |
| Clean: SOW sanctions sizing 30,000/day | AC08 | standard_authorised, included, no issues |
| Exploratory only: anomaly detection "later phase" | AC11 | authorisation null, no issues |

## Hard cases inside the documents

- Exploratory/conditional statements that precede firm ones (Tron in AR-01, Polygon in AR-02, behavioural connector in AR-02) must stay non-firm at statement level.
- Numbers in words ("Thirty thousand", "sixty thousand", "thirty thousand (30,000)") must merge with digit forms.
- STR is the local name for the catalogue's suspicious activity report drafting.
- One proposal sentence maps to two commitments (Ethereum and Polygon).
- SOW 5.1 and contract clauses 3 and 3.3 are pointers; Annex 1 holds the terms.
- Contract clause 15 (entire agreement) is boilerplate. It does not explicitly address any earlier promise and is not a withdrawal.
- Sales-process chatter (questionnaire pack, next calls, approval forum, legal mark-up) and customer obligations are excluded from statements.

**Counts:** 8 documents, 24 labelled statements, 12 commitments (5 planted issues, 6 not-flagged firm commitments including 1 approved exception, 1 exploratory-only).
