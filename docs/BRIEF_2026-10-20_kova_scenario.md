# Brief: a second demo scenario and per-deal catalogues (20 Oct 2026)

**For Claude Code. Step 1 is a read-only assessment.**
- Do not edit code, fixtures, catalogues or stored deal records.
- Run no paid model calls.
- Run no git.
- Report your plan, then wait for Lina's OK.

## Already decided: do not redo or undo

This came from an outside review. Most of its positioning and screen advice was **built today** (see DECISIONS.md, 20 Oct): the tagline "Catch deal surprises before you sign", the description and audience line, the landing page, the "Deal reviews" home, the trust wording, check coverage, the locked record showing open items first, and the compact sidebar.

**These were rejected on purpose. Keep them rejected:**
- **A "Log in" button and "Review your deal".** There are no accounts.
- **Hiding the document journey entirely.** It answers "which documents were checked", so the sidebar stays compact but visible.
- **Fewer coloured side rules.** Indigo for the brief and amber for the commitments form a two-colour system.

## Goal

**"Two vendors, one checking engine."**
- Add a fifth deal that complements Alder Bank; it does not replace it.
- Keep all four existing deals unchanged.
- **Don't claim "any vendor's catalogue"** on the evidence of two demonstrations.

## 1. Per-deal catalogue (assess first)

**Today, every deal is checked against one shared catalogue,** which belongs to Elva, an AML vendor.

**The direction:**
- the existing deals keep Elva's catalogue;
- the new deal uses Kova AI's catalogue;
- each deal resolves explicitly to its own vendor's catalogue.

**Assess the smallest reference mechanism,** for example a `catalogue` field in `data/profiles/<deal>.json` that defaults to Elva. Trace every dependency:
- catalogue loading and deal configuration;
- model detection and citation verification;
- documentary recheck and closure;
- configuration hashes (`config_sha256`, the hash definitions), the detection version (`v2_version`) and the cached model readings;
- note invalidation and brief re-confirmation;
- locked records and exports;
- the catalogue pop-up, inside a deal and from the home page.

**Must hold:**
- **The catalogue pop-up inside a deal opens that deal's catalogue.** From the home page, it shows a choice of vendor, or the catalogue of the deal last opened. Propose which.
- **Inspect the actual hash inputs before promising compatibility.** The four existing deals must keep identical hashes, findings and freshness states. If they can't, explain why.
- **Do not preserve hashes by leaving meaningful inputs out** or by hiding a genuine change.
- **Keep catalogue selection separate from a change in detection or verification behaviour.** If a real behaviour change requires raising `v2_version` or re-verifying, say so. The published sealed results describe `v2_version` 2.
- **Look for shared-state or caching bugs** that could make one deal use another vendor's catalogue: module-level caches, the catalogue store, the add-capability flow ("marks every deal out of date"), and the cache keys.
- **Not wanted:** multi-tenant administration or catalogue-management workflows.

## 2. The new scenario: Kova AI and Noma Journeys (all fictional)

- **Vendor: Kova AI,** an AI customer-support platform.
- **Customer: Noma Journeys,** a Singapore-based luxury travel company arranging tailored holidays across Asia for international travellers.
- **Deal:** an AI customer-support assistant that answers customers' questions about bookings, changes and refunds by chat and email. **Target launch: 1 February 2027.**
- **Dealshape reviews this software sale.** It is not the assistant being bought.

| Commitment | Initial finding | Final demo outcome |
| --- | --- | --- |
| Support in 12 languages at launch | The sales documents promise 12; the draft contract specifies four. Kova's catalogue supports 12. The SOW points to the contract for languages and does not itself specify four. | A revised contract specifies 12: **Closed by documents**, once the current evidence supports it |
| A dedicated launch specialist for the first 30 days, at no extra charge | A named internal exception is required and absent. The service is also missing from the contract and SOW. | The pricing-note update supplies the exception, so the approval finding closes. **It still Needs attention at handover,** because the contract commitment is still missing |
| AI answers customers' phone calls at launch | The catalogue states explicitly that voice is not offered; the assistant supports chat and email | A person records that Noma has agreed to launch with chat and email: **Addressed by note**, with the original mismatch still visible |

That covers all four finding types:
- required approval not found;
- missing contractual commitment;
- contract says something different;
- capability not offered.

**No performance promises,** such as "70% of tickets resolved".

## 3. Content to write (in step 2, after the OK)

- **A Kova catalogue of about 10 capabilities,** covering languages, channels (chat, email; voice explicitly not offered), integrations and launch-support conditions. **Use the same schema as Elva's.**
- **Eight starting documents, in the same format as Alder's:**
  - discovery call notes;
  - an evaluation or demo transcript;
  - an RFP response;
  - a proposal;
  - the internal pricing and services note;
  - a draft SOW;
  - a draft contract;
  - a customer clarification email.
- **Three update documents:**
  - a revised contract specifying 12 languages;
  - a revised pricing note with the named launch-specialist exception;
  - a signed contract reflecting the final scope, **with the launch specialist still absent,** so that it stays open at handover.
- **The profile:** the brief, the plain titles and the scope line. This is owner-confirmed wording, like Alder's.
- **Dates, versions and counts must reflect the stored history.**

## 4. Detection (step 3, after the OK: paid)

- **Findings come from the real pipeline only.** Never typed in, and never a hardcoded outcome.
- **At most two runs.** Record both outcomes and report any mismatch with the design honestly. Never quietly adjust the evidence to get the intended result.
- **This scenario is a demonstration, not an accuracy measurement.** The sealed evaluation fixtures stay untouched.

## 5. Presentation (step 4)

**The landing page offers two compact cards,** each with one genuine mismatch read from its own stored data:
- AI support assistant: Kova AI / Noma Journeys;
- Financial services, scam protection: Elva / Alder Bank.

**Also:**
- the full deal list stays reachable;
- the visual identity is the same across both scenarios;
- each demo gets its own script and update files;
- **demonstrations are kept clearly apart from sealed evaluations.**
  - Only Coral Pay and Atlas Remit are sealed evaluations.
  - Harbour Bank is the development deal.
  - **Don't label every fixture "evaluation".**

**README:** add the second scenario, one line saying the same commitment-checking applies to assistants used by financial-services operations teams, and the claim "two vendors, one engine".

## What to report from step 1

1. The catalogue-reference mechanism and every file it touches.
2. The hash and freshness answer for the four existing deals, with evidence from the hash inputs.
3. Whether `v2_version` or re-verification is needed, and why.
4. Any shared-state risks found, and the fix for each.
5. The catalogue pop-up behaviour you propose.
6. The order of work for steps 2 to 4, with tests for each, and an estimate of the model cost.
