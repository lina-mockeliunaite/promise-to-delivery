// Run with: node --test frontend/tests/*.mjs
import test from "node:test";
import assert from "node:assert/strict";
import {
  attentionText, cleanReason, countsLine, extractedAs, findingDetail, firstDocDate, firstPromised, groupByStage, mismatchLine,
  recordedBy, rowTitle, sourcesLine, stageLine, suggestFix, verdictLine, whatChanged,
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
  assert.equal(contractText("Not included"), "No matching wording found");
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
  assert.deepEqual(contractSide([{ evidence: {} }], "Not included"), { text: "No matching wording found" });
});

test("quotes are listed once, newest first", () => {
  const s = [{ quote: "A", doc_type_label: "RFP response", date: "2026-09-29" }, { quote: "B", doc_type_label: "Proposal", date: "2026-10-02" },
             { quote: "A", doc_type_label: "RFP response", date: "2026-09-29" }];
  assert.deepEqual(toldQuotes(s).map((x) => x.quote), ["B", "A"]);
});

test("completion lists every missing requirement", () => {
  assert.deepEqual(missingForHandover({ isSigned: false, notes: { sales: null, delivery: { note: "x" } }, canAct: true }),
                   ["save the signing date", "add the Sales note"]);
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
    "Not approved internally · Not in the contract",
    "Not approved internally · Not in the contract",
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
    "First promised in the RFP response, 29 Sep", "First promised in the proposal, 2 Oct", "First promised in the RFP response, 29 Sep"]);
  assert.equal(firstPromised([{ doc_type_label: "Draft SOW", date: "" }]), "First promised in the draft SOW");
  assert.equal(firstPromised([]), "");
});

test("a plain title replaces the extracted name, which is then shown as 'Extracted as'", () => {
  assert.equal(rowTitle(ALDER[0]), "Coaching-scam detection live at launch");
  assert.equal(extractedAs(ALDER[0]), ALDER[0].name);
  assert.equal(rowTitle({ name: "Weekly meeting", display_name: null }), "Weekly meeting");
  assert.equal(extractedAs({ name: "Weekly meeting", display_name: null }), "");
});

test("one count in the heading, zero parts left out, and never 'no open gaps' beside a note", () => {
  assert.equal(countsLine({ open: 3, noted: 1, closed: 1 }), "3 need attention · 1 addressed by note · 1 closed by documents");
  assert.equal(countsLine({ open: 1 }), "1 needs attention");
  assert.equal(countsLine({ open: 0, noted: 3 }), "Nothing needs attention · 3 addressed by note");
  assert.equal(countsLine({}), "");
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

test("the stage line names where the gaps were first made", () => {
  const stage = { current: "contracting", current_label: "Contracting",
    stages: [{ label: "Proposal / RFP", gaps_started: 3 }, { label: "Contracting", gaps_started: 0 }] };
  assert.equal(stageLine(stage), "Stage: Contracting · gaps first made at Proposal / RFP");
  assert.equal(stageLine({ ...stage, stages: [] }), "Stage: Contracting");
  assert.equal(stageLine({ current: null }), "");
});

test("the handover button lists what is missing in words, and never asks for a name", () => {
  assert.deepEqual(missingForHandover({ isSigned: false, notes: { sales: null, delivery: { by: "Sam" } }, canAct: false }),
    ["save the signing date", "add the Sales note"]);
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
