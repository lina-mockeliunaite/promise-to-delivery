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

## 2026-09-30 — Day 6

**Catalogue: 23 → 25 capabilities.** Chose: add CAP-026 (unsupervised anomaly detection; GA, standard, SG and AU) and CAP-027 (third-party behavioural intelligence connector, BioCatch illustrative; beta, named approval, SG and AU, planned GA 31 Dec 2027). Rejected: replacing an existing entry; per-entry description fields. Why: neither adds a scored case, so this does not improve the evaluation. I added them for realism, so the catalogue resembles AML and fraud platforms in this market, and as unscored near-match distractors for authorisation matching. Scope limits are in schema_note; IDs 022 and 025 stay retired. Catalogue SHA-256 before b649ab7b…c822, after 11826c96…31c2; the Day 4 baseline ran on the earlier version. Accepted risk, unverified: a GA anomaly entry could authorise a Coral Pay detection promise that CAP-020 should catch; no pre-edit check was run. Seal contact: Claude's command ran shasum -c over the sealed pack and listed its docs directory, without being asked; output discarded, no content exposed, no files changed.

**Extraction matching.** Chose: match an output to a label only within the same source document, using Jaccard overlap of lowercased word sets at 0.8 or above. Assign matches one-to-one from the highest score down; a duplicate output is a false positive. Report scores from 0.5 to below 0.8 as near-misses only when both sides remain unmatched. Check matched pairs for language agreement and missing digit-containing words. Rejected: exact text matching, which would reject harmless differences in quote length, and simple containment, which could accept a small fragment. Why: I fixed this rule before seeing the scores so I would not choose a threshold to flatter a run. Limit: word sets ignore order and repetition, and the digit check flagged the section numbers in “A.1” and “A.2” as lost details. Those are review prompts, not proof that a commitment term was lost.

**Harness safeguards.** Chose: accept only a resolved `results/extract_*.json` run path, take the deal name from the file, and check it against the allowlist before loading its labels. Hash the exact label-file bytes used for scoring and record that hash with the report so a later label revision produces distinguishable evidence. Reports cannot overwrite an existing file. The harness makes no API calls and does not read Coral Pay. Rejected: trusting any path passed at the command line; unversioned label files. Why: the score needs a traceable answer key, and neither a path supplied at the command line nor a changed label file should silently alter what was measured.

**Day 4 baseline.** Chose: keep the Day 4 baseline’s issue-level result on record, but do not compare its numbers with the new statement-level precision and recall. The baseline found 3 of 3 planted conflicts and 6 of 7 issue labels; the harness measures extracted statements against 14 statement labels. Rejected: presenting extraction’s 14/14 recall as an improvement on the baseline’s 3 of 3. Why: they answer different questions. A fair case-by-case comparison belongs in Day 9, using the same task and evidence.

**Label scope and pending revision.** Chose: track statements about what Elva may or will deliver if the deal proceeds, including exploratory and conditional versions needed to trace drift. A firm, specific promise about delivery or implementation belongs in the commitment set. Sales-process steps and generic descriptions of method do not; sentences that only refer to another section remain excluded under the Day 3 rule. Rejected: silently editing the labels to match the run; counting every firm SOW sentence as a commitment. Adjudication: HB-06-S03’s weekly implementation meeting is a real, measurable service promise in the SOW, so its absence is a label gap. HB-03-S02’s generic phased methodology remains a model error. I will add HB-06-S03 as S15/C08 on Day 7 and determine its authorisation from the permitted internal evidence; I will not assume that it is standard-authorised. The original score remains 14 TP, 9 FP, 0 FN (14/23 precision). If this is the only correction, the adjudicated count would be 15 TP, 8 FP, 0 FN (15/23, about 65% precision); that is a calculation, not a rerun result. Test-set rule: before opening Coral Pay, I am recording that any genuine label error found there will be judged against this same scope rule. I will retain the original sealed-run score, report any adjudicated score separately, and make no post-run prompt or model changes to improve it.

**Extraction model.** Chose: keep Sonnet 5 with default thinking.

| | Sonnet 5, default thinking | Sonnet 5, thinking off | Haiku 4.5 |
| --- | ---: | ---: | ---: |
| Recall | 14/14 | 14/14 | 11/14; missed Annex A S12–S14 |
| Precision | 61% | 64% | 65% |
| Language errors | 0 | S08 and S09: firm → conditional | S08 and S09: firm → conditional |
| Cost per run | $0.068 | $0.033 | $0.011 |

Rejected: Sonnet 5 with thinking off and Haiku 4.5. Why: both cheaper runs changed S08 and S09 to conditional, so the firm volume and VASP-date promises would skip authorisation review and two planted conflicts would disappear. Haiku also missed Annex A’s hourly-batch terms, losing the contract-side evidence for the Polygon expectation gap. Limit: this is one run per configuration on 14 development labels, with Harbour Bank already visible during prompt development. The decision rests on which consequential rows failed, not a claim of general performance. Haiku’s thinking-disabled support was inferred from the documentation and the request succeeded with HTTP 200; that does not reveal the model’s internal process.

**Spend.** $19.79 prepaid credit remained on 30 September; this is a balance, not a verified month-to-date usage total. Re-check on 12 October.

**Day 7 carry-over.** Add S15/C08 with its authorisation from permitted evidence; make the harness list language mismatches; fix the plan’s “$20 monthly limit” wording.

## 2026-09-30 — Day 7: regression, hard cases, extraction frozen

**S15/C08 label.** Chose: add HB-06's weekly project status meeting as S15 (firm) and C08, authorisation `unknown_needs_review`, included in the draft contract through the SOW, issue `needs_review`. The attempted match is recorded: HB-05 prices implementation at 60 person-days but names no status meetings; the catalogue lists capabilities, not services. Rejected: `standard_authorised` because meetings seem part of implementation; adding a line to HB-05. Why: approval is never inferred from scope or from contractual inclusion, and editing development data to fit a label corrupts the answer key. C08 becomes the development case for a silent internal note. Label hash 4f4a018f → dbdc17a3.

**Must-hold regression checks.** Chose: six checks, fixed before any run: every firm label matched; S08 and S09 matched and firm; S12–S14 matched; 100% quote validity; precision ≥ 60%; no statements from HB-05, HB-07 or HB-08. Built as `regression.py`. Rejected: judging a change by headline precision. Why: Day 6 showed a better headline can hide two planted conflicts; these rows carry the conflicts the product exists to catch.

**Pointer-sentence revision (the one permitted revision).** Chose: define the existing pointer rule's boundary: a sentence pointing elsewhere is a statement only if it states at least one material term of its own (network, asset, mode, volume, limit, date, frequency, region or price). Prompt hash 3b283af8 → db9e892a; template and schema unchanged. Rejected: repeating the existing rule, which the model already had and broke on every Day 6 run; recording HB-07 as a known failure. Why: "Provider will provide wallet screening services as described in SOW section 3" is firm and contract-side; on Day 8 it could be grouped with C01 and hide the Polygon expectation gap, which meets rule C. The prompt example is deliberately unlike any Harbour Bank sentence. Result: HB-07 0 statements, S11 and S12–S14 kept, precision 61% → 75% (15/20, against the new labels), 6/6 checks pass. One run.

**Hard-case fixtures.** Chose: a fictional Singapore deal, Kestrel Remit, 5 documents and 12 cases, designed from the general rules and catalogue only: no Australian market, no Solana, no training, to keep the sealed deal out of development. Labels carry authorisation and contractual presence so Day 9 inherits its first development cases for the absolute-limit (KC1, Arbitrum) and authorised-but-absent (KC6, CAP-014) paths, and the first in-contract, no-approval case (KC4). Claude drafted documents and labels; I signed off the labels. Result: 9/9, 1 false positive (H6, sales-process step). Limit: written after seeing the prompt.

**Freeze.** Chose: freeze extraction v1 (hashes in WHERE_I_STOPPED.md) with sales-process steps as a known failure for Day 8/9 to filter. Rejected: a second revision for sales-process steps. Why: they add noise rather than hide a conflict; further tuning on Harbour Bank would fit the development set.

**Plan wording.** The "$20 monthly limit" is prepaid credit ($19.79 remaining on 30 Sep), not a verified monthly usage cap; wording corrected in the plan.

## 2026-09-30 — Revision v3: local deal workspace (recorded before Day 8)

Days 1–7 and every entry above stand unchanged. The entries below add to them.

**Revision and precedence.** Chose: revise the remaining build into a local deal workspace with resolution checking (plan v3.0–v3.3, brief `docs/REVISION_BRIEF_2026-09-30.md`). Where the plan and the brief differ, the plan governs: completion Wed 21 Oct, hard stop Thu 22 Oct (brief: 20 Oct); uploads include text/Markdown, PDF, DOCX, Excel and PowerPoint (brief: to PDF/DOCX); 50 committed hours, 56 maximum (brief: 42). Rejected: keeping the v2.6 decision screen with a Lovable front end. Why: the recheck is the distinctive behaviour to validate, and a local app avoids a hosted backend. This supersedes the Day 2 "Scope change: Lovable demo front end" entry, which stays above as history; Lovable is dropped for this build. The seal does not depend on React or local hosting; it depends on the access controls.

