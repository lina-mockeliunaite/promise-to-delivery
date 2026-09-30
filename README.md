# From Promise to Delivery

A pre-signature deal review tool for SaaS vendors with complex implementations, starting in RegTech. It reads a deal's paper trail (calls, RFP response, proposal, SOW, draft contract) and catches two things:

- **Overcommitment:** promises that became firmer than the company authorised.
- **Expectation gaps:** firm promises that set the customer's expectations but never reached the contract, and were never withdrawn.

Each conflict goes to a person as a decision: an owner and one of five actions. The approved decisions become the handoff baseline for delivery.

## Status

A 12-day build (25 Sep – 16 Oct 2026). **Day 3 of 12 complete:** design, product catalogue, and a fully labelled development deal. The extraction pipeline starts on Day 5.

## Where to look

| File | What it is |
| --- | --- |
| [`DESIGN.md`](DESIGN.md) | The design: users, inputs, the three-attribute model, the pipeline |
| [`DECISIONS.md`](DECISIONS.md) | Every design choice, with the alternative rejected and why |
| [`LEARNING_LOG.md`](LEARNING_LOG.md) | What I learned, got stuck on and got wrong, day by day |
| [`data/catalogue.json`](data/catalogue.json) | The fictional product catalogue: the authority for what can be sold |
| [`data/harbour_bank/`](data/harbour_bank/) | Development deal: brief, 8 documents, hand-labelled statements and commitments |

## The core idea

Each commitment is tracked on three separate attributes: **language** (exploratory, conditional or firm), **authorisation evidence** (from the catalogue and pricing note only), and **contractual presence**. Approval is never inferred from confident wording or from appearing in a contract. Keeping the three apart exposes the riskiest case: a firm promise in the contract with no authorisation behind it.

## Honest notes

- All companies, people, products and deal terms are fictional. TRM Labs and Chainalysis are real blockchain analytics providers, and BioCatch is a real behavioural intelligence provider; all three are named in the catalogue for realism only. Elva's integrations with them are fictional, and no partnership or endorsement is claimed.
- Built with Claude Code as build partner. Claude drafted the fictional deal documents from my brief; the brief, labels and design decisions are mine.
- Results will be reported on a small synthetic test set, including what fails.
