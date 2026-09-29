# Review Findings: Harbour Bank Deal Paperwork

## A. Customer-facing promises that exceed Elva's catalogue or approved scope

**1. Real-time Polygon screening promised in the RFP response**
> "Through its pre-built connector to a blockchain analytics provider, Elva will return real-time wallet-screening results for Ethereum and Polygon before every NUSD payout is released."
— **HB-03** (RFP response, 6 Oct 2026)

Catalogue CAP-021 shows Polygon/NUSD/real_time as `status: beta`, `sellable: requires_named_approval`, with `roadmap_date: 2027-03-31`. HB-05 (deal desk) explicitly confirms "No named exception approved for Harbour Bank." Stating this as a flat, unconditional capability in a formal RFP answer misrepresents an unapproved, unreleased capability as generally available today. Notably, HB-02 (internal-facing call) correctly hedged this as conditional on named approval — the hedge was dropped in the customer-facing RFP response.

**2. Real-time Polygon screening promised again, tied to the launch date**
> "Every NUSD payout on Polygon will be screened in real time through Elva's analytics integration before release, from the 1 December launch."
— **HB-04** (proposal, 10 Oct 2026)

Same catalogue conflict as above, compounded here by committing to a specific go-live date (1 December) that is nearly four months before the catalogue's own planned GA date (31 March 2027) for this capability, with no named approval on record (HB-05).

**3. Payout volume promise exceeds the connector's regional limit**
> "The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year."
— **HB-04** (proposal, 10 Oct 2026)

Catalogue CAP-023 caps Singapore at `max_payouts_per_day: 25,000`. HB-05 confirms "No approval for 40,000/day." This promise is 60% above the sellable/approved limit.

**4. VASP counterparty data exchange date is wrong and ignores approval requirement**
> "For payouts to exchange-hosted wallets, VASP counterparty data exchange will be generally available in Singapore by 31 March 2027."
— **HB-04** (proposal, 10 Oct 2026)

Catalogue CAP-024 lists `status: roadmap`, `sellable: requires_named_approval`, `roadmap_date: 2027-06-30` — three months later than promised, and HB-05 confirms no named exception exists for Harbour Bank. The proposal states a firm GA date for a roadmap item that isn't even the correct roadmap date.

## B. Firm, specific promises missing or changed in the draft agreement without explicit withdrawal

**5. Polygon screening mechanism silently changed from real-time to batch**
> "Every NUSD payout on Polygon will be screened in real time through Elva's analytics integration before release, from the 1 December launch."
— **HB-04** (proposal)

versus

> "A.2 Polygon: recipient wallets are screened through the analytics integration in batches at hourly intervals. A Polygon payout is released after the next completed screening batch returns a clear result."
— **HB-06** (draft SOW, Annex A.2)

The SOW quietly substitutes hourly batch holds for the previously promised real-time, pre-release screening — a materially different control given the customer's stated design ("hold each payout until screening clears the recipient wallet," HB-01; reaffirmed in HB-08: "real-time screening result clearing every recipient wallet before release"). Nothing in HB-06 or later documents flags this as a change from the proposal, so the contradiction between the SOW and the customer's still-current expectation is unresolved.

**6. Year-one payout volume commitment dropped from the SOW without withdrawal**
> "The payout ledger connector will handle up to 40,000 payouts per day by the end of the first year."
— **HB-04** (proposal)

versus

> "The payout ledger connector will handle up to 12,000 payouts per day at launch."
— **HB-06** (draft SOW, §2 — no year-one figure at all)

The SOW only commits to the launch-day figure and is silent on the previously promised year-one scaling number. Since the dropped figure exceeded the catalogue limit (see Problem 3), its disappearance may be deliberate, but it was never communicated to the customer as a correction/withdrawal — leaving the customer's expectation (set in HB-01 and HB-04) unaddressed in the contract.

**7. Customer's real-time-for-all-wallets expectation reaffirmed post-SOW but never corrected**
> "Our 1 December launch depends on Elva's real-time screening result clearing every recipient wallet before release."
— **HB-08** (customer email, 27 Oct 2026, sent after the batch-based SOW draft of 20 Oct)

This email shows Harbour Bank still operating on the original "real-time for every wallet" premise even after receiving the SOW specifying hourly batch screening for Polygon (HB-06, A.2). There is no evidence in the record of Elva correcting this understanding before signature. If the MSA (HB-07, which incorporates the SOW by reference) is executed while this gap is live, Elva risks signing an agreement that contradicts the customer's explicit, written, and unretracted understanding of a core launch dependency.