**Architecture.** Chose: React (Vite) built to static files, plus a thin FastAPI/uvicorn layer bound to `127.0.0.1`, calling the existing modules. Model-backed routes check Origin and Host. Long operations run as background jobs the browser polls. No prompt or model ID in application code; model IDs stay in `config.py`. Rejected: standard-library `http.server` (uploads, routing and validation by hand); a second inference pipeline; a public model-backed endpoint. Why: one pipeline keeps the measured extraction behaviour the one the product uses. New dependencies: `fastapi`, `uvicorn`, `python-multipart`; later `pypdf`, `python-docx`, `openpyxl`, `python-pptx`; versions pinned at install. Node v26.10.0 and npm 11.19.1 confirmed installed.

**User-created deals and the guard.** Chose: a gitignored `workspace/` folder outside `data/`, reached through its own guarded path function in a separate module. Server-generated deal IDs; user-supplied names never become paths; files stored by content hash; resolved-path containment; symlinks rejected; extension allowlist and size caps (including uncompressed size for zip-based formats; macro-enabled formats rejected). No API route accepts a path. Results are served only for `extract_*.json` runs whose deal is in `ALLOWED_DEALS`. `ALLOWED_DEALS`, `deal_dir()` and `doc_path()` are unchanged. Rejected: extending `ALLOWED_DEALS` for user deals; storing uploads under `data/`. Why: the seal guards named sealed paths, and mixing user data into `data/` would weaken it. `.gitignore` additions (with step two): `workspace/`, `*.db`, `*.sqlite*`, `node_modules/`, `frontend/dist/`, `frontend/.vite/`.

**Findings record their configuration and closure criteria.** Chose: every issue stores which configuration raised it (rules or agent, with configuration hash and review ID) and structured closure criteria. A recheck evaluates each open issue's own criteria against current evidence; only met criteria close it. If the current checker no longer raises an issue it is annotated "not re-raised by current configuration" and stays open. A removed source document makes affected issues *Needs evidence*, never closed. Rejected: letting the latest checker's output replace earlier findings. Why: closure is a decision about evidence, and otherwise switching from agent to rules could silently drop an agent-found issue. The schema is designed on 2 Oct.

**Lenses retired; owner function field.** Chose: retire the Product / Delivery / Commercial reviewer lenses from DESIGN.md for this build. Each issue instead carries an owner function: Product, Commercial, Delivery, Customer Success or Support. Rejected: keeping lenses alongside owners. Why: the v3 form records owner, rationale and evidence, and lenses added a second axis with no closure meaning.

**Document types for uploads.** Chose: format and document type are separate. The user selects one of the seven existing types (plain-language labels in the UI) and a document date; the model never guesses the type. Adapters produce canonical text plus a location map (page or paragraph, sheet and cell, slide), and quotes are checked against the canonical text. The snapshot records the original-file hash, canonical-text hash and adapter version. Pricing/services notes and customer emails stay reference-only. A pricing note uploaded as a spreadsheet is accepted as a source but does not count as approval evidence. For non-Elva uploads the catalogue is off, so authorisation shows *Needs evidence*. Open for 4 Oct: whether PDF or DOCX pricing notes count as evidence, and how the rules parse the note.

**Open decision: `security_questionnaire`, due 4 Oct.** DECISIONS Day 4 records that Coral Pay adds a `security_questionnaire` document type. `config.py` lists only the seven types, so `extract.py` would flag it `flagged_unsupported_type` and not extract it. Options: add it to the configuration (extractable or reference-only), or accept that it is skipped. Decide by 4 Oct, before the 12 Oct candidate freeze, because it is part of the evaluated configuration. Decided without opening any Coral Pay file.

**Extraction cache.** Chose: cache extraction under a key of the canonical-text SHA-256, document type, any context passed to extraction (none today), system-prompt, template and schema hashes, model ID, thinking mode and thinking parameter sent, `MAX_TOKENS` and a cache-format version. Store the model's output and usage, not the final rows; rebuild `source_id` and `date` on a hit. Cache only complete extractions; record a hit's cost as cached and keep the original cost for audit. Three run kinds stay separate: recheck after a fix (re-extract only documents whose key changed, then reassess every issue on the affected commitments); unchanged-input rerun (no model call); fresh model run (bypasses the cache: repeatability, the three agent runs, the sealed evaluation). The `extract.py` command line is always fresh. Rejected: keying on the content hash alone; caching final rows. Why: otherwise model variation, not evidence, could open or close a finding. Required test for later: an injected client that raises if called, proving an unchanged-input rerun makes no model call.

**Plumbing edit to `extract_document`, approved in principle for later.** Add an optional `text=` parameter that skips the file read. Prompt, template, schema, model and thinking are untouched, so the three hashes do not change, and the command line behaves identically. Required test: a fake client proving the request sent via `text=` is byte-identical to the request sent via the file read. No model run. Rejected: copying the retry loop into a new module (a small second pipeline).

**Filter and consolidation: deterministic first.** Chose: build the sales-housekeeping filter and consolidation deterministically. Only if a stage needs a model does it use the cache mechanism, keyed on stage, input hash and configuration hash; that is a fallback, not the plan. Any rule-based filter must be checked on `hard_cases` as well as Harbour Bank. Rejected: a model-based filter by default. Why: a model stage could vary between runs and change findings on a recheck. Limit: filter rules tuned on Harbour Bank would fit the development set, hence the second deal.

**Freeze scope.** Chose: the 12 Oct candidate freeze and the final evaluated configuration cover the evaluated pipeline only: extraction, filter, consolidation, rules and agent. Recheck, cache, UI and adapters are outside the sealed evaluation and may continue after 12 Oct without delaying unsealing, provided they do not change evaluated modules. Rejected: freezing the whole backend. Why: the sealed run measures the evaluated pipeline; holding unrelated work back would delay unsealing for no measurement benefit. This narrows the plan's "backend freeze" wording (plan v3.3 says "candidate backend freeze"); the plan text needs a matching edit.

**Cut order at the 22 Oct hard stop.** Chose: anything unfinished at the close of 22 Oct is reported unfinished, not deleted, in this order: PowerPoint first (a deck saved as PDF goes through the PDF adapter), then visual refinement beyond the basic design, then Excel. Never cut: PDF, DOCX, both exports, recheck and the full evaluation. Rejected: deciding at the hard stop. Why: a pre-agreed order avoids trading things off under time pressure.

**Estimate check (judgement, not measurement).** The plan's ~30 hours of build (12 four-hour days at about 2.5 hours) was compared with Claude Code's estimate of build hours per block, made from code size and the repo audit, not from measured pace. I log actual build hours per block from 1 Oct; formal re-plan at the close of 5 Oct.

| Block | Estimate (build h) | Supply (h) | Risk |
| --- | --- | --- | --- |
| 1 Oct: docs and scaffold | 2.5–3 | 2.5 | Medium |
| 2 Oct: Checkpoint 1 and schema | ~1.5 | ~1.5 | Low |
| 3 Oct: filter, consolidation, ledger, score | 4–5 | 2.5 | High |
| 4 Oct: rules, citations, references | 4–5 | 2.5 | High |
| 5 Oct: agent, three runs, comparison | 3–4 | 2.5 | High |
| 12 Oct: recheck, cache, scenarios, freeze | 5–6 | 2.5 | Highest |
| 13 Oct: wire UI, integration, configuration record | 5–6 | 2.5 | High |
| 14 Oct: sealed run | ~1–1.5 | 2.5 | Low |
| 15 Oct: fix UI, README, demo | 3.5–4 | 2.5 | High |
| 19 Oct: PDF and DOCX, handoff, exports | 5–6 | 2.5 | High |
| 20 Oct: Excel and PowerPoint | 6–7 | 2.5 | Highest |
| 21 Oct: acceptance, docs | ~3 | 2.5 | Medium |

Total about 43–52 hours against about 30. Even the 56-hour maximum leaves about 36 hours of build. Reasons for the largest gaps: 12 Oct feeds the sealed run; the Excel and PowerPoint block needs two adapters, a canonical text form that survives the frozen prompt, sheet/cell and slide location tracing, script-generated fixtures (formula cells read as empty without stored values) and extraction runs; the frontend has about 5 hours scheduled across 13 and 15 Oct against about 8–10 needed. Mitigations that need no scope change: define the adapter interface and snapshot columns during the 2 Oct schema session; write the Excel and PowerPoint canonical-text specification on 2 Oct as a document only.

## 2026-10-02 — 1 Oct block completed; Checkpoint 1 run as a simulated review

**Schedule slip.** The 1 Oct block (scaffold) was not finished on 1 Oct; it was completed on 2 Oct. The 4 contingency hours pulled forward to 1–2 Oct were spent without lightening 3 Oct as intended. From here the only buffer is the 2 hours on 16 Oct.

**Scaffold (step two).** Chose: read-only FastAPI app (`api.py`) bound to 127.0.0.1 plus a React page, Harbour Bank only via `UI_DEALS` (a checked subset of `ALLOWED_DEALS`). Seal tested at runtime against a decoy `coral_pay` folder with a canary string in a temporary data directory, never the real path. Rejected: testing against the real `data/coral_pay/`. Why: a guard bug would read the sealed deal during the test itself, CLAUDE.md forbids touching the path, and a canary lets the test assert on content, not only on status codes. 94/94 tests pass; schema hash unchanged (a4debfaf).

