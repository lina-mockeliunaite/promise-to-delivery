// Run with: node --test frontend/tests/*.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {
  SIGNED_NOTE, attentionText, cleanReason, docLabel, extractedAs, findingDetail, firstDocDate, firstPromised, groupByStage, isSignedDoc, mismatchLine, promiseLabels, plainName, mismatchParts, partsText, hashFor, readHash, matchDoc, closedBy, confirmedBy, headerScrolledPast, handoverChecklist, splitQuote, commitmentView, frozenView, closedLines, changeResult, coverageLine, journeyOpen, docCount, dealsText, commitmentsNeedText,
  recordedBy, rowTitle, sourcesLine, suggestFix, verdictLine, whatChanged,
} from "../src/dealpage.js";

test("where the customer was told: newest first, each document once", () => {
  const st = [
    { doc_type_label: "RFP response", date: "2026-10-06" },
    { doc_type_label: "Proposal", date: "2026-10-10" },
    { doc_type_label: "Proposal", date: "2026-10-10" },
  ];
  assert.equal(sourcesLine(st), "Proposal (10 Oct) · RFP response (6 Oct)");
  assert.equal(sourcesLine([]), "");
});

test("the reason loses its status preamble, nothing else", () => {
  assert.equal(cleanReason("Still holds on the current documents. The catalogue caps it."), "The catalogue caps it.");
  assert.equal(cleanReason("The proposal ties it to 1 December."), "The proposal ties it to 1 December.");
  assert.equal(cleanReason(null), "");
});

test("a stage's first document date", () => {
  assert.equal(firstDocDate({ documents: [{ date: "2026-10-10" }, { date: "2026-10-06" }] }), "2026-10-06");
  assert.equal(firstDocDate({ documents: [] }), "");
});

test("what a new document changed: closed with its reason, still open on the same promise, nothing invented", () => {
  const reg = (states) => ({ commitments: [
    { name: "Coaching detection", issues: [
      { id: 1, finding: "No approval recorded", state: states[0], reason: "Closed: the pricing note now records an approval.", resolved_by: { text: "Resolved by Pricing and services note, version 2 · checked 16 Oct 2026" } },
      { id: 2, finding: "Missing from contract", state: "Needs action" }] },
    { name: "Azure hosting", issues: [{ id: 3, finding: "Not offered", state: "Needs action" }] },
  ] });
  const ch = whatChanged(reg(["Needs action"]), reg(["Resolved"]));
  assert.deepEqual(ch.closed, [{ promise: "Coaching detection", finding: "No approval recorded",
    why: "The pricing note now records an approval.", by: "Resolved by Pricing and services note, version 2 · checked 16 Oct 2026" }]);
  assert.deepEqual(ch.stillOpen, [{ promise: "Coaching detection", finding: "Missing from contract" }]);
  assert.deepEqual(ch.opened, []);
  assert.equal(ch.openPromises, 2);
  const none = whatChanged(reg(["Needs action"]), reg(["Needs action"]));
  assert.deepEqual([none.closed.length, none.opened.length, none.stillOpen.length], [0, 0, 0]);
});

test("the Resolve pop-up suggests the document that usually fixes the gap", () => {
  const docs = [{ source_key: "AB-05", doc_type: "pricing_services_note" }, { source_key: "AB-06", doc_type: "draft_sow" }];
  assert.equal(suggestFix([{ finding: "No approval recorded" }, { finding: "Missing from contract" }], docs).source_key, "AB-05");
  assert.equal(suggestFix([{ finding: "Missing from contract" }], docs).source_key, "AB-06");
  assert.equal(suggestFix([{ finding: "Contract says something different" }], docs).source_key, "AB-06");
  const notOffered = suggestFix([{ finding: "Not offered" }], docs);
  assert.equal(notOffered.source_key, "");
  assert.match(notOffered.hint, /Only changing the promise/);
  assert.equal(suggestFix([{ finding: "Not offered" }, { finding: "Contract says something different" }], docs).source_key, "");
});

import { contractText, gapLine, contractSide, toldQuotes, missingForHandover, changeHeadline } from "../src/dealpage.js";

test("evidence lines use only verified facts and say what the check can establish", () => {
  assert.equal(contractText("Not included"), "No matching wording found in the draft contract or SOW");
  assert.equal(contractText("Amazon Web Services"), "Amazon Web Services");
  assert.match(gapLine("Not offered", { unlisted_value: "Microsoft Azure" }, "CAP-019/AU"), /no Microsoft Azure option .* in AU\. No exception/);
  assert.equal(gapLine("No approval recorded", { limit_name: "max_transactions_per_day", promised_quantity: 750000, limit_value: 500000 }),
               "750,000 is above the catalogue limit of 500,000; a named approval is needed and the approvals note records none.");
  assert.equal(gapLine("Missing from contract", {}), ""); // title only: "Contract says" carries the "No matching wording found …" line (21 Oct)
  assert.equal(gapLine("Missing from contract", { missing_phrases: ["BioCatch"] }), "");
  assert.equal(gapLine("Contract says something different", { promised_value: "Azure", contract_value: "AWS" }), 'Told "Azure".'); // the told side only (21 Oct)
  assert.equal(gapLine("Contract says something different", {}), "The contract covers this on different terms.");
});

test("the contract side prefers verified contract wording, then the searched phrases, then the short term", () => {
  const q = { evidence: { contract_quote: { quote: "Provider will host on AWS.", source: "Draft SOW" } } };
  const miss = { evidence: { missing_phrases: ["BioCatch", "coached by a scammer"] } };
  assert.deepEqual(contractSide([miss, q], "x"), { quote: "Provider will host on AWS.", source: "Draft SOW" });
  assert.deepEqual(contractSide([miss], "Not included"), { missing: ["BioCatch", "coached by a scammer"] });
  assert.deepEqual(contractSide([{ evidence: {} }], "Not included"), { text: "No matching wording found in the draft contract or SOW" });
});

test("quotes are listed once, newest first", () => {
  const s = [{ quote: "A", doc_type_label: "RFP response", date: "2026-09-29" }, { quote: "B", doc_type_label: "Proposal", date: "2026-10-02" },
             { quote: "A", doc_type_label: "RFP response", date: "2026-09-29" }];
  assert.deepEqual(toldQuotes(s).map((x) => x.quote), ["B", "A"]);
});

test("completion lists every missing requirement", () => {
  assert.deepEqual(missingForHandover({ isSigned: false, notes: { sales: null, delivery: { note: "x" } }, canAct: true }),
                   ["upload the signed contract", "add the Sales note"]);
  assert.deepEqual(missingForHandover({ isSigned: true, notes: { sales: {}, delivery: {} }, canAct: true }), []);
});

test("the change headline counts gaps, not promises", () => {
  assert.equal(changeHeadline({ closed: [1], opened: [], stillOpen: [1] }), "1 gap closed. This promise still has 1 open gap.");
  assert.equal(changeHeadline({ closed: [], opened: [], stillOpen: [] }), "Nothing closed and nothing new.");
});

test("a two-gap promise says which document closes which gap", () => {
  const docs = [{ source_key: "AB-05", doc_type: "pricing_services_note" }];
  assert.match(suggestFix([{ finding: "No approval recorded" }, { finding: "Missing from contract" }], docs).hint, /contract gap needs a contract or SOW update/);
});


// Alder Bank's three commitments, as the register returns them (19 Oct).
const ALDER = [
  { name: "BioCatch-based coaching detection live from 1 February 2027 launch", display_name: "Coaching-scam detection live at launch",
    contract: "Not included",
    issues: [{ finding: "No approval recorded", evidence: { contract_value: null } }, { finding: "Missing from contract", evidence: {} }],
    statements: [{ doc_type_label: "Proposal", date: "2026-10-02" }, { doc_type_label: "RFP response", date: "2026-09-29" }] },
  { name: "Real-time scoring of 750,000 outbound instant payments per day by end of first year", display_name: "750,000 payments a day by the end of year one",
    contract: "Not included",
    issues: [{ finding: "No approval recorded" }, { finding: "Missing from contract" }],
    statements: [{ doc_type_label: "Proposal", date: "2026-10-02" }] },
  { name: "Hosting Alder's environment on Microsoft Azure in Australia East", display_name: "Hosting on Microsoft Azure",
    contract: "Amazon Web Services in the Sydney region",
    issues: [{ finding: "Not offered", evidence: { contract_value: null } }, { finding: "Contract says something different", evidence: { contract_value: null } }],
    statements: [{ doc_type_label: "RFP response", date: "2026-09-29" }] },
];

test("the plain mismatch line labels itself: the promise's findings, then the contract's, for Alder's three commitments", () => {
  assert.deepEqual(ALDER.map((c) => mismatchLine(c.issues, c.contract)), [
    "Promise: No approval found. Contract has no matching wording.",
    "Promise: No approval found. Contract has no matching wording.",
    'Promise: Not offered. Contract says: "Amazon Web Services in the Sydney region".',
  ]);
});

