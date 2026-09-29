# Decisions

## 2026-09-25 — 1. Provisional use of Sonnet 5, with a Day 5 comparison

**What I chose**
Use Sonnet 5 as the initial model for the Day 1 experiment and first extraction implementation. Keep the exact model ID in configuration rather than scattering it through the code.

**What I rejected**
- Comparing several models before the pipeline exists
- Automatically choosing the cheapest model
- Automatically choosing the most powerful and expensive model
- Treating the Day 1 selection as permanent

**Why**
The first objective is to establish a working baseline with one capable model. Comparing models before I have a schema, labelled examples and an evaluation harness would produce impressions rather than evidence.

Using one model also reduces the number of variables while I learn how API requests, responses, tokens and structured outputs work. If something fails, I have fewer possible causes to investigate.

The model decision remains provisional because extraction quality, cost and latency cannot be judged from one prompt. On Day 5, I will run candidate models against the same labelled development examples and compare:
- Commitment recall
- Precision
- Language-strength accuracy
- Quote validity
- Schema compliance
- Cost
- Latency

The sealed Coral Pay deal will not be used for model selection.

**Revisit when**
Day 5, once the development corpus, labels and evaluation harness exist.

## 2026-09-25 — 2. Three separate commitment attributes instead of one ladder

**What I chose**
Represent each commitment using three independent attributes:
1. Language strength — exploratory, conditional or firm
2. Contractual presence — absent or included in the draft contract
3. Authorisation evidence — standard-authorised, exception-approved, no approval evidence, or unknown/needs review

**What I rejected**
One ladder such as: exploratory → proposed → approved → contractually binding

**Why**
The original ladder combined three different questions:
- How confidently was the promise expressed?
- Did the company authorise it?
- Did it enter the contract?

Those questions do not always move together. For example:
- A salesperson can make a firm verbal promise with no approval evidence.
- A standard capability can be authorised, even though it was only discussed tentatively.
- A commitment can appear in a draft contract despite having no internal approval.
- A proposal can repeat a firm commitment without making it contractually binding.

A single ladder would force these situations into misleading categories and hide the conflicts the product is supposed to find.

The three-attribute model allows the system to identify precise risks, such as:
- Firm language with no approval evidence
- Draft-contract inclusion with no approval evidence
- A conditional promise becoming firm
- A catalogue-supported capability being described outside its approved limits

Because the build is pre-signature, "contractually binding" is not used. The system records only whether the commitment is present in the draft contract.

**Revisit when**
After Day 3 labelling, if the categories repeatedly overlap or cannot be applied consistently.

## 2026-09-25 — 3. Authorisation must come from authoritative evidence

**What I chose**
Assign authorisation evidence only by checking the commitment against designated authoritative sources:
- The capability catalogue establishes what may be sold as standard, including limits, regions and approval requirements.
- The pricing and services note records explicit exceptions, together with the approved terms, approver and date.
- If the commitment matches a capability but its specific terms are not authorised, label it no approval evidence.
- If it cannot be confidently matched to a catalogue capability, label it unknown/needs review.

**What I rejected**
- Inferring approval from confident language
- Assuming something is approved because it appears in a proposal or SOW
- Assuming a draft-contract clause must have received internal approval
- Asking the extraction model to decide whether a commitment was authorised

**Why**
A customer-facing document proves what was offered; it does not prove that the company approved the offer internally. Using the proposal or contract to infer approval would create circular reasoning: the system would treat the potentially problematic commitment as evidence that it was authorised.

The separation also makes the result auditable. Every authorisation verdict must point to either:
- A catalogue entry authorising the commitment on those terms, or
- An explicit exception in the pricing and services note

If neither exists, the system escalates rather than guesses.

This decision creates one of the product's most valuable findings: "This commitment appears in the draft contract, but no internal authorisation evidence was found."

Authorisation therefore belongs in conflict verification, after extraction and consolidation — not in extraction itself.

**Revisit when**
If the product later connects to a formal deal-desk or approval system that becomes an additional authoritative source.

## 2026-09-25 — 4. Label authorisation once per consolidated commitment, including clean examples

