// Round 10 (14 Nov): Print or save as PDF looks like the live locked record and keeps all its evidence: card borders, status outlines and icons, the page-margin header and footer,
// and (with the full text) each citation linked to its mark in the appendix, only when the quote is found word for word. Print and display only: no snapshot, fingerprint, hash, engine, cache or golden change.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { quoteRange, planAnchors, citationsOf, plainParagraphs } from "../src/appendix.js";
import { parsePreview } from "../src/preview.js";
import { appendixEntries } from "../src/docHash.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/round10-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { PlainText, RecordDetail } from ${abs("FrozenRecord.jsx")};\nexport { PreviewDoc } from ${abs("DemoUI.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { PlainText, RecordDetail, PreviewDoc } = await import(file);
const css = read("DealPage.css");
const printCss = css.slice(css.indexOf("@media print {\n  .fr-noprint"), css.indexOf("/* Locked record: document hashes"));

const SIGNED = "# Master Services Agreement\n\n**Clause 4. Languages.** The Assistant will respond to Guest enquiries in 12 languages,\nlisted in Schedule 1.\n\n| Item | Detail |\n| --- | --- |\n| Support hours | Monday to Friday, 08:00 to 18:00 |\n\n- Voice is not offered.\n";
const doc = { source_version_id: "sv-signed", name: "Signed contract" };

test("quoteRange: word for word (spaces may differ), nothing else", () => {
  const q = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
  const r = quoteRange(SIGNED, q); // the stored text breaks the line after "languages,"
  assert.equal(SIGNED.slice(r.from, r.to).replace(/\s+/g, " "), q);
  assert.equal(quoteRange(SIGNED, "The Assistant will respond to Guest enquiries in 11 languages"), null); // one word differs
  assert.equal(quoteRange(SIGNED, "the assistant will respond"), null); // not case-folded
  assert.equal(quoteRange(SIGNED, ""), null);
  assert.equal(quoteRange("", "x"), null);
});

test("planAnchors: a citation links only when its quote is in that document; every other case says why", () => {
  const entries = [{ id: "sv-signed", text: SIGNED }, { id: "sv-late", text: null }];
  const q = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
  const cites = [
    { doc, quote: q },
    { doc, quote: "Monday to Friday, 08:00 to 18:00" },
    { doc, quote: "Support in 14 languages" },
    { doc: null, quote: "x" },
    { doc: { source_version_id: "sv-late" }, quote: "x" },
    { doc: { source_version_id: "sv-gone" }, quote: "x" },
  ];
  const plan = planAnchors(entries, cites);
  assert.match(plan.status(doc, q).id, /^ap0-\d$/);
  assert.match(plan.status(doc, "Monday to Friday, 08:00 to 18:00").id, /^ap0-\d$/);
  assert.notEqual(plan.status(doc, q).id, plan.status(doc, "Monday to Friday, 08:00 to 18:00").id);
  assert.deepEqual(plan.status(doc, "Support in 14 languages"), { reason: "not-found" });
  assert.deepEqual(plan.status(null, "x"), { reason: "no-document" });
  assert.deepEqual(plan.status({ source_version_id: "sv-late" }, "x"), { reason: "no-text" });
  assert.deepEqual(plan.status({ source_version_id: "sv-gone" }, "x"), { reason: "no-text" });
  assert.equal(plan.anchorOf(doc, "Support in 14 languages"), null);
  // the same clause cited twice is one mark; overlapping quotes share one mark
  const again = planAnchors(entries, [{ doc, quote: q }, { doc, quote: q }, { doc, quote: "Guest enquiries in 12 languages" }]);
  assert.equal(again.marks["sv-signed"].length, 1);
  assert.equal(again.status(doc, q).id, again.status(doc, "Guest enquiries in 12 languages").id);
});

test("citationsOf: told quotes, the scope's two clauses, the contract line (signed first) and the related clause", () => {
  const v = { told: [{ quote: "a", doc: null }, { quote: "b", doc: doc }], scope: { start: { quote: "s", doc }, approval: { quote: "p", doc } }, signed: { quote: "c", doc }, contract: {}, related: { quote: "r", doc } };
  assert.deepEqual(citationsOf(v).map((c) => `${c.kind}:${c.quote}`), ["told:a", "told:b", "scope-start:s", "scope-approval:p", "contract:c", "related:r"]);
  assert.deepEqual(citationsOf({ told: [], contract: { quote: { quote: "d", doc } } }).map((c) => c.kind), ["contract"]);
  assert.deepEqual(citationsOf({ told: [], contract: {} }), []);
});