test("the mismatch line appends a contract term only when it is short, and never repeats a finding", () => {
  const diff = (v) => [{ finding: "Contract says something different", evidence: { contract_value: v } }];
  assert.equal(mismatchLine(diff("AWS Sydney")), 'Contract says: "AWS Sydney".'); // every term is quoted in the plain line
  assert.equal(mismatchLine(diff("x".repeat(80))), `Contract says: "${"x".repeat(80)}".`); // 80 characters still fits (28 Oct: the limit was 45)
  assert.equal(mismatchLine(diff("x".repeat(81))), "Contract differs."); // longer: left to the drawer, never shortened
  assert.equal(mismatchLine(diff(null), "Not included"), "Contract differs.");
  assert.equal(mismatchLine([{ finding: "Not offered" }, { finding: "Not offered" }]), "Promise: Not offered.");
  assert.equal(mismatchLine([{ finding: "Needs evidence" }]), "Promise: Needs evidence."); // an unlisted label is about the promise: never dropped
  assert.equal(mismatchLine([]), "");
});

test("the long wording of a finding", () => {
  assert.equal(findingDetail({ finding: "No approval recorded" }), "No approval found in the supplied documents");
  assert.equal(findingDetail({ finding: "Missing from contract" }), "Not in the draft contract or SOW");
  assert.equal(findingDetail({ finding: "Not offered" }), "Not offered: no exception can fix this; only changing the promise can");
  assert.equal(findingDetail({ finding: "Contract says something different", evidence: { contract_value: "AWS Sydney" } }),
    'The contract says something different: "AWS Sydney"');
  assert.equal(findingDetail({ finding: "Needs evidence" }), "Needs evidence");
});

test("first promised is the earliest statement's source and date", () => {
  assert.deepEqual(ALDER.map((c) => firstPromised(c.statements)), [
    "First found in the checked documents: RFP response, 29 Sep", "First found in the checked documents: Proposal, 2 Oct", "First found in the checked documents: RFP response, 29 Sep"]);
  assert.equal(firstPromised([{ doc_type_label: "Draft SOW", date: "" }]), "First found in the checked documents: Draft SOW");
  assert.equal(firstPromised([]), "");
});

test("a plain title replaces the extracted name, which is then shown as 'Extracted as'", () => {
  assert.equal(rowTitle(ALDER[0]), "Coaching-scam detection live at launch");
  assert.equal(extractedAs(ALDER[0]), ALDER[0].name);
  assert.equal(rowTitle({ name: "Weekly meeting", display_name: null }), "Weekly meeting");
  assert.equal(extractedAs({ name: "Weekly meeting", display_name: null }), "");
});

test("the heading chip says 'N need attention', or 'Nothing needs attention' with what a note settled, never 'no open gaps'", () => {
  assert.equal(attentionText(2), "2 need attention");
  assert.equal(attentionText(0, 3), "Nothing needs attention · 3 addressed by note");
  assert.equal(attentionText(0), "Nothing needs attention");
});

test("the handover verdict is honest about notes", () => {
  assert.equal(verdictLine({ open: 3, noted: 1, closed: 2 }), "Handed over with 3 needing attention, 1 addressed by note, 2 closed by documents.");
  assert.equal(verdictLine({ open: 1 }), "Handed over with 1 needing attention.");
  assert.equal(verdictLine({ open: 0, noted: 3 }), "Handed over with no open gaps; 3 addressed by note.");
  assert.equal(verdictLine({ open: 0, noted: 0, closed: 1 }), "Handed over with no open gaps on the documents checked.");
  assert.doesNotMatch(verdictLine({ open: 0, noted: 2 }), /no open gaps on the documents/);
});

test("the handover button lists what is missing in words, and never asks for a name", () => {
  assert.deepEqual(missingForHandover({ isSigned: false, notes: { sales: null, delivery: { by: "Sam" } }, canAct: false }),
    ["upload the signed contract", "add the Sales note"]);
  assert.deepEqual(missingForHandover({ isSigned: true, notes: { sales: {}, delivery: {} } }), []);
});

test("a note is attributed, with the date only when the record has one", () => {
  const fmt = (x) => `on ${x}`;
  assert.equal(recordedBy("Sam", "2026-10-16", fmt), "Recorded by Sam · on 2026-10-16");
  assert.equal(recordedBy("Sam", null, fmt), "Recorded by Sam");
});

// Alder Bank's documents and stages, as the documents and register APIs return them (19 Oct).
const STAGES = ["discovery", "evaluation", "proposal", "shortlisted", "contracting", "signed", "handover"]
  .map((key, n) => ({ key, label: key, state: n < 5 ? "done" : n === 5 ? "current" : "todo" }));
const alderDoc = (source_key, date, stage, extra = {}) => ({ source_key, date, stage, included: true, doc_type: "x", ...extra });
const ALDER_DOCS = [
  alderDoc("AB-08", "2026-10-14", "contracting"), alderDoc("AB-01", "2026-09-15", "discovery"),
  alderDoc("AB-06", "2026-10-09", "contracting"), alderDoc("AB-02", "2026-09-22", "evaluation"),
  alderDoc("AB-04", "2026-10-02", "proposal"), alderDoc("AB-03", "2026-09-29", "proposal"),
  alderDoc("AB-05", "2026-10-06", "proposal"), alderDoc("AB-07", "2026-10-12", "contracting"),
];

test("documents group under all seven stages in order, oldest first, with empty stages kept", () => {
  const g = groupByStage(STAGES, ALDER_DOCS);
  assert.deepEqual(g.map((s) => s.key), STAGES.map((s) => s.key));
  assert.deepEqual(g.map((s) => s.docs.map((d) => d.source_key)), [
    ["AB-01"], ["AB-02"], ["AB-03", "AB-04", "AB-05"], [], ["AB-06", "AB-07", "AB-08"], [], []]);
  assert.equal(g[3].docs.length, 0); // Shortlisted: no documents, still listed
  assert.equal(g[5].state, "current"); // the stage data is passed through untouched
});

test("documents that are excluded or have no stage are not placed", () => {
  const g = groupByStage(STAGES, [alderDoc("X-1", "2026-10-01", "proposal", { included: false }), alderDoc("X-2", "2026-10-01", null)]);
  assert.equal(g.flatMap((s) => s.docs).length, 0);
  assert.deepEqual(groupByStage(undefined, undefined), []);
});

test("', fictional' is dropped from displayed names only", () => {
  assert.equal(plainName("Tom Fraser (Account Executive, fictional)"), "Tom Fraser (Account Executive)");
  assert.equal(plainName("Deal owner (fictional)"), "Deal owner");
  assert.equal(plainName("Maya Tan"), "Maya Tan");
  assert.equal(plainName(null), "");
  assert.equal(recordedBy("Tom Fraser (Account Executive, fictional)", null, String), "Recorded by Tom Fraser (Account Executive)");
});

