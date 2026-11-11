// The demo bar and its guide (11 Nov, public mode): the six steps (1 Get the picture, a tour in the bar; 2-4 the documents; 5 the note; 6 the
// handover), their routing and hints, and the bar that shows them.
// Run with: node --test frontend/tests/
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
const dir = fileURLToPath(new URL("../node_modules/.cache/demo-bar-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CommitmentView } from ${abs("Drawer.jsx")};\nexport { commitmentView } from ${abs("dealpage.js")};\nexport * from ${abs("DemoUI.jsx")};\nexport * from ${abs("demo.js")};\nexport { default as ResetDemo } from ${abs("ResetDemo.jsx")};\n`);
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
const NOTE_ROW = { noma_journeys: /phone/i, alder_bank: /hosting/i };
// A deal at a stage of the walk: how many samples are in (0-3), whether the note is recorded on its row.
const state = (deal, samplesIn, noted = false) => {
  const keys = DOC_KEYS[deal];
  const documents = keys.map((k, i) => ({ source_key: k, version: i < samplesIn ? 2 : 1, doc_type: "x" }));
  if (samplesIn >= 3) documents.push({ source_key: "S", version: 1, doc_type: "signed_contract" });
  const commitments = ROWS[deal].map((c) => ({ ...c, noted_count: noted && NOTE_ROW[deal].test(`${c.display_name} ${c.name}`) ? 1 : 0 }));
  return { documents, commitments };
};
const states = (deal, samplesIn, noted, toured = true) => { const s = state(deal, samplesIn, noted); return m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments, false, toured).map((x) => x.state); };

const LABELS = {
  noma_journeys: ["Get the picture", "Launch specialist: add the approval", "Support in 12 languages: add the revised contract", "Add the signed contract",
    "Phone calls: record the customer's agreement as a note", "Complete the handover"],
  alder_bank: ["Get the picture", "Coaching-scam detection: add the BioCatch connector approval", "Coaching-scam detection: add the revised SOW", "Add the signed contract",
    "Hosting on Microsoft Azure: record the customer's agreement as a note", "Complete the handover"],
};
const HINTS = {
  noma_journeys: [null, "Promised in the RFP and again in the proposal, never approved, not in the contract. Add the approval and see what closes.",
    "Told 12 languages; the draft contract says four. Add the revised contract.", "The signed contract decides what Delivery inherits. Add it and see which fixes survive.",
    "Aivuna doesn't offer voice, so no document can fix this. Noma agreed on a call: record it as a note.", null],
  alder_bank: [null, "Coaching detection depends on the BioCatch connector, which is in beta and needs a named approval; the SOW doesn't mention it. Add the approval and see what closes.",
    "The approval closed one gap, but the SOW still doesn't mention coaching detection. Add the revised SOW.", "The signed contract decides what Delivery inherits. Add it and see which fixes survive.",
    "Elva doesn't offer Azure hosting, so no document can fix this. The customer agreed AWS Sydney on a call: record it as a note.", null],
};
const decode = (t) => String(t).replace(/&#x27;/g, "'");

test("the six steps and their wording are as agreed; the samples are steps 2-4 and the sample panel numbers them that way", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) {
    const s = state(deal, 0);
    const steps = m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments);
    assert.deepEqual(steps.map((x) => x.label), LABELS[deal]);
    assert.deepEqual(steps.map((x) => x.n), [1, 2, 3, 4, 5, 6]);
    assert.deepEqual(steps.map((x) => x.kind), ["tour", "sample", "sample", "sample", "note", "handover"]);
    assert.deepEqual(m.sampleSteps(SAMPLES[deal], s.documents).map((x) => x.n), [2, 3, 4]); // the sample panel's numbers are the guide's
    assert.deepEqual(m.sampleSteps(SAMPLES[deal], s.documents).map((x) => x.after), [1, 2, 3]); // "After step N" names the step before it
    assert.deepEqual(steps.slice(1, 4).map((x) => x.sample), [0, 1, 2]);
  }
});

