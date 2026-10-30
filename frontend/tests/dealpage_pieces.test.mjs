// Pieces of the live deal page, rendered to static markup (31 Oct): the header meta line, the sidebar's stage rows and the footer.
// DealPage.jsx is bundled with Vite (as in commitrow.test.mjs); the chevron's rotation is CSS, so it is pinned in the stylesheet source.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");

const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("DealPage.jsx", SRC)), formats: ["es"], fileName: "dealpage" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/dealpage-pieces-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "dealpage.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { DealMeta, DealFooter, DocumentList } = await import(file);

const reg = { brief: { go_live: "2027-02-01" }, freshness: { finished_at: "2026-10-29T10:00:00Z" } };
const STAGES = [
  { key: "discovery", label: "Discovery", state: "done", gaps_started: 0 },
  { key: "shortlisted", label: "Shortlisted", state: "done", gaps_started: 0 },
  { key: "contracting", label: "Contracting", state: "current", gaps_started: 0 },
  { key: "signed", label: "Signed", state: "todo", gaps_started: 0 },
];
const doc = (key, stage) => ({ source_key: key, name: key, doc_type: "proposal", stage, date: "2026-10-01", version: 1, included: true });
const list = () => renderToStaticMarkup(createElement(DocumentList, {
  deal: "d", stages: STAGES, documents: [doc("A", "discovery"), doc("B", "contracting")], name: "", setName() {}, onChanged() {}, onView() {}, onAdd() {}, onHelp() {} }));
const stageRow = (html, label) => html.split('<li class="dp-tl ').find((x) => x.includes(`>${label}`));

test("header: no Documents count, and Target go-live and Last checked stay", () => {
  const html = renderToStaticMarkup(createElement(DealMeta, { reg }));
  assert.ok(!html.includes("Documents") && !/\(\d+\)/.test(html));
  assert.ok(html.includes("Target go-live") && html.includes("Last checked"));
  assert.ok(!read("DealPage.jsx").includes("<span>Documents</span>")); // the removed row is not rendered anywhere in the page
});

test("sidebar: a Not yet stage has no count; passed and current stages keep theirs, including 0 documents", () => {
  const html = list();
  const todo = stageRow(html, "Signed");
  assert.ok(todo.includes("Not yet") && !todo.includes("document"));
  assert.ok(stageRow(html, "Shortlisted").includes("· 0 documents"));
  assert.ok(stageRow(html, "Discovery").includes("· 1 document"));
  assert.ok(stageRow(html, "Contracting").includes("· 1 document"));
  assert.ok(html.includes("Deal journey · 2 documents")); // the one place the total is shown
});

test("sidebar: the plus is gone; stages with documents have a decorative chevron, empty stages none", () => {
  const html = list();
  assert.ok(!read("DealPage.css").includes('content: "+"'));
  assert.equal((html.match(/class="dp-tl-chev" aria-hidden="true"/g) || []).length, 2); // Discovery and Contracting only
  assert.ok(!stageRow(html, "Shortlisted").includes("dp-tl-chev") && !stageRow(html, "Signed").includes("dp-tl-chev"));
  assert.match(stageRow(html, "Shortlisted"), /disabled=""/);
  assert.match(stageRow(html, "Contracting"), /aria-expanded="true"/); // the current stage starts open, so its chevron points down
  assert.match(stageRow(html, "Discovery"), /aria-expanded="false"/); // a collapsed one points right
  assert.ok(stageRow(html, "Shortlisted").includes('class="dp-tl-gap" aria-hidden="true"') && stageRow(html, "Signed").includes("dp-tl-gap")); // an empty spacer keeps the tags in one column
  assert.match(read("DealPage.css"), /\.dp-tl-toggle \.dp-tl-right \{ margin-left: auto; \}/);
  assert.match(read("DealPage.css"), /\.dp-tl-toggle\[aria-expanded="true"\] \.dp-tl-chev \{ transform: rotate\(90deg\); \}/);
});

test("footer: the scope sentence is gone; the coverage sentence and the fictional line stay; the other pages' footers are untouched", () => {
  const html = renderToStaticMarkup(createElement(DealFooter, {}));
  assert.ok(!html.includes("Lists commitments"));
  assert.ok(html.includes("Checked against the documents listed and the product catalogue. All companies, people and deals are fictional."));
  assert.match(read("FrozenRecord.jsx"), /Lists commitments where the customer's expectation, the contract and what we can sell don't line up\. \{FICTIONAL\}/);
  assert.match(read("Deals.jsx"), /<footer className="dl-pagefoot">\{FICTIONAL\}/);
  assert.match(read("Landing.jsx"), /<footer className="dp-foot">\{FICTIONAL\}<\/footer>/);
});