**What I chose**
Label language strength for each individual source statement. After equivalent statements have been consolidated, label authorisation evidence once for each materially distinct set of commitment terms.

Include both:
- Planted conflicts
- Clean, correctly authorised commitments

**What I rejected**
- Labelling authorisation separately for every repeated quote
- Labelling only the six known conflicts
- Treating every mention of the same capability as having identical terms

**Why**
Authorisation applies to the actual terms of a commitment, not merely to the name of the capability.

For example, these may refer to the same connector but require different authorisation decisions:
- "The connector is generally available in Singapore."
- "The connector will support five million transactions per day."
- "The connector will be delivered by 31 October at no additional cost."

If identical terms appear in a call, proposal and SOW, they should become one consolidated commitment with several sources and one authorisation label. Labelling every occurrence would duplicate work and could introduce inconsistent ground truth.

If the terms materially change — such as a new deadline, volume, region, price or service obligation — the changed version requires its own authorisation assessment.

Clean examples are essential because evaluation must measure both:
- Whether the system catches real conflicts
- Whether it incorrectly flags valid commitments

Labelling only planted conflicts would allow measurement of recall, but not precision or false-positive behaviour.

**Revisit when**
If the corpus becomes much larger and some deterministic labels can be generated automatically and then human-verified.

## 2026-09-25 — 5. Typed close-of-day quiz instead of voice memos

Replaced voice memos with a typed close-of-day quiz; will practise spoken answers before Checkpoint 2.

## 2026-09-26 — 6. Detect expectation gaps across the complete deal record

**What I chose**
Detect unresolved specific commitments across the complete deal record, not only unauthorised commitments in the contract. Flag any firm, testable customer-facing commitment whose material terms are not matched or incorporated by reference in the draft contract, SOW or priced services, and for which no later document explicitly supersedes, excludes or withdraws that commitment. Testable means it contains a quantity, date, volume, geography, named capability or integration, defined scope, service effort or responsibility.

**What I rejected**
Flagging every earlier firm statement absent from the contract, because generic RFP answers would create excessive noise.

**Why**
A gap is raised only when material terms are unmatched and there is no explicit later disposition. The end states (incorporated, accepted with an owner, or explicitly changed and clarified with the customer) belong on the decision screen, not in extraction, and need no sixth action. Consolidation accuracy becomes a critical dependency: an uncertain link is shown as needs review, never asserted as a confirmed gap. One Harbour Bank conflict is replaced by an expectation-gap scenario, keeping the total at six.

This is the final conceptual change. New ideas go on the Later list.


## 2026-09-27 — Day 2: capability catalogue

**Per-region records.** Chose: status, sellable, limits and roadmap_date stored per region. Rejected: one status per capability; top-level defaults with regional overrides. Why: a capability can be GA in AU and beta in SG. Complete records per region are easier to verify than a fallback rule at 20 capabilities × 2 regions.

**Fixed vocabularies.** Chose: status = roadmap | beta | generally_available | deprecated | retired; sellable = standard | requires_named_approval | not_sellable; regions = SG, AU; clouds = AWS, GCP. Why: code matches exact words. A typo or synonym silently changes a verdict. HK dropped: no deal uses it.

**Valid combinations.** roadmap or beta → requires_named_approval or not_sellable. deprecated or retired → not_sellable. roadmap_date = planned GA date in that region: a date or null while roadmap/beta; null once GA.

**Absolute limits.** Chose: not_sellable and supported_clouds cannot be overridden by any exception. A pricing note that claims to is flagged as a contradiction. Numeric limits can be exceeded only with recorded exception approval. supported_clouds is an allowlist: anything not listed is unsupported. Status: not_sellable is untested in either deal (known gap).

**Authorisation checked for firm commitments only.** Why: exploratory and conditional statements are not promises. If one later firms up, the evidence rules catch it as drift. Otherwise a correct hedge becomes a false flag.

**Roadmap-date mismatch, not "slip".** Chose: the conflict is a firm proposal date earlier than the catalogue's GA date. Rejected: a Product email confirming the change. Why: two sources prove the dates conflict, not why they changed. No new authority source is needed.

