Claude product and build revision brief
Lina Mockeliunaite · 30 September 2026 · replaces the previous revision brief
Revise the remaining plan around a working deal workspace. This is an authorised product and schedule revision before Day 8. Preserve the measured extraction baseline and completed work.
1. Decisions to record
- Target completion: Tuesday 20 October. Checkpoint 2 remains Friday 16 October.
- Keep the core workspace AND the technical work: consolidation, conflict rules, the bounded agent, rules-versus-agent comparison, regression, the sealed evaluation and the learning record.
- Keep the agent experiment even if the evidence ultimately favours rules for the app.
- Use a local browser application for the demonstration and recording. No public model-backed upload endpoint in this build.
- Prefer a small React frontend with a thin Python HTTP wrapper, subject to repository inspection. Reuse the existing Python pipeline; do not substitute a builder's default model.
- Work in Bali is optional buffer. The committed schedule does not depend on it.
- Name research, domain checks, live connectors and generated resolution suggestions remain follow-on work after the core prototype is complete.
The distinction between the milestones matters: on 16 October, demonstrate the working review/recheck journey and defend the evaluation. On 20 October, complete the supported document formats, saved handoff/export and final acceptance checks.
2. Product specification
Working title: Promise to Delivery. Keep the repository name. Test the existing tagline, “Catch deal surprises before you sign”, with the business reviewer rather than spending build time renaming.
Product line:
“A simple workspace that shows what was promised, what needs resolving, and whether the fixes close the gaps.”
Audience: B2B software and services teams of any company size whose commitments are scattered across conversations, proposals, contracts and internal approvals. They may already use spreadsheets, shared folders, a CRM or an internal system. The shared handoff serves Delivery, Customer Success and Support.
User journey:
Create/open a deal → upload or select sources → Review deal → inspect evidence → record a fix → recheck → save/export the handoff.
The initial review must be useful without a long setup or approval workflow. Resolution checking is the differentiation hypothesis to validate, not a claim of category novelty.
Demonstrated scope: the prototype is evaluated on fictional Elva deals using a complete capability catalogue and a pricing/services note. Show this beside the demo source selection and in the README.
Retain manual upload. Other uploads may support comparison of promises and document terms, but their accuracy is not established by the fictional evaluation. Authorisation needs suitable internal evidence. Without it, show “Needs evidence”; never infer approval or prohibition from silence. Identify checks that could not be completed.
Support Markdown/plain text first, then text-based PDF and DOCX by the completion milestone. Display supported formats and extraction failures. Scanned documents require a separate OCR capability and are outside this build.
The saved record contains selected source versions, commitments, findings, owners, notes, resolution evidence and decision history. Its handoff includes agreed scope, exclusions, milestones, dependencies, relevant service/support obligations, exceptions and unresolved items. Include only what sources or recorded decisions support.
3. Evidence and closure rules
Keep language, internal authorisation and contractual coverage separate.
- Authorisation comes from the catalogue and pricing/services note under the existing policy. Confident sales language or a draft contract does not establish approval. Preserve the existing treatment of exploratory and conditional statements.
- Compare material terms: capability, scope, quantities, dates, effort, conditions and dependencies. Trace incorporated references. Real-time and hourly batch are different commitments.
- Pointer-only sentences remain excluded as standalone commitments, while their references remain available for coverage checks.
- Consolidation must preserve differing terms and conditions. Supersede only with explicit revision or the established document-lineage rule. Uncertain links need review.
- Filter sales housekeeping downstream of frozen extraction. Preserve S15's weekly implementation meeting; C08 and KC3 remain “needs review” when permitted authorisation evidence is silent.
- Keep absolute limits for the complete fictional catalogue. An incomplete uploaded reference cannot establish an absolute prohibition by omission.
Provide three manual resolution routes through one shared form:
1. Align the documents.
2. Record an allowed exception.
3. Change or withdraw the promise.
The form records the affected issue, owner, rationale and supporting evidence. Selecting a route or writing “resolved” is not proof of closure. Re-evaluate every issue attached to that commitment using the same policy.
An allowed exception needs permitted evidence for the exact terms and cannot override an absolute limit. Approval alone does not resolve a separate contract or customer-expectation gap. A changed or withdrawn promise needs explicit supporting evidence; describe customer acknowledgement only when documented.
Why a partial fix must stay open: the product checks agreement across the promise, internal approval and customer paperwork. Resolving one discrepancy does not resolve the others. Closing the whole commitment after one action would conceal the remaining gap.
Use separate Harbour Bank resolution scenarios, leaving original fixtures and labels intact:
- Approval added; hourly-batch SOW remains: contract gap stays open.
- SOW aligned; required approval remains missing: approval issue stays open.
- Both issues supported and resolved: the relevant finding closes.
- Absolute limit plus attempted exception: remains blocked.
- Insufficient evidence: remains “Needs evidence”.
4. Screen flow and local architecture
Build one frontend with three lightweight views, which may share one page layout:
View	Essential content
Deals	Create/reopen deal, last review, outstanding items
Deal workspace	Selected sources, Review deal button, commitment register, evidence and fix panel
Handoff	Shared record for Delivery, Customer Success and Support; decision and export


