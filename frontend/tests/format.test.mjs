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
  pricing_services_note: "Pricing and services note", rfp_response: "RFP response", proposal: "Proposal" };
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
    "This looks like a signed SOW. Add it as a pricing and services note anyway?");
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