**AU cloud trap.** Chose: AU hosting GA on AWS/GCP; the trap is a promise of another cloud. Rejected: AU hosting not_sellable. Why: a capability being available in Australia does not mean we can deliver it on the cloud platform Coral Pay requires.

**Who wrote the catalogue.** I chose the capabilities, facts and traps; Claude formatted the JSON; I validated and read every entry.

**Scope change: Lovable demo front end.** Chose: add a Lovable front end on Day 11 (15 Oct, +2 hours, six-hour day), reading the pipeline's exported JSON; record the demo on it. Streamlit stays as the working decision screen on Day 10. Rejected: replacing Streamlit with Lovable; raising every day to six hours. Why: a strong demo matters for the roles I'm targeting, and presentation work suits extra hours better than new concepts. Kill rule: if the pipeline or the sealed Coral Pay run isn't complete by end of Day 10, Lovable moves to the week of 19 Oct and the demo is recorded on Streamlit. Credit: the front end is generated with Lovable, and I'll say so.

**Schedule change.** Days 3–7 move one day earlier (28 Sep – 2 Oct). Mon 5 Oct becomes a buffer, used only if something slips. Checkpoint 1 stays Fri 2 Oct. Phase 2 dates unchanged; Coral Pay sealed until 14 Oct.


## 2026-09-28 — Day 3: lean Harbour Bank storyline (revised pack)

**Lean storyline.** Use one headline conflict and two supporting conflicts: Polygon real-time screening, payout throughput, and the VASP availability date. Remove the Tron, hop-depth and retrospective-history branches so they do not compete with the main evidence chain. Keep current CAP IDs for retained items; CAP-022 and CAP-025 are intentionally unused and not reassigned.

**Product and partner boundary.** Elva is a fictional AML platform with a digital-asset screening capability delivered through pre-built integrations to specialist blockchain analytics providers. The catalogue names TRM Labs and Chainalysis as those integrations for realism; the connectors, their coverage and their status are fictional, and no real partnership, certification or endorsement is claimed. Harbour Bank keeps its own provider licence and credentials. The deal tests Elva's integration readiness, not the upstream provider's standalone service.

**Catalogue shape and vocabulary.** The catalogue is rebuilt for the lean pack (CAP-001 to CAP-021, CAP-023, CAP-024). For network integrations, status, sellability, limits and roadmap date sit at region → network → asset → screening mode. A network-level status cannot represent Polygon batch as GA and real-time as beta. roadmap_date always means planned GA in that region and mode; it is null after GA or when no date is scheduled. standard applies within the stated regions and quantitative limits; exceeding a quantitative limit requires named approval. A restricted list such as supported_clouds and not_sellable are absolute. Unlisted networks, assets and modes are unsupported.

**Authorisation for non-firm language.** Apply authorisation only to firm commitments. Store null for exploratory and conditional commitments; null means not applicable, not unknown. Keep the four-value authorisation vocabulary unchanged. Use unknown / needs review only when a firm statement cannot be matched confidently to an authoritative catalogue or pricing-note item.

**Contractual evidence and disposition.** Customer reliance explains consequence but does not establish contract content. Follow incorporated references to their actual terms. A later document that states different terms is a contradiction; silence is an omission. Neither is a disposition unless it explicitly addresses the earlier promise. Here, SOW §3 points to Annex A, Annex A specifies hourly Polygon screening, and contract clauses 3 and 3.4 incorporate that chain.

**Scope of claims.** The pricing/services note is authoritative for service scope and named exceptions. Customer-facing documents show what was said, not internal approval. The brief's three traps are the only planted conflicts in this lean deal: 7 consolidated commitments (3 conflicts, 3 clean firm, 1 conditional). exception_approved, unknown_needs_review and not_sellable remain valid design values but are not exercised here. Trade-off accepted: below the plan's cap of 12–15 commitments with at least 6 clean examples; scores on this deal move in coarse steps.

**Quotes are the commitment sentence only.** Statement quotes contain the sentence that carries the commitment, copied word for word, without speaker labels or surrounding next steps. Why: the extraction checker and scoring compare quotes; whole speaker turns would mix in excluded content.

