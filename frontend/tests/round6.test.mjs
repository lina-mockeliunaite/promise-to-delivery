// Round 6 (13 Nov): less noise on screen. (1) the "couldn't be verified" count splits by kind; (2) wording already shown in a drawer or the locked record is shown in full once.
// The server derives the kinds (rejection_kind.py); these tests pin what the screens do with them.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { APPROVAL_SCOPE_LABEL, commitmentView, coverageLine, coverageLines, frozenView, recordLines, withoutRepeatedWording } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/round6-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CommitmentView, CoverageLines } from ${abs("Drawer.jsx")};\nexport { RecordDetail } from ${abs("FrozenRecord.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitmentView, CoverageLines, RecordDetail } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&rsquo;/g, "’");
const drawer = (v, docs) => decode(renderToStaticMarkup(createElement(CommitmentView, { v, documents: docs, titleId: "t", me: "", onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} })));
const record = (v, docs) => decode(renderToStaticMarkup(createElement(RecordDetail, { v, documents: docs, onOpenDoc() {} })));
const heads = (html) => [...html.matchAll(/<h3 class="dr-label">([^<]*)<\/h3>/g)].map((m) => m[1]);
const count = (html, text) => html.split(text).length - 1;

// ---- 1. the count ---------------------------------------------------------------------------------------------------------------------------------------------------
test("the main line counts only findings whose evidence failed; the answered ones are a quieter second line; nothing is hidden", () => {
  assert.deepEqual(coverageLines(1, { failed: 0, answered: 1 }), { main: "", quiet: "1 point the model raised was already answered by the documents." });
  assert.deepEqual(coverageLines(3, { failed: 1, answered: 2 }), { main: coverageLine(1), quiet: "2 points the model raised were already answered by the documents." });
  assert.deepEqual(coverageLines(2, { failed: 2, answered: 0 }), { main: coverageLine(2), quiet: "" });
  assert.deepEqual(coverageLines(0, { failed: 0, answered: 0 }), { main: "", quiet: "" });
  // an older server without the split: the whole total is the main line, as before
  assert.deepEqual(coverageLines(2, undefined), { main: coverageLine(2), quiet: "" });
  assert.deepEqual(coverageLines(2, null), { main: coverageLine(2), quiet: "" });
  assert.deepEqual(coverageLines(null, null), { main: "", quiet: "" });
  // the two counts add up to the total for every split
  for (const [f, a] of [[0, 0], [1, 0], [0, 1], [2, 3]]) { const l = coverageLines(f + a, { failed: f, answered: a }); assert.equal(Number(/^(\d+)/.exec(l.main)?.[1] ?? 0) + Number(/^(\d+)/.exec(l.quiet)?.[1] ?? 0), f + a); }
});

test("the lines render: main in the existing style, the quiet one marked quiet; nothing at zero", () => {
  const html = decode(renderToStaticMarkup(createElement(CoverageLines, { lines: coverageLines(2, { failed: 1, answered: 1 }) })));
  assert.ok(html.includes(`<p class="dp-coverage">${coverageLine(1)}</p>`));
  assert.ok(html.includes('<p class="dp-coverage is-quiet">1 point the model raised was already answered by the documents.</p>'));
  assert.equal(renderToStaticMarkup(createElement(CoverageLines, { lines: coverageLines(0, { failed: 0, answered: 0 }) })), "");
  assert.ok(!renderToStaticMarkup(createElement(CoverageLines, { lines: coverageLines(1, { failed: 0, answered: 1 }) })).includes("couldn't be verified"));
});

test("both pages use the split: the live page keeps hiding the lines in public mode; the record shows them from the handover's split", () => {
  // Round 7: the warning line stays under the heading and the "already answered" footnote is the last line of the Commitments section, on the live page and in the record alike
  const live = read("DealPage.jsx"), locked = read("FrozenRecord.jsx");
  assert.ok(live.includes('{!demo.public && <CoverageLines part="main" lines={coverageLines(reg.check_coverage?.rejected, reg.check_split)} />}'));
  assert.ok(locked.includes('<CoverageLines part="main" lines={coverageLines(s.check_coverage?.rejected, hv.check_split)} />'));
  assert.match(live, /<\/ul>\s*\{!demo\.public && <CoverageLines part="quiet" lines=\{coverageLines\(reg\.check_coverage\?\.rejected, reg\.check_split\)\} \/>\}\s*<\/section>/);
  assert.match(locked, /<\/ul>\s*<CoverageLines part="quiet" lines=\{coverageLines\(s\.check_coverage\?\.rejected, hv\.check_split\)\} \/>\s*<\/section>/);
});

