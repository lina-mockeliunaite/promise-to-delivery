// The locked record without the noise, the drawer's grouped not-offered box, and the demo bar's colours (11 Nov). Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { byDocumentDate, commitmentView, frozenView, groupNotOffered, recordLines } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/record-noise-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CommitmentView } from ${abs("Drawer.jsx")};\nexport { RecordDetail, RecordBody } from ${abs("FrozenRecord.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitmentView, RecordDetail, RecordBody } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&");

const DOCS = [{ name: "Draft contract", version: 2, date: "2026-10-14", version_date: "2026-10-19" }, { name: "Internal approvals note", version: 2, date: "2026-10-08", version_date: "2026-10-18" }];
// Noma at handover: the specialist (approval closed, contract gap open), phone calls (not offered, addressed by note), languages (closed, confirmed in the signed contract)
const SPECIALIST = frozenView({ status: "open", documents: DOCS, titles: {},
  closedFindings: [{ finding: "No approval recorded", resolved_by: "Resolved by Internal approvals note, version 2 · 11 Nov 2026" }],
  item: { promise: "Dedicated launch specialist", contract: "Not included", contract_now: null, findings: [{ finding: "Missing from contract", evidence: { missing_phrases: ["launch specialist"] }, why: "r", seen: [] }],
    quotes: [{ quote: "A dedicated Aivuna launch specialist will work with Noma Journeys for the first 30 days.", source: "RFP response", date: "2026-09-28" }] } });
const PHONE = frozenView({ status: "noted", documents: DOCS, titles: {}, closedFindings: [],
  item: { promise: "AI answers phone calls", contract: "Not included", findings: [  // the saved column says "Not included"; the contract's wording is the conflicting finding's
    { finding: "Not offered", evidence: { unlisted_value: "phone calls", contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } }, catalogue_path: "CAP-003/SG", why: "r", seen: [],
      resolved_by_note: { by: "Maya Tan (Sales)", at: "2026-11-11T10:00:00Z", reason: "Noma agreed on 19 Oct to launch on chat and email; voice is not offered." } },
    { finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email", contract_quote: { quote: "Provider will operate the Assistant on chat and email.", source: "Draft SOW" } }, why: "r", seen: [] },
    { finding: "Missing from contract", evidence: { missing_phrases: ["phone calls"] }, why: "r", seen: [] }],
    quotes: [{ quote: "Aivuna's assistant will answer guests' phone calls and respond to chat and email.", source: "RFP response", date: "2026-09-28" }] } });
const LANGS = frozenView({ status: "closed", documents: DOCS, titles: {},
  closedFindings: [{ finding: "Contract says something different", resolved_by: "Resolved by Draft contract, version 2 · Draft SOW, version 1 unchanged · 11 Nov 2026" }],
  item: { promise: "Support in 12 languages", contract: "No gap found", contract_now: { target: "12 languages", quote: "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.", document: "Draft contract" },
    findings: [], signed: [{ status: "confirmed", text: "Confirmed in the signed contract (Signed contract, 20 Oct)" }],
    quotes: [{ quote: "Aivuna will support guest conversations in 12 languages from the 1 February 2027 launch.", source: "RFP response", date: "2026-09-28" }] } });

test("the record's commitment shows told, contract, the gap lines and how it was settled, once each", () => {
  const r = recordLines(SPECIALIST, DOCS);
  assert.deepEqual(r.told, ["“A dedicated Aivuna launch specialist will work with Noma Journeys for the first 30 days.” (RFP response, 28 Sep)"]);
  assert.equal(r.contract, "No matching wording found in the draft contract or SOW"); // once; the plain "Contract has no matching wording" line is not repeated
  // some gaps closed and one still open: both are said, per gap (never a bare "Closed by …" next to "Needs attention")
  assert.deepEqual(r.gaps, []);
  assert.deepEqual(r.settled, ["Approval: closed by Internal approvals note v2 (18 Oct)", "Not in the contract: still open"]);
  const html = decode(renderToStaticMarkup(createElement(RecordDetail, { v: SPECIALIST, documents: DOCS })));
  assert.equal(html.split("no matching wording").length - 1 + html.split("No matching wording").length - 1, 1);
  for (const gone of ["Extracted as", "AI-written", "Gap closed", "Check on", "unchanged, checked with it", "Contract has no matching wording"]) assert.ok(!html.includes(gone), gone);
  assert.ok(html.includes("<strong>Customer was told:</strong>") && html.includes("<strong>Contract says:</strong>"));
});