**Drafting and review.** AI may help draft and convert the brief into files. I check every final quote, reference and label against the source documents and own the ground truth. Label final document wording, not the brief's intention.

**Test-set limit: expectation gaps are not independent of authorisation.** Harbour Bank has three expectation gaps, but each is also an overcommitment. It cannot test whether the tool detects a missing contractual promise independently of authorisation. A passing Harbour Bank score therefore does not establish that capability.

**Statement vs reference.** Chose: a sentence that states its own terms (asset, network, delivery route, responsibility) is a statement, even when it points elsewhere for detail; a sentence that only points is contractual evidence, not a statement. So SOW §3 is S11 (→ C02, C03, via Annex A), while contract clauses 3 and 3.4 add no rows and instead set contractual_presence = included_in_draft_contract for C02, C03 and C04. Rejected: clause 3.4 as S15. Why: a generic "wallet screening" row would duplicate the SOW terms and risk treating C01 (real-time Polygon) as present in the contract; following the reference shows hourly batch instead.

**Scoring rule for the pricing-schedule sentence (set before any results).** HB-04 "Commercial terms are set out in the accompanying pricing schedule." is excluded, with no C-ID; the schedule is not in the record, and HB-05 (internal) is not that schedule. If the tool notes the missing schedule, it is recorded as a valid document-completeness observation, outside commitment and conflict scores. If it turns the sentence into an Elva commitment or a commitment-level needs_review, it counts as a false positive. Document-completeness checks go on the Later list.

**Harbour Bank labels complete.** 14 statements (HB-01 to HB-06; HB-05, HB-07 and HB-08 contain no Elva statements) and 7 commitments. C05 and C06 are labelled expectation_gap as well as overcommitment under the written rule; the brief's conflict table was corrected to match.

## 2026-09-29 — Day 4: Coral Pay sealed

**Coral Pay sealed (29 Sep).** Final pack: brief, 8 documents, manifest, 2 label files; SHA-256 hashes of all 12 files in `data/coral_pay.sha256` (outside the sealed folder); verified with `shasum -a 256 -c` on 14 Oct before the run. Exposure during preparation, recorded openly: Claude drafted the documents in this project conversation; a one-off validation script read the documents and labels to check that every quote matched its source. The seal restricts, from now until 14 Oct: development, extraction and evaluation code, and Claude Code's build context. None may read `data/coral_pay/`. Later project conversations get no Coral Pay content. Claude Code is blocked by deny rules in `.claude/settings.json`; shell commands are covered by ask-before-changes review and a CLAUDE.md rule (Day 5). Known dev/test differences: Harbour Bank's pricing note records missing approvals and Coral Pay's does not; Coral Pay adds a `security_questionnaire` document type and a reference-only service menu; Coral Pay's conflicts use the absolute-limit and authorised-but-absent paths, covered in development only by the Day 7 fixtures.

**Standard service authorisation.** Chose: label the two training sessions standard_authorised because CP-05 lists them as a standard service. I assume a pricing/services note has Commercial approval before it counts as authorisation evidence. The rules check both the catalogue and the note against a commitment's material terms and use the matching source. Rejected: adding a service/capability field to extraction or treating a Sales-written note as self-approval. Why: authorisation is an evidence check after extraction.

**Menu versus deal allocation.** Chose: a deal-priced service allocation both authorises and reflects the promise; a standard reference-menu line authorises it but does not place it in this deal. The menu must cover promised service timing, while capability timing is checked against GA status and roadmap_date. Rejected: treating the training menu line as if Coral Pay had ordered the sessions. Why: that would erase the expectation gap the test is designed to measure.

**Solana and Ethereum grouping.** Chose: keep Solana as one commitment; Annex A adds real-time screening to the proposal's compatible “before release” term. Exclude the Ethereum sentences as scope statements about Coral Pay's own provider. Rejected: splitting Solana by mode or extracting an Elva Ethereum promise. Why: Harbour Bank's Polygon terms were split because the Annex contradicted the proposal; here it adds detail without conflict, and the AU/Solana path is unsupported under either mode.

