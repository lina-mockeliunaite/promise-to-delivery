// Approval scope (Round 5, 12 Nov): an approval that closed the approval gap but starts later than the commitment holds the gap open. The server decides (approval_scope.py);
// these tests pin what the screens say: the drawer, the row, the result dialog and the locked record. Noma, whose approvals carry no dates, must not change.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { APPROVAL_SCOPE_DETAIL, APPROVAL_SCOPE_LABEL, FINDING_SHORT, SCOPE_HELD_TITLE, approvalScopeOf, changeView, commitmentView, frozenView, promiseLabels, recordLines, scopeHeldDetail,
         scopeNotesOf, scopeRowLines, suggestFix, whatChanged } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/approval-scope-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CommitmentView } from ${abs("Drawer.jsx")};\nexport { ChangeDialog, CommitRow } from ${abs("DealPage.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitmentView, ChangeDialog, CommitRow } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&rsquo;/g, "’");
const drawer = (v, docs) => decode(renderToStaticMarkup(createElement(CommitmentView, { v, documents: docs, titleId: "t", me: "", onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} })));
const heads = (html) => [...html.matchAll(/<h3 class="dr-label">([^<]*)<\/h3>/g)].map((m) => m[1]);

const SENTENCE = "Coaching-scam detection via BioCatch will be enabled from the 1 February 2027 launch.";
const ROW = "| CAP-027 Third-party behavioural intelligence connector | Australia, BioCatch signals | Beta; requires named approval; planned GA 31 December 2027 | Named exception approved by Arjun Rao (Head of Product) from 1 May 2027, subject to the beta terms in Annex B |";
const CELL = "Named exception approved by Arjun Rao (Head of Product) from 1 May 2027, subject to the beta terms in Annex B";
const HELD = "The signed start date is earlier than the approved start date.";
const DOCS = [
  { source_key: "AB-05", name: "Internal approvals note", doc_type: "pricing_services_note", version: 2, date: "2026-10-06", version_date: "2026-10-16", source_version_id: 5, included: true },
  { source_key: "AB-06", name: "Draft SOW", doc_type: "draft_sow", version: 2, date: "2026-10-09", version_date: "2026-10-16", source_version_id: 6, included: true },
  { source_key: "AB-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true },
  { source_key: "AB-03", name: "RFP response", doc_type: "rfp_response", version: 1, date: "2026-09-29", version_date: "2026-09-29", source_version_id: 3, included: true },
];
const scope = (source = "signed", extra = {}) => ({ status: "not_covered", reason: { signed: HELD, contract: "The contract start date is earlier than the approved start date.", promise: "The promised start date is earlier than the approved start date." }[source],
  catalogue_path: "CAP-027/AU", approval: { date: "2027-05-01", line: ROW, label: "Internal approvals note", key: "AB-05", version_id: 5, doc_date: "2026-10-16" },
  start: { source, sentence: SENTENCE, label: { signed: "Signed contract", contract: "Draft SOW", promise: "RFP response" }[source], key: { signed: "AB-09", contract: "AB-06", promise: "AB-03" }[source],
           version_id: { signed: 9, contract: 6, promise: 3 }[source], date: "2027-02-01", in: { signed: "signed SOW", contract: "draft SOW", promise: "promise" }[source] }, ...extra });
const held = (source = "signed", extra = {}) => ({ id: 5, type: "approval", finding: APPROVAL_SCOPE_LABEL, state: "Needs action", reason: scope(source).reason, evidence: { catalogue: ["CAP-027/AU"] }, signed_check: null, approval_scope: scope(source, extra) });
const CONTRACT_GAP = { id: 6, type: "contract_gap", finding: "Missing from contract", state: "Resolved", reason: "Closed: the contract documents now include “BioCatch”.", evidence: { missing_phrases: ["BioCatch"] },
  resolved_by: { text: "Resolved by Draft SOW, version 2" }, signed_check: { status: "confirmed", sentence: SENTENCE, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft SOW, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)",
  signed_sentence: SENTENCE, signed_key: "AB-09", signed_version_id: 9 } };
const COACH = (issues) => ({ name: "BioCatch-based coaching detection", display_name: "Coaching-scam detection live at launch", contract: "Not included", statements: [], issues });

test("the drawer: Why it's open first (the reason once), then the two dated clauses with their sources, then the rest; the false label is replaced and nothing is repeated", () => {
  const v = commitmentView(COACH([held("signed"), CONTRACT_GAP]), "open", DOCS);
  assert.deepEqual([v.scope.reason, v.scope.start.heading, v.scope.approval.heading], [HELD, "Signed SOW · 1 Feb", "Product approval starts · 1 May"]);
  assert.equal(v.scope.approval.quote, CELL); // the approval's own cell, not the table row
  const html = drawer(v, DOCS);
  const h = heads(html);
  assert.deepEqual(h.slice(0, 5), ["Where it stands", "Customer was told", "Why it’s open", "Contract says", "What we found"]);
  assert.ok(html.includes(`<h3 class="dr-label">Why it’s open</h3><p class="dr-plain">${HELD}</p>`));
  assert.equal(html.split(HELD).length - 1, 1); // the reason is shown once
  assert.ok(html.includes(`<span class="dr-muted">Signed SOW · 1 Feb</span><blockquote class="dr-quote">${SENTENCE}</blockquote>`));
  assert.ok(html.includes(`<span class="dr-muted">Product approval starts · 1 May</span><blockquote class="dr-quote">${CELL}</blockquote>`));
  assert.match(html, /Signed SOW · 1 Feb[\s\S]*?<button type="button" class="dr-linkbtn">Signed contract, 20 Oct<\/button>[\s\S]*?Product approval starts · 1 May[\s\S]*?<button type="button" class="dr-linkbtn">Internal approvals note, 16 Oct<\/button>/);
  assert.equal(APPROVAL_SCOPE_DETAIL, "The approval starts later than the commitment.");
  assert.ok(html.includes(`<div class="dr-row"><strong>The approval starts later than the commitment.</strong></div>`) && !html.includes("No approval found")); // What we found, only for the gap held open by scope
  assert.ok(!html.includes("narrower scope")); // the generic sentence is not shown anywhere
  assert.deepEqual(v.found, [{ label: APPROVAL_SCOPE_DETAIL, fact: "" }]);
  assert.deepEqual(v.ai, []); // the reason is code's, not an AI-written line
});

test("the heading of the start clause follows its source: Signed SOW, Draft SOW / contract, Promise; the reason follows too", () => {
  const by = (source) => commitmentView(COACH([held(source)]), "open", DOCS).scope;
  assert.deepEqual([by("signed").start.heading, by("signed").reason], ["Signed SOW · 1 Feb", "The signed start date is earlier than the approved start date."]);
  assert.deepEqual([by("contract").start.heading, by("contract").reason], ["Draft SOW · 1 Feb", "The contract start date is earlier than the approved start date."]);
  assert.deepEqual([by("promise").start.heading, by("promise").reason], ["Promise · 1 Feb", "The promised start date is earlier than the approved start date."]);
  assert.equal(approvalScopeOf([held("signed", { start: { ...scope().start, in: "signed contract" } })], DOCS).start.heading, "Signed contract · 1 Feb");
});

test("the row and the badge: the reason as a note on the row, and a badge that is not false", () => {
  assert.deepEqual(scopeRowLines([held("promise")]), ["The promised start date is earlier than the approved start date."]);
  assert.deepEqual(promiseLabels([held("signed")]), [FINDING_SHORT[APPROVAL_SCOPE_LABEL]]);
  assert.equal(FINDING_SHORT[APPROVAL_SCOPE_LABEL], "Approval starts later");
  const html = decode(renderToStaticMarkup(createElement(CommitRow, { c: COACH([held("signed"), CONTRACT_GAP]), status: "open", active: false, onOpen() {}, documents: DOCS })));
  assert.ok(html.includes("Approval starts later") && html.includes(`<span class="dp-prow-note">${HELD}</span>`));
  assert.ok(!html.includes("No approval found"));
  assert.match(suggestFix([{ finding: APPROVAL_SCOPE_LABEL }], DOCS).hint, /starts on or before the promised start date/);
});

test("no dates, or an approval that covers the start: nothing changes; the note appears only when exactly one date was found (the server says so)", () => {
  const closed = (status, note) => ({ id: 5, type: "approval", finding: "No approval recorded", state: "Resolved", reason: "Closed: the pricing note now records an approval with a named approver: x.", resolved_by: { text: "Resolved by Internal approvals note, version 2" },
    signed_check: null, approval_scope: { status, note, approval: { date: null }, start: { date: null } } });
  assert.deepEqual(scopeNotesOf([closed("no_dates", "No start dates to compare.")]), ["No start dates to compare."]);
  assert.deepEqual(scopeNotesOf([closed("no_dates", null), closed("covered", undefined)]), []); // neither date: silence (Noma); covered: nothing to say
  assert.ok(drawer(commitmentView(COACH([closed("no_dates", "No start dates to compare."), CONTRACT_GAP]), "open", DOCS), DOCS).includes("No start dates to compare."));
  assert.ok(!drawer(commitmentView(COACH([closed("no_dates", null)]), "closed", DOCS), DOCS).includes("No start dates"));
});

test("Noma unchanged: a closed approval with no dates renders exactly as it does without the approval_scope field", () => {
  const base = { id: 5, type: "approval", finding: "No approval recorded", state: "Resolved", reason: "Closed: the pricing note now records an approval with a named approver: Omar Haddad.", resolved_by: { text: "Resolved by Internal approvals note, version 2" }, signed_check: null };
  const withField = { ...base, approval_scope: { status: "no_dates", note: null, approval: { date: null }, start: null } };
  const open = { id: 7, type: "contract_gap", finding: "Missing from contract", state: "Needs action", reason: "Still holds.", evidence: { missing_phrases: ["launch specialist"] }, signed_check: null };
  for (const status of ["open", "closed"]) {
    const a = drawer(commitmentView(COACH([base, open]), status, DOCS), DOCS), b = drawer(commitmentView(COACH([withField, open]), status, DOCS), DOCS);
    assert.equal(a, b, status);
  }
  const v = commitmentView(COACH([withField, open]), "open", DOCS);
  assert.deepEqual([v.scope, v.scopeNotes], [null, []]);
});

test("result dialog, Alder steps 2 to 4: the approval was found but starts later than the promised date, and the gap stays open (exact strings)", () => {
  assert.equal(SCOPE_HELD_TITLE, "Approval found, but it starts later than the promised date");
  const reg = (issues) => ({ commitments: [{ id: 1, name: "BioCatch-based coaching detection", issues }] });
  const before = reg([{ id: 5, type: "approval", finding: "No approval recorded", state: "Needs action", signed_check: null }, { id: 6, type: "contract_gap", finding: "Missing from contract", state: "Needs action", signed_check: null }]);
  // step 2: AB-05 added. The start date comes from the promise.
  const step2 = whatChanged(before, reg([held("promise"), { id: 6, type: "contract_gap", finding: "Missing from contract", state: "Needs action", signed_check: null }]));
  assert.equal(step2.scopeHeld.length, 1);
  assert.equal(scopeHeldDetail(step2.scopeHeld[0]), "The approval starts 1 May 2027; the promise starts 1 February 2027. The gap stays open.");
  const view = changeView({ ...step2, acted: "BioCatch-based coaching detection" }, (n) => n, null);
  assert.equal(view.headline, "Approval found, but it starts later than the promised date, the gap stays open: BioCatch-based coaching detection.");
  assert.equal(step2.stillOpen.some((x) => x.finding === APPROVAL_SCOPE_LABEL), false); // said once
  const html = decode(renderToStaticMarkup(createElement(ChangeDialog, { change: { ...step2, openPromises: 1, doc: "Internal approvals note, new version (v2, 16 Oct)", acted: null, modelCalls: 0 }, titleOf: (n) => n, onClose() {} })));
  assert.ok(html.includes("<strong>Approval found, but it starts later than the promised date</strong><span class=\"dp-change-still\"> · still open</span>"));
  assert.ok(html.includes("<p>The approval starts 1 May 2027; the promise starts 1 February 2027. The gap stays open.</p>"));
  assert.ok(!html.includes("The promised start date is earlier than the approved start date.")); // the reason is the drawer's, not the dialog's
  assert.ok(!html.includes("dp-change-by"));
  // step 3: the revised SOW closes the contract gap; the approval gap was already held, so it is not announced again, and it is still open
  const afterAB05 = reg([held("promise"), { id: 6, type: "contract_gap", finding: "Missing from contract", state: "Needs action", signed_check: null }]);
  const step3 = whatChanged(afterAB05, reg([held("contract"), { ...CONTRACT_GAP, signed_check: null }]));
  assert.equal(step3.scopeHeld.length, 0);
  assert.equal(step3.closed.length, 1);
  assert.equal(step3.stillOpen.some((x) => x.finding === APPROVAL_SCOPE_LABEL), true);
  // step 4: the signed contract confirms the contract fix; the approval is still open
  const step4 = whatChanged(reg([held("contract"), { ...CONTRACT_GAP, signed_check: null }]), reg([held("signed"), CONTRACT_GAP]));
  assert.deepEqual([step4.confirmed.length, step4.scopeHeld.length, step4.stillOpen.some((x) => x.finding === APPROVAL_SCOPE_LABEL)], [1, 0, true]);
  // the detail names the source of the start date
  assert.equal(scopeHeldDetail({ approvalDate: "2027-05-01", startDate: "2027-02-01", source: "signed" }), "The approval starts 1 May 2027; the signed SOW starts 1 February 2027. The gap stays open.");
  assert.equal(scopeHeldDetail({ approvalDate: "2027-05-01", startDate: "2027-02-01", source: "contract" }), "The approval starts 1 May 2027; the contract starts 1 February 2027. The gap stays open.");
});

test("a gap that was never held and has nothing new: the dialog says nothing about approval scope (unchanged behaviour)", () => {
  const reg = (issues) => ({ commitments: [{ id: 1, name: "P", issues }] });
  const open = { id: 5, type: "approval", finding: "No approval recorded", state: "Needs action", signed_check: null };
  const c = whatChanged(reg([open]), reg([open]));
  assert.deepEqual(c.scopeHeld, []);
  assert.equal(changeView(c, (n) => n, null).headline, "Nothing closed and nothing new: the document did not change any gap.");
});

test("the locked record: Why it's open, then the two clauses, in one markup for screen and print (links screen-only); records locked before this have none", () => {
  const item = { promise: "BioCatch-based coaching detection", contract: "Not included", quotes: [], findings: [{ finding: APPROVAL_SCOPE_LABEL, catalogue_path: "CAP-027/AU", why: HELD, signed_check: null }] };
  const map = { [`BioCatch-based coaching detection|${APPROVAL_SCOPE_LABEL}`]: scope("signed") };
  const v = frozenView({ item, status: "open", documents: DOCS, titles: {}, relatedMap: {}, approvalScopes: map });
  assert.equal(v.scope.reason, HELD);
  const r = recordLines(v, DOCS);
  assert.equal(r.scope.why, HELD);
  assert.equal(r.scope.start, `Signed SOW · 1 Feb: “${SENTENCE}” (Signed contract, 20 Oct)`);
  assert.equal(r.scope.approval, `Product approval starts · 1 May: “${CELL}” (Internal approvals note, 16 Oct)`);
  assert.equal(frozenView({ item, status: "open", documents: DOCS, titles: {}, approvalScopes: {} }).scope, null);
  assert.deepEqual(v.found, [{ label: APPROVAL_SCOPE_DETAIL, fact: "" }]);
  assert.deepEqual(v.ai, []);
  const fr = read("FrozenRecord.jsx");
  const why = fr.indexOf("<strong>Why it&rsquo;s open:</strong> {r.scope.why}"), start = fr.indexOf("{r.scope.start}"), approval = fr.indexOf("{r.scope.approval}"), reopened = fr.indexOf("Why it reopened:");
  assert.ok(why > 0 && start > why && approval > start && reopened > approval); // the record's order
  assert.equal((fr.match(/dr-linkbtn fr-noprint/g) ?? []).length >= 4, true); // every link is screen-only; the clause text prints
});
