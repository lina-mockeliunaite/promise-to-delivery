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