test("signed paperwork is recognised and carries its one-line note", () => {
  assert.ok(isSignedDoc("signed_contract") && isSignedDoc("signed_sow"));
  assert.ok(!isSignedDoc("draft_contract") && !isSignedDoc(undefined));
  assert.equal(SIGNED_NOTE, "Marks the deal signed. Earlier contract and SOW fixes are checked against its text; new clauses aren't reviewed.");
  assert.ok(!/isn't checked|used the drafts/.test(SIGNED_NOTE)); // the pre-21 Oct line, untrue since the signed-contract check
});

test("the contract column never says 'Not included' and shows what was searched for", () => {
  assert.doesNotMatch(contractText("Not included"), /Not included|binding/i);
  const side = contractSide([{ evidence: { missing_phrases: ["BioCatch", "coached by a scammer"] } }], "Not included");
  assert.deepEqual(side, { missing: ["BioCatch", "coached by a scammer"] });
});

test("a sidebar document name drops a date that only repeats the date column", () => {
  assert.equal(docLabel("Call transcript of 15 Sep 2026", "2026-09-15"), "Call transcript");
  assert.equal(docLabel("Call transcript of 22 Sep 2026", "2026-09-22"), "Call transcript");
  assert.equal(docLabel("Call transcript of 15 Sep 2026", "2026-09-16"), "Call transcript of 15 Sep 2026"); // a different date stays
  assert.equal(docLabel("Draft SOW", "2026-10-09"), "Draft SOW");
  assert.equal(docLabel("Pricing and services note", ""), "Pricing and services note");
  assert.equal(docLabel(null, "2026-10-09"), "");
});

// --- The drawer (20 Oct) ---------------------------------------------------------------------------------------------
test("the contract line carries only what the contract says; the promise's findings are badges (27 Oct), for Alder's three commitments", () => {
  const texts = ALDER.map((c) => partsText(mismatchParts(c.issues, c.contract)));
  assert.deepEqual(texts, [
    "Contract has no matching wording",
    "Contract has no matching wording",
    "Contract says Amazon Web Services in the Sydney region",
  ]);
  assert.deepEqual(ALDER.map((c) => promiseLabels(c.issues)), [["No approval found"], ["No approval found"], ["Not offered"]]);
  const hosting = mismatchParts(ALDER[2].issues, ALDER[2].contract);
  assert.deepEqual(hosting.filter((p) => p.strong).map((p) => p.text), ["Amazon Web Services in the Sydney region"]);
  assert.ok(hosting.filter((p) => !p.strong).every((p) => p.text === "Contract says "));
  for (const c of ALDER) assert.ok(!partsText(mismatchParts(c.issues, c.contract)).includes(" · ")); // never joined with a badge
});

test("there is no 'Told' segment in the contract line", () => {
  for (const c of ALDER) assert.ok(!partsText(mismatchParts(c.issues, c.contract)).includes("Told"));
});

test("a commitment with only a contract finding, and one with none", () => {
  assert.equal(partsText(mismatchParts([{ finding: "Missing from contract" }])), "Contract has no matching wording");
  assert.equal(partsText(mismatchParts([{ finding: "Contract says something different", evidence: { contract_value: "AWS, Sydney" } }])), "Contract says AWS, Sydney");
  assert.equal(partsText(mismatchParts([{ finding: "Contract says something different" }], "Not included")), "Contract differs");
  assert.deepEqual(mismatchParts([{ finding: "No approval recorded" }]), []); // promise-only: no contract line
  assert.deepEqual(promiseLabels([{ finding: "No approval recorded" }]), ["No approval found"]);
  assert.deepEqual(mismatchParts([{ finding: "Needs evidence" }, { finding: "Needs evidence" }]), []);
  assert.deepEqual(promiseLabels([{ finding: "Needs evidence" }, { finding: "Needs evidence" }]), ["Needs evidence"]); // an unlisted label is a badge, once
  assert.deepEqual(promiseLabels([{ finding: "Missing from contract" }]), []); // contract-only: no badge
  assert.deepEqual(mismatchParts([]), []);
  assert.deepEqual(promiseLabels([]), []);
});

test("the address bar carries the deal and the commitment key, and reads them back", () => {
  assert.equal(hashFor({ d: "alder_bank", c: "6e5a9364550e" }), "#d=alder_bank&c=6e5a9364550e");
  assert.deepEqual(readHash("#d=alder_bank&c=6e5a9364550e"), { d: "alder_bank", c: "6e5a9364550e" });
  assert.deepEqual(readHash(hashFor({ d: "harbour_bank", c: "Hosting on Azure & more" })), { d: "harbour_bank", c: "Hosting on Azure & more" });
  assert.deepEqual(readHash(""), { d: null, c: null });
  assert.deepEqual(readHash("#d=alder_bank"), { d: "alder_bank", c: null });
  assert.equal(hashFor({}), "");
});

test("a source becomes a link only when label and date identify exactly one document", () => {
  const docs = [
    { name: "RFP response", doc_type_label: "RFP response", date: "2026-09-29" },
    { name: "Call transcript of 15 Sep 2026", doc_type_label: "Call transcript", date: "2026-09-15" },
    { name: "Call transcript of 22 Sep 2026", doc_type_label: "Call transcript", date: "2026-09-22" },
  ];
  assert.equal(matchDoc(docs, ["RFP response", "RFP response"], "2026-09-29"), docs[0]);
  assert.equal(matchDoc(docs, ["Call transcript of 15 Sep 2026", "Call transcript"], "2026-09-15"), docs[1]);
  assert.equal(matchDoc(docs, ["Call transcript"], "2026-09-22"), docs[2]); // label alone is ambiguous, the date settles it
  assert.equal(matchDoc(docs, ["Call transcript"], null), null); // two documents: plain text
  assert.equal(matchDoc(docs, ["RFP response"], "2026-10-01"), null); // wrong date
  assert.equal(matchDoc(docs, ["Proposal"], "2026-09-29"), null);
  assert.equal(matchDoc(docs, ["RFP response"], null), docs[0]); // a contract quote has no date; one match is enough
  assert.equal(matchDoc(undefined, ["x"], null), null);
});

test("the quoted sentence is found in the document, spaces aside, or not at all", () => {
  const text = "Intro.\nThe parties agree that   Elva will host on AWS.\nEnd.";
  assert.deepEqual(splitQuote(text, "Elva will host on AWS."), { before: "Intro.\nThe parties agree that   ", match: "Elva will host on AWS.", after: "\nEnd." });
  assert.equal(splitQuote(text, "agree that Elva will host").match, "agree that   Elva will host");
  assert.equal(splitQuote(text, "Elva will host on Azure"), null);
  assert.equal(splitQuote("", "x"), null);
  assert.equal(splitQuote(text, ""), null);
});

const LIVE_C = {
  ref: "6e5a9364550e", name: ALDER[0].name, display_name: ALDER[0].display_name, contract: "Not included", told: "BioCatch",
  statements: [{ source_name: "Proposal", doc_type_label: "Proposal", date: "2026-10-02", quote: "Elva will flag coached customers." },
               { source_name: "RFP response", doc_type_label: "RFP response", date: "2026-09-29", quote: "Elva will flag coached customers." }],
  issues: [
    { id: 1, finding: "No approval recorded", state: "Needs action", reason: "Still holds on the current documents. Needs a named approval.", evidence: {}, seen: [{ by: "Tom Fraser", at: "2026-10-19T10:00:00Z" }] },
    { id: 2, finding: "Missing from contract", state: "Needs action", reason: "", evidence: { missing_phrases: ["BioCatch"] } },
  ],
};
const DOCS = [{ name: "Proposal", doc_type_label: "Proposal", date: "2026-10-02", source_key: "AB-04" }, { name: "RFP response", doc_type_label: "RFP response", date: "2026-09-29", source_key: "AB-03" }];

test("the drawer's view of a live commitment uses stored data only, and hides the AI label when there is no AI text", () => {
  const v = commitmentView(LIVE_C, "open", DOCS);
  assert.equal(v.title, "Coaching-scam detection live at launch");
  assert.equal(v.extracted, LIVE_C.name);
  assert.equal(v.plain, "Promise: No approval found. Contract has no matching wording.");
  assert.equal(partsText(v.mismatch), "Contract has no matching wording");
  assert.deepEqual(v.badges, ["No approval found"]);
  assert.equal(v.first, "First found in the checked documents: RFP response, 29 Sep");
  assert.equal(v.told.length, 1); // the same quote in two documents is listed once, newest source first
  assert.equal(v.told[0].doc, DOCS[0]);
  assert.equal(v.contract.text, "No matching wording found in the draft contract or SOW");
  assert.deepEqual(v.contract.missing, ["BioCatch"]);
  assert.equal(v.found[0].label, "No approval found in the supplied documents");
  assert.equal(v.found[1].label, 'Not in the draft contract or SOW: "BioCatch"'); // the stored phrase is named (28 Oct)
  assert.deepEqual(v.ai, ["Needs a named approval."]); // the empty reason of the second finding is dropped
  assert.deepEqual(v.seen.map((s) => s.by), ["Tom Fraser"]);
  assert.deepEqual(v.notes, []);
  assert.deepEqual(commitmentView({ ...LIVE_C, issues: LIVE_C.issues.map((i) => ({ ...i, reason: "" })) }, "open", DOCS).ai, []);
});

test("notes in the drawer carry author and date, and a closed commitment shows what closed it", () => {
  const noted = { ...LIVE_C, issues: [{ ...LIVE_C.issues[0], note_resolution: { by: "Priya Nair", at: "2026-10-19T09:00:00Z", reason: "Agreed on the call.", current: true } }] };
  const n = commitmentView(noted, "noted", DOCS).notes;
  assert.deepEqual(n, [{ by: "Priya Nair", at: "2026-10-19T09:00:00Z", text: "Agreed on the call.", kind: "addressed" }]);
  const closed = { ...LIVE_C, issues: [{ id: 1, finding: "Missing from contract", state: "Resolved", resolved_by: { text: "Closed by Draft SOW, version 2" } }] };
  const v = commitmentView(closed, "closed", DOCS);
  assert.deepEqual(v.closed, [{ label: "Not in the contract", by: "Closed by Draft SOW, version 2",
    gap: { headline: "Gap closed: contract wording found in Draft SOW, version 2", notes: [] } }]);
  assert.deepEqual(v.found, []); // what closed it is shown once, under its own heading
  assert.equal(v.contract.missing, null); // no "searched for" on a commitment whose contract gap is closed
  assert.deepEqual(v.ai, []);
});

test("the locked record builds the same view from the snapshot and leaves out what an old snapshot lacks", () => {
  const item = { promise: ALDER[2].name, told: "Microsoft Azure in the Australia East region", contract: "Amazon Web Services in the Sydney region",
    told_in: [["RFP response", "2026-09-29"]], findings: [{ finding: "Not offered", why: "The catalogue has no Azure option.", seen: [], evidence: { unlisted_value: "Microsoft Azure" } },
               { finding: "Contract says something different", why: "", seen: [], evidence: {} }] };
  const v = frozenView({ item, status: "open", documents: DOCS, titles: { [ALDER[2].name]: "Hosting on Microsoft Azure" } });
  assert.equal(v.title, "Hosting on Microsoft Azure");
  assert.equal(v.extracted, ALDER[2].name);
  assert.equal(v.first, "First found in the checked documents: RFP response, 29 Sep");
  assert.deepEqual(v.told, []); // no quotes in this old snapshot: nothing is invented
  assert.equal(v.toldFallback, "Microsoft Azure in the Australia East region");
  assert.equal(partsText(v.mismatch), "Contract says Amazon Web Services in the Sydney region");
  assert.deepEqual(v.badges, ["Not offered"]);
  assert.deepEqual(v.ai, ["The catalogue has no Azure option."]);
  assert.equal(v.found[0].label, "Not offered: no exception can fix this; only changing the promise can");
});

test("the screen says 'Closed by', never 'Resolved by', for what closed a finding", () => {
  assert.equal(closedBy("Resolved by Pricing and services note, version 2 · checked 16 Oct 2026"), "Closed by Pricing and services note, version 2 · checked 16 Oct 2026");
  assert.equal(closedBy("Closed in the documents"), "Closed in the documents");
  assert.equal(closedBy(null), "");
  const closed = { ...LIVE_C, issues: [{ id: 1, finding: "No approval recorded", state: "Resolved", resolved_by: { text: "Resolved by Pricing and services note, version 2" } }] };
  assert.equal(commitmentView(closed, "closed", DOCS).closed[0].by, "Closed by Pricing and services note, version 2");
  const snap = frozenView({ item: { promise: "x", findings: [] }, status: "closed", closedFindings: [{ finding: "No approval recorded", resolved_by: "Resolved by Pricing and services note, version 2" }] });
  assert.equal(snap.closed[0].by, "Closed by Pricing and services note, version 2");
});

test("the brief's footer: name, role, initials and the document it was confirmed from", () => {
  assert.deepEqual(confirmedBy({ confirmed_by: "Tom Fraser (Account Executive, fictional)", basis: "draft SOW, 9 Oct" }),
    { name: "Tom Fraser", role: "Account Executive", initials: "TF", basis: "draft SOW, 9 Oct" });
  assert.deepEqual(confirmedBy({ confirmed_by: "Deal owner (fictional)", basis: "" }), { name: "Deal owner", role: "", initials: "DO", basis: "" });
  assert.deepEqual(confirmedBy({ confirmed_by: "Maya Tan", basis: "proposal, 2 Oct" }), { name: "Maya Tan", role: "", initials: "MT", basis: "proposal, 2 Oct" });
  assert.deepEqual(confirmedBy({}), { name: "", role: "", initials: "?", basis: "" });
});

test("the identity line shows only once the header card has scrolled up under the top bar", () => {
  assert.equal(headerScrolledPast(true, 300, 48), false); // still in view
  assert.equal(headerScrolledPast(false, 40, 48), true); // scrolled up past the bar
  assert.equal(headerScrolledPast(false, 48, 48), true); // exactly under the bar
  assert.equal(headerScrolledPast(false, 900, 48), false); // below the fold, not scrolled past
  assert.equal(headerScrolledPast(false, -200), true);
});

test("the handover checklist has three items and takes its done state from the existing missing rule", () => {
  const none = handoverChecklist({ isSigned: false, notes: { sales: null, delivery: null } });
  assert.deepEqual(none.map((i) => [i.label, i.done]), [
    ["Signed contract · from the documents", false], ["Sales · deal owner's handoff note", false], ["Delivery · acceptance note", false]]);
  const some = handoverChecklist({ isSigned: true, notes: { sales: { note: "x" }, delivery: null } });
  assert.deepEqual(some.map((i) => i.done), [true, true, false]);
  assert.ok(handoverChecklist({ isSigned: true, notes: { sales: {}, delivery: {} } }).every((i) => i.done));
  assert.equal(none.filter((i) => !i.done).length, missingForHandover({ isSigned: false, notes: {} }).length);
});

test("a closed row shows the full stored closing text, every distinct closing once, as 'Closed by'", () => {
  assert.deepEqual(closedLines(["Resolved by Draft SOW, version 2 · checked 16 Oct 2026", "Resolved by Draft SOW, version 2 · checked 16 Oct 2026"]),
    ["Closed by Draft SOW, version 2 · checked 16 Oct 2026"]);
  assert.deepEqual(closedLines(["Resolved by Draft SOW, version 2; Pricing note, version 2 · checked 16 Oct 2026", "Resolved by Pricing note, version 2 · 17 Oct 2026", "", null]),
    ["Closed by Draft SOW, version 2; Pricing note, version 2 · checked 16 Oct 2026", "Closed by Pricing note, version 2 · checked 17 Oct 2026"]);
  assert.deepEqual(closedLines(undefined), []);
});

test("the live and the locked view both carry the closing lines", () => {
  const c = { ...LIVE_C, issues: [{ id: 1, finding: "No approval recorded", state: "Resolved", resolved_by: { text: "Resolved by Pricing note, version 2 · checked 16 Oct 2026" } }] };
  assert.deepEqual(commitmentView(c, "closed", DOCS).closedLines, ["Closed by Pricing note, version 2 · checked 16 Oct 2026"]);
  const f = frozenView({ item: { promise: "P", findings: [] }, status: "closed", closedFindings: [{ finding: "No approval recorded", resolved_by: "Resolved by Pricing note, version 2 · checked 16 Oct 2026" }] });
  assert.deepEqual(f.closedLines, ["Closed by Pricing note, version 2 · checked 16 Oct 2026"]);
});

test("What changed leads with the result, in the agreed words", () => {
  const f = (finding, promise = "A") => ({ finding, promise });
  assert.equal(changeResult({ closed: [f("No approval recorded")], opened: [], stillOpen: [f("Missing from contract")] }),
    "Approval found · the contract gap on this commitment is still open.");
  assert.equal(changeResult({ closed: [f("Missing from contract")], opened: [], stillOpen: [] }), "Contract wording found");
  assert.equal(changeResult({ closed: [f("Contract says something different")], opened: [], stillOpen: [f("No approval recorded")] }),
    "Contract wording now matches the promise · the approval gap on this commitment is still open.");
  assert.equal(changeResult({ closed: [f("No approval recorded")], opened: [], stillOpen: [f("Missing from contract"), f("Contract says something different")] }),
    "Approval found · the contract gap and the contract difference on this commitment are still open.");
  assert.equal(changeResult({ closed: [f("No approval recorded", "A")], opened: [], stillOpen: [f("Not offered", "A"), f("Missing from contract", "B")] }),
    "Approval found · the not-offered gap and the contract gap are still open on 2 commitments.");
  assert.equal(changeResult({ closed: [], opened: [f("Not offered")], stillOpen: [] }), "1 new gap found.");
  assert.equal(changeResult({ closed: [], opened: [], stillOpen: [] }), "Nothing closed and nothing new: the document did not change any gap.");
  assert.ok(!/resolved|covers it/i.test(changeResult({ closed: [f("Missing from contract")], opened: [], stillOpen: [] })));
});

test("the coverage line is one neutral sentence, and absent when nothing failed or the record has no count", () => {
  assert.equal(coverageLine(1), "1 proposed finding couldn't be verified against the documents and isn't shown.");
  assert.equal(coverageLine(3), "3 proposed findings couldn't be verified against the documents and aren't shown.");
  for (const none of [0, null, undefined, "x", -1, 1.5]) assert.equal(coverageLine(none), "");
});

test("the journey opens only the current stage, and every stage keeps its count", () => {
  const stages = [{ key: "discovery", state: "done" }, { key: "contracting", state: "current" }, { key: "signed", state: "todo" }];
  assert.deepEqual([...journeyOpen(stages)], ["contracting"]);
  assert.deepEqual([...journeyOpen([{ key: "a", state: "none" }])], []);
  assert.deepEqual([...journeyOpen(undefined)], []);
  assert.equal(docCount(0), "0 documents");
  assert.equal(docCount(1), "1 document");
  assert.equal(docCount(3), "3 documents");
});

test("the home list counts deals in the tabs and commitments in the column", () => {
  assert.equal(dealsText(1), "1 deal");
  assert.equal(dealsText(4), "4 deals");
  assert.equal(commitmentsNeedText(3), "3 commitments need attention");
  assert.equal(commitmentsNeedText(1), "1 commitment needs attention");
  assert.equal(commitmentsNeedText(0, 2), "Nothing needs attention · 2 addressed by note");
});

test("the origin line is the server's earliest document containing the exact sentence, else the earliest statement's own source", () => {
  const statements = [{ doc_type_label: "Proposal", date: "2026-10-05", quote: "q" }];
  assert.equal(firstPromised(statements, { doc_type_label: "RFP response", date: "2026-09-28" }), "First found in the checked documents: RFP response, 28 Sep");
  assert.equal(firstPromised(statements, null), "First found in the checked documents: Proposal, 5 Oct"); // a locked record, or no match
  assert.equal(firstPromised(statements, undefined), "First found in the checked documents: Proposal, 5 Oct");
  assert.equal(firstPromised([], { doc_type_label: "Call transcript", date: "" }), "First found in the checked documents: Call transcript");
  assert.equal(firstPromised([], null), "");
  assert.equal(commitmentView({ ...LIVE_C, first_found: { doc_type_label: "Call transcript", date: "2026-09-22" } }, "open", DOCS).first,
    "First found in the checked documents: Call transcript, 22 Sep");
});

test("the locked record shows the stored origin when the snapshot has one, else the stored quote's own document", () => {
  const item = { promise: "P", findings: [], quotes: [{ quote: "q", source: "Proposal", date: "2026-10-05" }] };
  assert.equal(frozenView({ item: { ...item, first_found: { doc_type_label: "RFP response", date: "2026-09-28" } }, status: "open" }).first,
    "First found in the checked documents: RFP response, 28 Sep");
  assert.equal(frozenView({ item, status: "open" }).first, "First found in the checked documents: Proposal, 5 Oct"); // locked earlier
  assert.equal(frozenView({ item: { ...item, first_found: null }, status: "open" }).first, "First found in the checked documents: Proposal, 5 Oct");
});

test("the date on a closing line says it is the check date, on old stored strings too, once", () => {
  assert.equal(closedBy("Resolved by Draft contract, version 2 · Draft SOW, version 1 unchanged · 20 Oct 2026"),
    "Closed by Draft contract, version 2 · Draft SOW, version 1 unchanged · checked 20 Oct 2026");
  assert.equal(closedBy("Resolved by Draft SOW, version 1; Draft contract, version 2 · 9 Oct 2026"), "Closed by Draft SOW, version 1; Draft contract, version 2 · checked 9 Oct 2026");
  assert.equal(closedBy("Resolved by Pricing note, version 2 · 16 Oct 2026 · signed off by Daniel Koh"), "Closed by Pricing note, version 2 · checked 16 Oct 2026 · signed off by Daniel Koh");
  assert.equal(closedBy(closedBy("Resolved by X, version 2 · 16 Oct 2026")), "Closed by X, version 2 · checked 16 Oct 2026");
  assert.equal(closedBy("Closed in the documents"), "Closed in the documents");
  assert.equal(closedBy(undefined), "");
});

test("a conflict and a gap on one promise show the contract wording first and say what was searched for", () => {
  const c = { ...LIVE_C, contract: "Not included", issues: [
    { id: 1, finding: "Contract says something different", state: "Needs action", reason: "", evidence: { contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } } },
    { id: 2, finding: "Missing from contract", state: "Needs action", reason: "", evidence: { missing_phrases: ["phone calls"] } },
  ] };
  const v = commitmentView(c, "open", DOCS);
  assert.equal(v.contract.quote.quote, "Provider will operate the Assistant on chat and email.");
  assert.equal(v.contract.text, ""); // no "No matching wording found" beside an actual contract quote
  assert.deepEqual(v.contract.missing, ["phone calls"]);
  assert.equal(v.contract.missingLabel, "No matching wording found for");
  // a gap alone is unchanged: the general sentence and "Searched for:"
  const g = commitmentView({ ...c, issues: [c.issues[1]] }, "open", DOCS);
  assert.equal(g.contract.text, "No matching wording found in the draft contract or SOW");
  assert.equal(g.contract.missingLabel, "Searched for:");
  // a conflict alone has its quote and no missing line
  assert.equal(commitmentView({ ...c, issues: [c.issues[0]] }, "open", DOCS).contract.missing, null);
});

