// Demo polish (11 Nov): closed-gap names, one source rule, deal-list tabs, the guided sample path, row progress, stable order, and the
// banner after "All deals". Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { alsoIn, changeResult, changeView, closedTitle, gapProgress, orderPromises, toldQuotesWithDocs, whatChanged } from "../src/dealpage.js";
import { FILTERS, counts, visibleDeals } from "../src/deals.js";
import { sampleSteps } from "../src/demo.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/polish-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { ChangePanel, CommitRow } from ${abs("DealPage.jsx")};\nexport * from ${abs("DemoUI.jsx")};\nexport * from ${abs("demo.js")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);
const iss = (id, finding, state, extra = {}) => ({ id, finding, state, ...extra });

// ---- 1. a closed gap is named by what is now true
test("closed gaps are named by what is now true: the full before/after list", () => {
  const list = [
    ["No approval recorded", "Approval found"],
    ["Missing from contract", "Contract wording found"],
    ["Contract says something different", "Contract wording now matches the promise"],
    ["Needs evidence", "Evidence found"],
    ["A condition was dropped", "Condition restored"],
    ["Not offered", "Promise changed"],
  ];
  for (const [finding, title] of list) {
    assert.equal(closedTitle(finding), title, finding);
    assert.ok(!/^(No|Not|Missing|Needs)\b/i.test(title) && !/differs|dropped/.test(title), title); // never the original problem
  }
  assert.equal(closedTitle("Some other finding"), "Some other finding: closed"); // an unlisted label still never claims a gap as the result
  // the card's headline and its rows use the same words
  assert.equal(changeResult({ closed: [{ finding: "No approval recorded" }] }), "Approval found");
});

test("the card's closed row reads 'Approval found · closed by documents', with no problem-named title and no second chip", () => {
  const change = { closed: [{ promise: "P", finding: "No approval recorded", why: "A named approval is recorded.", by: "" }], opened: [], reopened: [], confirmed: [], stillOpen: [] };
  const html = renderToStaticMarkup(createElement(m.ChangePanel, { change: { ...change, openPromises: 0, doc: "Internal approvals note, new version (v2, 18 Oct)", acted: "P", modelCalls: 0 }, titleOf: (n) => n, onClose() {} }));
  assert.ok(html.includes("<strong>Approval found</strong>") && html.includes("· closed by documents"));
  assert.ok(!html.includes("No approval found") && !html.includes("dp-chip-green"));
});

// ---- 2. one source rule for the row and the drawer
test("the drawer names the earliest customer-facing source, then 'also in' every other document with the same sentence", () => {
  const Q = "A dedicated launch specialist will work with Noma Journeys for the first 30 days.";
  const statements = [{ quote: Q, doc_type_label: "Proposal", date: "2026-10-05", source_name: "Proposal",
    found_in: [{ doc_type_label: "RFP response", date: "2026-09-28" }, { doc_type_label: "Proposal", date: "2026-10-05" }] }];
  const docs = [{ name: "RFP response", doc_type_label: "RFP response", date: "2026-09-28", source_key: "NJ-03" }, { name: "Proposal", doc_type_label: "Proposal", date: "2026-10-05", source_key: "NJ-04" }];
  const [t] = toldQuotesWithDocs(statements, docs);
  assert.deepEqual([t.label, t.date, t.doc.source_key], ["RFP response", "2026-09-28", "NJ-03"]);
  assert.equal(alsoIn(t.also), "also in Proposal, 5 Oct");
  // the row's rule is the server's first_found: the same document
  assert.equal(t.label, "RFP response");
  // two statements with one sentence merge; a sentence found nowhere falls back to its own source; blocks go earliest first
  const merged = toldQuotesWithDocs([...statements, { ...statements[0] }, { quote: "Other.", doc_type_label: "Call transcript", date: "2026-09-14", found_in: [] }], docs);
  assert.deepEqual(merged.map((x) => [x.quote === Q, x.label]), [[false, "Call transcript"], [true, "RFP response"]]);
  assert.equal(alsoIn([]), "");
});

test("the drawer shows 'Source: … · also in …' from the one function; the row line is unchanged", () => {
  assert.match(read("Drawer.jsx"), /\{alsoIn\(also\) && <span className="dr-also"> · \{alsoIn\(also\)\}<\/span>\}/);
  assert.match(read("Drawer.jsx"), /<Source label=\{t\.label\} date=\{t\.date\} doc=\{t\.doc\} also=\{t\.also\}/);
});