// ---- 2. repeated wording --------------------------------------------------------------------------------------------------------------------------------------------
const SENTENCE = "Coaching-scam detection via BioCatch will be enabled from the 1 February 2027 launch.";
const ROW = "| CAP-027 Third-party behavioural intelligence connector | Australia, BioCatch signals | Beta | Named exception approved by Arjun Rao (Head of Product) from 1 May 2027, subject to the beta terms in Annex B |";
const CELL = "Named exception approved by Arjun Rao (Head of Product) from 1 May 2027, subject to the beta terms in Annex B";
const HELD = "The signed start date is earlier than the approved start date.";
const DOCS = [
  { source_key: "AB-05", name: "Internal approvals note", doc_type: "pricing_services_note", version: 2, date: "2026-10-06", version_date: "2026-10-16", source_version_id: 5, included: true },
  { source_key: "AB-06", name: "Draft SOW", doc_type: "draft_sow", version: 2, date: "2026-10-09", version_date: "2026-10-16", source_version_id: 6, included: true },
  { source_key: "AB-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true },
  { source_key: "AB-03", name: "RFP response", doc_type: "rfp_response", version: 1, date: "2026-02-01", version_date: "2026-02-01", source_version_id: 3, included: true },
];
const scope = (source, sentence = SENTENCE) => ({ status: "not_covered", reason: { signed: HELD, promise: "The promised start date is earlier than the approved start date." }[source],
  catalogue_path: "CAP-027/AU", approval: { date: "2027-05-01", line: ROW, label: "Internal approvals note", key: "AB-05", version_id: 5, doc_date: "2026-10-16" },
  start: { source, sentence, label: { signed: "Signed contract", promise: "RFP response" }[source], key: { signed: "AB-09", promise: "AB-03" }[source],
           version_id: { signed: 9, promise: 3 }[source], date: "2027-02-01", in: { signed: "signed SOW", promise: "promise" }[source] } });
const held = (source, sentence) => ({ id: 5, type: "approval", finding: APPROVAL_SCOPE_LABEL, state: "Needs action", reason: scope(source).reason, evidence: { catalogue: ["CAP-027/AU"] }, signed_check: null, approval_scope: scope(source, sentence) });
const GAP = (sentence = SENTENCE) => ({ id: 6, type: "contract_gap", finding: "Missing from contract", state: "Resolved", reason: "Closed: the contract documents now include “BioCatch”.", evidence: { missing_phrases: ["BioCatch"] },
  resolved_by: { text: "Resolved by Draft SOW, version 2" }, signed_check: { status: "confirmed", sentence, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft SOW, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)",
  signed_sentence: sentence, signed_key: "AB-09", signed_version_id: 9 } });
const COACH = (issues, statements = []) => ({ name: "BioCatch-based coaching detection", display_name: "Coaching-scam detection live at launch", contract: "Not included", statements, issues });
const TOLD = [{ quote: SENTENCE, doc_type_label: "RFP response", date: "2026-02-01" }];

test("Alder after the signed contract: the signed sentence is in full once (Why it's open); Contract says and History refer back", () => {
  const v = commitmentView(COACH([held("signed"), GAP()]), "open", DOCS);
  const html = drawer(v, DOCS);
  assert.equal(count(html, SENTENCE), 1);
  assert.ok(html.indexOf(SENTENCE) > html.indexOf("Why it’s open") && html.indexOf(SENTENCE) < html.indexOf("Contract says"));
  // Round 7: the status line is the one place Contract says names its source (the parenthesis is the link); no "Source:" line, and no History (its only line was "same wording")
  assert.ok(html.includes('<span class="dr-confirmed"><button type="button" class="dr-linkbtn">Signed contract · confirmed</button> (20 Oct): the clause shown above.</span>'));
  assert.ok(!/Contract says[\s\S]*Source:[\s\S]*What we found/.test(html.replace(/Why it’s open[\s\S]*?Contract says/, "Contract says")));
  assert.ok(!html.includes(">History<") && !html.includes("with the same wording") && !html.includes("Draft wording that closed it"));
  assert.equal(count(html, "confirmed in the signed contract (20 Oct)"), 1); // "Closed by … · confirmed in the signed contract" appears once, under Already closed by the documents
  assert.ok(html.includes(`<blockquote class="dr-quote">${CELL}</blockquote>`)); // the approval text stays in full
});

