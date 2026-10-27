// Run with: node --test frontend/tests/   (no dependencies; covers the display helpers that carry logic)
import test from "node:test";
import assert from "node:assert/strict";
import { fmtDate, fmtDateTime, recheckLine } from "../src/format.js";

test("dates read as 28 Sep 2026", () => {
  assert.equal(fmtDate("2026-09-28"), "28 Sep 2026");
  assert.equal(fmtDate("2026-10-02T10:00:00Z"), "2 Oct 2026");
  assert.equal(fmtDate(""), "");
  assert.equal(fmtDate(undefined), "");
});

test("a timestamp shows in the viewer's local time as 5 Oct 2026, 11:02", () => {
  assert.equal(fmtDateTime(new Date(2026, 9, 5, 11, 2).toISOString()), "5 Oct 2026, 11:02");
  assert.equal(fmtDateTime(new Date(2026, 0, 9, 9, 5).toISOString()), "9 Jan 2026, 09:05");
  assert.equal(fmtDateTime("not a date"), "not a date");
});

const issue = (id, label, state) => ({ id, label, state });

test("the recheck line names the issues that closed and the ones still open", () => {
  const before = [issue(1, "Needs internal approval"), issue(2, "Missing from the contract"), issue(3, "Contract says something different")];
  const after = [issue(1, "Needs internal approval", "Resolved"), issue(2, "Missing from the contract", "Needs action"), issue(3, "Contract says something different", "Needs action")];
  assert.equal(recheckLine(before, after), "Recheck: closed — Needs internal approval. Still open — Missing from the contract, Contract says something different.");
});

test("the recheck line says none when nothing closed or nothing is left", () => {
  const before = [issue(1, "A"), issue(2, "B")];
  assert.equal(recheckLine(before, [issue(1, "A", "Needs action"), issue(2, "B", "Needs evidence")]), "Recheck: nothing closed. Still open — A, B.");
  assert.equal(recheckLine(before, [issue(1, "A", "Resolved"), issue(2, "B", "Resolved")]), "Recheck: closed — A, B. Nothing still open.");
  assert.equal(recheckLine(before, []), "Recheck: closed — A, B. Nothing still open.");
  assert.equal(recheckLine([], []), "Recheck: nothing closed. Nothing still open.");
});

import { checkUpload, uploadKind } from "../src/format.js";

test("uploads: PDF and Word are sent as base64, Markdown and text as text, anything else is refused up front", () => {
  assert.equal(uploadKind("Proposal.PDF"), "binary");
  assert.equal(uploadKind("sow.docx"), "binary");
  assert.equal(uploadKind("notes.md"), "text");
  assert.equal(uploadKind("notes.txt"), "text");
  assert.equal(uploadKind("archive.zip"), null);
  assert.equal(uploadKind("noextension"), null);
  assert.equal(checkUpload("a.pdf", 1000), null);
  assert.equal(checkUpload("a.pdf", 10 * 1024 * 1024 + 1), "The file is larger than 10 MB.");
  assert.match(checkUpload("old.doc", 10), /Save the document as \.docx/);
  assert.match(checkUpload("x.exe", 10), /PDF, Word \(\.docx\), Excel \(\.xlsx\), PowerPoint \(\.pptx\), Markdown and text/); // 9 Oct: Office formats added
});

import { alsoLine, checkLine, guessType, typeFromName, plural } from "../src/format.js";

test("the file name suggests a type, and the finding fills in when it does not", () => {
  assert.equal(typeFromName("HB-05_v2_named_exception.md"), "pricing_services_note");
  assert.equal(typeFromName("HB-06_v2_annex_aligned.md"), "draft_sow");
  assert.equal(typeFromName("Harbour SOW v3.docx"), "draft_sow");
  assert.equal(typeFromName("notes.md"), null);
  assert.equal(guessType("notes.md", "approval"), "pricing_services_note");
  assert.equal(guessType("notes.md", "conflicting_terms"), "draft_sow");
  assert.equal(guessType("HB-06_v2_annex_aligned.md", "approval"), "draft_sow");
});

