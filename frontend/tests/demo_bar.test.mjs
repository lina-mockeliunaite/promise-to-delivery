// The demo bar and its guide (11 Nov, public mode): step logic and routing (from the guide card) and the bar that now shows them.
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
fs.writeFileSync(entry, `export * from ${abs("DemoUI.jsx")};\nexport * from ${abs("demo.js")};\nexport { default as ResetDemo } from ${abs("ResetDemo.jsx")};\n`);
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


// ---- the bar
const ON = { public: true, banner: "Public demo · fictional data", note: "Shared with other visitors. If a deal has already been worked through, click Reset demo.", note_max: 500 };
const bar = (guide, { demo = ON, samples = null, open = false } = {}) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: demo },
  createElement(m.GuideStateContext.Provider, { value: guide }, createElement(m.DemoBar, { initialSamples: samples, initialOpen: open }))));
const guideFor = (deal, samplesIn, noted, extra = {}) => { const s = state(deal, samplesIn, noted); return { deal, documents: s.documents, commitments: s.commitments, handoverComplete: false, onDo() {}, ...extra }; };
const stepText = (html) => ((html.match(/<span class="demo-bar-step" role="status">([^<]*)<\/span>/) || [])[1] || "").replace(/&#x27;/g, "'");

test("on a deal page the bar reads: status | Step N of 5 + Do step N | All steps and Reset demo", () => {
  const html = bar(guideFor("noma_journeys", 0), { samples: SAMPLES.noma_journeys });
  assert.ok(html.includes('<strong class="demo-bar-status">Public demo · fictional data</strong>'));
  assert.equal(stepText(html), "Step 1 of 5: Launch specialist: add the approval");
  assert.match(html, /<button type="button" class="demo-bar-do">Do step 1<\/button>/);
  assert.match(html, /<button type="button" class="demo-bar-link" aria-expanded="false" aria-haspopup="true">All steps ▾<\/button>/);
  assert.match(html, /<button type="button" class="demo-bar-link">Reset demo<\/button>/);
  assert.ok(!html.includes("Try it in 5 steps")); // no card
});

test("the bar's step follows the deal through every stage of both deals", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) {
    const L = LABELS[deal];
    const at = (n, noted) => stepText(bar(guideFor(deal, n, noted), { samples: SAMPLES[deal] }));
    assert.equal(at(0), `Step 1 of 5: ${L[0]}`);
    assert.equal(at(1), `Step 2 of 5: ${L[1]}`);
    assert.equal(at(2), `Step 3 of 5: ${L[2]}`);
    assert.equal(at(3), `Step 4 of 5: ${L[3]}`);
    assert.equal(at(3, true), `Step 5 of 5: ${L[4]}`);
    assert.match(bar(guideFor(deal, 2), { samples: SAMPLES[deal] }), />Do step 3</);
  }
});

test("with all five done the bar says 'Done · Reset demo to try again' and has no Do button", () => {
  const html = bar(guideFor("noma_journeys", 3, true, { handoverComplete: true }), { samples: [] });
  assert.equal(stepText(html), "Done · Reset demo to try again");
  assert.equal(m.BAR_DONE, "Done · Reset demo to try again");
  assert.ok(!html.includes("Do step") && html.includes("All steps ▾") && html.includes(">Reset demo<"));
});

test("on every other page the bar is the status and Reset demo only", () => {
  const html = bar(null);
  assert.ok(html.includes("Public demo · fictional data") && html.includes(">Reset demo<"));
  assert.ok(!html.includes("All steps") && !html.includes("Do step") && !html.includes("demo-bar-step"));
  // a deal without a guide (not one of the two) is the same
  const other = bar({ deal: "harbour_bank", documents: [], commitments: [], handoverComplete: false, onDo() {} }, { samples: [] });
  assert.ok(!other.includes("All steps") && !other.includes("demo-bar-step"));
});