test("a closed commitment shows the contract wording now found, labelled as a lookup, live and locked", () => {
  const now = { target: "12 languages", quote: "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.", document: "Draft contract" };
  const live = commitmentView({ ...LIVE_C, contract: "No gap found", contract_now: now,
    issues: [{ id: 1, finding: "Contract says something different", state: "Resolved", resolved_by: { text: "Resolved by Draft contract, version 2 · 20 Oct 2026" } }] }, "closed", DOCS);
  assert.equal(live.contract.now.target, "12 languages");
  assert.equal(live.contract.now.label, "Draft contract");
  const item = { promise: "P", findings: [], quotes: [{ quote: "Aivuna will support guest conversations in 12 languages.", source: "RFP response", date: "2026-09-28" }],
    contract: "No gap found", contract_now: now };
  const locked = frozenView({ item, status: "closed", closedFindings: [{ finding: "Contract says something different", resolved_by: "Resolved by Draft contract, version 2 · Draft SOW, version 1 unchanged · 20 Oct 2026" }] });
  assert.equal(locked.told.length, 1);
  assert.equal(locked.contract.now.quote, now.quote);
  assert.deepEqual(locked.closedLines, ["Closed by Draft contract, version 2 · Draft SOW, version 1 unchanged · checked 20 Oct 2026"]);
  // a record locked earlier has no such data: the sections stay empty, nothing is invented
  const old = frozenView({ item: { promise: "P", findings: [] }, status: "closed", closedFindings: [] });
  assert.equal(old.told.length, 0);
  assert.equal(old.contract.now, null);
});