test("step states at every stage of both deals: done, current (the first not done), later; step 1 is the browser's, the rest the deal's", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) {
    assert.deepEqual(states(deal, 0, false, false), ["current", "later", "later", "later", "later", "later"], `${deal} fresh`);
    assert.deepEqual(states(deal, 0), ["done", "current", "later", "later", "later", "later"], `${deal} after the tour`);
    assert.deepEqual(states(deal, 1), ["done", "done", "current", "later", "later", "later"], `${deal} after sample 1`);
    assert.deepEqual(states(deal, 2), ["done", "done", "done", "current", "later", "later"], `${deal} after sample 2`);
    assert.deepEqual(states(deal, 3), ["done", "done", "done", "done", "current", "later"], `${deal} after the signed contract`);
    assert.deepEqual(states(deal, 3, true), ["done", "done", "done", "done", "done", "current"], `${deal} after the note`);
    const s = state(deal, 3, true);
    assert.deepEqual(m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments, true, false).map((x) => x.state), Array(6).fill("done"), `${deal} handover complete`);
    assert.deepEqual(states(deal, 1, false, false), ["current", "done", "later", "later", "later", "later"], `${deal} deal worked ahead of the tour: a done step is ticked wherever it sits`);
  }
});

test("each 'Do step N' goes to the right place: the drawer on the evidence with its hint and the button to click; the signed contract the sample panel", () => {
  const act = (deal, i) => { const s = state(deal, 0); return m.guideAction(m.guideSteps(deal, SAMPLES[deal], s.documents, s.commitments)[i], s.commitments); };
  assert.deepEqual(act("noma_journeys", 0), { tour: true, drawer: null, row: null, handover: false });
  assert.deepEqual(act("noma_journeys", 1), { drawer: { type: "commitment", id: 17, guide: { hint: HINTS.noma_journeys[1], highlight: "add" } }, row: 17, handover: false });
  assert.deepEqual(act("noma_journeys", 2), { drawer: { type: "commitment", id: 16, guide: { hint: HINTS.noma_journeys[2], highlight: "add" } }, row: 16, handover: false });
  assert.deepEqual(act("noma_journeys", 3), { drawer: { type: "add", fromId: null, hint: HINTS.noma_journeys[3] }, row: null, handover: false });
  assert.deepEqual(act("noma_journeys", 4), { drawer: { type: "commitment", id: 15, guide: { hint: HINTS.noma_journeys[4], highlight: "note" } }, row: 15, handover: false });
  assert.deepEqual(act("noma_journeys", 5), { drawer: null, row: null, handover: true });
  assert.deepEqual(act("alder_bank", 0), { tour: true, drawer: null, row: null, handover: false });
  assert.deepEqual(act("alder_bank", 1), { drawer: { type: "commitment", id: 2, guide: { hint: HINTS.alder_bank[1], highlight: "add" } }, row: 2, handover: false });
  assert.deepEqual(act("alder_bank", 2), { drawer: { type: "commitment", id: 2, guide: { hint: HINTS.alder_bank[2], highlight: "add" } }, row: 2, handover: false });
  assert.deepEqual(act("alder_bank", 3), { drawer: { type: "add", fromId: null, hint: HINTS.alder_bank[3] }, row: null, handover: false });
  assert.deepEqual(act("alder_bank", 4), { drawer: { type: "commitment", id: 3, guide: { hint: HINTS.alder_bank[4], highlight: "note" } }, row: 3, handover: false });
  assert.deepEqual(act("alder_bank", 5), { drawer: null, row: null, handover: true });
});

// ---- the tour
const FACTS = { goLive: "2027-02-01", stage: "contracting", stageLabel: "Contracting", open: 3 };
test("the tour captions are exactly as agreed for Noma, and built from the deal's own date, stage and count", () => {
  assert.deepEqual(m.tourCaptions("noma_journeys", FACTS), [
    "What Aivuna is delivering, and the 1 February go-live Noma has promised its leadership.",
    "Every document so far, by stage. We're at Contracting: the last point to fix gaps cheaply.",
    "What the customer was told that the contract or catalogue doesn't back up. Three need attention.",
  ]);
  assert.deepEqual(m.tourCaptions("alder_bank", FACTS), [
    "What Elva is delivering, and the 1 February go-live Alder Bank has promised its board.",
    "Every document so far, by stage. We're at Contracting: the last point to fix gaps cheaply.",
    "What the customer was told that the contract or catalogue doesn't back up. Three need attention.",
  ]);
  // another date, stage and count change the captions; nothing is hard-coded
  const later = m.tourCaptions("noma_journeys", { goLive: "2027-03-15", stage: "signed", stageLabel: "Signed", open: 1 });
  assert.ok(later[0].includes("15 March go-live") && later[1] === "Every document so far, by stage. We're at Signed." && later[2].endsWith("One needs attention."));
  assert.ok(m.tourCaptions("alder_bank", { ...FACTS, open: 0 })[2].endsWith("Nothing needs attention."));
  assert.equal(m.dayMonth("2027-02-01"), "1 February"); assert.equal(m.dayMonth(null), "");
  assert.deepEqual(m.TOUR_KEYS, ["brief", "journey", "commitments"]);
});