// ---- 3. deal-list tabs
const deal = (name, o) => ({ deal: name.toLowerCase(), name, owner: null, stage_label: "Contracting", open_gaps: 0, in_handover: true, handover_complete: false, last_updated: null, ...o });
test("tabs: the first is every deal; needing attention and complete count what their labels say, at any stage", () => {
  assert.equal(FILTERS[0].label, "All deals");
  const deals = [deal("A", { open_gaps: 3 }), deal("B", { open_gaps: 0 }), deal("C", { open_gaps: 2, in_handover: false, stage_label: "Proposal" }),
    deal("D", { open_gaps: 4, handover_complete: true }), deal("E", { open_gaps: 0, handover_complete: true })];
  assert.deepEqual(counts(deals), { all: 5, open: 2, complete: 2, earlier: 1 });
  assert.deepEqual(visibleDeals(deals, { filter: "open" }).map((d) => d.name).sort(), ["A", "C"]); // C is early-stage but has gaps; D is complete
  assert.deepEqual(visibleDeals(deals, { filter: "complete" }).map((d) => d.name).sort(), ["D", "E"]);
  assert.equal(visibleDeals(deals).length, 5);
  const two = [deal("Alder", { open_gaps: 3 }), deal("Noma", { open_gaps: 3 })]; // two deals in Contracting: no tab says "In handover"
  assert.ok(!FILTERS.some((f) => f.label === "In handover"));
  assert.equal(counts(two).all, 2);
});

test("public mode shows only the table on the deal list: no new deal, tabs, search or sort", () => {
  const src = read("Deals.jsx");
  assert.match(src, /\{!demo\.public && <NewDeal onCreated=\{onCreated\} \/>\}/);
  assert.match(src, /\{!demo\.public && <section className="dl-bar-row">/);
});

// ---- 9. the guided sample path
const SAMPLES = [
  { file: "a.md", version_of: "NJ-05", title: "One", summary: "s1" },
  { file: "b.md", version_of: "NJ-07", title: "Two", summary: "s2" },
  { file: "c.md", doc_type: "signed_contract", doc_date: "2026-10-20", title: "Three", summary: "s3" },
];
const doc = (key, version, type = "proposal") => ({ source_key: key, version, doc_type: type, name: key });
const states = (docs) => sampleSteps(SAMPLES, docs).map((x) => x.state);
test("the next sample is derived from what is already in the deal; later ones wait", () => {
  assert.deepEqual(states([doc("NJ-05", 1), doc("NJ-07", 1)]), ["next", "later", "later"]);
  assert.deepEqual(sampleSteps(SAMPLES, [doc("NJ-05", 1), doc("NJ-07", 1)]).map((x) => x.after), [0, 1, 2]); // "After step 1" on the second, "After step 2" on the third
  assert.deepEqual(states([doc("NJ-05", 2), doc("NJ-07", 1)]), ["done", "next", "later"]);
  assert.deepEqual(states([doc("NJ-05", 2), doc("NJ-07", 2)]), ["done", "done", "next"]);
  assert.deepEqual(states([doc("NJ-05", 2), doc("NJ-07", 2), doc("S", 1, "signed_contract")]), ["done", "done", "done"]);
  assert.deepEqual(states([]), ["next", "later", "later"]); // a reset puts the path back at step 1
});

const within = (el) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: { public: true, banner: "b", note_max: 500 } }, el));
test("only the next sample has an active 'Add and check'; the later ones are disabled with 'After step N'", () => {
  const html = within(createElement(m.SamplePicker, { deal: "noma_journeys", documents: [doc("NJ-05", 2), doc("NJ-07", 1)], labels: { signed_contract: "Signed contract" }, onDone() {}, onClose() {}, initialSamples: SAMPLES }));
  assert.equal((html.match(/>Add and check</g) || []).length, 1);
  assert.equal((html.match(/disabled="">After step 2</g) || []).length, 1);
  assert.equal((html.match(/class="demo-sample-done">Added</g) || []).length, 1);
  assert.ok(!html.includes("All samples added"));
  assert.match(html, /<li class="is-done">/); assert.match(html, /<li class="is-next">/); assert.match(html, /<li class="is-later">/);
});

test("after the last sample the list says what to do next, naming the phone row (Noma) or the hosting row (Alder)", () => {
  const done = [doc("NJ-05", 2), doc("NJ-07", 2), doc("S", 1, "signed_contract")];
  const noma = within(createElement(m.SamplePicker, { deal: "noma_journeys", documents: done, labels: {}, onDone() {}, onClose() {}, initialSamples: SAMPLES }));
  assert.ok(noma.includes("All samples added. Next: record a note on the phone row, then complete the handover."));
  assert.ok(!noma.includes(">Add and check<"));
  const alder = within(createElement(m.SamplePicker, { deal: "alder_bank", documents: done, labels: {}, onDone() {}, onClose() {}, initialSamples: SAMPLES }));
  assert.ok(alder.includes("All samples added. Next: record a note on the hosting row, then complete the handover."));
});

