// Last polish (11 Nov): confirmed and reopened labels named by what is now true, and "Use sample text" in public mode. Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { changeView, confirmedTitle, reopenedTitle, whatChanged } from "../src/dealpage.js";
import { HANDOVER_SAMPLES, NOTE_SAMPLES, handoverSampleFor, noteSampleFor } from "../src/demo.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/last-polish-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { ChangeDialog } from ${abs("DealPage.jsx")};\nexport * from ${abs("DemoUI.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);

const iss = (id, finding, state, extra = {}) => ({ id, finding, state, ...extra });
const reg = (...rows) => ({ commitments: rows.map(([name, issues]) => ({ name, issues })) });
const LANG = "Support in 12 languages at launch";

// ---- 1
test("confirmations and reopens are named by what is now true: the full before/after list", () => {
  const confirmed = [
    ["No approval recorded", "Approval found"], ["Missing from contract", "Contract wording found"],
    ["Contract says something different", "Contract wording matches"], ["Needs evidence", "Evidence found"],
    ["A condition was dropped", "Condition restored"], ["Not offered", "Promise changed"],
  ];
  const reopened = [
    ["No approval recorded", "Approval not shown for the signed contract"], ["Missing from contract", "Contract wording missing from the signed contract"],
    ["Contract says something different", "Contract wording not in the signed contract"], ["Needs evidence", "Evidence not found in the signed contract"],
    ["A condition was dropped", "Condition missing from the signed contract"], ["Not offered", "Promise unchanged in the signed contract"],
  ];
  for (const [f, t] of confirmed) { assert.equal(confirmedTitle(f), t, f); assert.ok(!/earlier fix|differs|^No |^Not |^Missing/.test(t), t); }
  for (const [f, t] of reopened) { assert.equal(reopenedTitle(f), t, f); assert.ok(!/earlier fix|differs/.test(t), t); }
  assert.ok(!confirmedTitle("Other").includes("earlier fix") && !reopenedTitle("Other").includes("earlier fix"));
});

test("the card's confirmed row reads 'Contract wording matches · confirmed in the signed contract'; a reopened row names what is now true", () => {
  const before = reg([LANG, [iss(1, "Contract says something different", "Resolved")]], ["Phone", [iss(2, "Missing from contract", "Resolved")]]);
  const after = reg([LANG, [iss(1, "Contract says something different", "Resolved", { signed_check: { status: "confirmed" } })]],
    ["Phone", [iss(2, "Missing from contract", "Needs action", { signed_check: { status: "not_found", reason: "Not found in the signed contract." } })]]);
  const change = whatChanged(before, after);
  const html = renderToStaticMarkup(createElement(m.ChangeDialog, { change: { ...change, doc: "Signed contract, 20 Oct", acted: null, modelCalls: 0 }, titleOf: (n) => n, onClose() {} }));
  assert.ok(html.includes('<strong>Contract wording matches</strong><span class="dp-change-closed"> · confirmed in the signed contract</span>'));
  assert.ok(html.includes("<strong>Contract wording missing from the signed contract</strong>") && html.includes("Reopened"));
  assert.ok(!html.includes("earlier fix confirmed</strong>") && !html.includes("earlier fix not found in the signed contract</strong>"));
  assert.ok(!html.includes("Contract differs") && !html.includes("Not in the contract"));
  // the elsewhere line names the reopened gap the same way
  const elsewhere = changeView(change, (n) => n, "somewhere else").elsewhere;
  assert.ok(!elsewhere.includes("contract differs") && !elsewhere.includes("not in the contract"), elsewhere);
});