const ON = { public: true, banner: "Public demo · fictional data", note: "Shared with other visitors. If a deal has already been worked through, click Reset demo.", note_max: 500 };
const bar = (guide, { demo = ON, samples = null, open = false, tour = null, toured = null } = {}) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: demo },
  createElement(m.GuideStateContext.Provider, { value: guide }, createElement(m.DemoBar, { initialSamples: samples, initialOpen: open, initialTour: tour, toured }))));
const guideFor = (deal, samplesIn, noted, extra = {}) => { const s = state(deal, samplesIn, noted); return { deal, documents: s.documents, commitments: s.commitments, handoverComplete: false, facts: FACTS, onDo() {}, onTour() {}, ...extra }; };
const stepText = (html) => decode((html.match(/<span class="demo-bar-step" role="status">([^<]*)<\/span>/) || [])[1] || "");

test("step 1: the bar reads 'Step 1 of 6: Get the picture' with a 'Show me' button", () => {
  const html = bar(guideFor("noma_journeys", 0), { samples: SAMPLES.noma_journeys, toured: false });
  assert.ok(html.includes('<strong class="demo-bar-status">Public demo · fictional data</strong>'));
  assert.equal(stepText(html), "Step 1 of 6: Get the picture");
  assert.match(html, /<button type="button" class="demo-bar-do">Show me<\/button>/);
  assert.ok(!html.includes("Do step 1") && !html.includes("Skip tour"));
  assert.match(html, />All steps ▾</); assert.match(html, /<button type="button" class="demo-bar-link">Reset demo<\/button>/);
});

test("while the tour runs the bar's text is the caption, with 'N of 3', Next (Finish on the last part) and Skip tour", () => {
  for (const [part, label] of [[0, "Next"], [1, "Next"], [2, "Finish"]]) {
    const html = bar(guideFor("noma_journeys", 0), { samples: SAMPLES.noma_journeys, tour: part, toured: false });
    assert.equal(stepText(html), m.tourCaptions("noma_journeys", FACTS)[part]);
    assert.ok(html.includes(`<span class="demo-bar-tourn">${part + 1} of 3</span>`));
    assert.ok(html.includes(`<button type="button" class="demo-bar-do">${label}</button>`) && html.includes(">Skip tour<"));
    assert.ok(!html.includes("Do step") && !html.includes("Show me"));
  }
});

test("after the tour (or skipping it) step 1 is done and step 2 is current; the done state is the browser's, so a reset (which clears it) brings the tour back", () => {
  const html = bar(guideFor("noma_journeys", 0), { samples: SAMPLES.noma_journeys, toured: true });
  assert.equal(stepText(html), "Step 2 of 6: Launch specialist: add the approval");
  assert.match(html, />Do step 2</);
  // sessionStorage, not the server
  const store = () => { const mm = new Map(); return { getItem: (k) => mm.get(k) ?? null, setItem: (k, v) => mm.set(k, v), removeItem: (k) => mm.delete(k), mm }; };
  const s = store();
  assert.equal(m.tourDone("noma_journeys", s), false);
  m.markTourDone("noma_journeys", s); m.markTourDone("alder_bank", s);
  assert.equal(m.tourDone("noma_journeys", s), true); assert.equal(m.tourDone("alder_bank", s), true);
  assert.deepEqual([...s.mm.keys()].sort(), ["ptd.tour.alder_bank", "ptd.tour.noma_journeys"]);
  m.clearTourDone(s);
  assert.equal(s.mm.size, 0);
  const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }, removeItem() { throw new Error("blocked"); } };
  assert.equal(m.tourDone("noma_journeys", broken), false);
  assert.doesNotThrow(() => { m.markTourDone("noma_journeys", broken); m.clearTourDone(broken); });
  assert.equal(m.tourDone("noma_journeys", undefined), false); // no storage at all
  assert.ok(!/fetch|api\./.test(read("demo.js").slice(read("demo.js").indexOf("export function tourDone"), read("demo.js").indexOf("export const TOUR_FACTS"))), "never the server");
});

test("a reset clears the tour state before the page reloads", async () => {
  const { runReset } = await import("../src/deals.js");
  const log = [];
  await runReset(async () => ({}), { setHash: (h) => log.push(["hash", h]), beforeReload: () => log.push(["clear"]), reload: () => log.push(["reload"]) });
  assert.deepEqual(log, [["hash", "#welcome"], ["clear"], ["reload"]]);
  assert.match(read("ResetDemo.jsx"), /beforeReload: \(\) => clearTourDone\(\)/);
});