test("a check result reads as one line, and other closures are stated", () => {
  const r = { document: "Draft SOW, version 2", closed: ["Missing from contract", "Contract says something different"],
    still_open: ["No approval recorded"], closed_elsewhere: [] };
  assert.equal(checkLine(r), "Checked Draft SOW, version 2. Closed: Missing from contract; Contract says something different. Still open: No approval recorded.");
  assert.equal(alsoLine(r, "Missing from contract"), "This document also resolved: Contract says something different.");
  assert.equal(alsoLine({ ...r, closed: ["Missing from contract"] }, "Missing from contract"), "");
  assert.equal(checkLine({ document: "X", closed: [], still_open: [], closed_elsewhere: [] }), "Checked X. Nothing closed. Nothing still open on this commitment.");
  assert.equal(plural(1, "finding"), "1 finding");
  assert.equal(plural(3, "finding"), "3 findings");
});


test("Excel and PowerPoint upload as binary; old and macro formats are refused with the fix", () => {
  assert.equal(uploadKind("note.xlsx"), "binary");
  assert.equal(uploadKind("deck.PPTX"), "binary");
  assert.equal(checkUpload("note.xlsx", 1000), null);
  assert.match(checkUpload("note.xls", 1000), /saved as \.xlsx/);
  assert.match(checkUpload("note.xlsm", 1000), /no macros/);
  assert.match(checkUpload("deck.ppt", 1000), /saved as \.pptx/);
  assert.match(checkUpload("notes.csv", 1000), /Excel \(\.xlsx\), PowerPoint \(\.pptx\)/);
});

// --- A wrong file in the add-document form (20 Oct) --------------------------------------------------------------------
import { typeFromText, uploadMismatch } from "../src/format.js";

const LABELS = { draft_sow: "Draft SOW", draft_contract: "Draft contract", signed_contract: "Signed contract", signed_sow: "Signed SOW",
  pricing_services_note: "Internal approvals note", rfp_response: "RFP response", proposal: "Proposal" };
const SIGNED_HEAD = "# Master Services Agreement — Alder Bank (signed copy)\n\nDate: 12 October 2026\n\n## Signatures\n\nSigned for and on behalf of Elva:\nName: Tom Fraser\n";

test("signed files are recognised by name and by what the file says about itself", () => {
  assert.equal(typeFromName("AB-09_signed_contract.md"), "signed_contract");
  assert.equal(typeFromName("Signed SOW v2.pdf"), "signed_sow");
  assert.equal(typeFromName("AB-07_draft_contract.md"), "draft_contract"); // unchanged
  assert.equal(typeFromText(SIGNED_HEAD), "signed_contract");
  assert.equal(typeFromText("# Statement of Work (signed copy)\n\nText."), "signed_sow");
  assert.equal(typeFromText("# DRAFT Statement of Work\n\nText."), "draft_sow");
  assert.equal(typeFromText(""), null);
  assert.equal(typeFromText("Some notes."), null);
});

test("the wrong-file question: a signed contract offered as a new version of the Draft SOW", () => {
  const q = uploadMismatch({ fileName: "AB-09_signed_contract.md", head: SIGNED_HEAD, target: { type: "draft_sow", name: "Draft SOW" }, labels: LABELS });
  assert.equal(q, "This looks like a signed contract. Add it as a new version of Draft SOW anyway?");
  // the file's name alone is enough, before its text has been read
  assert.equal(uploadMismatch({ fileName: "signed_contract.pdf", head: "", target: { type: "draft_sow", name: "Draft SOW" }, labels: LABELS }), q);
});

test("the question names the type for a new document, and works the other way round", () => {
  assert.equal(uploadMismatch({ fileName: "AB-09_signed_contract.md", head: SIGNED_HEAD, target: { type: "draft_contract" }, labels: LABELS }),
    "This looks like a signed contract. Add it as a draft contract anyway?");
  assert.equal(uploadMismatch({ fileName: "x.md", head: "# Signed SOW (signed copy)", target: { type: "pricing_services_note" }, labels: LABELS }),
    "This looks like a signed SOW. Add it as an internal approvals note anyway?");
  // a draft going in as a signed document: name and heading agree it is a draft contract
  assert.equal(uploadMismatch({ fileName: "AB-07_draft_contract.md", head: "# DRAFT Master Services Agreement contract", target: { type: "signed_contract" }, labels: LABELS }),
    "This looks like a draft contract. Add it as a signed contract anyway?");
});