test("a not-offered commitment is one line instead of three overlapping findings, and keeps its note with who and when", () => {
  const r = recordLines(PHONE, DOCS);
  assert.deepEqual(r.gaps, ["Not offered: the catalogue has no phone calls option; the contract says chat and email"]);
  assert.equal(r.gaps.length, 1);
  assert.ok(r.settled.some((l) => l.includes("Maya Tan (Sales)") && l.includes("Noma agreed on 19 Oct to launch on chat and email; voice is not offered.")));
  const html = decode(renderToStaticMarkup(createElement(RecordDetail, { v: PHONE, documents: DOCS })));
  assert.ok(!html.includes("Promise: Not offered") && !html.includes("The contract says something different") && !html.includes("No exception can sell it") && !html.includes("Addressed by note"));
});

test("a closed commitment reads 'Closed by <document> v<N> (<date>) · confirmed in the signed contract (<date>)' with the contract quote", () => {
  const r = recordLines(LANGS, DOCS);
  assert.deepEqual(r.settled, ["Closed by Draft contract v2 (19 Oct) · confirmed in the signed contract (20 Oct)"]);
  assert.equal(r.contract, "“The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.” (Draft contract)");
  assert.deepEqual(r.gaps, []);
  const html = decode(renderToStaticMarkup(createElement(RecordDetail, { v: LANGS, documents: DOCS })));
  for (const gone of ["No gap found", "Contract wording containing", "unchanged", "checked with it", "Check on", "a lookup in the current documents", "that mentions"]) assert.ok(!html.includes(gone), gone);
});

test("the record page is cut down: no verdict sentence, 'Commitments' only, no scope note, the brief first, the short footer, documents oldest first", () => {
  const src = read("FrozenRecord.jsx");
  assert.ok(!src.includes("verdictLine") && !src.includes("scope_note") && !src.includes("Handed over with") && !src.includes("Demonstrated on") && !src.includes("At handover"));
  assert.match(src, /Checked \{s\.documents\.length\} documents and the product catalogue<\/p>/);
  assert.match(src, /recordPills\(counts\)\.map/); assert.match(src, /dp-chip dp-chip-amber/); // the three count chips stay (13 Nov, Round 7: a zero count is not shown; see round7.test.mjs)
  assert.ok(src.indexOf("<BriefCard") > src.indexOf('<section className="dp-card fr-head"') && src.indexOf("<BriefCard") < src.indexOf("<h2>Commitments</h2>"));
  assert.match(src, /<footer className="dp-foot">\{FICTIONAL\}<\/footer>/);
  assert.ok(!src.includes("PrintDetail") && !src.includes('"fr-print"') && !src.includes("AI-written"));
  const docs = [{ name: "B", date: "2026-10-12", sha256: "bb" }, { name: "A", date: "2026-10-05", sha256: "aa" }, { name: "C", date: "2026-10-05", version_date: "2026-10-20", sha256: "cc" }, { name: "A2", date: "2026-10-05", sha256: "a2" }];
  assert.deepEqual(byDocumentDate(docs).map((d) => d.name), ["A", "A2", "B", "C"]);
  assert.deepEqual(byDocumentDate(docs).map((d) => d.sha256).sort(), ["a2", "aa", "bb", "cc"]); // every document keeps its own hash
  assert.deepEqual(docs.map((d) => d.name), ["B", "A", "C", "A2"]); // the saved list is not reordered
});

test("the record's hashes are rendered as saved: the fingerprint and each document's SHA-256 are shown verbatim, and no new code computes one", () => {
  const src = read("FrozenRecord.jsx");
  assert.match(src, /title=\{hv\.fingerprint\}><span className="fr-h-short">\{hv\.fingerprint\.slice\(0, 12\)\}…\{hv\.fingerprint\.slice\(-4\)\}<\/span><span className="fr-h-full">\{hv\.fingerprint\}<\/span>/);
  assert.match(src, /SHA-256 <span className="fr-h-short">\{shortHash\(d\.sha256\)\}<\/span><span className="fr-h-full">\{d\.sha256\}<\/span>/);
  assert.ok(!/crypto|subtle|createHash|digest\(/.test(src + read("dealpage.js").slice(read("dealpage.js").indexOf("export function recordLines"))));
});

// ---- the drawer
const NOT_OFFERED = [{ id: 1, state: "Needs action", finding: "Not offered", evidence: { unlisted_value: "phone calls" }, catalogue_path: "CAP-003/SG", reason: "r" },
  { id: 2, state: "Needs action", finding: "Contract says something different", evidence: { promised_value: "phone calls", contract_value: "chat and email" }, reason: "r" },
  { id: 3, state: "Needs action", finding: "Missing from contract", evidence: { missing_phrases: ["phone calls"] }, reason: "r" }];
test("the drawer groups the overlapping findings under the not-offered line: one box, the others beneath it, and no 'Extracted as'", () => {
  const v = commitmentView({ name: "Assistant will answer guests' phone calls in addition to chat and email", display_name: "AI answers customers' phone calls", contract: "chat and email", statements: [], issues: NOT_OFFERED }, "open", []);
  assert.equal(v.found.length, 1);
  assert.match(v.found[0].label, /^Not offered/);
  assert.equal(v.found[0].sub.length, 2);
  const html = decode(renderToStaticMarkup(createElement(CommitmentView, { v, titleId: "t", me: "", onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} })));
  assert.equal((html.match(/class="dr-row"/g) || []).length, 1);
  assert.equal((html.match(/class="dr-sub"/g) || []).length, 2);
  assert.ok(!html.includes("Extracted as"));
  assert.deepEqual(groupNotOffered([{ label: "a", fact: "" }], [{ finding: "Not offered" }]), [{ label: "a", fact: "" }]); // a lone finding is untouched
  assert.equal(groupNotOffered([{ label: "x", fact: "" }, { label: "y", fact: "" }], [{ finding: "Missing from contract" }, { finding: "No approval recorded" }]).length, 2); // no not-offered: unchanged
});