test("the bar follows the deal through every stage of both deals", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) {
    const L = LABELS[deal];
    const at = (n, noted) => stepText(bar(guideFor(deal, n, noted), { samples: SAMPLES[deal], toured: true }));
    assert.equal(at(0), `Step 2 of 6: ${L[1]}`);
    assert.equal(at(1), `Step 3 of 6: ${L[2]}`);
    assert.equal(at(2), `Step 4 of 6: ${L[3]}`);
    assert.equal(at(3), `Step 5 of 6: ${L[4]}`);
    assert.equal(at(3, true), `Step 6 of 6: ${L[5]}`);
    assert.match(bar(guideFor(deal, 2), { samples: SAMPLES[deal], toured: true }), />Do step 4</);
  }
});

test("with everything done the bar says 'Done · Reset demo to try again' and has no Do button", () => {
  const html = bar(guideFor("noma_journeys", 3, true, { handoverComplete: true }), { samples: [], toured: false });
  assert.equal(stepText(html), "Done · Reset demo to try again");
  assert.ok(!html.includes("Do step") && !html.includes("Show me") && html.includes("All steps ▾") && html.includes(">Reset demo<"));
});

test("on every other page the bar is the status and Reset demo only", () => {
  const html = bar(null);
  assert.ok(html.includes("Public demo · fictional data") && html.includes(">Reset demo<"));
  assert.ok(!html.includes("All steps") && !html.includes("Do step") && !html.includes("demo-bar-step"));
  const other = bar({ deal: "harbour_bank", documents: [], commitments: [], handoverComplete: false, onDo() {} }, { samples: [] });
  assert.ok(!other.includes("All steps") && !other.includes("demo-bar-step"));
});

test("'All steps' opens a dropdown with the six steps (done, current, later) and the shared-demo line", () => {
  const html = bar(guideFor("noma_journeys", 1), { samples: SAMPLES.noma_journeys, open: true, toured: true });
  const menu = html.slice(html.indexOf('class="demo-bar-menu"'));
  assert.equal((menu.match(/<li class="is-done">/g) || []).length, 2);
  assert.equal((menu.match(/<li class="is-current">/g) || []).length, 1);
  assert.equal((menu.match(/<li class="is-later">/g) || []).length, 3);
  for (const label of LABELS.noma_journeys) assert.ok(decode(menu).includes(label), label);
  assert.ok(menu.includes('<p class="demo-bar-note">Shared with other visitors. If a deal has already been worked through, click Reset demo.</p>'));
  assert.ok(!bar(guideFor("noma_journeys", 1), { samples: SAMPLES.noma_journeys }).includes("demo-bar-menu"));
});

test("local mode has no bar at all", () => {
  assert.equal(bar(guideFor("noma_journeys", 0), { demo: m.DEMO_OFF, samples: SAMPLES.noma_journeys }), "");
  assert.equal(renderToStaticMarkup(createElement(m.DemoBar)), "");
});

test("'Reset demo' in the bar opens the existing confirm, as a panel under the bar", () => {
  const idle = renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.ResetDemo, { variant: "bar" })));
  assert.equal(idle, '<button type="button" class="demo-bar-link">Reset demo</button>');
  const confirm = renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.ResetDemo, { variant: "bar", initial: { step: "confirming", message: "" } })));
  assert.ok(confirm.includes("demo-bar-reset") && confirm.includes("Restore both sample deals to the start? This resets the demo for everyone."));
  assert.match(renderToStaticMarkup(createElement(m.ResetDemo)), /class="dl-about dl-reset-link"/);
});

// ---- the guided drawer and the hints
const open = { id: 1, finding: "No approval recorded", state: "Needs action", reason: "", evidence: {}, seen: [] };
const view = () => m.commitmentView({ name: "Dedicated launch specialist", contract: "", statements: [], issues: [open] }, "open", []);
const drawer = (guide) => renderToStaticMarkup(createElement(m.CommitmentView, { v: view(), titleId: "t", me: "", guide, onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} }));