test("Alder after the approval: the promise start refers back to what the customer was told; the approval text is in full", () => {
  const v = commitmentView(COACH([held("promise")], TOLD), "open", DOCS);
  const html = drawer(v, DOCS);
  assert.equal(count(html, SENTENCE), 1); // only under "Customer was told"
  assert.ok(html.indexOf(SENTENCE) < html.indexOf("Why it’s open"));
  assert.ok(html.includes('<span class="dr-muted">Promise · 1 Feb</span><p class="dr-muted"><button type="button" class="dr-linkbtn">RFP response, 1 Feb, above</button></p>')); // the reference is the link; no Source line of its own
  assert.ok(!/Promise · 1 Feb[\s\S]*?Source:[\s\S]*?Product approval starts/.test(html));
  assert.match(html, /Promise · 1 Feb[\s\S]*?<button type="button" class="dr-linkbtn">RFP response, 1 Feb, above<\/button>/);
  assert.ok(html.includes(`<blockquote class="dr-quote">${CELL}</blockquote>`));
  assert.equal(v.scope.start.ref, "RFP response, 1 Feb, above");
});

test("the first appearance wins, in drawer order; text that differs, even by a word, is shown in full; whitespace alone does not make it different", () => {
  const spaced = SENTENCE.replace("will be", "will   be\n");
  const html = drawer(commitmentView(COACH([held("promise", spaced)], TOLD), "open", DOCS), DOCS);
  assert.ok(html.includes("RFP response, 1 Feb, above"), "whitespace-only difference folds");
  const other = drawer(commitmentView(COACH([held("promise", SENTENCE.replace("1 February", "1 March"))], TOLD), "open", DOCS), DOCS);
  assert.ok(!other.includes("RFP response, 1 Feb, above") && other.includes("1 March 2027 launch"), "a different sentence is not folded");
  // nothing is repeated, so nothing is rewritten: a view with no repeats is returned equal
  const plain = commitmentView(COACH([GAP()], []), "closed", DOCS);
  assert.deepEqual(withoutRepeatedWording(plain), plain);
  assert.ok(!drawer(plain, DOCS).includes("that mentions"));
  assert.ok(!("ref" in plain.signed));
});

