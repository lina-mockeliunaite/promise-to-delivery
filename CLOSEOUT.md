# Dealshape: close-out

*Drafted by Claude on 2 Nov 2026 from DECISIONS.md, LEARNING_LOG.md, the README and the git history, for Lina to edit. Updated 13 Nov with Lina's figures for spend, hours and the video status.*

## In one paragraph

Dealshape catches deal surprises before signing. It reads a B2B deal's paper trail (calls, RFP answers, proposal, SOW, contract) against the vendor's product catalogue and flags promises that are missing from the contract, worded differently there, not offered, or made without a recorded approval. AI proposes each gap, code checks every quote and citation, and people decide the response. It was built between 25 Sep and 31 Oct 2026, in 132 commits, as a hands-on project to learn to design, build and evaluate an AI product end to end.

## What exists at close

- A local web app (FastAPI and React) with two demo deals that run end to end with no API key: Noma Journeys (main) and Alder Bank (a draft fix that did not survive signing).
- Detection v2: one structured model call proposes findings; a verifier rejects any finding whose quotes or citations do not check out; rejected findings are kept and counted on screen.
- Recheck: a new document version closes a gap only when code can show the stored claim no longer holds. The model never closes anything.
- Notes that stay visibly different from documentary proof; a signed-contract check that reopens a fix the signed paperwork dropped.
- A locked handover record with per-document SHA-256 hashes, checked in the browser.
- Two vendors' catalogues through one pipeline (Elva and Aivuna).
- A public demo (11 Nov): https://dealshape-demo.onrender.com. Noma Journeys and Alder Bank only, shared by every visitor, with sample files instead of uploads, no API key, and a reset every hour and on wake-up (free hosting sleeps when idle).
- 925 Python and 337 front-end tests passing (13 Nov).

## Results

| Test | What happened | Source |
| --- | --- | --- |
| Rules vs agent, practice set (3 Oct) | Agent right in substance on all 7 cases, but no verdict passed the evidence check across 6 runs; rules kept under the pre-registered rule | DECISIONS 3 Oct, 12:24 |
| First sealed deal, Coral Pay, v1 rules (10 Oct) | 1 of 3 planted issues, 2 false flags; a single prompt found 3 of 3 | docs/RESULTS_coral_pay_2026-10-10.md |
| Second sealed deal, Atlas Remit, v2 (10 Oct) | 8 of 8, 0 false flags, 0 rejected, pass criteria fixed beforehand; the single prompt also found 8 of 8 but was truncated | docs/RESULTS_atlas_remit_v2_2026-10-10.md |

Read straight: v2 matched a good prompt on detection on one unseen deal. Its value is findings that are verified and structured enough to recheck and close. One deal and eight targets is a small sample.

## The decisions that shaped it

| Date | Decision | What it reversed or replaced |
| --- | --- | --- |
| 25 Sep | Three attributes per promise (language, approval evidence, contract presence), not one firmness ladder | The first design |
| 3 Oct | The rules power the product; the agent stays a measured experiment | The plan to add an agent |
| 10 Oct | Rebuild detection as v2 (model proposes, code verifies) after the sealed run exposed overfit rules | The v1 rules engine |
| 15–16 Oct | Visibility, not workflow: decision buttons and forms removed after a COO and a Delivery lead both asked for it | The fix-and-decide workflow |
| 19 Oct | Nothing frozen, but every change needs tests, a regression check and a DECISIONS entry; renamed Dealshape | The design and pipeline freezes |
| 20 Oct | Lead with pre-signature review; the handover record stays an output | The 5 Oct handoff-first positioning |

## What is not done, stated plainly

- **The unaided test.** No one who had never seen the product has been asked to read a deal page cold. The 6 Oct and 16 Oct sessions were compromised (I named the gap first; I narrated first).
- **The demo video:** still to do. Not re-recorded after 31 Oct; the public demo at https://dealshape-demo.onrender.com is the current walkthrough.
- **A full promise inventory.** Only promises with findings are listed; listing every promise changes the tested prompt and needs a fresh sealed check.
- **The detection prompt still names the first vendor.** Changing it raises the detection version and invalidates saved readings.
- **No connectors or accounts.** Documents carry a Drive link field; no live Drive, CRM or sign-in.

## If it continued

1. The unaided test with two people from Delivery or Customer Success.
2. A promise inventory in the model output, then a third sealed deal from a different writer.
3. A vendor-neutral prompt and a fresh sealed check.
4. A Drive connector, then post-signature tracking against the locked record.
5. Show when a revision itself introduced a gap: the wording the check looked for (or the conflicting wording) was in the previous version of a changed document and is gone in the new one, with the changed wording and the document version. Today a gap opened by a recheck is labelled "Additional finding" when its commitment was already flagged and "New" when it was not, and nothing says whether the revision caused it (Noma's phone-support finding after the revised contract is another reading of unchanged wording, not a change in it).

## What carries into the next build (Waterline)

- The evidence contract: the model proposes, code verifies every citation, rejected claims are counted, never shown.
- Sealed tests written by someone who never sees the build, and a decision rule written before the run.
- Record and replay, so demos run with no key.
- The habit of saying what was not checked.
- A real test of an agent where the problem needs one: ownership tracing of unknown depth.

## Cost and effort

- API spend in November: $0.56 (about $0.45 for the three Alder readings on 13 Nov; the rest self-test runs). $15.87 of credit remaining. The API did not lapse on 31 Oct. Each sealed run cost about $0.25. The Claude subscription (Claude Code and chat) is separate and not included.
- Commits: 132, 25 Sep to 31 Oct.
- Hours: about 10 hours for 10–13 Nov (public demo, Alder rebuild, polish rounds, documentation). Build total not tracked.

## What I learned

[Lina to write: three to five lines in your own words. Suggested prompts: the moment a result went against you and what you did; what "verified" means to you now; what you would tell a team adopting AI for compliance work.]
