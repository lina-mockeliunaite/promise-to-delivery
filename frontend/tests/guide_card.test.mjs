// The guide card "Try it in 5 steps" (11 Nov, public mode). Run with: node --test frontend/tests/
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
const dir = fileURLToPath(new URL("../node_modules/.cache/guide-card-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export * from ${abs("DemoUI.jsx")};\nexport * from ${abs("demo.js")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);

const SAMPLES = {
  noma_journeys: [{ version_of: "NJ-05" }, { version_of: "NJ-07" }, { doc_type: "signed_contract" }],
  alder_bank: [{ version_of: "AB-05" }, { version_of: "AB-06" }, { doc_type: "signed_contract" }],
};
const DOC_KEYS = { noma_journeys: ["NJ-05", "NJ-07"], alder_bank: ["AB-05", "AB-06"] };
const ROWS = {
  noma_journeys: [{ id: 15, name: "Assistant will answer guests' phone calls in addition to chat and email", display_name: "AI answers customers' phone calls at launch" },
    { id: 16, name: "Assistant will support guest conversations in 12 languages at launch", display_name: "Support in 12 languages at launch" },
    { id: 17, name: "Dedicated Aivuna launch specialist for the first 30 days after launch at no extra charge", display_name: "Dedicated launch specialist for the first 30 days, at no extra charge" }],
  alder_bank: [{ id: 1, name: "Real-time scoring of 750,000 outbound instant payments per day by end of first year", display_name: "750,000 payments a day by the end of year one" },
    { id: 2, name: "BioCatch-based coaching detection live from 1 February 2027 launch", display_name: "Coaching-scam detection live at launch" },
    { id: 3, name: "Hosting Alder's environment on Microsoft Azure in Australia East", display_name: "Hosting on Microsoft Azure" }],
};
const HOSTING_OR_PHONE = { noma_journeys: /phone/i, alder_bank: /hosting/i };
// A deal at a stage of the walk: how many samples are in (0-3), whether the note is recorded on its row.
const state = (deal, samplesIn, noted = false) => {
  const keys = DOC_KEYS[deal];
  const documents = keys.map((k, i) => ({ source_key: k, version: i < samplesIn ? 2 : 1, doc_type: "x" }));
  if (samplesIn >= 3) documents.push({ source_key: "S", version: 1, doc_type: "signed_contract" });
  const commitments = ROWS[deal].map((c) => ({ ...c, noted_count: noted && HOSTING_OR_PHONE[deal].test(`${c.display_name} ${c.name}`) ? 1 : 0 }));
  return { documents, commitments };
};
const states = (deal, samplesIn, noted) => { const s = state(deal, samplesIn, noted); return m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments).map((x) => x.state); };

const LABELS = {
  noma_journeys: ["Launch specialist: add the approval", "Support in 12 languages: add the revised contract", "Add the signed contract",
    "Phone calls: record the customer's agreement as a note", "Complete the handover"],
  alder_bank: ["Coaching-scam detection: add the BioCatch connector approval", "Coaching-scam detection: add the revised SOW", "Add the signed contract",
    "Hosting on Microsoft Azure: record the customer's agreement as a note", "Complete the handover"],
};

test("the steps and their wording are exactly as agreed, numbered 1 to 5 as the sample panel numbers 1 to 3", () => {
  assert.equal(m.GUIDE_TITLE, "Try it in 5 steps");
  for (const deal of ["noma_journeys", "alder_bank"]) {
    const s = state(deal, 0);
    const steps = m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments);
    assert.deepEqual(steps.map((x) => x.label), LABELS[deal]);
    assert.deepEqual(steps.map((x) => x.n), [1, 2, 3, 4, 5]);
    // steps 1-3 are the samples of the same numbers, so the panel's "After step N" refers to this card
    assert.deepEqual(m.sampleSteps(SAMPLES[deal], s.documents).map((x) => x.n), [1, 2, 3]);
    assert.deepEqual(steps.slice(0, 3).map((x) => x.sample), [0, 1, 2]);
  }
});

test("step states at every stage of both deals: done, current (the first not done), later", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) {
    assert.deepEqual(states(deal, 0), ["current", "later", "later", "later", "later"], `${deal} fresh`);
    assert.deepEqual(states(deal, 1), ["done", "current", "later", "later", "later"], `${deal} after sample 1`);
    assert.deepEqual(states(deal, 2), ["done", "done", "current", "later", "later"], `${deal} after sample 2`);
    assert.deepEqual(states(deal, 3), ["done", "done", "done", "current", "later"], `${deal} after the signed contract`);
    assert.deepEqual(states(deal, 3, true), ["done", "done", "done", "done", "current"], `${deal} after the note`);
    const s = state(deal, 3, true);
    assert.deepEqual(m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments, true).map((x) => x.state), Array(5).fill("done"), `${deal} handover complete`);
    assert.deepEqual(states(deal, 0, true), ["current", "later", "later", "done", "later"], `${deal} note first: a done step is ticked wherever it sits`);
  }
});

