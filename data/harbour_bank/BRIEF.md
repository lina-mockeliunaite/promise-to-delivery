# Harbour Bank deal brief — HarbourPay Global

**Purpose:** Ground truth for the fictional deal paper trail. Draft documents from this brief, then check the final wording before labelling it. Label what the documents actually say, not what the brief intended.

**Test objective:** Find firm vendor commitments that exceed the catalogue or approved scope, and firm commitments that the final contract changes or leaves out.

All companies, people, tokens, dates and deal terms below are fictional. TRM Labs and Chainalysis are real specialist blockchain analytics providers, named in the catalogue as Elva's pre-built integrations for realism. The connectors, their coverage and their status are fictional; this scenario claims no real partnership, certification or endorsement. No document states what a regulator requires.

## The deal

**Elva** is a fictional Singapore-based AML platform for banks and payment providers. Its core product covers transaction monitoring, sanctions and name screening, alert and case management, suspicious activity report drafting, and operational reporting. For digital-asset screening, Elva offers pre-built integrations to specialist blockchain analytics providers. The provider supplies on-chain intelligence; Elva connects the request and result to the bank's existing workflow. Elva does not issue, custody or move stablecoins.

**Harbour Bank** is a fictional Singapore digital bank that already uses Elva for conventional payment monitoring and case management. It is launching **HarbourPay Global** on **1 December 2026**, letting SME customers pay suppliers in the Philippines and Vietnam in **NUSD**, a fictional USD stablecoin issued by fictional Northgate Trust.

Most HarbourPay Global payouts will use **Polygon**; larger payouts will use **Ethereum**. Harbour Bank's engine calls Elva's screening API and holds a payout until it receives a clear wallet-screening result. Real-time screening returns a result before the payout proceeds; hourly-batch screening can delay the decision by up to an hour. Harbour Bank has announced the launch date to partner merchants.

Harbour Bank expects about **8,000 payouts per day at launch** and plans for up to **40,000 per day by the end of year one**.

**Integration boundary:** Harbour Bank holds its own licence and API credentials with its selected analytics provider. Elva supplies the pre-built connector and workflow. Provider licence and usage fees are outside Elva's price. Harbour's documents leave the provider unnamed; this test is about Elva's integration readiness.

## Authority and labelling rules

- The catalogue dated 28 September 2026 is authoritative for product availability and limits. For CAP-021, the path is **region → network → asset → screening mode**; status, sellability, limits and roadmap date sit at the mode.
- roadmap_date means planned general availability for that exact mode and region. It is null once GA; a roadmap item may also have no scheduled date.
- Standard sellability applies within the stated regions and quantitative limits; exceeding a quantitative limit requires named approval. The pricing and services note is authoritative for service scope and named exceptions. Customer-facing documents show what Elva said; they do not prove internal approval.
- not_sellable is absolute. Unlisted networks, assets or modes are outside catalogue support.
- Check authorisation for firm commitments only. Exploratory and conditional statements use null for authorisation: not applicable, not unknown. Keep the four-value authorisation vocabulary unchanged.
- A customer reliance line explains the stakes; it is not an Elva commitment and does not establish contract content. A customer obligation is context attached to a related vendor commitment, not its own commitment record.
- A later document that states different terms is a contradiction; silence is an omission. Neither is a disposition unless it explicitly addresses the earlier promise. Follow every incorporated reference to its actual terms.
- A commitment is an Elva statement about what the product or services will do, deliver or include for this customer. Sales next steps, project governance, internal effort estimates and standard legal terms are excluded.

## Document set

| ID | Date | Document | Purpose in the paper trail |
|---|---|---|---|
| HB-01 | 28 Sep 2026 | Discovery call | Launch context, reliance, exploratory Polygon mode and conditional go-live |
| HB-02 | 2 Oct 2026 | Product and technical call | Named-approval condition and actual GA date for Polygon real-time |
| HB-03 | 6 Oct 2026 | RFP response | First firm real-time statement, covering Ethereum and Polygon |
| HB-04 | 10 Oct 2026 | Proposal | Firm launch promise and the two supporting conflicts |
| HB-05 | 14 Oct 2026 | Internal pricing and services note | Catalogue facts, no Polygon exception, and provider-cost boundary |
| HB-06 | 20 Oct 2026 | Draft SOW with Annex A | SOW refers to the wallet-screening specification; Annex A gives actual modes |
| HB-07 | 23 Oct 2026 | Draft agreement | Incorporates the SOW and Annex A by reference |
| HB-08 | 27 Oct 2026 | Customer email | Updates customer access date and confirms reliance |