// ---- the demo bar's colours
const lum = (hex) => { const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
test("the demo bar is dark slate with white text, an indigo button and light links; every text pair is AA (4.5:1)", () => {
  const css = read("App.css");
  const bar = css.match(/\.demo-bar \{ position: sticky; top: 0; z-index: 70; background: (#[0-9a-f]{6}); color: (#[0-9a-f]{6});/);
  assert.deepEqual([bar[1], bar[2]], ["#1e293b", "#ffffff"]);
  const link = css.match(/\.demo-bar-link \{[^}]*color: (#[0-9a-f]{6});/)[1];
  const btn = css.match(/\.demo-bar-do \{[^}]*background: (#[0-9a-f]{6}); color: (#[0-9a-f]{6});/);
  assert.equal(btn[1], "#4f46e5");
  assert.ok(!/prefers-color-scheme: dark\) \{ \.demo-bar/.test(css), "one look in both schemes");
  const pairs = [["bar text", bar[2], bar[1]], ["links", link, bar[1]], ["button", btn[2], btn[1]], ["menu text", "#e2e8f0", "#1e293b"], ["menu note", "#cbd5e1", "#1e293b"],
    ["current step", "#ffffff", "#312e81"], ["step number", "#ffffff", "#4f46e5"], ["done tick", "#bbf7d0", "#14532d"], ["confirm button", "#ffffff", "#334155"], ["confirm primary", "#ffffff", "#4f46e5"], ["confirm error", "#fcd34d", "#1e293b"]];
  for (const [name, fg, bg] of pairs) assert.ok(ratio(fg, bg) >= 4.5, `${name}: ${ratio(fg, bg).toFixed(2)}`);
  for (const [name, fg, bg] of [["menu text", "#e2e8f0", "#1e293b"], ["links", link, bar[1]]]) assert.ok(css.includes(fg) && css.includes(bg), name); // the colours under test are the ones in the stylesheet
  assert.match(css, /\.demo-bar-menu \.demo-guide-list li\.is-current \{ background: #312e81; color: #ffffff; \}/);
  assert.match(css, /\.demo-bar-reset \.dl-btn:first-child \{ background: #4f46e5;/);
});

// ---- partly closed, and what always prints
test("a partly closed commitment says both, per gap, on the record (the Noma specialist); a fully closed or fully open one is unchanged", () => {
  const html = decode(renderToStaticMarkup(createElement(RecordDetail, { v: SPECIALIST, documents: DOCS })));
  assert.ok(html.includes('<p class="fr-settled">Approval: closed by Internal approvals note v2 (18 Oct)</p>'));
  assert.ok(html.includes('<p class="fr-settled is-open">Not in the contract: still open</p>')); // the open gap carries the amber class; the closed line does not
  assert.ok(html.indexOf("closed by Internal approvals note") < html.indexOf("still open"));
  assert.ok(!html.includes(">Closed by Internal approvals note v2 (18 Oct)<")); // the bare line that read as resolved
  // a signed-contract confirmation stays attached to the closed gap, and the open gap is still named
  const withSigned = recordLines({ ...SPECIALIST, signedLines: ["Confirmed in the signed contract (Signed contract, 20 Oct)"] }, DOCS);
  assert.deepEqual(withSigned.settled, ["Approval: closed by Internal approvals note v2 (18 Oct) \u00B7 confirmed in the signed contract (20 Oct)", "Not in the contract: still open"]);
  // nothing closed: the gap lines, no "still open" bookkeeping; everything closed: the one closed line
  assert.deepEqual(recordLines({ ...SPECIALIST, closed: [], openGaps: ["Not in the contract"] }, DOCS).settled, []);
  assert.deepEqual(recordLines(LANGS, DOCS).settled, ["Closed by Draft contract v2 (19 Oct) \u00B7 confirmed in the signed contract (20 Oct)"]);
  // two gaps closed by different documents, one open: each gap named
  const two = { ...SPECIALIST, closed: [{ finding: "No approval recorded", label: "No approval found", by: "Closed by Internal approvals note, version 2 \u00B7 checked 11 Nov 2026" },
    { finding: "Missing from contract", label: "Not in the contract", by: "Closed by Draft contract, version 2 \u00B7 checked 11 Nov 2026" }], openGaps: ["Contract differs"] };
  assert.deepEqual(recordLines(two, DOCS).settled, ["Approval: closed by Internal approvals note v2 (18 Oct)", "Contract wording: closed by Draft contract v2 (19 Oct)", "Contract differs: still open"]);
});

test("print always carries the documents at handover (each SHA-256) and the fingerprint, unfolded, whatever the on-screen fold does", () => {
  const s = { documents: [{ name: "Draft contract", version: 2, date: "2026-10-14", version_date: "2026-10-19", sha256: "a".repeat(64), source_version_id: 7, text_stored: true },
    { name: "Draft SOW", version: 1, date: "2026-10-12", sha256: "b".repeat(64), source_version_id: 6, text_stored: true }] };
  const hv = { fingerprint: "f".repeat(64) };
  for (const interactive of [true, false]) {
    const html = renderToStaticMarkup(createElement(RecordBody, { s, hv, interactive, setDrawer() {}, copy() {}, copied: false }));
    assert.ok(html.includes("Documents at handover") && html.includes("Record fingerprint"));
    assert.ok(html.includes("a".repeat(64)) && html.includes("b".repeat(64)) && html.includes("f".repeat(64))); // every hash, in full
    assert.ok(html.indexOf("Draft SOW") < html.indexOf("Draft contract")); // oldest first
  }
  const src = read("FrozenRecord.jsx");
  // the folded copy and a print-only copy outside the <details>, both from the one component
  assert.match(src, /<details className="dp-card fr-record"[^>]*>[\s\S]*?<RecordBody s=\{s\} hv=\{hv\} interactive [^>]*\/>[\s\S]*?<\/details>\s*<section className="dp-card fr-print-record" aria-hidden="true">\s*<RecordBody s=\{s\} hv=\{hv\} interactive=\{false\}/);
  const css = read("DealPage.css");
  assert.match(css, /\.fr-print-record \{ display: none; \}/); // not on screen: the fold is the screen's copy
  const print = css.slice(css.indexOf("@media print {\n  .fr-noprint, .dr, .dr-backdrop"));
  assert.match(print, /\.fr \.fr-record \{ display: none; \}/); // the folded copy is not printed (a closed fold would print nothing anyway)
  assert.match(print, /\.fr \.fr-print-record \{ display: block;/); // the always-visible copy is
  assert.match(print, /\.fr \.fr-h-full \{ display: inline; word-break: break-all; \}/); // hashes in full
  assert.ok(!/\.fr-print-record[^}]*(display: none|visibility: hidden)/.test(print.replace(/\.fr \.fr-record \{ display: none; \}/, "")));
});

test("a 'still open' gap line is amber at normal weight on screen and in print; closed lines stay muted", () => {
  const html = decode(renderToStaticMarkup(createElement(RecordDetail, { v: SPECIALIST, documents: DOCS })));
  assert.equal((html.match(/class="fr-settled is-open"/g) || []).length, 1);
  assert.ok(html.includes('<p class="fr-settled">Approval: closed by Internal approvals note v2 (18 Oct)</p>')); // closed: no amber class
  assert.ok(!decode(renderToStaticMarkup(createElement(RecordDetail, { v: LANGS, documents: DOCS }))).includes("is-open")); // a fully closed commitment has none
  const css = read("DealPage.css");
  assert.match(css, /\.fr-detail \.fr-settled \{ color: var\(--muted\); font-size: 12\.5px; \}/); // closed lines: muted
  assert.match(css, /\.fr-detail \.fr-settled\.is-open \{ color: var\(--amber-text\); font-weight: 400; \}/);
  const print = css.slice(css.indexOf("@media print {\n  .fr-noprint, .dr, .dr-backdrop"));
  assert.match(print, /\.fr \.fr-detail \.fr-settled\.is-open \{ color: var\(--amber-text\); \}/); // print keeps it
  assert.match(css, /--amber-text: #b45309;/); // the colour of the "Needs attention" chip text (.dp-chip-amber)
  assert.match(css, /\.dp-chip-amber \{[^}]*color: var\(--amber-text\)/);
});
