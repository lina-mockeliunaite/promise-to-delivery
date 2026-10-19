# Alder Bank deal brief — Instant payment scam protection

**Purpose:** the main demo deal from 16 Oct 2026, replacing the stablecoin storyline as the lead example. A plain, current problem anyone in banking recognises: scams on instant payments. **Demo data, not an evaluation set.** It was written after v2 was frozen and has no sealed labels; the four intended findings below are what the documents were written to contain, so the first model run can be compared against intent, but agreement on one run is a smoke test, not a measured result.

All companies, people, dates and deal terms are fictional. BioCatch is a real behavioural-biometrics provider, already named in the catalogue as Elva's pre-built integration for realism; the connector and its status are fictional and no partnership is claimed. No document states what a regulator requires.

## The deal

**Elva** (fictional) sells payment controls to banks. **Alder Bank** (fictional, Australia) is launching scam protection on all outbound instant payments (PayID) on **1 February 2027** and has told its board that date. Customers are being talked into sending money by scammers posing as the bank; once an instant payment leaves, it is gone. Alder's payments platform holds each payment until Elva returns a decision.

Volumes: about 180,000 instant payments a day today; 200,000 a day at launch; planning for 750,000 a day by the end of year one. Alder runs on Microsoft Azure.

## Catalogue positions used (data/catalogue.json, unchanged)

| Capability | Australia |
|---|---|
| CAP-003 Real-time transaction monitoring | GA, standard, max 500,000 transactions a day |
| CAP-027 Third-party behavioural intelligence connector (BioCatch) | Beta, requires named approval, GA planned 31 Dec 2027 |
| CAP-019 Regional cloud deployment | GA, supported clouds AWS and GCP only |
| CAP-011 Case management workspace, CAP-014 Case audit history | GA, standard |

## Intended findings (what the documents were written to contain)

| # | Promise (where) | Intended finding | How it can close in the demo |
|---|---|---|---|
| 1 | BioCatch coaching detection live from launch (RFP 2.1.1, proposal §3) | Approval required: CAP-027/AU is beta and needs a named approval; the pricing note records none. Also missing from the contract: the SOW never mentions it (not planned, but true; found by the first run) | The approval **closes** when the pricing note v2 records a named exception (AB-05_v2); the contract gap **closes** when SOW v2 adds coaching detection (AB-06_v2_coaching_added) |
| 2 | All outbound instant payments scored in real time before release (proposal §2) | Contract says something different: SOW Annex A scores payments under AUD 1,000 in hourly batches after release | **Not shown:** proposed by the model in both runs and rejected by the strict verifier on wording (see run log) |
| 3 | 750,000 payments a day by end of year one (proposal §2) | Over limit (CAP-003/AU max 500,000; no approval) and missing from contract (SOW covers 200,000 at launch only) | Stays open: Delivery inherits it |
| 4 | Hosted on Microsoft Azure, Australia East (RFP 4.2.1) | Not offered: Azure is not a supported cloud for CAP-019/AU (absolute, no exception possible); the SOW says AWS Sydney | Stays open: only changing the promise resolves it |

**Not findings by design:** case management with audit history (offered and in the SOW); 200,000 a day at launch (within limit and in the SOW); "If Alder shares 12 months of confirmed scam cases by 15 November, we can tune the detection scenarios before launch" (conditional); "exploring whether we could add a payee name check next year" (exploratory); "I'll send our security pack by Friday" and the RFP/proposal next steps (sales housekeeping).

## The demo story

Three promises with gaps, all made before the contract existed. Coaching detection needs two fixes: add the pricing note v2 and its approval closes, but it is still missing from the contract; add SOW v2 and the contract gap closes too. What remains is what Delivery inherits: a volume the product can't carry without an exception, and a hosting promise no approval can fix, only a changed promise.

## Run log

- **16 Oct, first run** (`v2_demo_alder_bank_20261016T064901Z.json`, $0.08): 6 findings shown, 1 rejected. Found #1 (plus a true contract gap on the same promise), #3 (both parts) and #4 (both parts). #2 was proposed correctly but rejected by the verifier: the model named the subject "outbound instant payments" (plural), the proposal said "every outbound instant payment" (singular), and the verifier requires the subject word for word in both quotes. The frozen verifier was not changed. **Demo data changed after seeing model output:** proposal §2 reworded to the plural ("All outbound instant payments will be scored…"), then run again. Recorded here because it would be cherry-picking in an evaluation set; this deal is not one.
- **16 Oct, second run** (`v2_demo_alder_bank_20261016T065312Z.json`, $0.11): 6 shown, 1 rejected. Same findings; #2 rejected again, this time because the model paraphrased the promised value ("…with no exceptions"). **Stopped rerunning** after two attempts: running until it passes would be cherry-picking even for demo data. This run seeds the app. Because #2 is not shown, the SOW fix was rewritten to add coaching detection (closes the true contract gap on #1) instead of aligning Annex A.