test("a contract conflict is fixed in the document its contract-side quote comes from; a gap keeps the old rule (20 Oct)", () => {
  const docs = [
    { source_key: "NJ-05", name: "Pricing and services note", doc_type: "pricing_services_note" },
    { source_key: "NJ-06", name: "Draft SOW", doc_type: "draft_sow" },
    { source_key: "NJ-07", name: "Draft contract", doc_type: "draft_contract" },
  ];
  const conflict = (source) => ({ finding: "Contract says something different", evidence: { contract_quote: { quote: "q", source } } });
  const contractFix = suggestFix([conflict("Draft contract")], docs);
  assert.deepEqual([contractFix.source_key, contractFix.doc_type], ["NJ-07", "draft_contract"]);
  assert.match(contractFix.hint, /The contract wording behind this conflict is in Draft contract\. Add the new version of Draft contract\./);
  assert.equal(suggestFix([conflict("Draft SOW")], docs).source_key, "NJ-06"); // a conflict whose clause is in the SOW is fixed there
  assert.equal(suggestFix([conflict("Draft contract"), { finding: "Missing from contract", evidence: {} }], docs).source_key, "NJ-07"); // the conflict's document wins
  assert.equal(suggestFix([conflict("Some other file")], docs).source_key, "NJ-06"); // not found in the deal: the old rule (SOW first)
  assert.equal(suggestFix([{ finding: "Contract says something different", evidence: {} }], docs).source_key, "NJ-06"); // no stored quote: the old rule
  assert.equal(suggestFix([{ finding: "Missing from contract", evidence: {} }], docs).source_key, "NJ-06"); // a gap keeps the old rule
  assert.equal(suggestFix([{ finding: "No approval recorded" }, conflict("Draft contract")], docs).source_key, "NJ-05"); // approval still first
  assert.equal(suggestFix([{ finding: "Not offered" }, conflict("Draft contract")], docs).source_key, ""); // not offered still first
});

// --- The signed-paperwork check on the screens (21 Oct) ----------------------------------------------------------------------------
import { earlierLine, reopenedBySigned, reopenedLines, signedConfirmations } from "../src/dealpage.js";

const CONFIRMED = { status: "confirmed", text: "Confirmed in the signed contract (Signed contract, 20 Oct)" };
const NOT_FOUND = { status: "not_found", reason: "The fix in Draft contract, version 2 was not found in the signed contract.",
  earlier: "Resolved by Draft contract, version 2 · Draft SOW, version 1 unchanged · 20 Oct 2026" };
const NOT_CONFIRMED = { status: "not_confirmed", text: "Not confirmed against the signed contract" };

test("signed lines: confirmed and not-confirmed under a closed commitment, once each", () => {
  assert.deepEqual(signedConfirmations([CONFIRMED, CONFIRMED, null, undefined]), [CONFIRMED.text]);
  assert.deepEqual(signedConfirmations([NOT_CONFIRMED]), ["Not confirmed against the signed contract"]);
  assert.deepEqual(signedConfirmations([NOT_FOUND]), []); // a reopened gap is not a closed commitment's line
  assert.deepEqual(signedConfirmations(undefined), []);
});

