// Public demo mode (10 Nov). Run with: node --test frontend/tests/
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
const dir = fileURLToPath(new URL("../node_modules/.cache/public-demo-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
// One bundle that shares a single copy of demo.js (and so of the context) between the components and the test.
const entry = path.join(dir, "entry.jsx");
fs.writeFileSync(entry, `export * from ${JSON.stringify(fileURLToPath(new URL("DemoUI.jsx", SRC)))};\nexport * from ${JSON.stringify(fileURLToPath(new URL("demo.js", SRC)))};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);

const BANNER = "Public demo · fictional data";
const ON = { public: true, banner: BANNER, note_max: 500 };
const within = (demo, el) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: demo }, el));

const SAMPLES = [
  { file: "NJ-05_v2_named_exception.md", version_of: "NJ-05", title: "Approval for the launch specialist", summary: "Omar Haddad, Head of Customer Success, approves a named exception: first 30 days, no extra charge (18 October 2026)." },
  { file: "NJ-09_signed_contract.md", doc_type: "signed_contract", doc_date: "2026-10-20", title: "Signed contract", summary: "Signed 20 October 2026 by Liam Hart (Aivuna) and Celeste Wong (Noma Journeys)." },
];

test("the demo bar's status is the server's text, shown only when public mode is on (the bar itself is tested in demo_bar.test.mjs)", () => {
  const html = within(ON, createElement(m.DemoBar));
  assert.ok(html.includes(`<strong class="demo-bar-status">${BANNER}</strong>`));
  assert.equal(within(m.DEMO_OFF, createElement(m.DemoBar)), "");
  assert.equal(renderToStaticMarkup(createElement(m.DemoBar)), ""); // no provider at all: off
  assert.ok(!read("DemoUI.jsx").includes("Public demo ·"), "the wording comes from the server, in one place");
});

test("the demo bar sits above every screen: the app wraps its one body in it", () => {
  assert.match(read("App.jsx"), /<DemoBar \/><AppBody \/>/);
  assert.match(read("App.css"), /@media print \{ \.demo-bar \{ display: none; \} \}/);
});

test("the name note says other visitors can see the name and notes, only in public mode, at every place a name is set", () => {
  assert.equal(m.NAME_NOTE, "Your name and notes are visible to other visitors of this public demo.");
  assert.ok(within(ON, createElement(m.DemoNameNote)).includes(m.NAME_NOTE));
  assert.equal(within(m.DEMO_OFF, createElement(m.DemoNameNote)), "");
  const page = read("DealPage.jsx");
  assert.equal((page.match(/<DemoNameNote \/>/g) || []).length, 3); // the name field, the note form's field, the name prompt
  assert.match(page, /\(visible to other visitors\)/); // the top bar
});

test("note boxes take 500 characters in public mode and their own limit otherwise", () => {
  assert.equal(m.noteLimit(ON), 500);
  assert.equal(m.noteLimit(m.DEMO_OFF), 2000);
  assert.equal(m.noteLimit(ON, 300), 300);
  const page = read("DealPage.jsx");
  assert.equal((page.match(/maxLength=\{noteLimit\(demo\)\}/g) || []).length, 2);
  assert.ok(!/maxLength=\{2000\}/.test(page));
});

test("a sample is sent as the same body an upload would send: a new version carries its source, a new document its type and date", () => {
  assert.deepEqual(m.sampleBody(SAMPLES[0], "T"), { source_key: "NJ-05", filename: SAMPLES[0].file, text: "T" });
  assert.deepEqual(m.sampleBody(SAMPLES[1], "T"), { name: SAMPLES[1].file, filename: SAMPLES[1].file, doc_type: "signed_contract", doc_date: "2026-10-20", text: "T" });
  const docs = [{ source_key: "NJ-05", name: "Internal approvals note", version: 1 }];
  assert.deepEqual(m.sampleDone(SAMPLES[0], docs, {}), { name: "Internal approvals note", source_key: "NJ-05", date: "" });
  assert.deepEqual(m.sampleDone(SAMPLES[1], docs, { signed_contract: "Signed contract" }), { name: "Signed contract", source_key: null, date: "2026-10-20" });
});

test("choosing a sample fetches its text and calls the existing add-and-check once; the form is told what the upload form is told", async () => {
  const calls = [];
  const client = {
    fetchSample: async (deal, file) => { calls.push(["sample", deal, file]); return { text: "BODY" }; },
    addDocumentAndCheck: async (deal, body) => { calls.push(["add", deal, body]); return { review: { model_calls: 0 } }; },
  };
  const out = await m.addSample(client, "noma_journeys", SAMPLES[0], [{ source_key: "NJ-05", name: "Internal approvals note" }], {});
  assert.deepEqual(calls, [["sample", "noma_journeys", SAMPLES[0].file], ["add", "noma_journeys", { source_key: "NJ-05", filename: SAMPLES[0].file, text: "BODY" }]]);
  assert.deepEqual(out, { review: { model_calls: 0 }, added: { name: "Internal approvals note", source_key: "NJ-05", date: "" } });
  await assert.rejects(m.addSample({ ...client, addDocumentAndCheck: async () => { throw new Error("nope"); } }, "noma_journeys", SAMPLES[0], [], {}), /nope/);
});

test("the sample list is numbered in story order: title, one line of who did what, and the filing in plain words with no dates; there is no upload", () => {
  const docs = [{ source_key: "NJ-05", name: "Internal approvals note", version: 1 }];
  const labels = { signed_contract: "Signed contract" };
  const html = within(ON, createElement(m.SamplePicker, { deal: "noma_journeys", documents: docs, labels, onDone() {}, onClose() {}, initialSamples: SAMPLES }));
  assert.ok(html.includes("Use a sample file"));
  assert.match(html, /<ol class="demo-sample-list">/);
  assert.match(html, /demo-sample-n"[^>]*>2<\/span><div><strong>Approval for the launch specialist<\/strong>/);
  assert.match(html, /demo-sample-n"[^>]*>3<\/span><div><strong>Signed contract<\/strong>/);
  for (const s of SAMPLES) assert.ok(html.includes(s.title) && html.includes(s.summary));
  assert.ok(!html.includes("NJ-05_v2_named_exception.md")); // the file name is not the heading any more
  assert.ok(html.includes("Filed as a new version of: Internal approvals note<"));
  assert.ok(html.includes("Filed as a new document, type Signed contract<"));
  assert.ok(!html.includes("currently v") && !/Filed as[^<]*\d{4}/.test(html)); // no version number, no date in a filing line
  assert.equal((html.match(/Add and check/g) || []).length, 1); // only the next step is active; the other waits ("After step 2"); the samples are guide steps 2-4
  assert.ok(!html.includes('type="file"') && !html.includes("browse files"));
  const none = within(ON, createElement(m.SamplePicker, { deal: "x", documents: [], labels: {}, onDone() {}, onClose() {}, initialSamples: [] }));
  assert.ok(none.includes("This deal has no sample files in the public demo."));
});

test("filingLine: a version names the document it replaces, a new document its type; neither carries a date or a version number", () => {
  assert.equal(m.filingLine(SAMPLES[0], [{ source_key: "NJ-05", name: "Internal approvals note", version: 3 }], {}), "Filed as a new version of: Internal approvals note");
  assert.equal(m.filingLine(SAMPLES[1], [], { signed_contract: "Signed contract" }), "Filed as a new document, type Signed contract");
});

test("the add-document form shows the sample list only in public mode; off, the upload form is as it was", () => {
  const page = read("DealPage.jsx");
  assert.match(page, /if \(demo\.public\) return <SamplePicker deal=\{deal\} documents=\{documents\} labels=\{labels\} hint=\{hint\} onDone=\{onDone\} onClose=\{onClose\} \/>;/);
  assert.ok(page.includes("Drop file here or <u>browse files</u>")); // the upload form is still there
  assert.match(read("api.js"), /export const fetchDemoConfig = \(\) => getJson\("\/api\/demo\/config"\)/);
});
