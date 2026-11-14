// Sample preview (11 Nov, public mode). Run with: node --test frontend/tests/
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
const dir = fileURLToPath(new URL("../node_modules/.cache/sample-preview-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
fs.writeFileSync(entry, `export * from ${JSON.stringify(fileURLToPath(new URL("DemoUI.jsx", SRC)))};\nexport * from ${JSON.stringify(fileURLToPath(new URL("demo.js", SRC)))};\nexport { AddPanel } from ${JSON.stringify(fileURLToPath(new URL("DealPage.jsx", SRC)))};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);
const scenario = (f) => fs.readFileSync(fileURLToPath(new URL(`../../data/scenarios/${f}`, import.meta.url)), "utf8");

const SAMPLES = [
  { file: "NJ-05_v2_named_exception.md", version_of: "NJ-05", title: "Approval for the launch specialist", summary: "s1" },
  { file: "NJ-07_v2_languages_aligned.md", version_of: "NJ-07", title: "Revised draft contract", summary: "s2" },
  { file: "NJ-09_signed_contract.md", doc_type: "signed_contract", doc_date: "2026-10-20", title: "Signed contract", summary: "s3" },
];
const doc = (key, version, type = "proposal") => ({ source_key: key, version, doc_type: type, name: key === "NJ-05" ? "Internal approvals note" : key });
const ON = { public: true, banner: "b", note_max: 500 };
const picker = (extra = {}) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.SamplePicker,
  { deal: "noma_journeys", documents: [doc("NJ-05", 1), doc("NJ-07", 1)], labels: { signed_contract: "Signed contract" }, onDone() {}, onClose() {}, initialSamples: SAMPLES, ...extra })));
const text05 = scenario("NJ-05_v2_named_exception.md");
const key05 = [14]; // the named-exception line, as the sample route reports it

test("every sample in the list has a quiet Preview link beside its button, waiting ones included; a waiting one says what to add first (Round 9)", () => {
  const html = picker();
  assert.equal((html.match(/class="dp-link-btn dp-brand demo-sample-preview"[^>]*>Preview<\/button>/g) || []).length, 3);
  const items = html.split("<li ").slice(1);
  assert.ok(items[0].includes(">Add and check<") && items[0].includes(">Preview<"));        // the current step
  assert.ok(items[1].includes(">Not yet<") && /first: step 2</.test(items[1]) && items[1].includes(">Preview<"));        // a waiting sample can be previewed
  assert.ok(items[2].includes(">Not yet<") && /first: step 3</.test(items[2]) && items[2].includes(">Preview<"));
  assert.equal((html.match(/>Add and check</g) || []).length, 1); // adding is still only for the current step
  const done = picker({ documents: [doc("NJ-05", 2), doc("NJ-07", 1)] });
  assert.ok(done.split("<li ")[1].includes(">Added<") && done.split("<li ")[1].includes(">Preview<")); // an added sample can still be read
});

const decode = (t) => t.replace(/&amp;/g, "&").replace(/&#x27;/g, "'").replace(/&quot;/g, '"');

test("the preview is a formatted document, not raw text: headings, paragraphs and a table, read-only", () => {
  const html = picker({ initialPreview: { sample: SAMPLES[0], text: text05, key: key05 } });
  assert.ok(html.includes("2. Approval for the launch specialist") && html.includes("Filed as a new version of: Internal approvals note"));
  assert.match(html, /<h3 class="demo-doc-h">INTERNAL — Pricing and services note: Noma Journeys<\/h3>/); // "# …" is a heading, not text
  assert.match(html, /<h4 class="demo-doc-h">Capability and approval check<\/h4>/);
  assert.match(html, /<table class="demo-doc-table"><thead><tr><th>Capability<\/th><th>Region and scope<\/th><th>Catalogue position<\/th><th>Deal approval<\/th><\/tr><\/thead>/);
  assert.equal((html.match(/<tr/g) || []).length, 1 + 5 + 1 + 2); // the header and 5 rows, then the priced-services table's header and 2 rows
  assert.ok(html.includes("<strong>Provider commercial boundary:</strong>")); // inline bold
  for (const raw of ["# INTERNAL", "## Capability", "|---|", "**Provider", "| CAP-002"]) assert.ok(!decode(html).includes(raw), `raw markdown left in: ${raw}`);
  assert.ok(!html.includes("<textarea") && !html.includes("<input") && !html.includes("contenteditable"));
  assert.ok(!html.includes("demo-sample-list")); // it replaces the list in the same panel
});

test("the key row of the pricing note is a highlighted table row, and only that row", () => {
  const html = picker({ initialPreview: { sample: SAMPLES[0], text: text05, key: key05 } });
  const rows = [...html.matchAll(/<tr( class="is-key")?>(.*?)<\/tr>/g)];
  const marked = rows.filter((r) => r[1]);
  assert.equal(marked.length, 1);
  assert.ok(decode(marked[0][2]).includes("Named exception approved by Omar Haddad"));
  assert.ok(html.includes("<mark>Highlighted</mark>: the lines the check will use."));
  assert.match(read("App.css"), /\.demo-doc-table tr\.is-key td:first-child \{ box-shadow: inset 3px 0 0 var\(--accent, #4f46e5\); \}/); // the brand indigo bar
});

test("the signed contract's signature block is highlighted whole (heading and paragraphs), and the clause above it is not", () => {
  const signed = scenario("NJ-09_signed_contract.md");
  const lines = signed.split("\n");
  const from = lines.findIndex((l) => l.trim() === "## Signatures");
  const key = lines.map((_, i) => i).filter((i) => i >= from && lines[i].trim() && !lines[i].startsWith("All companies"));
  const html = decode(picker({ initialPreview: { sample: SAMPLES[2], text: signed, key } }));
  assert.match(html, /<h4 class="demo-doc-h is-key">Signatures<\/h4>/);
  const marked = [...html.matchAll(/<span class="demo-doc-ln is-key">(.*?)<\/span>/g)].map((x) => x[1].replace(/<[^>]+>/g, "")).join(" ");
  for (const n of ["Name: Liam Hart", "Name: Celeste Wong", "Date: 20 October 2026", "Title: Account Executive"]) assert.ok(marked.includes(n), n);
  assert.ok(!/<span class="demo-doc-ln is-key">[^<]*Clause 4/.test(html));
  const none = picker({ initialPreview: { sample: SAMPLES[1], text: scenario("NJ-07_v2_languages_aligned.md"), key: [] } });
  assert.ok(!none.includes("Highlighted") && !none.includes("is-key")); // no key lines, no legend, no highlight
});

test("on open the first highlighted line is centred: the scroll position is worked out from the container and the line", () => {
  // a 400px-high preview scrolled to 0, the key row 900px down and 30px tall: it ends up in the middle
  assert.equal(m.centeredScrollTop({ scrollTop: 0, containerTop: 100, containerHeight: 400, elTop: 1000, elHeight: 30 }), 715);
  assert.equal(m.centeredScrollTop({ scrollTop: 0, containerTop: 100, containerHeight: 400, elTop: 120, elHeight: 30 }), 0); // near the top: no negative scroll
  assert.equal(m.centeredScrollTop({ scrollTop: 300, containerTop: 100, containerHeight: 400, elTop: 500, elHeight: 30 }), 300 + 400 - 185); // relative to where it is scrolled now
  const ui = read("DemoUI.jsx");
  assert.match(ui, /const el = c\?\.querySelector\("\.is-key"\);/); // the first highlighted element, row or line
  assert.match(ui, /c\.scrollTop = centeredScrollTop\(\{ scrollTop: c\.scrollTop, containerTop: cr\.top, containerHeight: c\.clientHeight, elTop: er\.top, elHeight: er\.height \}\);/);
  assert.match(ui, /\}, \[preview\]\);/); // when a preview opens
});

test("'Add and check' on the current step is in a sticky footer, always visible; a waiting sample has no footer", () => {
  const html = picker({ initialPreview: { sample: SAMPLES[0], text: text05, key: key05 } });
  assert.match(html, /<div class="demo-preview-foot"><button type="button" class="dp-btn dp-btn-dark">Add and check<\/button><\/div><\/div>$/); // the last thing in the panel
  assert.ok(html.indexOf("demo-preview-text") < html.indexOf("demo-preview-foot"));
  const css = read("App.css");
  assert.match(css, /\.demo-preview-foot \{ position: sticky; bottom: 0;/); // pinned at the bottom of the drawer's scrolling body, like its buttons
  assert.match(css, /\.demo-preview-text \{[^}]*max-height: calc\(100dvh - var\(--demo-bar-h, 0px\) - var\(--topbar-h, 56px\) - 300px\); overflow: auto;/); // the document scrolls, the footer does not
  const waiting = picker({ initialPreview: { sample: SAMPLES[2], text: scenario("NJ-09_signed_contract.md"), key: [] } });
  assert.ok(!waiting.includes("demo-preview-foot") && !waiting.includes(">Add and check<") && waiting.includes("4. Signed contract"));
});

test("only one back link in the preview, and it says 'Back to samples'; the list view keeps 'Back to commitment'", () => {
  const c = { name: "Dedicated launch specialist", issues: [{ id: 1, finding: "No approval recorded", state: "Needs action" }] };
  const panel = (extra) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.AddPanel,
    { deal: "noma_journeys", c, titleId: "t", documents: [doc("NJ-05", 1), doc("NJ-07", 1)], docTypes: [], onDone() {}, onBack() {}, onClose() {}, ...extra })));
  const inPreview = panel({ initialPreview: { sample: SAMPLES[0], text: text05, key: key05 } });
  assert.equal((inPreview.match(/Back to/g) || []).length, 1);
  assert.ok(inPreview.includes("Back to samples") && !inPreview.includes("Back to commitment"));
  assert.match(inPreview, /<button type="button" class="dr-back"[^>]*>[^]*?Back to samples/);
  assert.ok(!inPreview.includes("demo-preview-back")); // no second link inside the panel
  const list = panel({});
  assert.ok(list.includes("Back to commitment") && !list.includes("Back to samples"));
  // from + Add there is no commitment: the only back link is the one in the preview
  const noRow = renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.AddPanel,
    { deal: "noma_journeys", c: null, titleId: "t", documents: [], docTypes: [], onDone() {}, onBack() {}, onClose() {}, initialPreview: { sample: SAMPLES[2], text: scenario("NJ-09_signed_contract.md"), key: [] } })));
  assert.equal((noRow.match(/Back to/g) || []).length, 1);
  const page = read("DealPage.jsx");
  assert.match(page, /backLabel=\{preview \? "Back to samples" : c \? "Back to commitment" : null\} onBack=\{preview \? \(\) => setPreview\(null\) : onBack\}/);
});

test("the text comes from the existing sample route and nothing is stored; the highlight is a style, never an edit", () => {
  const ui = read("DemoUI.jsx");
  const body = ui.slice(ui.indexOf("const show = async"), ui.indexOf("const steps = sampleSteps"));
  assert.match(body, /api\.fetchSample\(deal, s\.file\)/);
  assert.match(body, /setPreview\(\{ sample: s, text: r\.text, key: r\.key_lines \?\? \[\] \}\)/);
  assert.ok(!/addDocument|saveNote|localStorage|sessionStorage|postJson|fetch\(/.test(body));
  assert.ok(!/dangerouslySetInnerHTML|innerHTML/.test(ui + read("preview.js"))); // only text nodes carry the document
  assert.match(read("api.js"), /export const fetchSample = \(deal, file\) => getJson\(`\/api\/demo\/sample\?deal=/);
  assert.ok(!/f59e0b|fde68a/.test(read("App.css").slice(read("App.css").indexOf("Sample preview (11 Nov"))));
});

test("Add and check from the preview is the same call as from the list", () => {
  const ui = read("DemoUI.jsx");
  assert.match(ui, /onClick=\{\(\) => add\(preview\.sample\)\}>\{busy === preview\.sample\.file \? "Checking…" : "Add and check"\}/);
  assert.match(ui, /const \{ review, added \} = await addSample\(api, deal, s, documents, labels\);/); // one add path
});