## Main storyline: Polygon real-time screening

CAP-021, Singapore, NUSD:
- **Ethereum real-time:** generally available, standard.
- **Polygon real-time:** beta, requires named approval, planned GA 31 March 2027.
- **Polygon batch:** generally available, standard.

| Source | Evidence | Language or role |
|---|---|---|
| HB-01 | Priya: “We're exploring whether Elva's pre-built connector to a blockchain analytics provider can return real-time screening results for Polygon wallets in time for your launch.” | Exploratory |
| HB-02 | Maya: “If Product grants named approval, Elva's pre-built integration to the selected blockchain analytics provider could return real-time screening results for Polygon wallets as a limited beta; planned general availability in Singapore is 31 March 2027.” | Conditional |
| HB-03 | Elva says it “will return real-time wallet-screening results for Ethereum and Polygon before every NUSD payout is released.” | Firm; one statement maps to two commitments |
| HB-04 | Elva says every NUSD payout on Polygon will be screened in real time before release, from 1 December. | Firm and dated |
| HB-05 | Internal note says Polygon real-time is beta, needs named approval, and no named exception is approved for Harbour Bank. | Approval evidence |
| HB-06 §3 | Wallet-screening services are provided “in accordance with the Wallet Screening Specification in Annex A.” | Reference to terms |
| HB-06 Annex A.2 | Polygon wallets are screened in hourly batches; a payout is released after the next completed batch returns a clear result. | Explicit batch term |
| HB-07 clauses 3 and 3.4 | Clause 3 incorporates the SOW and Annex A; clause 3.4 points to SOW §3, which points to Annex A. | Contract reference chain |
| HB-08 | Harbour Bank says its 1 December launch depends on Elva's real-time result clearing each wallet before release. | Reliance context |

**Evidence conclusion:** HB-03 and HB-04 firmly promise Polygon real-time screening. The SOW points to Annex A, which says Polygon is screened hourly. The draft contract incorporates that SOW and annex. The same service and network are identified, and the mode differs. This is a contradiction and an expectation gap; the specific real-time terms are absent from the incorporated contract terms. No later document explicitly addresses or withdraws the earlier real-time promise. HB-08 shows reliance but is not evidence of what the contract contains.

## Three planted conflicts

| # | Conflict | Ground truth |
|---|---|---|
| 1 | **Polygon real-time screening** | CAP-021 requires named approval for beta Polygon real-time; none is recorded. The RFP and proposal make a firm promise. Annex A and the contract chain specify hourly batches instead. Label overcommitment, expectation gap and contradiction. |
| 2 | **Year-one payout volume** | HB-04 promises 40,000 payouts/day by year one. CAP-023's standard limit is 25,000/day. Label overcommitment; the 12,000/day launch commitment is within the limit. |
| 3 | **VASP counterparty data date** | HB-04 promises general availability by 31 March 2027. CAP-024 is roadmap with planned GA 30 June 2027 and requires named approval. Label overcommitment and roadmap-date mismatch. |

## Clean and hard examples

- **Clean firm commitments:** Ethereum real-time screening (CAP-021); Polygon hourly-batch screening in the incorporated Annex A (CAP-021); 12,000 payouts/day at launch (CAP-023).
- **Hard non-firm case:** HB-01's 1 December go-live is conditional on sandbox and testnet access by 15 November. HB-08 changes the customer's access date to 10 November. Keep authorisation null for the conditional vendor statement.
- **Customer context:** attach the launch-reliance lines from HB-01 and HB-08 to the Polygon screening commitment. Attach the sandbox/testnet access statements from HB-01 and HB-08 as customer-obligation context to the go-live statement.
- **RFP hard case:** the single HB-03 sentence maps to Ethereum real-time and Polygon real-time separately. It is one statement and two commitments.

**Lean-set coverage:** 7 consolidated commitments: three planted conflicts, three clean firm examples, and one conditional go-live. The statement and commitment files retain blank fields for Lina to complete. The exception_approved, unknown_needs_review, and absolute not_sellable cases are intentionally not tested in this Harbour Bank version.
