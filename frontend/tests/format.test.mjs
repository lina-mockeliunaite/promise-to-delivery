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