test("a reopened gap says why and keeps the earlier closure visible", () => {
  assert.equal(earlierLine(NOT_FOUND), "Earlier closed by Draft contract, version 2 · Draft SOW, version 1 unchanged · checked 20 Oct 2026");
  assert.deepEqual(reopenedLines([{ signed_check: NOT_FOUND }, { signed_check: CONFIRMED }, {}]),
    [NOT_FOUND.reason, "Earlier closed by Draft contract, version 2 · Draft SOW, version 1 unchanged · checked 20 Oct 2026"]);
  assert.equal(reopenedBySigned([{ signed_check: NOT_FOUND }, { signed_check: CONFIRMED }]).length, 1);
  assert.equal(earlierLine(null), "");
});

test("the drawer's view of a reopened commitment: the reason in 'What we found', the earlier closure, and no AI line for it", () => {
  const c = { ...LIVE_C, contract: "four languages", issues: [
    { id: 1, finding: "Contract says something different", state: "Needs action", reason: NOT_FOUND.reason, signed_check: NOT_FOUND,
      evidence: { contract_quote: { quote: "The Assistant will respond in four languages.", source: "Draft contract" } } },
  ] };
  const v = commitmentView(c, "open", DOCS);
  assert.equal(v.found[0].fact, NOT_FOUND.reason);
  assert.deepEqual(v.earlier, ["Earlier closed by Draft contract, version 2 · Draft SOW, version 1 unchanged · checked 20 Oct 2026"]);
  assert.deepEqual(v.ai, []); // the deterministic reason is not an AI-written summary
  assert.deepEqual(v.reopenedLines, [NOT_FOUND.reason, v.earlier[0]]);
});

test("a closed commitment carries the confirmation, live and in the locked record; an older record has none", () => {
  const live = commitmentView({ ...LIVE_C, contract: "No gap found", issues: [{ id: 1, finding: "Contract says something different", state: "Resolved",
    resolved_by: { text: "Resolved by Draft contract, version 2 · 20 Oct 2026" }, signed_check: CONFIRMED }] }, "closed", DOCS);
  assert.deepEqual(live.signedLines, [CONFIRMED.text]);
  const locked = frozenView({ item: { promise: "P", findings: [], quotes: [], signed: [CONFIRMED, NOT_CONFIRMED] }, status: "closed", closedFindings: [] });
  assert.deepEqual(locked.signedLines, [CONFIRMED.text, NOT_CONFIRMED.text]);
  assert.deepEqual(frozenView({ item: { promise: "P", findings: [] }, status: "closed", closedFindings: [] }).signedLines, []);
  const open = frozenView({ item: { promise: "P", findings: [{ finding: "Contract says something different", signed_check: NOT_FOUND, why: NOT_FOUND.reason }] }, status: "open" });
  assert.equal(open.found[0].fact, NOT_FOUND.reason);
  assert.deepEqual(open.ai, []);
  assert.equal(open.reopenedLines.length, 2);
});

// 21 Oct: no sentence is shown twice between "Contract says" and "What we found", for every finding kind, live and locked.
test("no sentence appears in both 'Contract says' and the finding card, for every finding kind", async () => {
  const { contractSaid } = await import("../src/dealpage.js");
  const key = (s) => String(s).replace(/[‘’]/g, "'").replace(/[“”]/g, '"').toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
  const split = (t) => String(t ?? "").split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);
  const E = {
    notOffered: { finding: "Not offered", evidence: { unlisted_value: "phone calls" }, catalogue_path: "CAP-003/SG" },
    notOfferedBare: { finding: "Not offered", evidence: null, catalogue_path: null },
    noApproval: { finding: "No approval recorded", evidence: null, catalogue_path: null },
    noApprovalLimit: { finding: "No approval recorded", evidence: { limit_name: "payments", promised_quantity: 750000, limit_value: 200000 }, catalogue_path: "CAP-1/AU" },
    missing: { finding: "Missing from contract", evidence: { missing_phrases: ["BioCatch", "coached by a scammer"] }, catalogue_path: null },
    missingNoPhrases: { finding: "Missing from contract", evidence: null, catalogue_path: null },
    differs: { finding: "Contract says something different",
      evidence: { promised_value: "phone calls", contract_value: "chat and email", contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } }, catalogue_path: null },
    differsBare: { finding: "Contract says something different", evidence: null, catalogue_path: null },
  };
  const combos = Object.entries(E).map(([n, e]) => [n, [e], n.startsWith("missing") || n === "notOffered" ? "Not included" : "chat and email"])
    .concat([["missing+noApproval", [E.missing, E.noApproval], "Not included"], ["all", [E.notOffered, E.differs, E.missing, E.noApproval], "chat and email"]]);
  for (const [name, issues, term] of combos) {
    const live = commitmentView({ name: "X", ref: "x", contract: term, statements: [], issues: issues.map((e, i) => ({ id: i, state: "Needs action", reason: "r", ...e })) }, "open", []);
    const locked = frozenView({ item: { promise: "X", contract: term, findings: issues.map((e) => ({ ...e, why: "r", seen: [] })) }, status: "open", documents: [], titles: {} });
    for (const [where, v] of [["live", live], ["locked", locked]]) {
      const said = new Set(contractSaid(v.contract).map(key));
      for (const f of v.found) for (const s of split(f.fact)) assert.ok(!said.has(key(s)), `${name} (${where}): "${s}" is said in both`);
      assert.deepEqual(v.found.map((f) => f.label).length, issues.length, `${name} (${where}): every finding keeps its title`);
    }
  }
});