test("no question when the file fits, when nothing is clear, or when only a weak hint disagrees", () => {
  assert.equal(uploadMismatch({ fileName: "AB-09_signed_contract.md", head: SIGNED_HEAD, target: { type: "signed_contract" }, labels: LABELS }), "");
  assert.equal(uploadMismatch({ fileName: "notes.md", head: "Some notes.", target: { type: "draft_sow", name: "Draft SOW" }, labels: LABELS }), "");
  assert.equal(uploadMismatch({ fileName: "AB-06_draft_sow_v2.md", head: "", target: { type: "draft_contract" }, labels: LABELS }), ""); // one weak signal
  assert.equal(uploadMismatch({ fileName: "a.md", head: "", target: null, labels: LABELS }), "");
  assert.match(uploadMismatch({ fileName: "rfp_signed_contract.md", head: "", target: { type: "rfp_response" }, labels: LABELS }), /^This looks like a signed contract\. Add it as an RFP response anyway\?$/);
});

// --- The wrong-file notice states the consequence and offers the right action (20 Oct) --------------------------------------------
import { addReady, detectedType, mismatchNotice, suggestVersionOf } from "../src/format.js";

const CONTRACT_HEAD = "# DRAFT Master Services Agreement — Noma Journeys\n\nDate: 19 October 2026\n";
const PRICING_HEAD = "# INTERNAL — Pricing and services note: Noma Journeys\n\nDate: 18 October 2026\n";
const DOCS = [
  { source_key: "NJ-03", name: "RFP response", doc_type: "rfp_response" },
  { source_key: "NJ-04", name: "Proposal", doc_type: "proposal" },
  { source_key: "NJ-05", name: "Internal approvals note", doc_type: "pricing_services_note" },
  { source_key: "NJ-06", name: "Draft SOW", doc_type: "draft_sow" },
  { source_key: "NJ-07", name: "Draft contract", doc_type: "draft_contract" },
  { source_key: "NJ-01", name: "Call transcript of 14 Sep 2026", doc_type: "call_transcript" },
  { source_key: "NJ-02", name: "Call transcript of 21 Sep 2026", doc_type: "call_transcript" },
];
const L2 = { ...LABELS, call_transcript: "Call transcript", proposal: "Proposal" };

test("a file's own heading is enough to question a filing, even when its name says nothing", () => {
  assert.equal(detectedType({ fileName: "NJ-07_v2_languages_aligned.md", head: CONTRACT_HEAD }), "draft_contract");
  assert.equal(detectedType({ fileName: "NJ-05_v2_named_exception.md", head: PRICING_HEAD }), "pricing_services_note");
  assert.equal(detectedType({ fileName: "NJ-07_v2_languages_aligned.md", head: "" }), null); // no readable heading (Word, PDF…): the name alone is weak
  assert.equal(detectedType({ fileName: "notes.md", head: "Some notes." }), null);
  assert.equal(detectedType({ fileName: "AB-09_signed_contract.md", head: "" }), "signed_contract"); // signed: the name is enough
  assert.equal(detectedType({ fileName: "pricing_v2.md", head: "# DRAFT Statement of Work" }), "draft_sow"); // the heading wins over the name
});

test("the plain question now also fires for a contract filed as the SOW (heading only)", () => {
  assert.equal(uploadMismatch({ fileName: "NJ-07_v2_languages_aligned.md", head: CONTRACT_HEAD, target: { type: "draft_sow", name: "Draft SOW" }, labels: L2 }),
    "This looks like a draft contract. Add it as a new version of Draft SOW anyway?");
  assert.equal(uploadMismatch({ fileName: "NJ-07_v2_languages_aligned.md", head: CONTRACT_HEAD, target: { type: "draft_contract", name: "Draft contract" }, labels: L2 }), "");
});

