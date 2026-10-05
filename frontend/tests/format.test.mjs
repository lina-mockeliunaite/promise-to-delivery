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