Register: Commitment | What needs attention | Owner | Status. Show clean commitments as well as flagged ones. Put all related issues on the same commitment.
Show conflicting terms and exact quotes together, with traceable source references. Use readable typography, neutral surfaces, one accent colour and clear spacing. Status needs text as well as colour. A calm, usable design is essential; decorative dashboards and separate role dashboards are unnecessary.
Distinguish issue state (“Needs action”, “Needs evidence”, “Resolved”) from review freshness. Changes to selected sources or decision evidence mark previous results “Review out of date” until rerun. Changing an owner or a note alone does not alter the evidence. An empty result with missing sources must not look like a completed clean review.
Preferred architecture, to confirm from the repo:
- React frontend built as static assets.
- Thin Python API invoking existing modules, without a second inference pipeline.
- Serve the built frontend and API locally from the Python application.
- Reuse the planned SQLite ledger for deal persistence and decisions.
- Store source snapshots/content hashes and review IDs; avoid building a general document-management system.
- Keep model credentials in the existing server environment, never in browser code or saved exports.
Lovable is not inherently incompatible with the seal: it can be used independently with sanitised UI examples and without connecting the project repo. Its current documentation says existing GitHub repos cannot be imported directly. A hosted API integration also requires a reachable backend. For this build, a local frontend avoids needing a hosted backend or tunnel. A separate UI-builder experiment can follow later.
The seal depends on access controls, not on React or local hosting. Preserve the existing denied paths, ALLOWED_DEALS guard and path containment. Do not connect or upload the project repo to a UI builder before the sealed evaluation. Do not read Coral Pay, seed it in the UI, include it in static assets, or expose the repo/data root through file-serving routes. Avoid repository-wide content scans that could read sealed fixtures. Use explicit permitted paths.
References:
- Lovable GitHub workflow: https://docs.lovable.dev/integrations/github
- Lovable API reachability: https://docs.lovable.dev/integrations/introduction
- Python static serving example: https://fastapi.tiangolo.com/tutorial/static-files/
- Frontend/backend integration: https://vite.dev/guide/backend-integration
5. Protected evaluation and learning
Preserve extraction v1 and its recorded configuration/hashes. Any change to prompt, template, schema, model or thinking settings must pass the six Harbour Bank checks and be logged with old/new hashes:
- All 15 labelled firm statements found.
- S08 and S09 firm.
- S12–S14 extracted.
- 100% quote validity.
- Precision at least 60% against agreed labels.
- No extracted statements from HB-05, HB-07 or HB-08.
Add meaningful downstream checks: preserve S15 during scope filtering; match “thirty thousand” and “30,000”; preserve conflicting terms during grouping; keep partial fixes open; refuse unsupported exceptions; avoid confident conclusions from missing references.
Retain the rules-versus-agent comparison only at the capability/authorisation stage. Write the decision rule BEFORE seeing comparison results. Preserve the existing requirements: an additional material conflict caught, no unsupported findings or uncited verdicts, and acceptable extra cost/latency. Make the cost/latency acceptance bounds explicit before running. Keep both implementations and report why the selected one powers the demonstration.
Run the agent three times on Harbour Bank. Compare individual cases and evidence, repeatability, cost and latency. Compare the pipeline against the simple baseline using the same answer key. Keep extraction scores separate from complete-product findings and resolution correctness.
Coral Pay remains sealed until 14 October. Freeze the evaluated backend configuration before unsealing, then run the baseline, rules and agent once each under the existing protocol. Record commit/configuration, inputs, findings, cost and limitations. Do not tune or rerun on Coral Pay after seeing results.
Work after 14 October may finish the UI, file adapters, persistence and exports using development data. If a material pipeline change is necessary, version and disclose it: the earlier sealed scores belong to the evaluated configuration, not automatically to the changed system. New PDF/DOCX support needs separate development checks and is not validated by a Markdown-only sealed run.
Publish the small synthetic-set limitations and known failures. Keep metrics out of the ordinary product screen but preserve them in the README, results and technical checkpoint.
Retain course learning, DECISIONS.md, LEARNING_LOG.md and WHERE_I_STOPPED.md. UNDERSTAND items remain Lina's: explain the choices and ask her to defend them in her own words. Claude Code handles implementation.
6. Extended schedule
Planning estimate: 42 hours remaining, with up to 6 hours of contingency inside the four-hour daily ceiling. Confirm estimates after inspecting the repo. These are effort allocations, not claims that the implementation has already been verified.
Completed Days 1–7 remain complete. Preserve their history; add the revised work blocks rather than silently rewriting completed days.
Date	Hours	Work and evidence by close
Thu 1 Oct	2	Repo/design audit; revise plan and decisions; local UI/API scaffold with permitted sources
Fri 2 Oct	2	Checkpoint 1 paper story; log feedback; agree closure criteria and remaining scope
Sat 3 Oct	4	Sales-housekeeping filter, consolidation and SQLite ledger; score grouping
Sun 4 Oct	4	Material conflict/coverage and authorisation rules; citations and silent-note cases
Mon 5 Oct	4	Bounded catalogue-search agent, three development runs and rules comparison
Tue–Thu 6–8 Oct	Optional	Bali: review screen copy, learn, inspect a prepared diff or practise explanations; no required milestone
Fri–Sun 9–11 Oct	0 committed	Unallocated; no assumed availability
Mon 12 Oct	4	Resolution/recheck domain logic; all five scenarios, source snapshots and closure checks
Tue 13 Oct	4	Wire local UI to live pipeline; text/Markdown upload, saved results and freshness; freeze evaluation configuration
Wed 14 Oct	4	Sealed evaluation once per configuration; exact-case results and failure log
Thu 15 Oct	4	Demonstrable review → partial fix → full fix; technical README and recorded demo
Fri 16 Oct	2	Checkpoint 2: working journey, results, design defence and explicit unfinished items
Mon 19 Oct	4	PDF/DOCX adapters, complete handoff/export and UI refinements
Tue 20 Oct	4	Development acceptance checks, reopen/export verification, final record and write-up