**Naive baseline.** Chose: give one prompt the catalogue, pricing note and all Harbour Bank documents, but no brief or gold labels. Rejected: withholding authorisation evidence or adding a method to the prompt. Why: the methods should have the same evidence. The run caught 3 of 3 conflicts and 6 of 7 issue labels, missing C06's expectation gap; it made 0 false flags, used only valid quotes, and cost about 7.5k input and 6.9k output tokens. Harbour Bank's pricing note states the missing approvals outright, so the baseline could largely quote HB-05; Coral Pay's note does not. This is one strong run, not proof of repeatability, and the pipeline must earn its complexity through auditable verdicts for every commitment, including the cleared ones.

**Claude Code 101.** Chose: complete it in full and keep GitHub unconnected. Rejected: stopping at the short version or connecting GitHub for this build. Why: I need to understand permissions before Day 5, and a GitHub-connected session could access a copy of the public repo outside the local deny rule, weakening Coral Pay's seal.

## 2026-09-29 — Day 5: extraction v1 and first Harbour Bank run

**Test-set seal.** Chose: deny rules for the Coral Pay folder and checksum, manual Claude Code permission mode (auto mode switched off), an `ALLOWED_DEALS` guard, and `deal_dir`/`doc_path` containment before file reads. Rejected: relying on `CLAUDE.md` alone or letting scripts build deal paths independently. Why: the controls reduce accidental test-set access through both tools and code. This is a workflow seal, not OS-level isolation; file-tool deny rules do not stop every arbitrary subprocess.

**Document selection.** Chose: extract from customer-facing document types in which Elva speaks; mark the internal pricing/services note and customer email `REFERENCE_ONLY`, and flag unknown types. Rejected: running statement extraction on all eight documents or silently skipping unfamiliar types. Why: internal authorisation evidence and customer reliance are needed later, but neither is a new Elva statement. A possible Elva promise reported only in a customer email will be missed by v1 and needs later review.

**Speaker attribution.** Chose: extract the named Elva speaker from calls, but have code assign the speaker for written Elva documents and discard the model's guess. Rejected: trusting a generated author for a written document. Why: document provenance is known to the code, while call turns still require speaker identification.

**Validation and retries.** Chose: use `messages.create` so each attempt's raw response and usage remain available, then validate with Pydantic and check quotes separately. Retry a failed, refused, truncated or API-errored extraction once with the same prompt, log both attempts and their costs, and mark the document `incomplete` if neither succeeds. Rejected: silent drops, unlimited retries, or treating an incomplete document as clean. Why: the reviewer must see both missing coverage and what the failed attempt cost.

**Model settings.** Chose: keep Sonnet 5 provisionally with `MAX_TOKENS = 8000` and thinking left at the model default, explicitly named in config and recorded in each run. Rejected: silently inheriting an unrecorded setting or switching thinking off before the first comparison. Why: the Day 4 baseline used the default; recording the setting keeps this variable visible, without claiming that thinking improves extraction. The cost estimate uses the official Sonnet 5 rates checked on 29 September: $2 per million input tokens and $10 per million output tokens (https://platform.claude.com/docs/en/about-claude/pricing). Model comparison is deferred to Day 6 morning because of the time ceiling; Decision 1 remains open.

**Prompt and schema traceability.** Chose: before the first live run, clarify that bare investigation steps are excluded, possible customer-facing outcomes are exploratory, and planned delivery or availability is conditional. Record SHA-256 hashes of the exact system prompt, user-message template and schema in every run. Rejected: labelled Harbour Bank sentences as prompt examples or untracked wording changes. Why: the general rules address a real language ambiguity, while hashes make later runs distinguishable. The generic examples still resemble some development wording; that limitation should be disclosed.

**First-run interpretation.** Chose: treat the first Harbour Bank extraction as a diagnostic result, not a scored success or failure. Rejected: calling the difference between 23 extracted and 14 labelled statements a false-positive count without matching rows. Why: all 23 extracted quotes passed the quote check, but quote validity does not establish correct inclusion or language. The run cost an estimated $0.068 and about 70% of output tokens were thinking. Day 6 hypotheses are over-extraction of process promises and a reference-only sentence in HB-07 being treated as a statement; both need row-level review against the labels.