test("each 'Do step N' goes to the right place", () => {
  const rowId = (deal, re) => ROWS[deal].find((c) => re.test(`${c.display_name} ${c.name}`)).id;
  const act = (deal, i) => { const s = state(deal, 0); return m.guideAction(m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments)[i], s.commitments); };
  // Noma: steps 1-2 open that commitment's drawer on the sample panel; 3 the sample panel from + Add; 4 the row's note form; 5 the Handover card
  assert.deepEqual(act("noma_journeys", 0), { drawer: { type: "add", fromId: rowId("noma_journeys", /launch specialist/i) }, row: 17, handover: false });
  assert.deepEqual(act("noma_journeys", 1), { drawer: { type: "add", fromId: 16 }, row: 16, handover: false });
  assert.deepEqual(act("noma_journeys", 2), { drawer: { type: "add", fromId: null }, row: null, handover: false });
  assert.deepEqual(act("noma_journeys", 3), { drawer: { type: "note", id: 15 }, row: 15, handover: false });
  assert.deepEqual(act("noma_journeys", 4), { drawer: null, row: null, handover: true });
  // Alder: both coaching steps open the coaching row, the note step the hosting row
  assert.deepEqual(act("alder_bank", 0), { drawer: { type: "add", fromId: 2 }, row: 2, handover: false });
  assert.deepEqual(act("alder_bank", 1), { drawer: { type: "add", fromId: 2 }, row: 2, handover: false });
  assert.deepEqual(act("alder_bank", 2), { drawer: { type: "add", fromId: null }, row: null, handover: false });
  assert.deepEqual(act("alder_bank", 3), { drawer: { type: "note", id: 3 }, row: 3, handover: false });
  assert.deepEqual(act("alder_bank", 4), { drawer: null, row: null, handover: true });
});

const card = (deal, samplesIn, noted, extra = {}) => {
  const s = state(deal, samplesIn, noted);
  return renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: { public: true } },
    createElement(m.GuideCard, { deal, documents: s.documents, commitments: s.commitments, onDo() {}, initialSamples: SAMPLES[deal], ...extra })));
};

test("the card shows ticks for done steps, a highlighted current step with 'Do step N', and plain later steps", () => {
  const html = card("noma_journeys", 1);
  assert.ok(html.includes("<h2>Try it in 5 steps</h2>"));
  assert.match(html, /<li class="is-done"><span class="demo-guide-n" aria-hidden="true">✓<\/span><span class="demo-guide-label">Launch specialist: add the approval/);
  assert.match(html, /<li class="is-current"><span class="demo-guide-n" aria-hidden="true">2<\/span><span class="demo-guide-label">Support in 12 languages: add the revised contract.*?<button type="button" class="dp-btn dp-btn-dark">Do step 2<\/button>/);
  assert.equal((html.match(/class="is-later"/g) || []).length, 3);
  assert.equal((html.match(/Do step/g) || []).length, 1); // only the current step has a button
  assert.ok(!html.includes("Done. Reset demo to try again."));
});

test("the card can be collapsed, and when everything is done it says so", () => {
  const collapsed = card("alder_bank", 0, false, { initialCollapsed: true });
  assert.ok(collapsed.includes("Try it in 5 steps") && collapsed.includes(">Show<") && !collapsed.includes("demo-guide-list"));
  assert.ok(card("alder_bank", 0).includes(">Hide<") && card("alder_bank", 0).includes('aria-expanded="true"'));
  const done = card("noma_journeys", 3, true, { handoverComplete: true });
  assert.ok(done.includes('<p class="demo-guide-done" role="status">Done. Reset demo to try again.</p>') && !done.includes("Do step"));
  assert.equal(m.GUIDE_DONE, "Done. Reset demo to try again.");
});

test("no card for a deal without a guide; the card is wired into the public deal page only, above the commitments card", () => {
  assert.equal(renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: { public: true } },
    createElement(m.GuideCard, { deal: "harbour_bank", documents: [], commitments: [], onDo() {}, initialSamples: [] }))), "");
  const page = read("DealPage.jsx");
  assert.match(page, /\{demo\.public && <GuideCard deal=\{deal\} documents=\{docs\.documents\} commitments=\{reg\.commitments\} onDo=\{doStep\} \/>\}\s*<section className=\{`dp-card dp-promises/);
  assert.ok(page.indexOf("<GuideCard") < page.indexOf('id="dp-commitments"'));
  // "Do step N" opens the drawer, expands Handover, highlights and scrolls
  assert.match(page, /if \(a\.drawer\) setDrawer\(a\.drawer\);/);
  assert.match(page, /if \(a\.handover\) setHandoverManual\(\{ stage: reg\.stage\.current, open: true \}\);/);
  assert.match(page, /setFlash\(\{ row: a\.row, handover: a\.handover \}\)/);
  assert.match(page, /scrollIntoView\(\{ behavior: "smooth", block: "center" \}\)/);
  assert.match(page, /className=\{`dp-card dp-handover \$\{flash\.handover \? "is-flash" : ""\}`\.trim\(\)\} id="dp-handover"/);
  assert.match(page, /flash=\{flash\.row === c\.id\}/);
  // the order is untouched, and the locked record shows only the done state, public mode only
  assert.match(page, /const promiseRows = orderPromises\(\[/);
  assert.match(read("FrozenRecord.jsx"), /\{demo\.public && <div className="fr-noprint"><GuideCard deal=\{deal\} documents=\{\[\]\} commitments=\{\[\]\} handoverComplete \/><\/div>\}/);
  assert.match(read("App.css"), /@media print \{ \.demo-guide \{ display: none; \} \}/);
});