// ---- 3
const ON = { public: true, banner: "b", note_max: 500 }, OFF = { public: false, banner: null, note_max: null };
test("sample text is exactly what was agreed, within the 500-character note limit", () => {
  assert.equal(NOTE_SAMPLES.noma_journeys.text, "Noma agreed on 19 Oct to launch on chat and email; voice is not offered.");
  assert.equal(NOTE_SAMPLES.alder_bank.text, "Customer agreed AWS Sydney on the 14 Oct call.");
  assert.equal(HANDOVER_SAMPLES.noma_journeys.sales, "Signed. Noma was promised a launch specialist for the first 30 days; it's approved as a named exception at no charge, but it isn't in the contract. Noma expects it: provide it, and get it into writing at kickoff. Noma launches on chat and email; voice isn't offered.");
  assert.equal(HANDOVER_SAMPLES.noma_journeys.delivery, "Accepted. We start on chat and email as contracted and provide the launch specialist for 30 days as approved; putting it in writing goes on the kickoff agenda.");
  assert.equal(HANDOVER_SAMPLES.alder_bank.sales, "The signed statement of work commits to scam-call alerts at launch. Product approved them from 1 May. Confirm the delivery plan with Product and Alder before kickoff.");
  assert.equal(HANDOVER_SAMPLES.alder_bank.delivery, "Accepted. We start on AWS Sydney as contracted; scam-call alerts go on the kickoff agenda.");
  for (const t of [...Object.values(NOTE_SAMPLES).map((x) => x.text), ...Object.values(HANDOVER_SAMPLES).flatMap((x) => Object.values(x))]) assert.ok(t.length <= 500, t);
});

test("the note sample is offered only in public mode, only on the matching commitment of the matching deal, and selects 'addressed by note'", () => {
  const phone = { name: "Assistant will answer guests' phone calls in addition to chat and email" }, hosting = { name: "Hosting on Microsoft Azure", display_name: "Hosting on Azure" };
  const languages = { name: "Support in 12 languages at launch" };
  assert.equal(noteSampleFor(ON, "noma_journeys", phone), NOTE_SAMPLES.noma_journeys);
  assert.equal(noteSampleFor(ON, "noma_journeys", phone).addressed, true);
  assert.equal(noteSampleFor(ON, "alder_bank", { name: "Hosting on Amazon Web Services in Sydney" }), NOTE_SAMPLES.alder_bank);
  assert.equal(noteSampleFor(ON, "alder_bank", hosting), NOTE_SAMPLES.alder_bank);
  assert.equal(noteSampleFor(ON, "noma_journeys", languages), null); // no other row gets one
  assert.equal(noteSampleFor(ON, "noma_journeys", hosting), null);   // not the other deal's row
  assert.equal(noteSampleFor(OFF, "noma_journeys", phone), null);    // never in local mode
  assert.equal(noteSampleFor(undefined, "noma_journeys", phone), null);
});

test("the handover samples are offered per deal and role, in public mode only", () => {
  assert.equal(handoverSampleFor(ON, "noma_journeys", "sales"), HANDOVER_SAMPLES.noma_journeys.sales);
  assert.equal(handoverSampleFor(ON, "alder_bank", "delivery"), HANDOVER_SAMPLES.alder_bank.delivery);
  assert.equal(handoverSampleFor(ON, "noma_journeys", "product"), null);
  assert.equal(handoverSampleFor(ON, "harbour_bank", "sales"), null);
  assert.equal(handoverSampleFor(OFF, "noma_journeys", "sales"), null);
});

test("the link only fills the box: it is a plain button that sets the text; Save stays the visitor's click", () => {
  const html = renderToStaticMarkup(createElement(m.UseSampleText, { onUse() {} }));
  assert.equal(html, '<button type="button" class="dp-link-btn dp-brand demo-sample-text">Use sample text</button>');
  const page = read("DealPage.jsx");
  assert.match(page, /\{sample && <UseSampleText onUse=\{\(\) => \{ setNote\(sample\.text\); if \(sample\.addressed\) setHow\("addressed"\); \}\} \/>\}/); // the note form
  assert.match(page, /\{sample && <UseSampleText onUse=\{\(\) => setText\(sample\)\} \/>\}/); // both handover fields (one component, sales and delivery)
  assert.equal((page.match(/<UseSampleText/g) || []).length, 2);
  // neither handler saves: no api call sits in the onUse bodies, and the forms still submit only on their own Save buttons
  assert.ok(!/onUse=\{[^}]*api\./.test(page));
  assert.match(page, /<NotePanel deal=\{deal\} role="sales"/); assert.match(page, /<NotePanel deal=\{deal\} role="delivery"/);
});
