# Design — From Promise to Delivery

*Pre-signature deal review. v0.1, 25 Sep 2026.*

## Problem

In complex B2B software deals, customer commitments change as they move from sales calls to RFP responses, proposals, SOWs and contracts. Each step can make a promise slightly firmer, broader or more contractual: a hedge disappears, a date is added, a roadmap item becomes a deliverable. No single change is dramatic, and no one sees the whole chain, so the company signs obligations that Product and Delivery never approved. The delivery team usually discovers the gap at kickoff, when fixing it means unpriced services, missed go-lives or commercial concessions.

## Primary user

The person who owns the pre-signature review of a deal: in this build, a solutions or pre-sales lead acting as deal reviewer in the final days before signature. They don't resolve every conflict themselves; they make sure each one reaches the right function (Product, Delivery or Commercial/Contractual) and leaves with an owner and a decision. Sales reps and customers are not users of this build.

## Inputs

1. **One deal's paper trail**: 7–8 documents — two call transcripts, an RFP response, a proposal, a draft SOW, a draft contract, a pricing and services note (which also records any explicit exception approvals, with approver and date), and one later email that revises something important. Each document carries its type and date.
2. **The product capability catalogue**: 18–20 capabilities, each with its status (e.g. generally available, beta, roadmap), whether it is sellable as standard or requires named approval, regional availability, limits and any roadmap date.

All data is fictional: a RegTech vendor selling transaction monitoring and case management.

## Output

A list of conflicts, each put to a person as a decision. Every conflict shows the commitment, the evidence from each source side by side with exact quotes, how its language, authorisation evidence and contractual presence changed across documents, the catalogue position it conflicts with, and a suggested resolution. It closes only when a person assigns an owner and one of five actions: confirm capability, change scope, price services, move a milestone, or clarify a customer dependency. The approved decisions become the handoff baseline for delivery.

## Two failure modes

The system asks where every meaningful customer promise ended up, not only which risky promises reached the contract.

1. **Overcommitment**: a promise becomes firmer, broader or more contractual than the company authorised.
2. **Expectation gap**: a firm, testable promise made in a call, RFP response, proposal or email is not reflected in the draft contract, SOW or priced services, and nothing explicitly withdrew it. The system can see only the absence of a written disposition, not the customer's expectations.

Before signature, every expectation gap must end in one of three states, chosen on the decision screen using the existing five actions: incorporated into the contract or SOW; accepted as an approved delivery commitment with an owner; or explicitly changed, excluded or superseded and clarified with the customer.

## Core model

Every commitment carries three separate attributes, because what someone said, what the company authorised and what is heading into the contract are different things:

- **Language** (read from the words): exploratory → conditional → firm.
- **Authorisation evidence** (derived from authoritative sources only):
  - *Standard-authorised* — the catalogue lists the capability as sellable as standard, on these terms.
  - *Exception-approved* — the pricing/services note records an explicit exception, with approver and date.
  - *No approval evidence* — the commitment matches a catalogue entry, but neither source authorises it on these terms.
  - *Unknown / needs review* — the commitment cannot be confidently matched to a catalogue entry.
- **Contractual presence** (derived from document type): absent, or included in draft contract. This build uses draft contracts only; "signed" is reserved for later.

**Key rule:** approval is never inferred from confident language, or from appearance in a proposal, SOW or draft contract. It requires an authoritative catalogue entry or an explicit exception approval in the pricing/services note.

One of the strongest findings the system can make: *this appears in the draft contract, but no internal authorisation evidence exists.*

## Architecture

1. **Ingest** — load the deal documents and their metadata.
2. **Extract** — the model finds every commitment, with the exact quote, who made it and its language level. Contractual presence comes from the document type. A checker confirms every quote exists word for word in its source.
3. **Consolidate** — merge the same promise worded different ways into one record with its history, stored in a SQLite ledger. Later evidence supersedes an earlier commitment only when it explicitly revises it or belongs to the same controlled document lineage. Otherwise both versions remain and the system flags a contradiction; a later email does not silently override a draft contract or approved SOW.
4. **Find conflicts** — two kinds:
   - **Evidence conflicts**: drift, contradictions, disappearing conditions and newly added dates across documents. Largely deterministic once commitments are consolidated. This includes **expectation gaps**: flag any firm, testable customer-facing commitment whose material terms are not matched or incorporated by reference in the draft contract, SOW or priced services, and for which no later document explicitly supersedes, excludes or withdraws that commitment. *Testable* means it contains a quantity, date, volume, geography, named capability or integration, defined scope, service effort or responsibility. A generic umbrella clause does not match specific terms. Where the link between a commitment and a contract clause is uncertain, the result is *needs review*, never a confirmed gap.
   - **Capability and authorisation conflicts**: whether the resulting commitment is supported by the catalogue or an explicit exception approval; this step assigns authorisation evidence. Built twice, once with rules and once as an agent with catalogue-search tools; the evaluation results decide which one stays.
5. **Decide** — a review screen presents each conflict with its evidence and three reviewer lenses (Product, Delivery, Commercial/Contractual). A person picks the owner and action. Once approved, the decision is immutable; any later change creates a new version and preserves the earlier decision in the audit history.
6. **Approved baseline** — export the approved decisions as the handoff record.

Design principle: the system suggests, a person decides. Every finding cites its source.

## Non-goals

- Tracking commitments after signature, or delivery status.
- Lenses for Sales, Technology, Support, Finance or Customer Success.
- Margin modelling.
- CRM or contract-system integrations.
- A customer-facing view.
- Editing contracts automatically, or giving legal advice.
- Any real customer, employer or deal data.
