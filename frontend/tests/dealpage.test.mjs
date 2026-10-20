// Run with: node --test frontend/tests/*.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {
  SIGNED_NOTE, attentionText, cleanReason, docLabel, extractedAs, findingDetail, firstDocDate, firstPromised, groupByStage, isSignedDoc, mismatchLine, plainName, mismatchParts, partsText, hashFor, readHash, matchDoc, closedBy, confirmedBy, headerScrolledPast, handoverChecklist, splitQuote, commitmentView, frozenView, closedLines, changeResult, coverageLine, journeyOpen, docCount, dealsText, commitmentsNeedText,
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
      { id: 1, finding: "No approval recorded", state: states[0], reason: "Closed: the pricing note now records an approval.", resolved_by: { text: "Resolved by Pricing and services note, version 2 · 16 Oct 2026" } },
      { id: 2, finding: "Missing from contract", state: "Needs action" }] },
    { name: "Azure hosting", issues: [{ id: 3, finding: "Not offered", state: "Needs action" }] },
  ] });
  const ch = whatChanged(reg(["Needs action"]), reg(["Resolved"]));
  assert.deepEqual(ch.closed, [{ promise: "Coaching detection", finding: "No approval recorded",
    why: "The pricing note now records an approval.", by: "Resolved by Pricing and services note, version 2 · 16 Oct 2026" }]);
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
               "750,000 is above the catalogue limit of 500,000; a named approval is needed and the pricing note records none.");
  assert.equal(gapLine("Missing from contract", {}), "No matching wording found in the draft contract or SOW.");
  assert.equal(gapLine("Contract says something different", { promised_value: "Azure", contract_value: "AWS" }), 'Told "Azure"; the contract says "AWS".');
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

test("the mismatch line is built from verified finding labels, for Alder's three commitments", () => {
  assert.deepEqual(ALDER.map((c) => mismatchLine(c.issues, c.contract)), [
    "No approval found · Not in the contract",
    "No approval found · Not in the contract",
    "Not offered · Contract differs: Amazon Web Services in the Sydney region",
  ]);
});

test("the mismatch line appends a contract term only when it is short, and never repeats a finding", () => {
  const diff = (v) => [{ finding: "Contract says something different", evidence: { contract_value: v } }];
  assert.equal(mismatchLine(diff("AWS Sydney")), "Contract differs: AWS Sydney");
  assert.equal(mismatchLine(diff("x".repeat(80))), "Contract differs");
  assert.equal(mismatchLine(diff(null), "Not included"), "Contract differs");
  assert.equal(mismatchLine([{ finding: "Not offered" }, { finding: "Not offered" }]), "Not offered");
  assert.equal(mismatchLine([{ finding: "Needs evidence" }]), "Needs evidence");
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
  assert.equal(SIGNED_NOTE, "Marks the deal signed. Its wording isn't checked; the checks used the drafts.");
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
test("the sentence-style mismatch line starts with the contract segment, for Alder's three commitments", () => {
  const texts = ALDER.map((c) => partsText(mismatchParts(c.issues, c.contract)));
  assert.deepEqual(texts, [
    "Contract has no matching wording · no approval found",
    "Contract has no matching wording · no approval found",
    "Contract says Amazon Web Services in the Sydney region · not offered",
  ]);
  const hosting = mismatchParts(ALDER[2].issues, ALDER[2].contract);
  assert.deepEqual(hosting.filter((p) => p.strong).map((p) => p.text), ["Amazon Web Services in the Sydney region", "not offered"]);
  assert.ok(hosting.filter((p) => !p.strong).every((p) => p.text === "Contract says " || p.text === " · "));
});

test("there is no 'Told' segment, and the plain mismatch line is untouched", () => {
  for (const c of ALDER) assert.ok(!partsText(mismatchParts(c.issues, c.contract)).includes("Told"));
  assert.equal(mismatchLine(ALDER[0].issues, ALDER[0].contract), "No approval found · Not in the contract");
});

test("a commitment with only a contract finding, and one with none", () => {
  assert.equal(partsText(mismatchParts([{ finding: "Missing from contract" }])), "Contract has no matching wording");
  assert.equal(partsText(mismatchParts([{ finding: "Contract says something different", evidence: { contract_value: "AWS, Sydney" } }])), "Contract says AWS, Sydney");
  assert.equal(partsText(mismatchParts([{ finding: "Contract says something different" }], "Not included")), "Contract differs");
  assert.equal(partsText(mismatchParts([{ finding: "No approval recorded" }])), "No approval found");
  assert.equal(partsText(mismatchParts([{ finding: "Needs evidence" }, { finding: "Needs evidence" }])), "Needs evidence");
  assert.deepEqual(mismatchParts([]), []);
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
  assert.equal(v.plain, "No approval found · Not in the contract");
  assert.equal(partsText(v.mismatch), "Contract has no matching wording · no approval found");
  assert.equal(v.first, "First found in the checked documents: RFP response, 29 Sep");
  assert.equal(v.told.length, 1); // the same quote in two documents is listed once, newest source first
  assert.equal(v.told[0].doc, DOCS[0]);
  assert.equal(v.contract.text, "No matching wording found in the draft contract or SOW");
  assert.deepEqual(v.contract.missing, ["BioCatch"]);
  assert.equal(v.found[0].label, "No approval found in the supplied documents");
  assert.equal(v.found[1].label, "Not in the draft contract or SOW");
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
  assert.deepEqual(v.closed, [{ label: "Not in the contract", by: "Closed by Draft SOW, version 2" }]);
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
  assert.equal(partsText(v.mismatch), "Contract says Amazon Web Services in the Sydney region · not offered");
  assert.deepEqual(v.ai, ["The catalogue has no Azure option."]);
  assert.equal(v.found[0].label, "Not offered: no exception can fix this; only changing the promise can");
});

test("the screen says 'Closed by', never 'Resolved by', for what closed a finding", () => {
  assert.equal(closedBy("Resolved by Pricing and services note, version 2 · 16 Oct 2026"), "Closed by Pricing and services note, version 2 · 16 Oct 2026");
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
  assert.deepEqual(closedLines(["Resolved by Draft SOW, version 2 · 16 Oct 2026", "Resolved by Draft SOW, version 2 · 16 Oct 2026"]),
    ["Closed by Draft SOW, version 2 · 16 Oct 2026"]);
  assert.deepEqual(closedLines(["Resolved by Draft SOW, version 2; Pricing note, version 2 · 16 Oct 2026", "Resolved by Pricing note, version 2 · 17 Oct 2026", "", null]),
    ["Closed by Draft SOW, version 2; Pricing note, version 2 · 16 Oct 2026", "Closed by Pricing note, version 2 · 17 Oct 2026"]);
  assert.deepEqual(closedLines(undefined), []);
});

test("the live and the locked view both carry the closing lines", () => {
  const c = { ...LIVE_C, issues: [{ id: 1, finding: "No approval recorded", state: "Resolved", resolved_by: { text: "Resolved by Pricing note, version 2 · 16 Oct 2026" } }] };
  assert.deepEqual(commitmentView(c, "closed", DOCS).closedLines, ["Closed by Pricing note, version 2 · 16 Oct 2026"]);
  const f = frozenView({ item: { promise: "P", findings: [] }, status: "closed", closedFindings: [{ finding: "No approval recorded", resolved_by: "Resolved by Pricing note, version 2 · 16 Oct 2026" }] });
  assert.deepEqual(f.closedLines, ["Closed by Pricing note, version 2 · 16 Oct 2026"]);
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