test("'Not in the draft contract or SOW' names the stored phrases and has no body; 'Contract says something different' shows the told side only", () => {
  const issues = [{ id: 1, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["BioCatch"] }, reason: "r" }];
  const v = commitmentView({ name: "X", contract: "Not included", statements: [], issues }, "open", []);
  assert.equal(v.contract.text, "No matching wording found in the draft contract or SOW");
  assert.deepEqual(v.found, [{ label: 'Not in the draft contract or SOW: "BioCatch"', fact: "" }]);
  // no body, whatever evidence the finding carries, live and locked; the title names the stored phrases and nothing else
  const TITLE = "Not in the draft contract or SOW";
  const expectedTitle = new Map([[null, TITLE], [{}, TITLE], [{ missing_phrases: [] }, TITLE], [{ missing_phrases: ["a", "b"] }, `${TITLE}: "a" or "b"`]]);
  for (const [evidence, title] of expectedTitle) {
    const live = commitmentView({ name: "X", contract: "Not included", statements: [], issues: [{ id: 1, state: "Needs action", finding: "Missing from contract", evidence, reason: "r" }] }, "open", []);
    const locked = frozenView({ item: { promise: "X", contract: "Not included", findings: [{ finding: "Missing from contract", evidence, why: "r", seen: [] }] }, status: "open", documents: [], titles: {} });
    assert.deepEqual(live.found, [{ label: title, fact: "" }]);
    assert.deepEqual(locked.found, [{ label: title, fact: "" }]);
  }
  // reopened by the signed check, the reason is new information and stays
  const reopened = commitmentView({ name: "X", contract: "Not included", statements: [], issues: [{ id: 3, state: "Needs action", finding: "Missing from contract", evidence: null, reason: "r",
    signed_check: { status: "not_found", reason: "The fix in Draft SOW, version 2 was not found in the signed contract.", earlier: "" } }] }, "open", []);
  assert.equal(reopened.found[0].fact, "The fix in Draft SOW, version 2 was not found in the signed contract.");
  // a conflict shows what the customer was told, and not the contract side again
  const d = commitmentView({ name: "X", contract: "chat and email", statements: [], issues: [{ id: 2, state: "Needs action", finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email" }, reason: "r" }] }, "open", []);
  assert.equal(d.found[0].fact, 'Told "phone calls".');
  const dl = frozenView({ item: { promise: "X", contract: "chat and email", findings: [{ finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email" }, why: "r", seen: [] }] }, status: "open", documents: [], titles: {} });
  assert.equal(dl.found[0].fact, 'Told "phone calls".');
  assert.ok(!/the contract says/.test(d.found[0].fact + dl.found[0].fact));
});

// 27 Oct: a finding about the promise sits with the promise (a badge beside the title); what the contract says is its own line.
test("Noma phone calls: 'Not offered' is a badge, and the contract line says only what the contract says", () => {
  const issues = [{ id: 1, state: "Needs action", finding: "Not offered", evidence: { unlisted_value: "phone calls" }, catalogue_path: "CAP-003/SG", reason: "r" },
    { id: 2, state: "Needs action", finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email" }, reason: "r" }];
  const live = commitmentView({ name: "Phone", display_name: "AI answers customers' phone calls at launch", contract: "chat and email", statements: [], issues }, "open", []);
  const locked = frozenView({ item: { promise: "Phone", contract: "chat and email", findings: issues.map((i) => ({ finding: i.finding, evidence: i.evidence, catalogue_path: i.catalogue_path, why: "r", seen: [] })) }, status: "open", documents: [], titles: { Phone: "AI answers customers' phone calls at launch" } });
  for (const v of [live, locked]) {
    assert.deepEqual(v.badges, ["Not offered"]);
    assert.equal(partsText(v.mismatch), "Contract says chat and email");
    assert.equal(v.plain, 'Promise: Not offered. Contract says: "chat and email".');
  }
});

test("Noma launch specialist: 'No approval found' is a badge, and the contract line is 'no matching wording'", () => {
  const issues = [{ id: 3, state: "Needs action", finding: "No approval recorded", evidence: null, reason: "r" },
    { id: 4, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["launch specialist"] }, reason: "r" }];
  const live = commitmentView({ name: "Specialist", contract: "Not included", statements: [], issues }, "open", []);
  assert.deepEqual(live.badges, ["No approval found"]);
  assert.equal(partsText(live.mismatch), "Contract has no matching wording");
  assert.equal(live.plain, "Promise: No approval found. Contract has no matching wording.");
});

test("contract-only has no badge, promise-only has no contract line, and several promise findings give several badges in order", () => {
  const contractOnly = commitmentView({ name: "Lang", contract: "four languages", statements: [], issues: [{ id: 5, state: "Needs action", finding: "Contract says something different", evidence: { contract_value: "four languages" }, reason: "r" }] }, "open", []);
  assert.deepEqual(contractOnly.badges, []);
  assert.equal(partsText(contractOnly.mismatch), "Contract says four languages");
  assert.equal(contractOnly.plain, 'Contract says: "four languages".');
  const promiseOnly = commitmentView({ name: "P", contract: "Not included", statements: [], issues: [{ id: 6, state: "Needs action", finding: "Not offered", evidence: {}, reason: "r" }] }, "open", []);
  assert.deepEqual(promiseOnly.badges, ["Not offered"]);
  assert.deepEqual(promiseOnly.mismatch, []);
  assert.equal(promiseOnly.plain, "Promise: Not offered.");
  const several = commitmentView({ name: "S", contract: "Not included", statements: [], issues: [
    { id: 7, state: "Needs action", finding: "No approval recorded", evidence: null, reason: "r" }, { id: 8, state: "Needs action", finding: "Not offered", evidence: {}, reason: "r" }] }, "open", []);
  assert.deepEqual(several.badges, ["No approval found", "Not offered"]); // the existing finding order
  assert.equal(several.plain, "Promise: No approval found, Not offered.");
});

test("a closed commitment shows no badges", () => {
  const closed = commitmentView({ name: "C", contract: "x", statements: [], issues: [{ id: 9, state: "Resolved", finding: "No approval recorded", evidence: null, reason: "r", resolved_by: { text: "Resolved by Internal approvals note, version 2" } }] }, "closed", []);
  assert.deepEqual(closed.badges, []);
});

// 28 Oct: the contract line has its own line, so a longer term fits (limit 80); the plain line quotes every term.
test("the Noma languages term is shown in full on the contract line, in the plain line and in the locked view", () => {
  const TERM = "four languages: English, Mandarin Chinese, Japanese and Korean"; // 62 characters, the longest in the sample deals
  const issue = { id: 1, state: "Needs action", finding: "Contract says something different", evidence: { promised_value: "12 languages", contract_value: TERM }, reason: "r" };
  const live = commitmentView({ name: "Lang", contract: TERM, statements: [], issues: [issue] }, "open", []);
  assert.equal(partsText(live.mismatch), `Contract says ${TERM}`);
  assert.equal(live.plain, `Contract says: "${TERM}".`);
  assert.deepEqual(live.badges, []);
  const locked = frozenView({ item: { promise: "Lang", contract: TERM, findings: [{ finding: issue.finding, evidence: issue.evidence, why: "r", seen: [] }] }, status: "open", documents: [], titles: {} });
  assert.equal(partsText(locked.mismatch), `Contract says ${TERM}`);
  assert.equal(locked.plain, `Contract says: "${TERM}".`);
  // stored wording is never shortened: a term over the limit falls back to "Contract differs" and the full wording stays in the evidence
  const long = "x".repeat(120);
  const over = commitmentView({ name: "L", contract: long, statements: [], issues: [{ ...issue, evidence: { contract_value: long } }] }, "open", []);
  assert.equal(partsText(over.mismatch), "Contract differs");
});

test("landing cards stack the badge under the title on every card, and the drawer summary carries only the badges", async () => {
  const fs = await import("node:fs");
  const landing = fs.readFileSync(new URL("../src/Landing.jsx", import.meta.url), "utf8");
  const drawer = fs.readFileSync(new URL("../src/Drawer.jsx", import.meta.url), "utf8");
  const css = fs.readFileSync(new URL("../src/DealPage.css", import.meta.url), "utf8");
  assert.ok(landing.includes("labels={found[s.deal].badges} stacked />"));
  assert.match(css, /\.dp-titleline\.is-stacked \{ flex-direction: column; align-items: flex-start;/);
  const summary = drawer.slice(drawer.indexOf('className="dr-mismatch"') - 120, drawer.indexOf('className="dr-mismatch"') + 160);
  assert.ok(summary.includes("PromiseBadges") && !summary.includes("MismatchSentence")); // the "Contract says" section below carries the wording
  // rows, locked rows and the drawer keep the beside-then-wrap behaviour: only Landing.jsx passes `stacked`
  for (const f of ["DealPage.jsx", "FrozenRecord.jsx"]) assert.ok(!fs.readFileSync(new URL(`../src/${f}`, import.meta.url), "utf8").includes("stacked"));
});

// 28 Oct: the drawer head. The status chip is always on its own line beneath the title; the close button is centred on the first line
// of the title by a offset derived from the title's size and line height and the button's size (CSS variables, defined once).
test("the drawer head puts the chip beneath the title and derives the close button's offset from the variables", async () => {
  const fs = await import("node:fs");
  const css = fs.readFileSync(new URL("../src/DealPage.css", import.meta.url), "utf8");
  const jsx = fs.readFileSync(new URL("../src/Drawer.jsx", import.meta.url), "utf8");
  assert.match(css, /\.dr-head-title \{ display: flex; flex-direction: column; align-items: flex-start;/); // never beside, never wrapping
  assert.ok(!/\.dr-head-title \{[^}]*flex-wrap/.test(css));
  for (const v of ["--dr-title-size: 18px", "--dr-title-leading: 1.3", "--dr-x-size: 32px"]) assert.equal(css.split(v).length - 1, 1, `${v} is defined once`);
  assert.match(css, /\.dr-head-title h2 \{[^}]*font-size: var\(--dr-title-size\)[^}]*line-height: var\(--dr-title-leading\)/);
  assert.match(css, /margin-top: calc\(\(var\(--dr-title-size\) \* var\(--dr-title-leading\) - var\(--dr-x-size\)\) \/ 2\)/); // no hard-coded offset
  assert.ok(!/\.dr-head-row \.dp-x \{[^}]*margin-top: -\d/.test(css));
  assert.match(css, /\.dr-head-row \.dp-x \{[^}]*min-height: 0;/); // the app-wide button min-height must not make it taller than --dr-x-size
  // the chip is rendered inside the title block, after the heading, and the close button after both
  const head = jsx.slice(jsx.indexOf("export function DrawerHead"), jsx.indexOf("const NOTE_KIND"));
  assert.ok(head.indexOf("<h2") < head.indexOf("dp-chip") && head.indexOf("dp-chip") < head.indexOf("dp-x"));
});

// 28 Oct: the "Not in the draft contract or SOW" card names the phrases stored on the finding, and the contract section no longer repeats them.
test("the missing-from-contract title lists the stored phrases: one, two, three or more, none", () => {
  const detail = (missing_phrases) => findingDetail({ finding: "Missing from contract", evidence: missing_phrases === undefined ? null : { missing_phrases } });
  assert.equal(detail(["phone calls"]), 'Not in the draft contract or SOW: "phone calls"');
  assert.equal(detail(["first 30 days", "no extra charge"]), 'Not in the draft contract or SOW: "first 30 days" or "no extra charge"');
  assert.equal(detail(["dedicated Aivuna launch specialist", "first 30 days after launch", "no extra charge"]),
    'Not in the draft contract or SOW: "dedicated Aivuna launch specialist", "first 30 days after launch" or "no extra charge"');
  assert.equal(detail(["a", "b", "c", "d"]), 'Not in the draft contract or SOW: "a", "b", "c" or "d"');
  assert.equal(detail([]), "Not in the draft contract or SOW"); // nothing stored: unchanged
  assert.equal(detail(undefined), "Not in the draft contract or SOW");
  assert.equal(detail(["", "  "]), "Not in the draft contract or SOW"); // blank phrases are not names
});

test("the contract section does not repeat the phrases: no 'No matching wording found for' and no 'Searched for' line, live and locked", async () => {
  const fs = await import("node:fs");
  for (const f of ["Drawer.jsx", "FrozenRecord.jsx"]) {
    const src = fs.readFileSync(new URL(`../src/${f}`, import.meta.url), "utf8");
    assert.ok(!src.includes("missingLabel") && !src.includes("contract.missing.map"), `${f} renders no searched-for line`);
  }
  // Noma phone calls (a conflict with a quote, plus a missing finding): the contract section shows the quote only; the card names "phone calls"
  const issues = [
    { id: 1, state: "Needs action", finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email", contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } }, reason: "r" },
    { id: 2, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["phone calls"] }, reason: "r" }];
  const v = commitmentView({ name: "Phone", contract: "chat and email", statements: [], issues }, "open", []);
  assert.equal(v.contract.text, ""); // the generic line is hidden when there is a quote
  assert.equal(v.contract.quote.quote, "Provider will operate the Assistant on chat and email.");
  assert.deepEqual(v.found.map((f) => f.label), ['The contract says something different: "chat and email"', 'Not in the draft contract or SOW: "phone calls"']);
  // launch specialist (a gap alone, no quote): the generic line stays; the phrases are on the card only
  const gap = commitmentView({ name: "S", contract: "Not included", statements: [], issues: [{ id: 3, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["launch specialist"] }, reason: "r" }] }, "open", []);
  assert.equal(gap.contract.text, "No matching wording found in the draft contract or SOW");
  assert.equal(gap.found[0].label, 'Not in the draft contract or SOW: "launch specialist"');
});

// 27 Oct: the promise badge has a light neutral fill so it is easy to find; the fill is an existing theme variable, never a colour.
test("the promise badge fill is the theme's --soft variable: no hard-coded colour, and no urgency colour", async () => {
  const fs = await import("node:fs");
  const css = fs.readFileSync(new URL("../src/DealPage.css", import.meta.url), "utf8");
  const rule = css.slice(css.indexOf(".dp-fbadge {"), css.indexOf("}", css.indexOf(".dp-fbadge {")) + 1);
  assert.match(rule, /background: var\(--soft\);/);
  assert.match(rule, /border: 1px solid var\(--line\);/);
  assert.match(rule, /color: var\(--ink\);/);
  assert.ok(!/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/.test(rule), "the badge rule contains no literal colour"); // so it follows light and dark mode
  assert.ok(!/amber|green|red|--tint|--accent/.test(rule), "no status colour: the status chip stays the only urgency signal");
  // --soft is defined for both colour schemes
  assert.match(css, /--soft: #f8fafc;/);
  assert.match(css, /prefers-color-scheme: dark\) \{\s*\.dp \{[^}]*--soft: #16213a;/);
});

// 28 Oct: the customer's side and the contract's side are parallel lines, each with its stored term and its source.
import { toldParts, firstSource } from "../src/dealpage.js";
import { pickMismatch } from "../src/landing.js";
const lineText = (parts) => partsText(parts);

test("Noma phone calls: both lines carry the stored term and the document", () => {
  const issues = [{ id: 1, state: "Needs action", finding: "Not offered", evidence: {} },
    { id: 2, state: "Needs action", finding: "Contract says something different",
      evidence: { promised_value: "phone calls", contract_value: "chat and email", contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } } }];
  const c = { name: "Phone", display_name: "AI answers customers' phone calls at launch", contract: "chat and email", first_found: { doc_type_label: "RFP response", date: "2026-09-28" }, statements: [], issues };
  const live = commitmentView(c, "open", []);
  assert.equal(lineText(live.toldLine), "Customer was told phone calls · RFP response, 28 Sep");
  assert.equal(lineText(live.mismatch), "Contract says chat and email · Draft SOW");
  assert.deepEqual(live.toldLine.filter((p) => p.strong).map((p) => p.text), ["phone calls"]); // the term is dark, the label and source muted
  const locked = frozenView({ item: { promise: "Phone", contract: "chat and email", first_found: c.first_found, findings: issues.map((i) => ({ finding: i.finding, evidence: i.evidence, why: "r", seen: [] })) }, status: "open", documents: [], titles: {} });
  assert.equal(lineText(locked.toldLine), "Customer was told phone calls · RFP response, 28 Sep");
  assert.equal(lineText(locked.mismatch), "Contract says chat and email · Draft SOW");
});

test("no stored promised term: the customer line is the source alone; no stored contract source: the contract line has none", () => {
  const issues = [{ id: 3, state: "Needs action", finding: "No approval recorded", evidence: null },
    { id: 4, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["launch specialist"] } }];
  const c = { name: "Specialist", contract: "Not included", first_found: { doc_type_label: "RFP response", date: "2026-09-28" }, statements: [], issues };
  const v = commitmentView(c, "open", []);
  assert.equal(lineText(v.toldLine), "Customer was told in RFP response, 28 Sep"); // no leading dot, no term
  assert.equal(lineText(v.mismatch), "Contract has no matching wording"); // nothing was found anywhere, so there is no source to name
  // a conflict with no stored quote has no source either; and an over-limit term falls back to "Contract differs" (the source stays)
  assert.equal(lineText(mismatchParts([{ finding: "Contract says something different", evidence: { contract_value: "AWS Sydney" } }])), "Contract says AWS Sydney");
  const long = "x".repeat(81);
  assert.equal(lineText(mismatchParts([{ finding: "Contract says something different", evidence: { contract_value: long, contract_quote: { quote: "q", source: "Draft SOW" } } }])), "Contract differs · Draft SOW");
  assert.equal(lineText(toldParts([{ finding: "Contract says something different", evidence: { promised_value: long } }], [], { doc_type_label: "Proposal", date: "2026-10-02" })), "Customer was told in Proposal, 2 Oct");
});

test("a closed row says where the customer was told and nothing about a term; no source and no term gives no line", () => {
  const closed = commitmentView({ name: "Lang", contract: "x", first_found: { doc_type_label: "RFP response", date: "2026-09-28" }, statements: [],
    issues: [{ id: 5, state: "Resolved", finding: "Contract says something different", evidence: { promised_value: "12 languages" }, resolved_by: { text: "Resolved by Draft contract, version 2" } }] }, "closed", []);
  assert.equal(lineText(closed.toldLine), "Customer was told in RFP response, 28 Sep");
  assert.deepEqual(closed.mismatch, []); // the Closed by lines are unchanged
  assert.ok(closed.closedLines.length > 0);
  assert.deepEqual(toldParts([], [], null), []);
  assert.equal(firstSource([{ doc_type_label: "Proposal", date: "2026-10-05" }, { doc_type_label: "RFP response", date: "2026-09-28" }], null), "RFP response, 28 Sep"); // the earliest statement
  // the term and the source can each be absent on its own
  assert.equal(lineText(toldParts([{ finding: "Contract says something different", evidence: { promised_value: "12 languages" } }], [], null)), "Customer was told 12 languages");
});

test("the landing pick carries the customer line above the contract line, from the same helpers", () => {
  const reg = { commitments: [{ name: "Phone", display_name: "AI answers customers' phone calls at launch", contract: "chat and email",
    first_found: { doc_type_label: "RFP response", date: "2026-09-28" }, statements: [],
    issues: [{ finding: "Not offered", state: "Needs action", evidence: {} },
      { finding: "Contract says something different", state: "Needs action", evidence: { promised_value: "phone calls", contract_value: "chat and email", contract_quote: { quote: "q", source: "Draft SOW" } } }] }] };
  const m = pickMismatch(reg);
  assert.equal(partsText(m.told), "Customer was told phone calls"); // the cards carry the terms only (28 Oct)
  assert.equal(partsText(m.parts), "Contract says chat and email");
  // rows keep their sources: the same findings through the row helpers
  assert.equal(partsText(toldParts(reg.commitments[0].issues, [], reg.commitments[0].first_found)), "Customer was told phone calls · RFP response, 28 Sep");
  assert.equal(partsText(mismatchParts(reg.commitments[0].issues, "chat and email")), "Contract says chat and email · Draft SOW");
  // no stored promised term: no customer line on the card
  const bare = pickMismatch({ commitments: [{ name: "S", contract: "Not included", first_found: { doc_type_label: "RFP response", date: "2026-09-28" }, statements: [],
    issues: [{ finding: "No approval recorded", state: "Needs action", evidence: null }, { finding: "Missing from contract", state: "Needs action", evidence: { missing_phrases: ["x"] } }] }] });
  assert.deepEqual(bare.told, []);
  assert.equal(partsText(bare.parts), "Contract has no matching wording");
});