**Known limits found today (not fixed).**
- The `.claude/settings.json` deny rules cover Claude Code's Read and Edit tools, not shell commands; for those the seal relies on the CLAUDE.md instruction.
- `regression.py` copies prompt hashes from the run file rather than verifying them. A hash-verification check is needed before the 12 Oct candidate freeze.
- Two 404 bodies exist: the deal guard returns "Not found", unknown routes return FastAPI's "Not Found". Not a seal leak (all rejected deals share one body), but noted.
- The API field `status` means document-type eligibility on the sources route and run outcome on the results route. Rename to `eligibility` on 3 Oct, before issue statuses arrive.
- UI copy: document-type labels ("Rfp response", "Draft sow", "Pricing services note") to be corrected on 3 Oct.

**Checkpoint 1: simulated review, not the real checkpoint.** The reviewer pack was run as a simulated Delivery/CS review. Chose: log it as design input only; Checkpoint 1 stays open until a real CS, implementation or pre-sales leader reviews the revised pack, **deadline 5 Oct**. Rejected: counting the simulation as Checkpoint 1. Why: it cannot answer whether checking the fix beats a spreadsheet for a real team, and it restated an existing decision (issue-level closure), so it confirmed rather than tested the design.

**Deviation from the plan.** The plan allows schema design only after Checkpoint 1 feedback is logged. Chose: design the schema on 2 Oct from the simulated review's inputs. Why: the schema is design-only and cheap to change; waiting would move 3 Oct with no benefit. Risk: the schema rests on assumptions no real reviewer has tested; capped by the 5 Oct deadline.

**Design inputs adopted from the simulated review (acceptance criteria for the schema):**
1. Approval closes an approval issue only if it covers the promised terms *and* conditions (for example launch date and beta conditions), not the capability alone.
2. A contract gap closes only when the annex version currently incorporated by the contract matches the promise, including screening before release. Sources therefore carry versions, and references record which version they resolve to.
3. Commitments can be linked: a commitment that is clean on its own (Polygon hourly batch) can be the contract side of another commitment's open issue, and the register must show that link.
4. Closing one commitment leaves every other finding visible with its owner and outstanding action; the handoff lists unresolved commitments.
5. Closure records the evidence checked and the reason it passed; a partial or mismatched fix states what remains unmet.
6. "Resolved" means the documented gap is closed. It does not establish operational readiness for launch; the UI and handoff say so.
7. The handoff record lets a recipient establish the final promise, conditions, owner, approval and remaining actions, with traceable source versions.

**Not adopted:** changing the tagline. The simulation said it conveys detection more than rechecking; one simulated opinion is not enough. Test it with real reviewers by asking what they expect the product to do before explaining it.

**Reviewer pack changed:** the leading line in Step 2 was replaced with "What would happen next in your current process?", and the hourly-batch row now shows its link to the open Polygon issue.

**Ledger schema approved (design only): `docs/LEDGER_SCHEMA.md`.** 17 tables and 3 derived views; DDL written once on 3 Oct, behaviour built in tranches (3 Oct: write path from imported run files; 4 Oct: issues and references; 12 Oct: fixes, closure checks, cache reuse, links). Key choices:
- Issue state and commitment status are derived views, never stored columns: state follows the latest closure check, so a resolved issue reopens if a later recheck fails, and a commitment is Resolved only when all its issues are. Rejected: stored status fields. Why: a stored status goes stale when one issue changes and another is overlooked.
- Authorisation and contractual presence are stored per review (`commitment_assessments`), not on the commitment. Why: they change between steps; overwriting them loses the audit trail.
- References resolve by source plus cited date: a re-dated SOW leaves the contract pointing at the old version and the gap open.
- Every recheck reassesses every commitment and issue. Rejected: reassessing only commitments whose evidence changed. Why: the rules are deterministic and cost nothing at this scale; change-tracking code could silently skip a commitment that should have been rechecked.
- C01 keeps three issues as labelled (labels are frozen); the UI groups contract gap and contradiction under one "Contract" heading.
- Imported rows from the frozen run file are `reusable = 0` (it lacks the content hash, context field and cache-format version), so the app's first review makes six model calls (~$0.07).
- **New allowlist `LEDGER_DEALS`, separate from `ALLOWED_DEALS`.** Why: on 14 Oct `ALLOWED_DEALS` must be widened for the sealed run; a ledger that trusted it would admit Coral Pay the same day. Each layer keeps its own allowlist. The sealed run's output stays in `results/` only, never in the ledger or UI.
- Risk: the schema rests on the simulated review; the database is disposable until 13 Oct (rebuilt from sources plus cache, no migrations).

## 2026-10-02 (evening) — 3 Oct block started early: term parsing, many-to-many links, seal test fix

I chose deterministic parsing to derive material terms from exact quotes, using catalogue vocabularies and number/date normalisers. I rejected a new model stage because it would be non-deterministic and require separate evaluation, and rejected adding extraction fields because that would break the freeze. I accept under-merging when wording falls outside the parser’s rules. Missing required terms must produce `terms_incomplete`, and the rules must return needs review, never a confirmed gap based on an uncertain match.

I chose the `review_statement_commitments` link table because one statement can support several commitments, and each commitment can have several statements. This is a correctness fix to the approved ledger schema: its single `commitment_id` could discard a valid link and create a false contract gap. I rejected splitting quotes into rewritten statements because the original statements must remain immutable and exact. Only kept statements may have links.

I chose to tighten the seal test rather than skip it. The bug: in built mode, the static frontend mount takes a `{path}` parameter, and the old test checked the module-level app, so its result depended on whether `frontend/dist` existed. The new tests build both cases themselves and allow a path-taking route only if it is the mount named `frontend` serving exactly the built frontend folder. A negative control, a mount on a different directory, proves the rule fails when it should. A separate test sends six traversal requests at a decoy Coral Pay folder: none may return 200, and its canary must never appear in any response body, since checking only the status code could miss a leak. I rejected testing against the real sealed folder because a broken guard could expose the evaluation data. 97/97 tests pass with and without the built frontend. The ledger gate and its seal tests remain planned for 3 October.

The 30-minute small-fix box overran by 10 minutes because of the seal bug. I accepted that overrun to address the bug and strengthen the test, rather than carry forward weak evidence of protection. The overrun is recorded; tomorrow’s four-hour ceiling and cut order remain unchanged.

## 2026-10-03 — 3 Oct block: ledger, parser, filter, consolidation, grouping score

*Drafted by Claude from the day's decisions; reviewed and accepted by Lina.*

