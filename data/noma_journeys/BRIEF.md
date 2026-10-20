# Noma Journeys deal brief — AI customer-support assistant (Aivuna)

**Purpose:** the second demo deal from 20 Oct 2026, to show the same commitment-checking on a second vendor's catalogue: "two vendors' catalogues, one pipeline". **Demo data, not an evaluation set.** It was written after v2 was frozen and has no labels. The three intended findings below are what the documents were written to contain, so the first model run can be compared against intent; agreement on one run is a smoke test, not a measured result. Dealshape reviews this software sale; it is not the assistant being bought.

All companies, people, dates and deal terms are fictional. Zendesk and Freshdesk are named in Aivuna's catalogue as illustrative helpdesk integrations only; the connectors are fictional and no partnership is claimed.

**The detection prompt still names the original vendor.** `detect_v2.SYSTEM_PROMPT` says "the vendor, Elva". It was not changed for this deal (changing it would raise v2_version and invalidate every saved reading). The documents and the catalogue name Aivuna throughout. Whatever the two runs show is what the claim rests on.

## The deal

**Aivuna** (fictional) sells an AI customer-support platform. **Noma Journeys** (fictional, Singapore) arranges tailored holidays across Asia for international travellers, and is launching an AI assistant that answers guests' questions about bookings, changes and refunds by chat and email on **1 February 2027**. It has told its leadership that date.

## Catalogue positions used (data/catalogue_aivuna.json; Singapore)

| Capability | Singapore |
|---|---|
| CAP-002 Multilingual support | GA, standard, 12 supported languages |
| CAP-003 Support channels | GA, standard: chat and email only. Voice (phone) is not listed, and the catalogue's unlisted rule says it is not offered |
| CAP-005 Booking system connector, CAP-007 Human agent handoff | GA, standard |
| CAP-008 Dedicated launch specialist | GA, **requires named approval** |

## Intended findings (what the documents were written to contain)

| # | Promise (where) | Intended finding | How it can close in the demo |
|---|---|---|---|
| 1 | Support in 12 languages at launch (RFP 2.1.1, proposal §2) | **Contract says something different:** draft contract clause 4 specifies four languages. Aivuna's catalogue supports 12, so there is no catalogue finding. The SOW points to the contract for languages and does not itself specify four | **Closes** when the revised contract (NJ-07_v2) specifies 12 languages |
| 2 | A dedicated launch specialist for the first 30 days at no extra charge (call 14 Sep, RFP 5.1.1, proposal §5) | **Approval required** (CAP-008 needs a named approval; the pricing note records none) **and missing from the contract and SOW** | The approval **closes** when the revised pricing note (NJ-05_v2) records a named exception; the contract gap **stays open**, so it still needs attention at handover |
| 3 | AI answers guests' phone calls at launch (RFP 3.1.1) | **Not offered:** the catalogue lists chat and email only and says voice is not offered. Absolute: no exception can cover it | Stays open in the documents; a person records that Noma agreed to launch with chat and email: **Addressed by note**, original mismatch still visible |

All four finding types appear: required approval not found, missing contractual commitment, contract says something different, capability not offered.

**Not findings by design:** chat and email at launch (offered and in the SOW); the booking system connector and human handoff (offered and in the SOW); "If Noma shares its refund policy by 15 November, we can tune the assistant's answers before launch" (conditional); "exploring whether we could add a WhatsApp channel next year" (exploratory); "I'll send our security pack by Friday" and the RFP and proposal next steps (sales housekeeping). There are no performance promises.

## Update documents (data/scenarios/)

- `NJ-05_v2_named_exception.md`, 18 Oct (first): the pricing note with the named exception for CAP-008.
- `NJ-07_v2_languages_aligned.md`, 19 Oct (second): the contract specifying 12 languages. It still does not mention a launch specialist.
- `NJ-09_signed_contract.md`, 20 Oct: the signed contract. Signed paperwork marks the deal Signed and is not read by the checks ("Its wording isn't checked; the checks used the drafts"); its text matches the final scope, with the launch specialist still absent.

## Verifier notes (what the documents are shaped around)

- A "not offered" finding is accepted only if the value (for example "phone calls") appears in the promise and **nowhere in that region's catalogue entry**. That is why voice is excluded in the catalogue's top-level unlisted rule rather than as an explicit not-sellable entry: an explicit voice entry would make the verifier reject the very finding.
- A "contract says something different" finding needs a subject word in both the promise and the contract quote ("languages"), the promised value ("12 languages") nowhere in the contract chain, and the contract value ("four languages") in the contract quote.
- A contract gap needs short phrases (at most six words) copied from the promise and found nowhere in the contract chain ("launch specialist", "first 30 days").

## Run log

(To be filled in after the paid runs: at most two initial readings, with the cost of every call.)
