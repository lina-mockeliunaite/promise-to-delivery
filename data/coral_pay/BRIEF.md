# Coral Pay deal brief — DRAFT (to be completed on Day 4)

**Status:** Requirements only. The full brief, documents and labels are written on Day 4, then sealed. No code reads this folder before 14 October 2026.

## Required cases

### Authorised promise that disappears from the contract

Include one authorised, customer-facing service promise that disappears from the draft contract.

- The proposal promises two 90-minute operations training sessions before launch.
- Coral Pay's pricing note approves exactly those sessions.
- Leave them out of the SOW and contract, with no withdrawal.
- **Gold label:** standard_authorised | absent | expectation_gap | null — no overcommitment or contradiction.
- Count it within the planned conflict set, rather than adding another case.

**Why:** Harbour Bank's three expectation gaps are all also overcommitments, so it cannot show that the tool detects a missing contractual promise independently of authorisation (see DECISIONS.md, 28 Sep).

**Open before drafting (Day 4):** training is a service, not a catalogue capability. Confirm that a service priced and approved in the pricing note maps to standard_authorised, and record it in DECISIONS.md. Otherwise the rules will find no catalogue match and return unknown_needs_review.

## Deal
Buyer / market: Coral Pay, payments company, Sydney
Launch story: AUD-funded contractor payouts across Asia in NUSD on Ethereum and Solana. Coral Pay already handles the Ethereum wallet-screening route outside Elva's scope; it is evaluating Elva for its Solana route and wider compliance workflow.
Launch date: 15 January 2027
Customer's own launch rule (not a regulator's): Coral Pay will hold each contractor payout until its recipient-wallet screening decision is clear.

## Planted conflicts (3)
1. Training: Elva firmly promises two 90-minute operations training sessions before launch. The Commercial-approved internal pricing/services note lists these as a normal, separately priced service available to any customer. No SOW, contract or incorporated customer-facing schedule includes the sessions, and no later document withdraws them → standard_authorised; absent; expectation_gap only.
2. Solana: Elva firmly promises NUSD recipient-wallet screening through its pre-built integration for Coral Pay's Solana payouts. CAP-021 has no AU/Solana/NUSD screening entry; no exception can authorise an unlisted network path. Put the promise in the incorporated SOW → no_approval_evidence; included_in_draft_contract; overcommitment; reason absolute_limit.
3. AU cloud: Elva firmly promises to deploy the Coral Pay environment on Azure in Australia. CAP-019 AU permits AWS and GCP only; supported_clouds is an absolute allowlist. Put Azure in the incorporated SOW → no_approval_evidence; included_in_draft_contract; overcommitment; reason absolute_limit.

## Clean commitments (3 firm, authorised, in contract)
- Payout ledger connector for up to 12,000 payouts per day at launch — CAP-023 AU standard, below its 20,000/day limit.
- Sanctions screening API for up to 25,000 conventional payer and beneficiary name screenings per day — CAP-007 AU standard, below its 50,000/day limit; this does not imply on-chain wallet coverage.
- Case management workspace for payout exceptions — CAP-011 AU standard.

## Conditional (1)
- Elva targets the 15 January 2027 go-live provided Coral Pay supplies sandbox and testnet access by 15 December 2026. Keep the vendor statement conditional and its authorisation null.

## Documents (same 8 as Harbour Bank?) yes / changes:
Eight documents in the same sequence and roles. Use a security/deployment questionnaire instead of the RFP response for document 3; it carries the AU hosting claim. The proposal carries the firm Solana and training promises. The internal pricing/services note records the standard training line and the product limits; the SOW and incorporated contract carry Solana and Azure but omit training. The customer email records reliance and access context, not an Elva statement.

## Development checks fixed before the seal
On Day 7, create three tiny synthetic fixtures outside either deal: an unlisted network (missing catalogue branch), a cloud outside supported_clouds (value outside an allowlist), and a standard service promised firmly, listed only on a Commercial-approved reference menu and absent from the deal's priced services and contract (expected: standard_authorised; absent; expectation_gap). Record expected labels before implementation. Use them to check extraction on Day 7 and the authorisation rules on Day 9, before the single Coral Pay run.

## Solana drift
In CP-01, Elva says: "We're exploring whether Elva's integration could screen NUSD recipient wallets on Solana for your Australian launch." Label it exploratory and map it to the same Solana commitment that becomes firm in the proposal. A bare "we need to confirm coverage" would be a next step, not a commitment statement.

## Ethereum clean negative
Coral Pay already screens its Ethereum payout wallets through its own provider. The documents make no Elva promise to screen Ethereum wallets; any extracted Elva commitment for that service is a false positive.

The two absolute limits remain distinct: Solana is a missing catalogue branch; Azure is outside an explicit allowlist.