**Unlisted networks stay visible.** Chose: recognise blockchain network names from a small general list and record any network outside the catalogue as a term with `in_catalogue = false`. Rejected: ignoring anything the catalogue does not list (Claude Code's first proposal). Why: an unlisted network is an absolute limit, and the 4 Oct rule can only flag what the parser can see; ignoring Arbitrum would have turned KC1 from "not authorised: absolute limit" into a vague needs review.

**Go-live as a non-catalogue promise type.** Chose: a `go_live` promise type keyed on the type alone, with the date stored as an attribute. Rejected: treating every promise outside the catalogue as permanently incomplete. Why: date drift is a core finding; with the date outside the key, a go-live that moves between documents becomes one commitment with conflicting dates for the rules to flag. Recurring service obligations (the weekly status meeting) stay `terms_incomplete` for now.

**`not_assessed` as an explicit value.** Chose: `contractual_presence` stays NOT NULL with `'not_assessed'` added; `authorisation` also accepts `'not_assessed'`, and NULL keeps meaning "not applicable" only. Rejected: a nullable `contractual_presence` where NULL means "not yet assessed". Why: NULL must mean one thing; two columns reading NULL differently would let an unassessed commitment look clean or absent. Rules must handle `'not_assessed'` explicitly and never treat it as absent.

**Commitment status order.** Chose: Needs action, Needs evidence, Not in current documents, Resolved, No issues raised. Rejected: checking `unsupported` first (the DDL as first written). Why: removing a source must never hide an open issue.

**Many-to-many links enforced in the database.** Chose: triggers that refuse a link to any statement not kept in that review, and refuse dropping a statement that is linked. Why: the Python write path already respects this, but future routes, imports and scripts could miss it; the database rule applies to every writer.

**Import pinned and refusing re-runs.** Chose: the development import reads only the two run files named in config, and refuses if the deal is already imported (`--rebuild` builds into a temporary file and swaps it in). Rejected: "latest run file" and merge-if-equal. Why: the ledger's inputs change only by a deliberate, committed config change, never by a new run appearing; the same principle as the extraction cache key.

**Result.** Grouping score (`results/grouping_score_20261003T012724Z.json`): Harbour Bank 14/15 statements and 6/8 commitments exact; hard cases 8/9 and 6/7; all 10 must-holds pass. The two misses are accepted under-merges, not tuned away: S11 (SOW sentence with no mode of its own; due to be resolved through Annex A on 4 Oct) and K01 ("Arbitrum screening live for your launch", no mode, so it stays apart from K05). 297 tests pass.

**Process.** Closed in about 2 h 10 against a 4-hour ceiling; the brief's cut order was not needed.

## 2026-10-03 (working ahead) — 4 Oct block: decisions, decision rule, rules, reference resolution

*Built by Claude at Lina's request ("move fast, do everything, I will monitor"); Lina had not yet reviewed the code at the time of writing. Items marked **Lina to confirm** were applied as recommendations so the build could proceed. Brief: `docs/BRIEF_2026-10-04.md`.*

**`security_questionnaire` is reference-only (Lina to confirm).** Chose: add it to `REFERENCE_ONLY_DOC_TYPES` (logged as skipped, not extracted). Rejected: extracting it (no development example exists, so it would enter the sealed run untested) and leaving it unlisted (also not extracted, but flagged as an unknown type: noise). Accepted cost: a firm promise written only inside a security questionnaire is missed; reported with the customer-email gap. Settled before the 12 Oct candidate freeze, as required.

**PDF and DOCX pricing notes count as approval evidence (Lina to confirm).** Chose: the rules read a note's canonical text, so its content decides approval, not its file format; obligation on the 19 Oct adapters to keep one table row per line, with a test. Excel pricing notes remain a source but not evidence, as the plan says. Rejected: Markdown-only evidence (a deal-desk note is usually a Word file; refusing it would make most real uploads "needs evidence").

**Rules-vs-agent decision rule, fixed before any agent code (Lina to confirm).** Keep the agent only if, over three fresh runs per development deal, it (1) adds at least one material issue the rules miss that the labels support, (2) produces no unsupported finding and no uncited verdict, and (3) stays within ≤ $0.10 extra cost and ≤ 60 s extra latency per deal review (means of three runs; no single run above twice the bound), with a hard cap of 6 tool calls per commitment and 40 per deal. Variation is recorded, not a condition. Today's rules score 100% on both development deals (below), so condition 1 can only be met by a case the development labels contain and the rules miss; the honest expectation for 5 Oct is that the agent does not earn its place on development data, and the sealed run decides nothing about this rule.

**Rules run inside the consolidating review.** Chose: one review holds consolidation, assessments, issues, raised closure checks, reference resolutions and links (`consolidate_all(..., assess=True)`; the CLI runs it by default). Rejected: a second "rules review" copying the build-time review's rows. Why: the design says an app review runs every stage inside one review; a copy would duplicate snapshots and invite drift. `assess=False` keeps the 3 Oct behaviour for its tests.

**Pointer statements take missing terms from the section they cite (S11).** Chose: a statement citing "Annex A" fills a missing term from the complete statements inside that section of its own document, only when they agree on one value and match every key term the pointer states; `filled` records value, source statements and route; the quote never changes. Rejected: searching other documents for the section (the first version did, and a test caught it pulling in a re-dated SOW the contract does not incorporate; fixed before use). Result: S11 joins Ethereum real-time and Polygon batch; Harbour Bank grouping 15/15 statements and 8/8 commitments (was 14/15, 6/8). K01 remains the one accepted miss.

**`terms_incomplete` interpreted narrowly for authorisation (Lina to confirm).** The 2 Oct rule ("never a confirmed gap") is applied to contractual presence: an incomplete commitment gets *needs evidence*, never a contract gap. For authorisation, a verdict stands only if every catalogue completion of the missing terms agrees (Arbitrum is unlisted for every mode, so it is an absolute limit either way); otherwise *unknown / needs review*. Why: refusing a certain verdict because of an irrelevant missing term would hide an absolute limit.

**Rules, in brief.** Authorisation for firm commitments only, citing catalogue paths and the pricing-note line; anything unlisted is an absolute limit (`closes_by` only a changed or withdrawn promise); quantity limits compare unit and period; promises outside the catalogue (go-live, weekly meeting) are *unknown / needs review*, never inferred from implementation scope; no pricing note means *unknown*, not *no approval*. Presence follows the contract chain (contract plus everything it incorporates, by cited date); no contract means `not_assessed` plus an insufficient-evidence issue, never `absent`; a missing or unresolved reference makes an absence uncertain only where its topic overlaps the commitment (KR-03's missing Schedule 2 on reporting does not touch case audit history). Conflicting terms: same capability and key terms except one (mode, or volume at the same milestone) against a contract-side commitment, with a `contract_side_of` link. Every issue's `raised` closure check is written in the same transaction (tested by forcing the check insert to fail: nothing is written).

**Result.** `results/rules_score_20261003T025653Z.json` (the 02:25 run it replaced was deleted uncommitted; same scores): Harbour Bank authorisation 8/8, presence 8/8, issue sets 8/8, issues TP 8 / FP 0 / FN 0, no false flags on clean commitments; hard cases 7/7, 7/7, 7/7, TP 6 / FP 0 / FN 0, absolute limit 7/7. The unmatched Arbitrum fragment (K01) carries its own approval issue and an insufficient-evidence issue, reported separately. **Caveat:** the rules were written with these documents in view, so 100% on development data shows the rules do what was designed, not that they generalise; Coral Pay on 14 Oct is the honest test. 356 tests pass (297 before). No model calls; spend unchanged.

**Process note.** SQLite cannot write on the shared folder from Claude's side, so the ledger was built in Claude's workspace and copied into `workspace/ledger.sqlite`; two temporary files from the failed attempt were deleted with Lina's permission. Lina's check: rebuild and run the tests on the Mac (commands in WHERE_I_STOPPED.md); the result should match.

**Revised 3 Oct, 10:40 (Lina) — two of the four items reversed; two confirmed.**
- **`security_questionnaire` is extracted** (reverses the item above). Lina: questionnaire answers on SSO, MFA, encryption and certifications are commitments Delivery and Security inherit. Moved to `EXTRACTABLE_DOC_TYPES`; the extraction prompt is generic, so no frozen hash changes. Known consequences: the catalogue has no security capabilities, so these promises reach review as *Needs evidence* (authorisation unknown, contract presence uncertain) until a security section is added to the catalogue (Later list: it changes the catalogue hash and could disagree with the sealed labels, which were written against the 29 Sep catalogue). No development example exists yet: a fictional questionnaire fixture, its labels (Lina) and one extraction run are needed before the 12 Oct candidate freeze, or the sealed run is the first test of this document type, reported as such.
- **Excel pricing notes count as approval evidence** (reverses the plan's v3.2 line "a pricing note uploaded as a spreadsheet … does not count as approval evidence"). Same rule as PDF and DOCX: content decides, once the Excel adapter (20 Oct) gives one table row per line with sheet and cell references. Added condition: hidden sheets, rows or columns are read as a source but never count as approval evidence, and formula results count only as their values. Risk: Excel is last in the hard-stop cut order; if the adapter is cut, Excel notes revert to "source, not evidence" and the README says so.
- **Rules-vs-agent decision rule: confirmed** as written.
- **`terms_incomplete` interpretation: confirmed** after examples (Arbitrum unlisted for every mode: absolute limit stands; Polygon with no mode: real time needs approval, batch is standard, so *unknown / needs review*).

**Revised 3 Oct, 11:00 (Lina) — conclusions kept specific; evidence rules tightened.**
- **Absolute limits need an explicit catalogue rule.** Chose: `data/catalogue.json` now declares `"coverage": "complete"` and an `unlisted_rule` (anything unlisted is not offered and cannot be sold under a named exception). `rules.py` treats an unlisted item as an absolute limit only when that declaration is present; without it, the item is outside current authorisation and an approval can close it. This is the plan's rule ("an incomplete uploaded reference cannot prohibit by omission"), now stated in data instead of assumed in code. **Catalogue hash 11826c96 → 2d2d96a0** (first 8 of SHA-256). Consequence: `baseline.py` embeds the catalogue, so the 14 Oct baseline sees the rule too, as do the rules. Extraction does not read the catalogue; its hashes are unchanged. Scores unchanged.
- **Verdict wording states what was checked.** A volume with no region now reads, for example: "Checked: capability, volume, milestone. Not stated in the promise: region; the verdict is the same for every value the catalogue lists, but the deal's own region is not checked here." A deal-level region (deal metadata) is on the Later list; until then, a deal outside the catalogue's regions is not detected from an unstated region.
- **Approval needs a named approver; conditions are recorded.** `exception_approved` now requires the evidence line to name who approved it ("approved by …" or "Approver: …"); approval wording without one gives *unknown / needs review*. Conditions ("subject to", "provided that", "only if", "until", "limited to") are stored in `evidence_refs.approval` and must be carried into the contract (closure criteria on 12 Oct). Applies to every format.
- **Excel evidence (20 Oct adapter specification), replacing "hidden is never evidence".** Hidden is a display setting, not a measure of authority. Every cell keeps its sheet, cell reference and a visibility flag (sheet, row or column hidden) in `location_map`; the evidence citation and the handoff show the flag. Hidden evidence is assessed like any other: owner, scope and conditions. Formula cells count by their cached value only when one is present and not an error; a missing or error cached value gives *needs evidence*, never a guessed value.
- **Coral Pay labels stay sealed.** The questionnaire question is answered from memory or left open until 14 Oct. Procedure fixed now, before the run: the original labels and score are the headline and are never edited; every extraction not in the labels is reviewed once, with a written reason, and reported as a separate, labelled "label coverage" note (genuine promise the key omitted, or genuine false positive). No adjudicated score replaces the original.
- **Fair rules-vs-agent comparison.** The decision rule stands. Because the rules already score 100% on the practice deals, those deals cannot show added detection. Before any agent code on 5 Oct: a separate set of practice cases (paraphrases and out-of-vocabulary wording, for example "instant screening", "near-real-time", "about 25k payouts daily"), labelled by Lina, hashed and frozen before either checker runs on it. Both the rules and the agent are scored on it. If this set is not ready, the conclusion is "the agent showed no benefit on the tested cases", not "the agent adds nothing". Coral Pay stays for the final evaluation.

**Seal incident, 3 Oct, about 10:10 (Claude).** While surveying the repository, Claude ran `ls data data/*`, which listed the directory contents of `data/coral_pay/` (the names `BRIEF.md`, `docs`, `labels`) and the existence of `data/coral_pay.sha256`. No file inside `data/coral_pay/` was opened, read, hashed or searched, and no file content appeared in any output. This breaches the CLAUDE.md rule against listing the sealed folder. Cause: a wildcard listing of `data/`. Corrective rule: never use wildcards or recursive listings over `data/`; name development deal folders explicitly. The seal's integrity check (`shasum -a 256 -c data/coral_pay.sha256`) on 14 Oct is unaffected.

**Reproduced on Lina's Mac, 3 Oct 11:01.** Tests 361 OK; ledger rebuilt with `ledger_import.py --rebuild` and `ledger_consolidate.py`; `results/rules_score_20261003T030126Z.json` has metrics identical to the committed `rules_score_20261003T025653Z.json`, built on Claude's side. Commit 9ad2b6b.

## 2026-10-03, 11:40 — Practice set signed off and frozen (Tidewater Pay, `data/practice_cases/`)

*Applied by Claude from Lina's written sign-off; before any extraction or checker run on this deal.*

**Purpose and bias.** A targeted development comparison for rules vs agent, because the rules already score 100% on Harbour Bank and the hard cases. Drafted by Claude knowing the rules' vocabulary, so most issue cases use wording the rules do not recognise. Not an independent generalisation result; Coral Pay on 14 Oct remains the final evaluation.

**Judgement calls (Lina).**
- **Tron is a firm screening promise.** "Tron wallets will be covered by the same pre-release checks" refers to the screening in the immediately preceding turn; the quote stays verbatim and P02 carries that turn as context. Tron is recorded explicitly as the network. Authorisation verified against the catalogue: Tron is unlisted in every region, and the catalogue declares `coverage: complete` with its `unlisted_rule`, so it is outside current authorisation and not open to a named exception.
- **30k/day against 20,000/day is a contractual contradiction.** Interpretation: the SOW's unqualified "up to 20,000 payouts per day" defines contracted capacity from service start, with no separate phase or later milestone; the proposal promises about 30k/day from launch. The statements stay separate with their original wording. The 25,000/day limit is a separate overcommitment.
- **Graph analytics: no confirmed issue.** "Subject to Product sign-off" and "could be trialled" make it conditional; the approval dependency is recorded on PC5 and the case is kept for a possible demo.

**Wording corrections before freezing.** PC-04: "Case audit history is provided for all alerts." → "Case audit history is provided for every case." (scope matches the proposal). PC-02: "Our name screening service handles up to 120,000 checks every day." → "Our service handles up to 120,000 sanctions checks every day." (the comparison with the sanctions-screening limit is explicit). Statement quotes P13 and P06 and the affected label evidence updated; IDs unchanged.

**Ground truth validated.** 5 documents, 15 statements, 12 commitments (5 with issues, 7 without, including one exploratory and one conditional); every quote and the P02 context quote verbatim in its source; every statement links to a labelled commitment and every commitment has a statement. Catalogue and pricing-note claims checked: unlisted rule; Polygon real time SG requires named approval; Polygon batch and Ethereum real time standard; CAP-007 SG 100,000 screenings/day; CAP-023 SG 25,000 payouts/day; CAP-024 SG roadmap, named approval, GA 2027-06-30 (end of Q1 2027 is earlier); CAP-020 SG roadmap, GA 2027-09-30; CAP-014 and CAP-010 standard; the contract cites the SOW's date. No discrepancy found. One stated interpretation: a "sanctions check" is counted as a catalogue "screening".

**Frozen.** `data/practice_cases.sha256`: the five documents, the manifest (it decides which documents enter a run) and both label files; verified immediately after creation. BRIEF.md, labels, DECISIONS.md and the fingerprint file are never extraction or checker inputs. Labels are not changed after extraction or checker results; misses and disagreements are recorded against them.

**Practice deal extracted and pinned, 3 Oct 11:44.** One run on Lina's Mac: `results/extract_practice_cases_20261003T034401Z.json` (PC-01 4, PC-02 6, PC-04 5, PC-05 0 statements; PC-03 skipped as reference-only; $0.031). Pinned in `LEDGER_IMPORT_RUN_FILES`; `practice_cases` added to `LEDGER_DEALS` (subset check of `ALLOWED_DEALS` holds). The import tests for the two original deals now pin `LEDGER_DEALS` to those deals; a separate test covers the practice deal's fingerprints, import and raised checks, and asserts no score. No result on this deal has been looked at yet.

## 2026-10-03 (working ahead, past the ceiling at Lina's request) — 5 Oct block: bounded agent, fair comparison set up

**Rules baseline on the practice set, recorded before agent code** (`results/rules_score_20261003T035110Z.json`): 0 of 5 approval issues found on Tidewater Pay; all five reach review as *Needs evidence*; no false flags on clean commitments. This is the blind spot the set was built to expose (bias disclosed).

**Agent as escalation, not replacement.** Chose: the agent sees only firm commitments the rules leave *unknown / needs review*. Rejected: the agent assessing every commitment (more cost and latency for verdicts the rules already make with citations, and more chances of an unsupported flag). Why: rules where the reference data is authoritative, a model only where language is ambiguous.

**The agent interprets; code verifies.** Chose: the agent proposes catalogue terms with verbatim evidence phrases and citations; code recomputes the verdict from those terms with the same rule functions and rejects anything its own evidence does not support. Rejected: trusting the agent's verdict with a citation check only. Why: a citation can exist and still not support the conclusion; recomputing makes "no unsupported findings" checkable, not a matter of reading rationales. Consequence: the agent's contribution is mapping paraphrase to catalogue terms; it cannot invent policy.

**Same model as extraction** (`config.AGENT_MODEL = EXTRACTION_MODEL`), bounds in `config.py` as fixed on 3 Oct. Tests use a scripted fake client (no spend): a careful script finds the 5 missed approval issues with no false flags; one over-reaching verdict fails condition 2; a looping agent is capped and fails condition 3; variation across runs is recorded. These test the code, not the model. 377 tests pass.

**Scoring now covers every ledger deal** (`score_grouping.build_report`, `score_rules.build_report` iterate `config.LEDGER_DEALS`); the deal-specific grouping must-holds are unchanged.

## 2026-10-03, 12:24 — Rules vs agent: result (pre-registered rule applied as written)

**Runs.** `agent_compare.py --runs 3` was run twice on Lina's Mac (the first by accident), so six runs per deal: `results/agent_compare_20261003T042156Z.json` and `results/agent_compare_20261003T042424Z.json`. Both are reported; neither is discarded. Total spend about $0.68 (above the $0.10–0.30 estimate, because of the double run and about $0.09 per practice-set run).

**Verdict under the decision rule: the rules power the demo.** Condition 1 false (no accepted verdict added an approval issue), condition 2 false (every one of the 7 practice-set verdicts was rejected in all 6 runs), condition 3 true (practice set: mean $0.091–0.094 and 38–40 s per review, against $0.10 and 60 s; Harbour Bank and hard cases about $0.01 and 5 s, one escalated commitment each, both correctly left as *unknown*).

**Why the verdicts were rejected (from the saved verdicts, read after the run).** In every run the agent's authorisation was the one its own terms implied: all five approval issues (Polygon "instant risk check", Tron, 120,000 sanctions checks, 30k payouts, VASP by Q1 2027) and both clean paraphrases (Ethereum "risk-checked live", "audit trail") were judged correctly in substance. Every rejection was a failure of the evidence contract: no evidence phrase for the capability itself; a region (SG) or asset (NUSD) stated without a supporting phrase from the quote; the volume tagged as term "limit" instead of "quantity"; a catalogue path without its region ("CAP-014" instead of "CAP-014/SG"). Part of that is the agent's fault and part is mine: the tool schema did not name the allowed term labels or say that the capability itself needs a phrase. Under the rule as fixed, a rejected verdict that claims more than *unknown* is unsupported, so condition 2 fails. That stands. No label, prompt or validator was changed after the result.

**A real rules defect the comparison exposed.** For the sanctions and payout volumes, the rules (and so the validator's expected citation) cited the Polygon row "No named exception approved for Tidewater Pay" as if it were a deal-wide statement. The verdict was still right (no approval recorded), but the citation was wrong. Fixed after the run in `rules.note_finding`: a deal-wide "no exceptions" line must not be a table row or name a capability. Test added. Development scores unchanged (377 → 378 tests).

**What this means, said plainly.** On these cases the agent read the paraphrases correctly but could not yet back its reading with evidence in the form the code checks. It earns no place on development data. The agent stays in the repository as an escalation step with its interface defect recorded; any change to its interface is a new, versioned configuration, and it is not re-judged on the practice set (now seen). Whether the agent runs on Coral Pay on 14 Oct is decided before 12 Oct and recorded with its configuration.

## 2026-10-03 (afternoon, working ahead) — Agent v2 interface; 12 Oct block built early: fixes, cache, recheck, scenarios

**Agent v2 (not re-run on the practice set).** The tool schema now lists the allowed term labels, requires a phrase for the capability itself, says to leave unstated terms null, and that a catalogue path always includes its region; runs record `agent_version`. Why: v1's failure was partly an interface defect (DECISIONS 12:24). Rejected: re-running on the practice set (now seen; that would be tuning to the test). Whether v2 runs on Coral Pay is decided before 12 Oct.

**Closure is a decision about evidence.** An issue is met only when the recheck no longer finds it and its own closure condition holds with cited evidence (table in `docs/BRIEF_2026-10-12.md`). Rejected: "met when not re-raised". Why: that would let a change of checker, or a removed document, close an issue; the plan says closure is about evidence, not about which checker ran last.

**Identity across reviews by largest statement overlap.** Rejected: matching by term key. Why: the key is exactly what a fix changes (an annex moving from batch to real time); the quotes that made the promise are what persist.

**Withdrawal closes only with replacing versions.** A commitment with no statement left closes its issues only if every source that made it has a newer included version without it. Why: deleting or excluding a document must never look like withdrawing a promise.

**Development rechecks reuse extraction by version identity.** An unchanged source version reuses the extraction its previous review used (for development deals, the imported run-file rows, which stay non-reusable by key). A changed extractable version goes through the full-key cache. Why: the same version is the same text and the same frozen run; calling the model again would only add variation.

**Scenarios.** Five expected outcomes written before the recheck code ran on them (`data/scenarios/scenarios.json`). With a scripted extractor: 5 of 5 and the unchanged-input control pass; 390 tests pass. The real-model run (two SOW extractions) is Lina's.

**Scenarios with the real model, 3 Oct 12:51** (`results/scenarios_20261003T045108Z.json`, after commit a3827e1 pre-registered the expected outcomes): control (unchanged-input rerun, no model client) passes; **5 of 5 scenarios as expected**; $0.029 for the two revised-SOW extractions. Plan metric "Resolution correctness: 5 of 5" met on development fixtures; written by Claude with the rules in view, so it shows the design works as specified, not that it generalises.

## 2026-10-03 (afternoon, working ahead) — 13 Oct block, first part: workspace API and screens

**What exists.** `workspace.py` (read model in plain language), new routes in `api.py` (documents with text/Markdown upload and include/exclude, Review deal, register, fixes, issue owner and note, user deals), `review_freshness` computed from the source-set and decision-evidence hashes ("Up to date", "Review out of date", "Not reviewed"), and a rebuilt React workspace (deal list, documents, register, commitment card with quotes, issues, next step, owner and note, and one fix form that records the fix and rechecks). Recheck now also runs a deal's first review (user deals). 399 tests pass.

**Security choices.** The only path parameter stays `{deal}`; everything else is in a JSON body. A deal is either in `UI_DEALS` or an existing user deal (`u_` + 16 hex); anything else is one generic 404 (hard cases and Coral Pay included). Writes need `X-Requested-With: deal-workspace` and a JSON body, which forces a CORS preflight the server never grants, so another website cannot post to the local app. The model key stays in the server's environment; a review that needs extraction without it answers 409 with a plain instruction.

**Bug found by driving the real browser, not by the tests.** The database connection was opened by a FastAPI dependency on one worker thread and used on another; SQLite refused. TestClient did not show it. Fixed with one connection per request opened with `check_same_thread=False` (API only).

**Checked in a real browser (Claude's side, headless Chromium):** register loads with no console errors; uploading HB-05 v2 marks the review out of date; recording the approval fix and rechecking closes only the approval issue, leaves the contract gap and conflict open, and returns the deal to "Up to date". Copies of the code and development data were moved to Claude's side for this in a temporary archive (no labels, no Coral Pay), then deleted.

**Open for 13 Oct:** integration checks on development data, then record the final evaluated configuration; CSV and readable handoff export (19 Oct); internal keys such as "C07" still appear inside some evidence text.

## 2026-10-05 — Handoff view and exports (`docs/BRIEF_2026-10-05_handoff.md`)

**What exists.** `handoff.py`, `handoff_schema.sql`, five routes in `api.py`, a Handoff panel in the workspace. A save is an immutable snapshot of one specific review (version table with abort triggers; a new save is a new version). The view, CSV and printable HTML summary are rendered from the saved snapshot, never from the live screen. No model calls, no pipeline file changed, no new extraction.

**Decisions.** (1) "Ready for handoff" is refused while any issue is open: a reviewer cannot erase a system finding. (2) The readable export is printable HTML (browser Save as PDF), not a generated PDF/DOCX. (3) Milestones, dependencies and service obligations appear only as commitments already in the ledger. (4) Saving is refused while the review is out of date or missing. (5) Schema: additive and idempotent (`handoff_schema.sql`, applied on first use), so `schema_version` stays 1 and an existing database keeps its data. (6) Saved version travels as `?version=N`; `{deal}` stays the only path parameter. (7) Document keys (HB-05, D-01), commitment keys (C07) and statement keys are removed from all handoff and register text; documents are named by their display name.

**Owner confirmation (Lina's change to the brief).** The brief's "every open issue has an owner" check could never fail: `issues.owner_function` is NOT NULL and rules assign a default. Replaced by: "Proceed with open items" needs the reviewer to tick the owner of each open issue in the save form. Ticks live in the snapshot only; the issues table is unchanged. Each owner shows as "default" or "confirmed by [reviewer]" in the view, CSV and summary. A confirmation records that someone looked at the owner; it does not make the owner correct.

**Known limits.** The CSV "Evidence quote" for an issue lists every statement behind the commitment (joined with " | "), not only the one that triggered the issue. Document names are the display names in the ledger, which for the development deals are the file names (e.g. `HB-05_pricing_services_note.md`).

## 2026-10-05 — Text-based PDF and Word adapters (`docs/BRIEF_2026-10-05_pdf_docx.md`)

**What exists.** `adapters.py` (PDF text layer with a `[Page N]` marker per page; Word body and tables in order, tables flattened with " | " in the canonical text only, headers and footers not read, skipped images, text boxes, embedded objects, footnotes, comments and tracked changes reported; Markdown and text unchanged), upload of `.pdf` and `.docx` as base64 inside the existing JSON body (same deal allowlist, write guard and `{deal}`-only path parameter), a Format column and plain-language problems in the Documents table, page citations ("Proposal, version 1, page 3") in the register, handoff view and summary, and "Proposal (page 3)" in the CSV Source document cell. No evaluated pipeline file, prompt or hash changed; no model call in any test.

**Libraries (pinned in `requirements.txt`).** `pypdf==6.19.0` (pure Python, BSD, text layer only; PyMuPDF is AGPL, pdfminer.six and pdfplumber are heavier than needed), `python-docx==1.2.0` (opens the package and walks the body; text is read with `lxml` XPath because its text API misses tracked insertions), `lxml==6.1.3` (its dependency, pinned for reproducibility). Test PDFs come from a small hand-written writer (`tests/fixtures/make_formats.py`), so no PDF-writing library is needed; fixtures are generated at test time and nothing binary is committed.

**Decisions.** (1) Problems an adapter finds are stored in an additive, immutable table (`source_version_notes`, `adapter_notes_schema.sql`, applied on first use), so `schema_version` stays 1 and an existing database keeps its data. (2) The extraction cache key is unchanged: it already includes the hash of the canonical text, so a different adapter output changes the key, while a new adapter version that yields identical text correctly reuses the cache; bumping `CACHE_FORMAT_VERSION` would have forced re-extraction of everything. The adapter name and version (with the library version) are recorded on every source version. (3) Limits: 10 MB upload, 200 PDF pages, 1,000,000 characters of canonical text, 50 MB unpacked Word; there is no per-file timeout, so the limits are the only guard. (4) A scanned PDF is refused when no page has text and warned about per page when partial. (5) Not validated by the sealed run; the README and the Documents table hint say so. (6) A quote's page is shown only when the quote appears on one page of the PDF; a quote that crosses a page break belongs to the page it starts on; an ambiguous quote shows no page.

**Real-model check (Lina's, about $0.01 per document):** `.venv/bin/python check_formats.py [--pdf FILE]... [--docx FILE]...` extracts the generated PDF and Word versions of HB-04 (and any file you export from Word or Pages) once each and compares firm statements and quote validity with the Markdown HB-04 run. **Result (5 Oct, `results/formats_check_20261005T063309Z.json`, $0.0405 in total, one run per format):** quotes valid 6 of 6 (generated PDF), 5 of 5 (generated Word), 5 of 5 (PDF exported from TextEdit). All material firm statements were found in every format. The one difference: "A draft Statement of Work will follow." is missing from the Word and TextEdit PDF runs. It is a sales-housekeeping statement the filter removes, so no finding changes. One run per format cannot separate format loss from model variation. **Verdict: PDF and Word are adequate on development documents; not validated by the sealed run.**

**Process note (5 Oct).** While reading the codebase for this change I ran `ls data`, which printed the name of the Coral Pay folder. Its contents were never read or listed and nothing inside it was opened. The listing was a slip against the sealed-test-set rule; the seal itself (the four deny rules) was not tested or bypassed.


## 2026-10-05 — Simulated reviews, integrity rules and signing-brief hypotheses (`docs/BRIEF_2026-10-06_integrity.md`)

**Evidence and credit.** Claude ran the simulated implementation review with a simulated reviewer persona (Priya). Codex/ChatGPT supplied the founder-perspective critique and interactive mock-ups. Lina directed the exploration and owns the decisions. Neither exercise is real user validation.

Step 2 did not establish unaided issue discovery. The open issues were named before the simulated reviewer reacted; a successful approval-only fix followed by recheck was not observed in that exercise. No claim can be made that a real reviewer independently found the remaining contract issues.

The simulated ownership answers suggested that Product and Commercial address approval and contract gaps, and that the document-gathering function could run the review. These are hypotheses, not observed workflow fit.

Real Checkpoint 1 is booked for Tuesday 6 October 2026. Complete the unaided step 2 before showing the corrected design concepts. Record what the reviewer actually finds and whom they name as accountable. The freeze remains dependent on the real checkpoint.

**What I chose — integrity work now.** Inspect and preserve the following guarantees, implementing only the gaps found:

- Accepting a risk leaves the finding open and does not reduce the open count.
- Human impact assessments, accountable names and deadlines do not change finding status.
- Accepted risks and signing decisions are bound to the evidence reviewed.
- Saved handoffs retain their original contents and state after later changes.
- Ownership carries forward only when recheck identifies the same issue.

These rules hold whether the person using the product is a founder, an implementation lead or someone assembling the deal packet. They do not depend on validating a new layout.

**What I chose — test before building.** Test the signing-brief layout, consequence categories, founder as recipient, and proposed accountability/deadline fields at the real checkpoint. Show the concepts only after the unaided issue-discovery test. Record both useful and unhelpful reactions; do not treat endorsement of a concept as demonstrated use.

Describe responsibilities as functions: gather documents, review findings, make corrections, decide whether to proceed, and receive the handoff. One person may perform several functions in a small company.

The founder is a possible decision-maker, not an established primary user. The signing brief and Delivery handoff should use the same commitment record. Test whether that workflow fits before building the layout.

**Business-impact hypothesis to test.** The documents support the finding; a person assesses its business consequence.

An empty assessment shows "Business impact: not assessed." It must not contain a system-written consequence sentence. Proposed unselected categories are:

- Launch date pressure
- Extra delivery work
- Scope disagreement
- Roadmap change
- Pricing or commercial terms

The reviewer selects applicable categories and adds an explanatory note. Also provide "Assessed: no material impact", with reviewer attribution, so a completed assessment is distinguishable from nobody having assessed it. This is the reviewer's judgement, not a system assurance.

Impact confirmation records the evidence context. Changed evidence makes the earlier assessment require reassessment; it is not silently presented as current.

**Escalation and ordering hypothesis to test.** At signing, the brief's issue list contains every open issue and every applicable accepted-risk decision, without duplicate rows.

An accepted-risk decision is applicable when it was made on this deal for an issue still open in the current review. Show whether it is current or needs re-confirmation. Acceptance associated with an issue that is now closed remains in history rather than appearing as a current open risk. Superseded decisions remain in history too.

No importance judgement is required for inclusion. Unassessed issues still appear. Default ordering is "Not prioritised · Commitment name A–Z." Any later human prioritisation needs a recorded reason.

**Version-binding rule and pre-implementation inspections.** Accepted risks and signing decisions record both the source-set hash and the decision-evidence hash of the completed review they concern. Impact confirmations retain the relevant evidence binding as well.

If either bound hash changes, earlier accepted risks and signing decisions become "Needs re-confirmation". Earlier impact confirmations become "Needs reassessment". Preserve the original records and evidence context; re-confirmation or reassessment creates a new record. Historical handoffs are not rewritten.

Before implementation, inspect:

1. Hash coverage: how each hash is calculated; whether the catalogue, pricing/approval evidence and other inputs affecting findings or decisions are included; and whether the hashes are deal-level or issue-level. Do not assume the catalogue is covered. Define and close any coverage gap before relying on the binding.
2. Issue identity: how the ledger creates issue IDs and reconciles findings after recheck. Establish how it distinguishes the same continuing issue from a new issue, including changed terms, a different issue type, and an issue that closed then reappeared. Do not assume that the same capability or similar wording establishes identity.

An accountable person and deadline belong to the issue. They may carry forward only for a verified continuing issue. New or ambiguous issues must not silently inherit them. Carrying ownership forward never makes an earlier risk acceptance or impact assessment current.

**What I rejected, and why.**

| Rejected | Why |
| --- | --- |
| System-written business-impact conclusions | The current document checks do not establish business consequences; a person must assess them. Hedging a generated sentence does not make it assessed. |
| Numerical risk score | There is no defensible calculation or validation basis. |
| Separate founder application with a second commitment record | Duplicated records could drift; prefer views of the same ledger. |
| Claims of delivery readiness | The engine does not assess staffing, implementation effort or delivery capacity. |
| Building the proposed layout from simulation alone | A simulation can generate hypotheses but cannot establish reviewer behaviour or workflow fit. |

**Acceptance checks — predicted outcomes, not test results.**

| Check | Predicted result |
| --- | --- |
| Accept a risk | The finding remains open and the open count is unchanged. |
| Confirm impact, including "no material impact", or name an accountable person | Assessment/ownership metadata changes; no finding's status changes. |
| Make later decisions after saving a handoff | The earlier handoff retains its original contents and state. |
| Add a new contract version | Earlier signing decisions and accepted risks need re-confirmation; original records remain available. |
| Open the proposed signing brief | Its issue list contains every open issue and applicable accepted risk, without duplicate rows; closed and superseded acceptances remain in history. |
| Recheck a continuing issue, then a genuinely new or ambiguous issue | Ownership/deadline carry forward only for the verified continuing issue. |
| Change an issue's supporting evidence after confirming its impact | The earlier assessment needs reassessment; its original version is preserved and no finding is closed by that assessment. |
| Change catalogue or approval evidence affecting a decision | The verified hash binding detects the change and prevents the earlier decision or impact assessment appearing current. |

**Schedule.** The hours ceiling is lifted. The 22 October hard stop, Coral Pay seal until 14 October, and end-of-day learning close remain unchanged.

The next implementation brief covers only integrity rules and the two pre-implementation inspections (`docs/BRIEF_2026-10-06_integrity.md`). Layout and recipient choices await the real checkpoint. No integrity change requires opening Coral Pay before the sealed evaluation.

## 2026-10-05 — Reframe: handoff record first, pre-signature review second

Decision: Position the product as a handoff record for Delivery, CS and
Support ("the deal as it was actually promised"), with pre-signature use
as the upgrade ("run it before signature and gaps can still be fixed in
the contract").

Why: The users who feel the pain are the ones receiving the deal; CS
leadership holds budget for reducing escalations; it avoids positioning
against Sales' incentive to sign.

Not changed: engine, rules, fix routes, recheck, handoff build. No code
changes before Checkpoint 1. Scope freeze 12 Oct still applies.

Accepted weak point: document assembly still depends on Sales. Today's
answer: the AE attaches documents at handoff; later, connectors (not built).

To test at CP1: does the reviewer name a real, recent kickoff surprise
and its cost; who would assemble the documents; trust vs AE handoff notes.

Deferred to 12 Oct: handoff record as landing screen; post-signature
"reset the expectation with the customer" fix route.

## 2026-10-06 — Checkpoint 1 (real reviewer) and resulting decisions

Reviewer: Head of Growth, former colleague, revenue side. Not the planned CS/delivery profile; friendly reviewer, so praise is not evidence.

What happened
- Step 2 (unaided gap-finding) not tested: I named the contract gap before asking. Wrong evidence attached twice in the demo (KR-05 file; then aligned SOW typed as pricing note).
- Reviewer could not tell what the fix had resolved; main page still said "needs approval". I was confused too.

What he said
- Owners: deal owner / CRO / commercial lead / pre-sales lead; documents assembled by pre-sales or sales.
- One deadline per deal, not per issue ("not a project management tool"). Ask where each item lives after handoff.
- "Accept the risk" alarms people; prefers "okay to proceed".
- Wants AI-suggested business impact (person can override). "Where does the AI come in? It seems rules-based."
- Stopper: if it feels like a burden. Needs a quick deal summary at the top.

Decisions
- Prioritise layout (`docs/BRIEF_2026-10-06_layout.md`), after integrity Part B. Overview: compact rows, finding types in words, two separate counts (unresolved vs awaiting decision), sort by open findings.
- Fix inside the finding: attach, confirm document type, Save & check, result in place; resolved findings name their evidence.
- "Okay to proceed" and "Must fix before signing" are per-finding human decisions with name and reason; never change a finding. "Must fix" stays visible until a named person clears it.
- Re-confirmation is deal-wide for the prototype. Rejected: narrow carry-forward (needs tested dependency tracking). Cost: re-confirmation noise on large deals.
- Deal summary typed by a person. Rejected: generated summary (new model call, new scope).
- Business impact stays "Not assessed" until a person records it. AI-suggested impact → Later; check with a delivery reviewer first.

Triage
- Before freeze: layout brief; integrity Part B.
- After freeze: deal-level deadline field; "where it lives after handoff".
- Later: AI-suggested impact; narrower re-confirmation.

Rule slips (Claude Code): `ls data` listed coral_pay names (not read); one `git diff --stat`. Seal intact.

## 2026-10-06 — Checkpoint 1 (real reviewer) and resulting decisions

Reviewer: Head of Growth, former colleague, revenue side. Not the planned CS/delivery profile; friendly reviewer, so praise is not evidence.

What happened
- Step 2 (unaided gap-finding) not tested: I named the contract gap before asking. Wrong evidence attached twice in the demo (KR-05 file; then aligned SOW typed as pricing note).
- Reviewer could not tell what the fix had resolved; main page still said "needs approval". I was confused too.

What he said
- Owners: deal owner / CRO / commercial lead / pre-sales lead; documents assembled by pre-sales or sales.
- One deadline per deal, not per issue ("not a project management tool"). Ask where each item lives after handoff.
- "Accept the risk" alarms people; prefers "okay to proceed".
- Wants AI-suggested business impact (person can override). "Where does the AI come in? It seems rules-based."
- Stopper: if it feels like a burden. Needs a quick deal summary at the top.

Decisions
- Prioritise layout (BRIEF_2026-10-06_layout.md), after integrity Part B. Overview: compact rows, finding types in words, two separate counts (unresolved vs awaiting decision), sort by open findings.
- Fix inside the finding: attach, confirm document type, Save & check, result in place; resolved findings name their evidence.
- "Okay to proceed" and "Must fix before signing" are per-finding human decisions with name and reason; never change a finding. "Must fix" stays visible until a named person clears it.
- Re-confirmation is deal-wide for the prototype. Rejected: narrow carry-forward (needs tested dependency tracking). Cost: re-confirmation noise on large deals.
- Deal summary typed by a person. Rejected: generated summary (new model call, new scope).
- Business impact stays "Not assessed" until a person records it. AI-suggested impact → Later; check with a delivery reviewer first.

Triage
- Before freeze: layout brief; integrity Part B.
- After freeze: deal-level deadline field; "where it lives after handoff".
- Later: AI-suggested impact; narrower re-confirmation.

Rule slips (Claude Code): `ls data` listed coral_pay names (not read); one `git diff --stat`. Seal intact.

---

## 2026-10-09/10 — Unattended build day; decisions; pre-freeze runs

*Built by Claude while Lina was away (layout redesign, Excel and PowerPoint adapters). Full detail, alternatives and checks: `docs/DECISIONS_DRAFT_2026-10-09_layout.md`; spec `docs/SPEC_xlsx_pptx_canonical_text.md`. Built on Part B before Part B was reviewed (the brief said wait).*

Decisions (Lina, 9 Oct):
- **Agent v2 on Coral Pay: option C** — smoke test on development deals first, then one run on Coral Pay. Rejected: rules only (drops the headline's third column); v2 untested on the sealed run; a fresh practice set (2–3 h labelling before the freeze). Decision rule unchanged.
- **A spreadsheet approval cell whose formula has no saved value gives *Needs evidence*** (confirms 3 Oct). `rules.py` changed before the freeze; rules scores on all three development deals identical to 3 Oct.
- **Hidden PowerPoint slides are read and flagged.** Speaker notes not read.
- **A fix addresses only the finding it was attached to.** Rejected: every open finding on the commitment. Other findings the document closes are reported as effects.

Runs (10 Oct, Lina's Mac):
- Real-model 5/5 scenarios: all pass, control pass, $0.025 (`results/scenarios_20261010T025651Z.json`). First real-model check of the Part B `recheck.py` change. Regression check only for the formula rule (no scenario uses a spreadsheet).
- Agent v2 smoke test: ran end to end, both deals within bounds, $0.022 (`results/agent_smoke_20261010T030129Z.json`). Proves v2 runs, not that it maps paraphrases: both items went to *unknown* in one call.
- 568 tests pass. Demo reset.

**Configuration for the 14 Oct sealed run (recorded before the 12 Oct candidate freeze).** One run per configuration, nothing changed afterwards: (1) baseline; (2) rules; (3) rules + agent v2 as escalation for firm commitments the rules leave *unknown*. Extraction frozen v1: `claude-sonnet-5`, thinking `model_default`, `MAX_TOKENS = 8000`. Agent: `AGENT_VERSION = 2`, same model, `AGENT_MAX_TOKENS = 4000`, 6 tool calls per commitment, 40 per deal, 15 turns; bounds $0.10 and 60 s per deal review. Decision rule as written 4 Oct; on Coral Pay condition 2 is judged on the single run (v1 was judged on three runs on the practice set). Rules as of 9 Oct.

---

## 2026-10-10, 11:30 — Security-questionnaire fixture: first extraction of the document type (pre-freeze)

Fixture `data/questionnaire_cases/` (extraction only; in `ALLOWED_DEALS`, not `LEDGER_DEALS` or `UI_DEALS`). Labels written by Claude at Lina's request, who also wrote the document: a smoke test of the document type, not an accuracy measure. Run `results/extract_questionnaire_cases_20261010T032843Z.json`, $0.021; evaluation `results/eval_extract_questionnaire_cases_20261010T032843Z_t0.8_L2c3f3ead.json`.

- Recall 8/8 (firm 7/7), precision 8/9, all quotes valid. Questionnaire tables read without a format problem.
- **False positive, as predicted:** the bare answer "Yes." (row 10) extracted as a firm statement with the quote "Yes." It carries no terms, so in a full review it would become an unnamed commitment needing evidence: noise for Delivery. Known limitation of a frozen prompt; recorded, not fixed. Expect the same on any yes/no questionnaire, including the sealed deal.
- **Language mismatch:** row 6 ("…will share the executive summary … on request") labelled firm, extracted conditional. Arguable either way ("on request" is a trigger, not a hedge). Labels are not changed after results; reported as is.
- Nothing here changes the evaluated configuration. The freeze can proceed.

## 2026-10-06 — Decision integrity (Part B; accepted by Lina 10 Oct after review): three-hash bindings, versioned hash definitions, and a correction on extraction reuse

**Correction.** `docs/PLAN_v3.4.md` (line 79, "Recheck must be deterministic where inputs haven't changed") says: *"A recheck reuses a cached result only when the whole key matches; any change re-extracts that document."* `docs/LEDGER_SCHEMA.md` line 183 says the same of reuse. That is true of the **cache lookup** (`extraction_cache.lookup`, `get_or_extract`) and false of the **recheck**.

What the code does (`recheck.py`, the sources loop): a source version that already had an extraction in the previous review reuses that `extraction_id` by version ID, without consulting the cache key. The full key is checked only for a version with no extraction in the previous review (a new version, or one re-included). So a recheck can reuse an extraction made under a different model, prompt, schema, thinking mode or `MAX_TOKENS`, and an extraction stays with its version across any number of configuration changes. Imported run-file extractions (`reusable = 0`) are carried forward the same way. Checked on 6 Oct: with `MAX_TOKENS` and the model ID changed and a model that fails if called, an unchanged-source recheck made 0 model calls and recorded the old extraction as a hit; a new version under the changed config reached the model.

Why it was left as it is: forcing re-extraction on any configuration change would cost model calls and could change findings through model variation, which the cache exists to prevent. The plan's guarantee that matters (no model variation on unchanged inputs) holds. The sentence in the plan should read: *"A cache lookup hits only when the whole key matches. A recheck reuses the extraction its previous review used for an unchanged source version, whatever configuration made it; a new or re-included version is looked up by the whole key."*

**What changed instead (record and show, no gating).** Each review now records which extraction cache key every source used (`review_bindings.extraction_keys`; `NULL` for imported ones). When any source was read under settings other than today's, the review shows one plain line: "Some documents were read under earlier extraction settings." It is never a reason to mark a review or a decision out of date, because the documents did not change.

**Decision.** Every saved decision is bound to three hashes of the review it concerns: source set, decision evidence and config (catalogue and rules). Freshness compares all three, with plain reasons: "Documents changed", "Approval or fix evidence changed", "Catalogue or rules changed". The catalogue is not merged into the source-set hash.

**Hash definitions are versioned.** Definition 1: `reviews.config_sha256` as recorded before 6 Oct (`ledger_consolidate.rules_sha256`: five rule files and the raw catalogue bytes). Definition 2 (`integrity.py`): the same files plus `recheck.py`, which decides closure and identity and was outside the hash, and the catalogue as canonical JSON, so re-indenting is not a change. A record is compared only against a hash of its own definition. A record under an older definition reads "Needs re-confirmation: checking rules updated", never "Documents changed". An imported review has no config hash and reads "Not comparable: rerun the review". Neither stops the review being called up to date on its documents, but neither can back a new handoff or decision until a rerun (which makes no model call) moves the review to definition 2. Existing handoffs are never rewritten; their binding is derived from their review.

**Human records never touch findings.** Accepted risks, impact assessments and accountable people live in their own append-only tables with immutability triggers. They never write to `issues` or `closure_checks` and are not part of `decision_evidence_sha256`. Recording one leaves findings, open counts and review freshness as they were. An impact assessment whose issue context has changed reads "Needs reassessment"; the original is kept.

**Ownership carries forward only for the verified same issue.** An accountable person is stamped with a hash of the issue's context (type, subject, the commitment's term sets and quote hashes, the same for the conflicting commitment, the evidence of its latest closure check) and the id of its latest closure check. It carries forward automatically only if the issue row is the same, that context is unchanged, and no closure check has closed the issue since. Otherwise it reads "Confirm owner still applies" and a named person must confirm. New issues start with none. Carrying ownership forward never makes an accepted risk or an impact assessment current. Case traced on Harbour Bank: a revised SOW changing only the batch interval keeps the same issue row (the interval is not a term the rules compare) and now asks for confirmation, because the quote behind it changed.

**Rerun labels.** `reviews.run_kind` allows four values and a CHECK cannot be changed additively, so a rerun after a document change is still stored as `unchanged_input_rerun`. Whether inputs changed is recorded in `review_bindings.inputs_changed` (1 changed, 0 unchanged, `NULL` for a first review) and in the review note ("recheck of review N; documents changed"). Any count of unchanged-input reruns must use `inputs_changed`, not `run_kind`.

Not changed: `extract.py`, `schema.py`, `sales_filter.py`, `ledger_consolidate.py`, `terms.py`, `references.py`, `rules.py`, `agent.py`; `schema_version`; any existing row.

**Accepted 10 Oct.** Reviewed with Claude after the real-model 5/5 rerun passed with Part B in place. Known costs accepted: deal-wide re-confirmation and evidence-sensitive owner checks create re-confirmation noise (one new pricing note re-asks every decision and every approval owner on the deal); narrowing them is on the Later list. Plan and ledger schema corrected on the cache-key sentence.

---
