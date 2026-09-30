# Design — From Promise to Delivery

*Pre-signature deal review. v0.1, 25 Sep 2026. v0.2, 30 Sep 2026: revised into a local deal workspace with resolution checking (see "Revision v3" below).*

## Revision v3 (30 Sep 2026)

After Day 7 the product was revised from a pre-signature review with a decision screen into a **local deal workspace with resolution checking**: create or open a deal → upload or select sources → Review deal → inspect evidence → record a fix → recheck → save and export the handoff. `docs/PLAN_v3.3.md` is the schedule and governs; `docs/REVISION_BRIEF_2026-09-30.md` is the detailed specification. Where they differ (completion 21 Oct, hard stop 22 Oct, uploads including Excel and PowerPoint), the plan governs.

Everything below the v0.1 text is kept for history. Passages that v3 replaces are marked **Superseded by v3** and point here. The sections "Core model" and "Non-goals" still apply, with the additions noted in them.

**What v3 changes**

- **Audience.** B2B software and services teams of any size whose commitments are scattered across calls, proposals, contracts and internal approvals. The shared handoff serves Delivery, Customer Success and Support. The pre-signature deal reviewer remains the primary user.
- **Input.** Uploads of text/Markdown, text-based PDF, DOCX, Excel (.xlsx) and PowerPoint (.pptx) into user-created deals. Each file is tagged by the user with one of the seven existing document types and a document date. Harbour Bank, Kestrel Remit and Coral Pay remain fixed evaluation folders under `data/`. Scanned or image-only files (OCR) are outside this build.
- **Resolution replaces the five-action decision screen.** Three routes through one shared form: align the documents; record an allowed exception; change or withdraw the promise. The form records the affected issue, owner, rationale and supporting evidence. Choosing a route or writing "resolved" is not proof. The recheck re-evaluates every issue on that commitment with the same rules.
- **Issues, not commitments, close.** One commitment card carries every related issue. An issue closes only when its own closure criteria are met with permitted evidence. A commitment shows *Resolved* only when every issue on it is closed. Issue states: *Needs action*, *Needs evidence*, *Resolved*. Review freshness (*Review out of date*) is separate: changed sources or decision evidence mark a result out of date until rerun; a changed owner or note does not.
- **Every issue records the configuration that raised it (rules or agent) and its closure criteria.** A recheck can close an issue or keep it open; it cannot drop one because the current checker would not have raised it. Closure is a decision about evidence, not about which checker ran last. A reviewer cannot erase a system finding, only record an evidenced disposition.
- **Owner function replaces the three reviewer lenses.** The Product / Delivery / Commercial lenses (Architecture, step 5 in v0.1) are retired for this build. Each issue instead has an owner function field: Product, Commercial, Delivery, Customer Success or Support.
- **Scope statement, shown beside demo source selection and in the README:** "Demonstrated on fictional deals with a complete capability catalogue." Other uploads can compare promises with contractual terms, but their accuracy is unvalidated. Authorisation shows *Needs evidence* without suitable internal evidence; approval or prohibition is never inferred from silence, and an incomplete uploaded reference cannot establish an absolute limit by omission.

**Local architecture**

- A React frontend built to static files and a thin Python HTTP layer (FastAPI with uvicorn), both served locally on `127.0.0.1`. The API calls the existing modules; there is no second pipeline, no builder-default model, and no prompt or model ID in application code. Model IDs stay in `config.py`.
- Long operations (Review deal, recheck) run as background jobs the browser polls, so processing and failed states are visible.
- SQLite holds deals, source snapshots, commitments, findings and decisions. Credentials stay server-side (`ANTHROPIC_API_KEY`) and never reach browser code, exports or logs.
- No public model-backed endpoint in this build. Model-backed routes check the request's Origin and Host so a web page cannot trigger paid calls on localhost.
- **User-created deals** live in a gitignored `workspace/` folder outside `data/`, reached through their own guarded path function in a separate module. Deal IDs are server-generated; user-supplied names never become paths; files are stored by content hash. `ALLOWED_DEALS`, `deal_dir()` and `doc_path()` are unchanged.
- **Seal across every entry point.** The app serves only the frontend build. No route accepts a filesystem path. Results are served only for `extract_*.json` runs whose deal is in `ALLOWED_DEALS`. Coral Pay is never seeded in the UI and never read before 14 Oct.

**Extraction cache and the three kinds of run**