test("'All steps' opens a dropdown with the five steps (done, current, later) and the shared-demo line", () => {
  const html = bar(guideFor("noma_journeys", 1), { samples: SAMPLES.noma_journeys, open: true });
  assert.match(html, /aria-expanded="true"/);
  const menu = html.slice(html.indexOf('class="demo-bar-menu"'));
  assert.equal((menu.match(/<li class="is-done">/g) || []).length, 1);
  assert.equal((menu.match(/<li class="is-current">/g) || []).length, 1);
  assert.equal((menu.match(/<li class="is-later">/g) || []).length, 3);
  for (const label of LABELS.noma_journeys) assert.ok(menu.replace(/&#x27;/g, "'").includes(label), label);
  assert.ok(menu.includes('<span class="demo-guide-n" aria-hidden="true">✓</span>') && menu.includes(">2</span>"));
  assert.ok(menu.includes('<p class="demo-bar-note">Shared with other visitors. If a deal has already been worked through, click Reset demo.</p>'));
  assert.ok(!bar(guideFor("noma_journeys", 1), { samples: SAMPLES.noma_journeys }).includes("demo-bar-menu")); // closed by default
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
  assert.match(confirm, />Reset<\/button>/); assert.match(confirm, />Cancel<\/button>/);
  const footer = renderToStaticMarkup(createElement(m.ResetDemo)); // the footer variant is as it was
  assert.match(footer, /class="dl-about dl-reset-link"/);
});

test("the card is gone from the deal page: the commitments card follows the 'What changed' card directly, in public and local mode alike", () => {
  const page = read("DealPage.jsx");
  assert.ok(!page.includes("GuideCard") && !page.includes("Try it in 5 steps") && !page.includes("demo-guide"));
  assert.match(page, /\{change && <ChangePanel [^\n]*\/>\}\s*<section className=\{`dp-card dp-promises/);
  assert.ok(!read("FrozenRecord.jsx").includes("GuideCard"));
  assert.ok(!read("DemoUI.jsx").includes("export function GuideCard") && !read("DemoUI.jsx").includes("DemoBanner"));
});

test("the deal page publishes where the visitor is; 'Do step N' in the bar comes back to the page's own doStep", () => {
  const page = read("DealPage.jsx");
  assert.match(page, /publishGuide\(\{ deal, documents: docs\.documents, commitments: reg\.commitments, handoverComplete: !!reg\.handover\.complete, onDo: \(step\) => doStepRef\.current\(step\) \}\);/);
  assert.match(page, /return \(\) => publishGuide\(null\);/);
  assert.match(page, /if \(!demo\.public \|\| !GUIDES\[deal\] \|\| !reg \|\| !docs\) return undefined;/);
  // the routing, highlight and scroll from the card are the same code
  assert.match(page, /if \(a\.drawer\) setDrawer\(a\.drawer\);/);
  assert.match(page, /setFlash\(\{ row: a\.row, handover: a\.handover \}\)/);
  assert.match(read("DemoUI.jsx"), /guide\.onDo\(now\.step\)/);
  const app = read("App.jsx");
  assert.match(app, /<DemoBar \/><AppBody \/>/);
  assert.match(app, /<GuidePublishContext\.Provider value=\{setGuide\}>\s*<GuideStateContext\.Provider value=\{guide\}>/);
});

test("the bar is sticky above every page, one line on desktop, two below 640px, and the page's own sticky parts sit under it", () => {
  const css = read("App.css");
  assert.match(css, /\.demo-bar \{ position: sticky; top: 0; z-index: 70;/);
  assert.match(css, /\.demo-bar-row \{ display: flex; align-items: center; gap: 12px; padding: 6px 16px; \}/); // no wrap: one line
  assert.match(css, /\.demo-bar-step \{ flex: 0 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; \}/);
  const narrow = css.slice(css.indexOf("@media (max-width: 639px) {\n  .demo-bar-row"));
  assert.match(narrow, /\.demo-bar-row \{ flex-wrap: wrap;/); // line 1 status and step, line 2 the buttons
  assert.match(narrow, /\.demo-bar-step \{ flex: 1 1 150px; white-space: normal; overflow: visible; \}/); // wraps, never clips
  assert.match(css, /@media print \{ \.demo-bar \{ display: none; \} \}/);
  const dp = read("DealPage.css");
  assert.match(dp, /\.dp-topbar \{ position: sticky; top: var\(--demo-bar-h, 0px\);/);
  assert.match(dp, /\.dr \{ position: fixed; top: calc\(var\(--demo-bar-h, 0px\) \+ var\(--topbar-h\)\);/);
  assert.match(dp, /\.dr-backdrop \{ position: fixed; inset: calc\(var\(--demo-bar-h, 0px\) \+ var\(--topbar-h\)\) 0 0 0;/);
  assert.match(read("Identity.jsx"), /--demo-bar-h/);
  assert.match(read("DemoUI.jsx"), /root\.style\.setProperty\("--demo-bar-h"/);
  assert.match(read("DemoUI.jsx"), /root\.style\.removeProperty\("--demo-bar-h"\)/); // not public: the variable is unset and the page is as it was
});

test("the deal list's footer 'Reset demo' link is for local mode only (the bar has it in public mode)", () => {
  assert.match(read("Deals.jsx"), /\{!demo\.public && <ResetDemo \/>\}<\/footer>/);
});
