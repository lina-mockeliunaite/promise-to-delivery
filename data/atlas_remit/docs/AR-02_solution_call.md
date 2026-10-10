# Elva / Atlas Remit — solution deep-dive

Wednesday 7 October 2026 · 15:00–16:10 SGT · Teams

Present
- Elva: Koh Wen Jie (Solutions Consultant), Rachel Pereira (Product Manager, Digital Assets), Farid Hakim (Account Executive)
- Atlas Remit: Melissa Chua (CCO/MLRO), Joel Seah (CTO), Arjun Pillai (Head of Payments Operations)

Notes taken by Farid; speaker turns kept where useful.

---

**Joel Seah:** Let's start with wallet screening, because it gates everything.

**Rachel Pereira:** Happy to. Polygon in real time is still in beta for us in Singapore. If I can get it signed off internally as a named exception, we could turn it on for your launch; otherwise it's the batch flavour until general availability next March.

**Melissa Chua:** Batch means what in practice?

**Rachel Pereira:** Hourly runs. In batch mode a payout typically waits for the next run.

**Arjun Pillai:** An hour's hold on a remittance is a support-ticket factory. We'd really want real time.

**Rachel Pereira:** Understood. I'll take it to our approval forum this month.

**Joel Seah:** And Tron? Wen Jie said he'd check.

**Koh Wen Jie:** Still checking, I don't have an answer for you today.

**Arjun Pillai:** Next, volumes. We'll start around eighteen thousand payouts per day but I'd like headroom.

**Koh Wen Jie:** Thirty thousand a day is fine on our side.

**Arjun Pillai:** Good. That's the mid-year number.

**Melissa Chua:** Let me ask about case work. My team writes STRs by hand right now, it's painful.

**Koh Wen Jie:** Once an analyst marks a case as suspicious, we generate the STR for them. It's pre-filled from the case file, so your team edits rather than types.

**Melissa Chua:** That alone would save us two FTE.

**Joel Seah:** Fraud side: we already license a behavioural-biometrics product on the app. Can you consume its scores?

**Koh Wen Jie:** We have a connector for third-party behavioural risk scores, but it's in beta, so I'd need to check what we can commit to before I say yes.

**Joel Seah:** Please do.

**Joel Seah:** On our side, we'll have the analytics provider API keys loaded into your sandbox by 8 January.

**Farid Hakim:** Great. Action items: Rachel to take Polygon real-time to approvals; Wen Jie to come back on Tron and the behavioural connector; I'll get the proposal drafted once the questionnaire is back. We'll schedule a pricing walkthrough after that.

*Call ended 16:08.*
