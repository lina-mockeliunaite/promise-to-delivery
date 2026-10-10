# Atlas Remit x Elva — intro / discovery call (transcript, lightly edited)

Recorded: Thursday 1 October 2026, 10:00–10:50 SGT, video call

On the call:
- Farid Hakim — Enterprise Account Executive, Elva
- Koh Wen Jie — Solutions Consultant, Elva
- Melissa Chua — Chief Compliance Officer and MLRO, Atlas Remit
- Joel Seah — CTO, Atlas Remit

---

**Farid Hakim:** Thanks both for making time. Wen Jie and I mostly want to listen today, then we'll come back with something concrete.

**Melissa Chua:** Sure. Quick background: Atlas Remit is a Singapore major payment institution, mostly SGD outbound to Indonesia and the Philippines. Early next year we launch Atlas Direct, where the recipient can take the payout in NUSD straight into their own wallet instead of a bank account. Target date is 1 February 2027 and it's already in front of the regulator as part of our licence variation.

**Joel Seah:** On the rails side: the bulk of payouts go over Polygon because fees are tiny. Bigger tickets go over Ethereum. And our Indonesian distribution partners keep asking for Tron, because that's where a lot of their recipients already hold balances.

**Melissa Chua:** From a compliance point of view I won't release a single payout until the receiving wallet has been screened and come back clean. That's non-negotiable for me.

**Koh Wen Jie:** Understood, and that's the pattern most of our payments customers run. Ethereum is the easy part — that one's live today, we screen the receiving wallet in real time before you release anything.

**Joel Seah:** And Polygon?

**Koh Wen Jie:** Polygon I'd rather have our product manager speak to directly, there's some nuance on modes. Let me take Tron away and check whether our analytics hook-up can see wallets on that network at all.

**Joel Seah:** Fair enough.

**Melissa Chua:** Volumes: we think roughly eighteen thousand payouts a day in the first month. Joel's model has us closer to thirty thousand by mid-year if Indonesia goes the way we think.

**Koh Wen Jie:** Helpful, thank you. Longer term, we could look at whether our unsupervised anomaly models would add anything on the corridor data — no promises, it's just a thought for a later phase.

**Melissa Chua:** Interesting. Park it for now; launch first.

**Joel Seah:** One practical thing on our side — we already have a contract with a blockchain analytics provider, so we'll bring our own credentials.

**Farid Hakim:** Perfect, that's how the connector is designed. Next steps from us: I'll send the security and deployment questionnaire pack over tonight, and Wen Jie will set up a technical session for next week with product on the line.

**Melissa Chua:** Wednesday works for us.

**Farid Hakim:** Wednesday it is. Thanks, all.

*[End of recording]*