test("Noma: a closed row's History says the draft had the same wording instead of repeating the signed clause; a row with no repeat is unchanged", () => {
  const CLAUSE = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
  const docs = [{ source_key: "NJ-07", name: "Draft contract", doc_type: "draft_contract", version: 2, date: "2026-10-14", version_date: "2026-10-19", source_version_id: 4, included: true },
    { source_key: "NJ-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true }];
  const c = { name: "Support in 12 languages", contract: "No gap found", statements: [], contract_now: { target: "12 languages", quote: CLAUSE, document: "Draft contract" },
    issues: [{ id: 1, finding: "Contract says something different", state: "Resolved", resolved_by: { text: "Resolved by Draft contract, version 2 · 19 Oct 2026" },
      signed_check: { status: "confirmed", sentence: CLAUSE, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft contract, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)", signed_sentence: CLAUSE, signed_key: "NJ-09", signed_version_id: 9 } }] };
  const html = drawer(commitmentView(c, "closed", docs), docs);
  assert.equal(count(html, CLAUSE), 1);
  assert.ok(!html.includes(">History<") && !html.includes("with the same wording")); // Round 7: History said only this, and "What closed it" says it once
  const none = { ...c, issues: [{ ...c.issues[0], signed_check: undefined }] };
  assert.ok(!drawer(commitmentView(none, "closed", docs), docs).includes("with the same wording"));
});

test("the locked record: the same rule on its lines; for a gap held by approval scope Why it's open comes before Contract says", () => {
  const told = [{ quote: "We will detect coaching scams from launch.", source: "RFP response", date: "2026-02-01" }]; // a different sentence from the signed clause
  const live = { issues: [held("signed"), GAP()] };
  const res = scope("signed");
  const v = frozenView({ item: { promise: "BioCatch-based coaching detection", findings: [{ finding: APPROVAL_SCOPE_LABEL, evidence: {}, signed_check: null }], quotes: told, contract: "Not included", signed: [] }, status: "open", closedFindings: [{ finding: "Missing from contract", resolved_by: "Resolved by Draft SOW, version 2" }],
    documents: DOCS, live, snapshotDocs: DOCS, approvalScopes: { "BioCatch-based coaching detection|Approval starts later": res } });
  const r = recordLines(v, DOCS);
  assert.ok(r.scope.start.includes(SENTENCE), "the first appearance is in full");
  assert.equal(r.contract, "Signed contract · confirmed (20 Oct): the clause shown above.");
  const html = record(v, DOCS);
  assert.ok(html.indexOf("Why it’s open") < html.indexOf("Contract says"));
  assert.equal(count(html, SENTENCE), 1); // the signed clause, once, in "Why it's open"
});

test("follow-up: reference-backs name the first source and its date; the lookup line names its document and date", () => {
  // the promise: "RFP response, 1 Feb, above", never a bare "the RFP response above"
  const v = commitmentView(COACH([held("promise")], TOLD), "open", DOCS);
  assert.equal(v.scope.start.ref, "RFP response, 1 Feb, above");
  assert.ok(!drawer(v, DOCS).includes("the RFP response above"));
  // a clause first shown under Why it's open, pointed back to from the draft lookup: the lookup line already names document and date, so it says "the clause shown above"
  const DRAFT = "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank.";
  const html = drawer(commitmentView({ ...COACH([held("signed", DRAFT), { ...GAP(DRAFT), signed_check: undefined }]), contract_now: { target: "scam-call alerts", quote: DRAFT, document: "Draft SOW" } }, "open", DOCS), DOCS);
  assert.ok(html.includes("Wording in Draft SOW (16 Oct) that mentions “scam-call alerts”:"));
  assert.ok(!html.includes("a lookup in the current documents") && !html.includes("Contract wording containing"));
  assert.equal(count(html, DRAFT), 1);
  // not a repeat: the lookup shows the clause in full with the new line
  const lone = drawer(commitmentView({ ...COACH([{ ...GAP(DRAFT), signed_check: undefined }]), contract_now: { target: "scam-call alerts", quote: DRAFT, document: "Draft SOW" } }, "closed", DOCS), DOCS);
  assert.ok(lone.includes("Wording in Draft SOW (16 Oct) that mentions “scam-call alerts”:") && lone.includes(DRAFT));
});

test("print: a record row is one block that print keeps together, so a reference-back never points to another page; the quiet coverage line is muted, last, and not a status", () => {
  const css = read("DealPage.css");
  assert.match(css, /@media print \{[\s\S]*?\.fr \.dp-prow \{ break-inside: avoid; \}/);
  const frozen = read("FrozenRecord.jsx");
  assert.match(frozen, /<li className=\{`dp-prow[^`]*`\}>[\s\S]*?<RecordDetail v=\{v\} documents=\{documents\} onOpenDoc=\{onOpenDoc\} anchorOf=\{anchorOf\} \/>\s*<\/li>/); // the detail (told, why it's open, contract says) is inside the row
  assert.ok(css.includes(".dp-coverage { margin: 0; padding: 0 20px 8px; font-size: 12px; color: var(--muted); }"));
  assert.ok(css.includes(".dp-coverage.is-quiet { padding-top: 0; font-size: 11.5px; opacity: .85; }"));
  const html = renderToStaticMarkup(createElement(CoverageLines, { lines: coverageLines(3, { failed: 1, answered: 2 }) }));
  assert.ok(html.lastIndexOf("is-quiet") > html.indexOf('class="dp-coverage"')); // the quiet line comes after the main line
  assert.ok(!/dp-chip|dp-dot|is-attention|amber|status/.test(html)); // no chip, dot or status styling
});