test("parsePreview with offsets: every text node knows where it starts in the stored text; without them nothing changes", () => {
  const walk = (nodes, f) => nodes.forEach((n) => (n.children ? walk(n.children, f) : f(n)));
  const check = (nodes) => walk(nodes, (n) => assert.equal(SIGNED.slice(n.start, n.start + n.text.length), n.text));
  for (const b of parsePreview(SIGNED, true)) {
    if (b.t === "h") check(b.nodes);
    else if (b.t === "p") b.lines.forEach((l) => check(l.nodes));
    else if (b.t === "ul") b.items.forEach((i) => check(i.nodes));
    else if (b.t === "table") [b.head, ...b.rows].forEach((r) => r.cells.forEach(check));
  }
  assert.deepEqual(parsePreview(SIGNED), parsePreview(SIGNED, false));
  assert.equal(parsePreview(SIGNED)[0].nodes[0].start, 0); // as before: offsets within the line
  assert.equal(parsePreview(SIGNED, true)[0].nodes[0].start, 2); // with offsets: after "# " in the stored text
});

test("PreviewDoc draws a mark on exactly the quote (also in a table cell, across a line break), the first carrying its id; no marks, no change", () => {
  const plan = planAnchors([{ id: "sv-signed", text: SIGNED }], [
    { doc, quote: "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1." }, { doc, quote: "Monday to Friday, 08:00 to 18:00" }]);
  const html = renderToStaticMarkup(createElement(PreviewDoc, { text: SIGNED, marks: plan.marks["sv-signed"] }));
  assert.match(html, /<mark id="ap0-1">The Assistant will respond to Guest enquiries in 12 languages,<\/mark>/);
  assert.match(html, /<mark>listed in Schedule 1\.<\/mark>/); // the second line of the same quote: marked, no second id
  assert.match(html, /<td><mark id="ap0-2">Monday to Friday, 08:00 to 18:00<\/mark><\/td>/);
  assert.match(html, /<strong>Clause 4\. Languages\.<\/strong>/); // text outside the quote is untouched
  assert.equal(renderToStaticMarkup(createElement(PreviewDoc, { text: SIGNED })).includes("<mark"), false);
  assert.equal(renderToStaticMarkup(createElement(PreviewDoc, { text: SIGNED, marks: [] })), renderToStaticMarkup(createElement(PreviewDoc, { text: SIGNED })));
});

test("PlainText marks the quote in a document that is not Markdown; without marks it is as before", () => {
  const text = "Call notes\n\nWe will support 12 languages at launch, said the customer.\n\nNext steps";
  const plan = planAnchors([{ id: "sv-signed", text }], [{ doc, quote: "support 12 languages at launch" }]);
  const html = renderToStaticMarkup(createElement(PlainText, { text, marks: plan.marks["sv-signed"] }));
  assert.match(html, /<p class="fr-plain-para">We will <mark id="ap0-1">support 12 languages at launch<\/mark>, said the customer\.<\/p>/);
  assert.equal(renderToStaticMarkup(createElement(PlainText, { text })), '<p class="fr-plain-para">Call notes</p><p class="fr-plain-para">We will support 12 languages at launch, said the customer.</p><p class="fr-plain-para">Next steps</p>');
  assert.deepEqual(plainParagraphs(text).map((p) => text.slice(p.at, p.at + p.text.length) === p.text), [true, true, true]);
});

const view = (over = {}) => ({
  key: "k", title: "Support in 12 languages", status: "closed", told: [], toldFallback: "", reopened: false, whyReopened: "", closed: [], openGaps: [], notes: [], found: [], notOffered: null,
  contract: { text: "", quote: null, now: null }, signed: null, related: null, scope: null, ...over,
});

test("RecordDetail: a citation shows its link in print when the quote is found; a quote that is not found shows with no link; without the full text there is no link", () => {
  const q = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
  const v = view({ signed: { quote: q, doc, ref: "", date: "2026-10-20", label: "Signed contract" }, told: [{ quote: "Support in 14 languages", label: "Proposal", date: "2026-10-05", doc }] });
  const plan = planAnchors([{ id: "sv-signed", text: SIGNED }], citationsOf(v));
  const html = renderToStaticMarkup(createElement(RecordDetail, { v, documents: [doc], anchorOf: plan }));
  assert.match(html, /<a class="fr-cite" href="#ap0-1" data-cite="contract" data-cite-status="linked">In the appendix/);
  assert.match(html, /data-cite="told" data-cite-status="not-found" hidden/); // the told quote is not in the document: no link
  assert.equal((html.match(/<a class="fr-cite"/g) || []).length, 1);
  const plain = renderToStaticMarkup(createElement(RecordDetail, { v, documents: [doc] }));
  assert.equal(plain.includes("fr-cite"), false);
  assert.equal(plain.includes("data-cite"), false);
});

