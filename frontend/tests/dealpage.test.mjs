// Run with: node --test frontend/tests/*.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { cleanReason, firstDocDate, sourcesLine, suggestFix, whatChanged } from "../src/dealpage.js";

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
