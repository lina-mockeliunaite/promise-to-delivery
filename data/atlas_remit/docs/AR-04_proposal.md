# Proposal: Financial-crime controls for Atlas Direct

**Prepared for:** Melissa Chua, Chief Compliance Officer, Atlas Remit Pte. Ltd.
**Prepared by:** Farid Hakim and Koh Wen Jie, Elva
**Date:** 16 October 2026
**Version:** 1.0

---

## 1. Why we're writing

Atlas Direct puts a stablecoin payout in the recipient's own wallet, which means your controls have to hold the line before value leaves Atlas, not after. This proposal sets out how Elva will support the 1 February 2027 launch and the first year of growth.

## 2. Wallet screening before every release

Your rule is simple: nothing goes out until the receiving wallet is clear. We've built the screening design around it.

Recipient wallets on both Ethereum and Polygon will be screened in real time, ahead of release, for every NUSD payout. As discussed, Atlas brings its own analytics-provider licence and credentials.

We know your Indonesian partners have been vocal about Tron. NUSD payouts that Atlas routes over Tron will also have the receiving wallet screened in real time before funds are released, so your Indonesian partners are covered from day one.

## 3. Name and sanctions screening

Name and sanctions screening is sized at up to sixty thousand checks a day, comfortably above your forecast peak.

## 4. Payout ledger integration

The payout ledger connector will be provisioned for 30,000 payouts daily from launch. That matches the mid-year figure Arjun's team shared.

## 5. Investigations and reporting

Investigators will work alerts and cases in a single case workspace, with a full audit trail of every action.

Suspicious transaction reports will be drafted automatically from the case record, ready for your MLRO to review and file.

## 6. Fraud signals

Elva will ingest the device and behavioural risk scores from your existing behavioural-biometrics vendor and make them available to fraud rules and investigators from go-live.

## 7. Where it runs

Your tenant will run on Elva's AWS deployment in Singapore.

## 8. Next steps

We'd welcome a call next week to walk through this proposal and the commercial schedule. Farid will circulate a draft Statement of Work shortly afterwards.

---

*This proposal is valid for 60 days from the date above. It is an invitation to negotiate and is not a binding offer. Commercial terms are set out in a separate schedule.*