test("the print stylesheet: Inter, thin card borders, the rules as real borders, notes as bordered cards, status outlines and icons that survive no background graphics", () => {
  assert.match(printCss, /\.dp\.fr \{ font-family: "Inter"/);
  assert.match(printCss, /print-color-adjust: exact/);
  assert.match(printCss, /\.fr \.dp-card \{ border: 1px solid var\(--line\)/);
  assert.match(printCss, /\.fr \.dp-brief-card, \.fr \.dp-promises \{ border-left: 4px solid var\(--accent\)/);
  assert.match(printCss, /\.fr \.dp-promises\.is-attention \{ border-left-color: var\(--amber-dot\)/);
  assert.match(printCss, /\.fr \.dp-note \{ border: 1px solid var\(--line\); break-inside: avoid/);
  assert.match(printCss, /\.fr \.fr-bar \{ border: 1px solid/);
  assert.match(printCss, /\.fr \.fr-verdict \{ border: 1px solid/);
  for (const c of ["amber", "green", "note"]) assert.match(printCss, new RegExp(`\\.fr \\.dp-chip-${c} \\{ border-color:`)); // every status has an outline of its own colour
  assert.match(printCss, /\.fr \.dp-chip \.dp-dot \{[^}]*border: 2px solid/); // the dot is a ring when fills are not printed
  assert.match(printCss, /\.fr \.dp-chip \.dp-dot-green \{ border-color/);
  assert.match(printCss, /\.fr \.fr-appendix-text mark \{[^}]*outline: 1px solid[^}]*text-decoration: underline/); // the mark shows without background graphics
  assert.match(printCss, /\.fr \.fr-cite \{ display: inline;/);
  assert.match(css, /\n\.fr-cite \{ display: none; \}/); // the link is print only
  assert.match(printCss, /\.fr \.dp-prow \{ break-inside: avoid; \}/); // each commitment stays whole
  assert.match(printCss, /\.fr-print-h \{[^}]*break-after: avoid/); // headings stay with their content
  assert.equal(/\.fr-print-h \{[^}]*margin: 16px 20px/.test(printCss), false); // the headings line up with the card edges
});

test("one set of page margins, a page number in the footer margin box, no running header on page 1, and the header text from the record in the top margin box", () => {
  assert.equal((printCss.match(/@page \{ margin:/g) || []).length, 1);
  assert.match(printCss, /@page \{ margin: 16mm 10mm 15mm;[^}]*@bottom-center \{ content: "Page " counter\(page\) " \/ " counter\(pages\)/);
  assert.match(printCss, /@page :first \{ @top-center \{ content: none; \} \}/);
  const jsx = read("FrozenRecord.jsx");
  assert.match(jsx, /@page \{ @top-center \{ content: \$\{JSON\.stringify\(`\$\{s\.deal\} \\u00B7 Handover record`\)\}; \} \} @page :first \{ @top-center \{ content: none; \} \}/);
  assert.equal(/continued/i.test(jsx.slice(jsx.indexOf("<style>"), jsx.indexOf("</style>"))), false);
  assert.equal(/position:\s*fixed/.test(printCss), false); // the header and footer sit in the page margin, not over the content
});

test("display only: the appendix entries, the snapshot and the screen styles are untouched", () => {
  const d = [{ source_version_id: "sv-1", name: "N", version: 1, date: "2026-10-20", sha256: "ab" }];
  assert.deepEqual(Object.keys(appendixEntries(d, { "sv-1": "t" }, [{ source_version_id: "sv-1", format: "Markdown" }])[0]), ["key", "name", "version", "date", "sha256", "text", "format"]);
  const screen = css.replace(/@media print \{[\s\S]*?\n\}\n/g, "");
  assert.equal(/\.fr \.dp-card \{ border: 1px solid/.test(screen), false); // the new card borders exist only in the print block
  assert.match(css, /\.dp-card \{ background: var\(--card\); border: 0; border-radius: 14px;/);
});