test("a guided drawer shows one hint line above the buttons and highlights the button to click", () => {
  const add = drawer({ hint: HINTS.noma_journeys[1], highlight: "add" });
  assert.ok(decode(add).includes(`<p class="dr-guide-hint" role="note">${HINTS.noma_journeys[1]}</p>`));
  assert.ok(add.indexOf("dr-guide-hint") < add.indexOf('class="dr-actions"')); // above the buttons
  assert.match(add, /<button type="button" class="dp-btn dp-btn-dark is-guided">Add updated document<\/button>/);
  assert.match(add, /<button type="button" class="dp-btn">Record a note<\/button>/);
  const note = drawer({ hint: HINTS.noma_journeys[4], highlight: "note" });
  assert.match(note, /<button type="button" class="dp-btn is-guided">Record a note<\/button>/);
  assert.match(note, /<button type="button" class="dp-btn dp-btn-dark">Add updated document<\/button>/);
  const plain = drawer(null); // an ordinary drawer is as it was
  assert.ok(!plain.includes("dr-guide-hint") && !plain.includes("is-guided"));
});

test("the signed-contract hint shows at the top of the sample panel; the panel's numbers are the guide's", () => {
  const html = renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: ON }, createElement(m.SamplePicker, {
    deal: "noma_journeys", documents: state("noma_journeys", 2).documents, labels: {}, onDone() {}, onClose() {}, hint: HINTS.noma_journeys[3],
    initialSamples: SAMPLES.noma_journeys.map((s, i) => ({ ...s, file: `f${i}.md`, title: `T${i}`, summary: `S${i}` })) })));
  assert.ok(html.includes(`<p class="demo-hint" role="note">${HINTS.noma_journeys[3]}</p>`));
  assert.match(html, /demo-sample-n"[^>]*>4<\/span>/);
  assert.ok(html.includes(">Add and check<") && !html.includes("After step"));
});

test("the page wires the tour and the guided drawer; the card is gone and local mode's markup is untouched", () => {
  const page = read("DealPage.jsx");
  assert.match(page, /data-tour=\{tourKey \|\| undefined\}/); // no attribute at all unless a tour is running
  assert.match(page, /onTour: \(key\) => tourRef\.current\(key\)/);
  assert.match(page, /facts: \{ goLive: reg\.brief\?\.go_live, stage: reg\.stage\.current, stageLabel: reg\.stage\.current_label, open: reg\.open_rows\.length \}/);
  assert.match(page, /guide=\{drawer\.guide\}/); assert.match(page, /hint=\{drawer\.hint\}/);
  assert.ok(!page.includes("GuideCard") && !page.includes("Try it in"));
  assert.match(page, /\{message && <div className=\{`dp-message is-\$\{message\.kind\}`\} role="status">\{message\.text\}<\/div>\}\s*<section className=\{`dp-card dp-promises/); // nothing sits between the brief and the commitments card
  const ui = read("DemoUI.jsx");
  assert.match(ui, /guide\?\.onTour\?\.\(TOUR_KEYS\[part\]\)/);
  assert.match(ui, /if \(finished\) \{ markTourDone\(deal\);/);
  const css = read("DealPage.css");
  assert.match(css, /\.dp-grid\[data-tour="brief"\] \.dp-brief-card, \.dp-grid\[data-tour="commitments"\] #dp-commitments, \.dp-grid\[data-tour="journey"\] \.dp-aside > \* \{ outline: 3px solid var\(--accent\);/); // the brand indigo (the primary button's colour), not amber
  assert.match(css, /\.dr-actions \.dp-btn\.is-guided \{/);
});

test("the bar is sticky above every page, one line on desktop, two below 640px, and the page's own sticky parts sit under it", () => {
  const css = read("App.css");
  assert.match(css, /\.demo-bar \{ position: sticky; top: 0; z-index: 70;/);
  assert.match(css, /\.demo-bar-row \{ display: flex; align-items: center; gap: 12px; padding: 6px 16px; \}/);
  assert.match(css, /\.demo-bar-step \{ flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; \}/);
  const narrow = css.slice(css.indexOf("@media (max-width: 639px) {\n  .demo-bar-row"));
  assert.match(narrow, /\.demo-bar-row \{ flex-wrap: wrap;/);
  assert.match(narrow, /\.demo-bar-step \{ flex: 1 1 150px; white-space: normal; overflow: visible; \}/);
  assert.match(css, /@media print \{ \.demo-bar \{ display: none; \} \}/);
  const dp = read("DealPage.css");
  assert.match(dp, /\.dp-topbar \{ position: sticky; top: var\(--demo-bar-h, 0px\);/);
  assert.match(dp, /\.dr \{ position: fixed; top: calc\(var\(--demo-bar-h, 0px\) \+ var\(--topbar-h\)\);/);
  assert.match(read("Identity.jsx"), /--demo-bar-h/);
});

test("the deal list's footer 'Reset demo' link is for local mode only (the bar has it in public mode)", () => {
  assert.match(read("Deals.jsx"), /\{!demo\.public && <ResetDemo \/>\}<\/footer>/);
});