// ---- 10. row progress
test("a row shows '1 of 2 gaps closed' only when some gaps are closed and others are not", () => {
  assert.equal(gapProgress([iss(1, "x", "Resolved"), iss(2, "y", "Needs action")]), "1 of 2 gaps closed");
  assert.equal(gapProgress([iss(1, "x", "Resolved"), iss(2, "y", "Resolved"), iss(3, "z", "Needs action")]), "2 of 3 gaps closed");
  assert.equal(gapProgress([iss(1, "x", "Needs action"), iss(2, "y", "Needs action")]), "");
  assert.equal(gapProgress([iss(1, "x", "Resolved"), iss(2, "y", "Resolved")]), ""); // all closed: the status says it
  assert.equal(gapProgress([]), "");
  const c = { name: "Specialist", statements: [], issues: [iss(1, "No approval recorded", "Resolved"), iss(2, "Missing from contract", "Needs action")] };
  const html = renderToStaticMarkup(createElement(m.CommitRow, { c, status: "open", active: false, onOpen() {} }));
  assert.match(html, /<span class="dp-prow-progress">1 of 2 gaps closed<\/span><span class="dp-chip dp-chip-amber"[^>]*>.*Needs attention/s);
  const none = renderToStaticMarkup(createElement(m.CommitRow, { c: { ...c, issues: [iss(2, "Missing from contract", "Needs action")] }, status: "open", active: false, onOpen() {} }));
  assert.ok(!none.includes("dp-prow-progress"));
});

// ---- 11. stable order (revised 11 Nov, later: by stored id, the order the commitments were first recorded)
test("rows are ordered by their stored id; status, dates and titles never move a row", () => {
  const row = (id, name, status, extra = {}) => ({ status, c: { id, name, first_found: { date: "2026-09-28" }, statements: [], ...extra } });
  const rows = [row(30, "Alpha", "open"), row(10, "Zebra", "closed"), row(20, "Middle", "noted", { first_found: null, display_name: "Aardvark" })];
  const ids = (rs) => rs.map((r) => r.c.id);
  assert.deepEqual(ids(orderPromises(rows)), [10, 20, 30]);
  assert.deepEqual(ids(orderPromises([...rows].reverse())), [10, 20, 30]); // input order does not matter: the same for every visitor
  const flipped = rows.map((r) => ({ ...r, status: r.status === "open" ? "closed" : "open", c: { ...r.c, first_found: { date: "2027-01-01" }, name: "renamed", display_name: "Q" } }));
  assert.deepEqual(ids(orderPromises(flipped)), [10, 20, 30]); // a check flips status, dates and wording; the order does not change
  assert.match(read("DealPage.jsx"), /const promiseRows = orderPromises\(\[/);
  const src = read("dealpage.js");
  assert.ok(!/localStorage|useRef\(/.test(src.slice(src.indexOf("export const orderPromises"), src.indexOf("export const orderPromises") + 200)), "no remembered order");
  assert.ok(!src.includes("firstPromisedDate"), "the movable first-promised date is not a sort key any more");
});

// ---- banner after landing -> Open sample deal -> "All deals"
test("the demo bar is above every screen, and a new screen starts at the top (landing, Open sample deal, All deals back)", () => {
  const app = read("App.jsx");
  assert.match(app, /<DemoBar \/><AppBody \/>/); // one bar above landing, list and deal
  assert.match(app, /useEffect\(\(\) => \{ window\.scrollTo\(0, 0\); \}, \[current, landing, classic\]\);/); // the deal page's scroll offset no longer carries to the list
  assert.match(app, /fetchDemoConfig\(\)\.then\(\(r\) => alive && setDemo\(r\), \(\) => \{ if \(alive && left > 0\) setTimeout/); // a failed config answer is asked again
  assert.match(read("Landing.jsx"), /onOpen\(/); // "Open sample deal" and the back link both stay inside the one provider
  const back = app.match(/const back = \(\) => \{[^}]*\}/)[0];
  assert.ok(back.includes("setCurrent(null)")); // "All deals" goes to the list, which the effect then scrolls to the top
});

test("the deal list's table scrolls inside its card: the scroller is positioned, so the hidden header text cannot widen the page", () => {
  assert.match(read("Deals.css"), /\.dl-scroll \{ overflow-x: auto; position: relative; \}/);
  assert.match(read("Deals.css"), /\.dl-sr \{ position: absolute;/);
});

test("at 390px the row's gap progress stacks above the status chip, so the title keeps its width", () => {
  assert.match(read("DealPage.css"), /@media \(max-width: 639px\) \{\s*\.dp-prow-state \{ flex-direction: column; align-items: flex-end; gap: 4px; \}\s*\.dp-prow-progress \{ white-space: normal; text-align: right; \}/);
});