test("a pricing note filed as a proposal: the consequence, the right action first, the quiet way to go ahead", () => {
  const n = mismatchNotice({ fileName: "NJ-05_v2_named_exception.md", head: PRICING_HEAD, target: { type: "proposal" }, documents: DOCS, labels: L2 });
  assert.equal(n.question, "This looks like an internal approvals note.");
  assert.equal(n.consequence, "Filed as a proposal, it won't close the approval gap.");
  assert.equal(n.use.text, "Use “A new version of Internal approvals note”");
  assert.deepEqual([n.use.source_key, n.use.doc_type], ["NJ-05", ""]);
  assert.equal(n.anyway, "Add as proposal anyway");
});

test("a contract filed as a new version of the SOW: it replaces the SOW's wording and can close gaps it shouldn't", () => {
  const n = mismatchNotice({ fileName: "NJ-07_v2_languages_aligned.md", head: CONTRACT_HEAD, target: { type: "draft_sow", name: "Draft SOW" }, documents: DOCS, labels: L2 });
  assert.equal(n.consequence, "Filed as a new version of Draft SOW, it replaces Draft SOW's wording and can close gaps it shouldn't.");
  assert.equal(n.use.text, "Use “A new version of Draft contract”");
  assert.equal(n.use.source_key, "NJ-07");
  assert.equal(n.anyway, "Add as a new version of Draft SOW anyway");
});

test("when the deal has no single document of that type, the primary action sets the type instead", () => {
  const none = mismatchNotice({ fileName: "x.md", head: PRICING_HEAD, target: { type: "proposal" }, documents: [{ source_key: "A", name: "Proposal", doc_type: "proposal" }], labels: L2 });
  assert.equal(none.use.text, "Use “Internal approvals note” as the type");
  assert.deepEqual([none.use.source_key, none.use.doc_type], ["", "pricing_services_note"]);
  const two = mismatchNotice({ fileName: "x.md", head: "# Call transcript — Noma", target: { type: "proposal" }, documents: DOCS, labels: L2 });
  assert.equal(two, null); // a call transcript heading is not one of the clear types, so no question
});

test("the consequences for signed paperwork and for a draft filed as a pricing note", () => {
  const signed = mismatchNotice({ fileName: "AB-09_signed_contract.md", head: SIGNED_HEAD, target: { type: "draft_contract" }, documents: [], labels: LABELS });
  assert.equal(signed.consequence, "Filed as a draft contract, it will be checked like a draft, and it won't mark the deal Signed.");
  const asPricing = mismatchNotice({ fileName: "NJ-07.md", head: CONTRACT_HEAD, target: { type: "pricing_services_note" }, documents: [], labels: L2 });
  assert.equal(asPricing.consequence, "Filed as an internal approvals note, it would count as approval evidence, which it isn't.");
  const asSigned = mismatchNotice({ fileName: "NJ-07.md", head: CONTRACT_HEAD, target: { type: "signed_contract" }, documents: [], labels: LABELS });
  assert.equal(asSigned.consequence, "Filed as a signed contract, it would mark the deal Signed, but it isn't signed.");
  assert.equal(mismatchNotice({ fileName: "NJ-05.md", head: PRICING_HEAD, target: { type: "pricing_services_note" }, documents: DOCS, labels: L2 }), null);
  assert.equal(mismatchNotice({ fileName: "a.md", head: "", target: null, documents: DOCS, labels: L2 }), null);
});