The remaining two hours on 1, 2 and 16 October provide the six-hour contingency. Optional Bali work can substitute for lightweight tasks; it is not additional promised capacity. Do not schedule heavy coding around travel or the sunrise excursion.
On 2 October, use the remaining hours for frontend scaffolding only if useful. Preserve the existing rule that consolidation starts after Checkpoint 1 feedback is recorded.
If the repo audit exceeds this budget, move the completion target explicitly. Keep the evaluation and learning commitments. Report the actual state on 16 October; do not imply the 20 October features are already finished.
7. Checkpoint 1: test the pivot before building it
Show the Harbour Bank story on paper:
1. Real-time promise conflicts with hourly-batch SOW and requires internal approval.
2. Approval is recorded; the SOW discrepancy stays open.
3. Both discrepancies receive sufficient evidence; the finding closes.
Ask the CS/implementation reviewer:
- Which remaining discrepancy would affect your handoff?
- Would you trust this enough to use it before signing, and what evidence is missing?
- Is checking the fix materially more useful than a flagged-items spreadsheet?
- What is the minimum shared record Delivery, Customer Success and Support need?
Record objections and acceptance criteria. A positive reaction is early qualitative feedback, not market validation.
8. Component changes
Component	Action
Frozen extraction, schema, quote checker, evaluation/regression	Reuse; preserve configuration and hashes
config.deal_dir(), allowed deals and seal controls	Reuse across new entry points; do not bypass
Catalogue and pricing evidence policy	Reuse; expose incomplete-evidence status
Consolidation/SQLite ledger	Build as planned; extend with deals, snapshots and decisions
Deterministic checks and bounded agent	Build and compare as planned
Recheck service	Add issue-level closure against revised evidence; retain previous results
Python HTTP wrapper and React UI	Add one thin local application
Upload adapters	Text/Markdown first; PDF/DOCX next; report unreadable inputs
Handoff/export	CSV register plus readable summary, with unresolved items and reviewed sources
Connectors, branding research, generated fixes	Follow-on after the core prototype


9. First small Claude Code instruction
Paste this into Claude Code:
We are revising Promise to Delivery into a local deal workspace, with a technical checkpoint on 16 October and target completion on 20 October. This is an authorised scope revision. Preserve completed Days 1–7, extraction v1 and the Coral Pay seal.

First inspect only the current DESIGN.md, DECISIONS.md, WHERE_I_STOPPED.md, build plan, dependency declarations and the explicitly needed Python modules/configuration. Respect all existing denied paths. Do not open Coral Pay, search its contents, connect the repo to a builder, or run a model evaluation in this task.

Use the attached revision brief to update the project design and remaining schedule. Keep regression, rules-versus-agent and the sealed evaluation. Confirm the local frontend architecture against the actual code; React plus a thin Python HTTP wrapper is preferred. List any missing dependencies or estimate changes.

Then create the smallest local UI/API scaffold that can display the permitted Harbour Bank source list and existing saved extraction results through the existing safe path handling. Label this intermediate view accurately; the complete deal review will be wired later. No hard-coded pretend findings or closure states.

Keep credentials server-side. Serve only the frontend build assets, never the repository or data root. Keep the frozen extraction files/configuration unchanged.

Return the small diff, local launch instructions, what was verified, what remains unwired, and the next implementation slice. Explain the API/frontend separation in plain language so I can defend it.
Update the real project documents from this brief after inspecting the repository. Do not claim those documents or code have been changed merely because this instruction file has been revised.