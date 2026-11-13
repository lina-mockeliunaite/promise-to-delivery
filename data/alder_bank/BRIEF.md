# Alder Bank deal brief — Instant payment scam protection

**Purpose:** the main demo deal. A plain, current problem anyone in banking recognises: scams on instant payments. **Demo data, not an evaluation set.** It was written after v2 was frozen and has no sealed labels. (12 Nov 2026: rewritten as a two-row story; see DECISIONS.md, Round 5.)

All companies, people, dates and deal terms are fictional. The feature the story turns on is called **scam-call alerts**: it warns the bank when a customer seems to be on a call with a scammer while making a payment. No partner or third-party company is named anywhere in these documents; the catalogue Alder is checked against (`data/catalogue_alder.json`) is a demo fixture, a copy of Elva's catalogue in which CAP-027 is named "Scam-call alerts" and lists no pre-built integration. No document states what a regulator requires.

## The deal

**Elva** (fictional) sells payment controls to banks. **Alder Bank** (fictional, Australia) is launching scam protection on all outbound instant payments (PayID) on **1 February 2027** and has told its board that date. Customers are being talked into sending money by scammers posing as the bank; once an instant payment is sent it is gone. Alder sends about 180,000 instant payments a day today and 200,000 a day at launch, and runs on Microsoft Azure.

## Catalogue positions used (data/catalogue_alder.json)

| Capability | Australia |
|---|---|
| CAP-027 Scam-call alerts | Beta, requires named approval, general release planned 31 Dec 2027 |
| CAP-019 Regional cloud deployment | GA, supported clouds AWS and GCP only |
| CAP-003 Real-time transaction monitoring, CAP-011 Case management workspace, CAP-014 Case audit history | GA, standard |

## Intended findings (what the documents were written to contain)

| # | Promise (where) | Intended finding | How it plays out in the demo |
|---|---|---|---|
| 1 | Scam-call alerts live from the 1 February 2027 launch (RFP 2.1.1, proposal §3) | Approval required: CAP-027/AU is beta and needs a named approval; the pricing note records none. Also missing from the contract: the SOW never mentions it | Add the approval (from 1 May 2027): found, but it starts later than the promise, so the gap stays open. Add the revised SOW: the contract gap closes. Add the signed contract: one identical sentence, so the contract fix is confirmed; the approval still starts after the signed launch date, so the gap stays open and Delivery inherits it |
| 2 | Hosted on Microsoft Azure, Australia East (RFP 4.2.1) | Not offered: Azure is not a supported cloud for CAP-019/AU (absolute, no exception possible); the SOW says AWS Sydney | Stays open until a person records the customer's agreement as a note |

**Not findings by design:** all outbound instant payments are scored in real time (the proposal and SOW Annex A agree); 200,000 a day at launch (within the catalogue limit and in the SOW); case management with audit history (offered and in the SOW); "If Alder shares 12 months of confirmed scam cases by 15 November, we can tune the detection scenarios before launch" (conditional); "exploring whether we could add a payee name check next year" (exploratory).

## The identical sentence

The revised SOW (AB-06 v2, section 5) and the signed contract's Appendix 1 (AB-09) carry one identical sentence, so the signed check can confirm the contract fix by exact match: "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank when a customer seems to be on a call with a scammer while making a payment." The approval (AB-05 v2) says "from 1 May 2027".

## Run log

Readings for this version of the documents are filled in by `fill_alder_readings.py` (two states: the base documents, and the base documents with AB-05 and AB-06 v2 added). Results and cost are recorded here when they are accepted.