test("'+ Add' suggests, never applies: by the file name's source key, then by the heading's type", () => {
  assert.equal(suggestVersionOf({ fileName: "NJ-05_v2_named_exception.md", head: "", documents: DOCS }).source_key, "NJ-05");
  assert.equal(suggestVersionOf({ fileName: "nj-07_revised.md", head: "", documents: DOCS }).source_key, "NJ-07"); // case-blind
  assert.equal(suggestVersionOf({ fileName: "NJ-070_x.md", head: "", documents: DOCS }), null); // a longer key is not a match
  assert.equal(suggestVersionOf({ fileName: "revised.md", head: CONTRACT_HEAD, documents: DOCS }).source_key, "NJ-07");
  assert.equal(suggestVersionOf({ fileName: "revised.md", head: "# Call transcript", documents: DOCS }), null); // not a clear type
  assert.equal(suggestVersionOf({ fileName: "revised.md", head: SIGNED_HEAD, documents: DOCS }), null); // a signed document is not a new draft
  assert.equal(suggestVersionOf({ fileName: "revised.md", head: CONTRACT_HEAD, documents: [DOCS[3], { ...DOCS[3], source_key: "X", name: "Other SOW" }] }), null);
  assert.equal(suggestVersionOf({ fileName: "revised.md", head: "", documents: DOCS }), null);
});

test("there is no silent default type: a file needs a chosen type or a chosen document", () => {
  assert.equal(addReady({ file: { name: "a.md" }, source_key: "", doc_type: "" }), false);
  assert.equal(addReady({ file: { name: "a.md" }, source_key: "NJ-07", doc_type: "" }), true);
  assert.equal(addReady({ file: { name: "a.md" }, source_key: "", doc_type: "proposal" }), true);
  assert.equal(addReady({ file: null, source_key: "NJ-07", doc_type: "" }), false);
});

// --- A revision filed as "A new document" (21 Oct) ---------------------------------------------------------------------------------
import { newDocumentNotice } from "../src/format.js";

test("a revision filed as a new document is questioned before anything is added: dated today, beside the original", () => {
  const n = newDocumentNotice({ fileName: "NJ-05_v2_named_exception.md", head: PRICING_HEAD, documents: DOCS, docType: "pricing_services_note", today: "21 Oct 2026" });
  assert.equal(n.question, "This looks like a new version of Internal approvals note.");
  assert.equal(n.consequence, "Added as a new document, it would be dated 21 Oct 2026 and sit beside Internal approvals note, not replace it, so the check would read both.");
  assert.deepEqual([n.use.source_key, n.use.text], ["NJ-05", "Use “A new version of Internal approvals note”"]);
  assert.equal(n.anyway, "Add as a new document anyway");
});

test("with no type chosen yet there is no way to go ahead as a new document, only the right action", () => {
  const n = newDocumentNotice({ fileName: "NJ-07_v2_languages_aligned.md", head: CONTRACT_HEAD, documents: DOCS, docType: "", today: "21 Oct 2026" });
  assert.equal(n.use.text, "Use “A new version of Draft contract”");
  assert.equal(n.anyway, "");
});

test("no notice for a file that does not look like a revision of anything in the deal", () => {
  assert.equal(newDocumentNotice({ fileName: "notes.md", head: "Some notes.", documents: DOCS, docType: "proposal", today: "21 Oct 2026" }), null);
  assert.equal(newDocumentNotice({ fileName: "AB-09_signed_contract.md", head: SIGNED_HEAD, documents: DOCS, docType: "signed_contract", today: "21 Oct 2026" }), null);
  assert.equal(newDocumentNotice({ fileName: "x.md", head: CONTRACT_HEAD, documents: [], docType: "draft_contract", today: "21 Oct 2026" }), null);
});

test("a label that starts with a vowel gets 'an': the internal approvals note", () => {
  const labels = { pricing_services_note: "Internal approvals note", proposal: "Proposal", rfp_response: "RFP response", draft_sow: "Draft SOW" };
  assert.equal(uploadMismatch({ fileName: "Pricing note.md", head: "# INTERNAL — Pricing and services note: X\n", target: { type: "proposal" }, labels }),
    "This looks like an internal approvals note. Add it as a proposal anyway?");
  assert.equal(uploadMismatch({ fileName: "proposal.md", head: "# Proposal\n", target: { type: "pricing_services_note" }, labels }),
    "This looks like a proposal. Add it as an internal approvals note anyway?");
  assert.equal(uploadMismatch({ fileName: "rfp.md", head: "# RFP response\n", target: { type: "proposal" }, labels }), "This looks like an RFP response. Add it as a proposal anyway?");
});