Extraction results are cached under a key built from everything that can change the output: the SHA-256 of the canonical text sent to the model, the document type, any context passed to extraction (none today), the system-prompt, template and schema hashes, model ID, thinking mode and the thinking parameter actually sent, `MAX_TOKENS`, and a cache-format version. The cache stores the model's output and usage, not the final rows; code-attached fields (`source_id`, `date`) are rebuilt on a hit. Only complete extractions are cached.

- **Recheck after a fix:** reuse cache for every document whose key is unchanged, re-extract only changed eligible documents, update the affected commitments, then reassess every issue on them against its closure criteria.
- **Unchanged-input rerun:** cached extraction plus deterministic rules gives the same result with no model call.
- **Fresh model run:** bypasses the cache. Used for repeatability measurements, the three agent runs and the sealed evaluation. The existing `extract.py` command line is always a fresh run.

The filter and consolidation stages are to be deterministic. Only if a stage needs a model does it use the same cache mechanism, keyed on stage, input hash and configuration hash.

**Freeze scope.** The candidate freeze on 12 Oct covers the evaluated pipeline only: extraction, filter, consolidation, rules and agent. Recheck, cache, UI and adapters sit outside the sealed evaluation and may continue after 12 Oct, provided they do not change evaluated modules.

## Problem

In complex B2B software deals, customer commitments change as they move from sales calls to RFP responses, proposals, SOWs and contracts. Each step can make a promise slightly firmer, broader or more contractual: a hedge disappears, a date is added, a roadmap item becomes a deliverable. No single change is dramatic, and no one sees the whole chain, so the company signs obligations that Product and Delivery never approved. The delivery team usually discovers the gap at kickoff, when fixing it means unpriced services, missed go-lives or commercial concessions.

## Primary user

The person who owns the pre-signature review of a deal: in this build, a solutions or pre-sales lead acting as deal reviewer in the final days before signature. They don't resolve every conflict themselves; they make sure each one reaches the right function (Product, Delivery or Commercial/Contractual) and leaves with an owner and a decision. Sales reps and customers are not users of this build.

## Inputs

1. **One deal's paper trail**: 7–8 documents — two call transcripts, an RFP response, a proposal, a draft SOW, a draft contract, a pricing and services note (which also records any explicit exception approvals, with approver and date), and a customer email that records the customer's reliance or obligations (customer context, not a source of Elva commitments in v1). Each document carries its type and date.
2. **The product capability catalogue**: 25 capabilities, each with its status (e.g. generally available, beta, roadmap), whether it is sellable as standard or requires named approval, regional availability, limits and any roadmap date.

All data is fictional: Elva, an AML platform for banks and payment providers (transaction monitoring, sanctions and name screening, alert and case management, suspicious activity report drafting, a payout ledger connector, unsupervised anomaly detection, and a connector for third-party behavioural and device risk signals) with digital-asset wallet screening delivered through pre-built integrations to specialist blockchain analytics providers. For those integrations the catalogue holds region → network → asset → screening mode, with status and sellability at the mode; unlisted networks, modes, assets and clouds are absolute limits. Dev deal: Harbour Bank's HarbourPay Global stablecoin payout launch (Singapore). Test deal: Coral Pay (Sydney), same world, sealed.

## Output

> **Superseded by v3** (see "Revision v3" above): the five-action decision screen is replaced by three resolution routes, issue-level closure and a recheck. The v0.1 text is kept for history.

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
5. **Decide** — *Superseded by v3: resolve and recheck.* A review screen presents each conflict with its evidence and three reviewer lenses (Product, Delivery, Commercial/Contractual). A person picks the owner and action. Once approved, the decision is immutable; any later change creates a new version and preserves the earlier decision in the audit history. (v3: lenses retired in favour of an owner function field; five actions replaced by three routes; approved decisions stay immutable and versioned, and closure is checked per issue.)
6. **Approved baseline** — *v3: handoff.* Export the approved decisions as the handoff record. (v3: saved record plus CSV register and readable summary, with unresolved items visible.)

The v3 local architecture, extraction cache and freeze scope are described in "Revision v3" above.

Design principle: the system suggests, a person decides. Every finding cites its source.

## Non-goals

- Tracking commitments after signature, or delivery status.
- Lenses for Sales, Technology, Support, Finance or Customer Success.
- Margin modelling.
- CRM or contract-system integrations.
- A customer-facing view.
- Editing contracts automatically, or giving legal advice.
- Any real customer, employer or deal data.

Added by v3: post-signature tracking; OCR for scanned documents; live connectors (Google Drive first, later); generated resolution suggestions; per-role dashboards; name and domain research; a public model-backed endpoint.
