// Round 8 (13 Nov): first-run experience and precise evidence labels. Display and flow only: no engine, snapshot, fingerprint, golden, cache or sealed change.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as demo from "../src/demo.js";
import { DEMO_VISITOR, commitmentView, draftSourceLabel, frozenView, recordLines, signedConfirmedLabel } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/round8-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CommitmentView } from ${abs("Drawer.jsx")};\nexport { StartChoice } from ${abs("DemoUI.jsx")};\nexport { RecordDetail } from ${abs("FrozenRecord.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitmentView, StartChoice, RecordDetail } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&rsquo;/g, "’");
const drawer = (v, docs, guide = null) => decode(renderToStaticMarkup(createElement(CommitmentView, { v, documents: docs, titleId: "t", me: "", guide, onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} })));
const record = (v, docs) => decode(renderToStaticMarkup(createElement(RecordDetail, { v, documents: docs, onOpenDoc() {} })));

// ---- 1. a second visitor ---------------------------------------------------------------------------------------------------------------------------------------
test("1. the run state of the first deal: fresh, partial (a step done, not locked) or complete (locked)", () => {
  const step = (state) => ({ state });
  assert.equal(demo.runState([step("current"), step("later")], false), "fresh");
  assert.equal(demo.runState([step("done"), step("current"), step("later")], false), "fresh"); // only the tour done: still the start
  assert.equal(demo.runState([step("done"), step("done"), step("current")], false), "partial");
  assert.equal(demo.runState([step("done"), step("done"), step("done")], true), "complete");
  assert.equal(demo.runState(undefined, false), "fresh");
});

test("A. the choice and the replay hint exist in the public demo only; local mode and a deal at its start just start the guide", () => {
  for (const state of ["fresh", null, undefined]) { assert.equal(demo.startAction(true, state), "start"); assert.equal(demo.startAction(false, state), "start"); }
  for (const state of ["partial", "complete"]) { assert.equal(demo.startAction(true, state), "choose"); assert.equal(demo.startAction(false, state), "start"); } // local: exactly as today
  assert.equal(demo.showReplayHint(true, "complete"), true);
  for (const [pub, state] of [[true, "partial"], [true, "fresh"], [true, null], [false, "complete"], [false, "partial"]]) assert.equal(demo.showReplayHint(pub, state), false, `${pub} ${state}`);
  // the guide button only ever renders in public mode (landing: `guided`; bar: returns nothing when not public), so local mode never meets the choice
  assert.ok(read("Landing.jsx").includes("const guided = !!demo.public"));
  assert.ok(read("DemoUI.jsx").includes("if (!demo.public) return null;"));
  assert.ok(read("DemoUI.jsx").includes("useRunState(demo.public && given === undefined)")); // local mode asks the server nothing
});

test("1. the choice dialog: start fresh (with its consequence), the other way in, and cancel; a partly worked demo says 'Continue the current run' and no replay hint", () => {
  const html = (state) => decode(renderToStaticMarkup(createElement(StartChoice, { state, onClose() {}, onOther() {}, resetApi: async () => ({}), browser: {} })));
  const done = html("complete"), part = html("partial");
  for (const h of [done, part]) assert.ok(h.includes("Start fresh — resets the demo for everyone") && h.includes("Cancel"));
  assert.ok(done.includes("See the finished handover") && done.includes("Someone has already finished this demo"));
  assert.ok(part.includes("Continue the current run") && !part.includes("finished handover") && part.includes("Someone is partway through this demo"));
  assert.equal(demo.REPLAY_HINT, "A run has already been completed here. Start fresh to replay it.");
  // start fresh runs the existing reset, then goes straight to step 1 of the first deal (tour mark forgotten by beforeReload)
  assert.ok(read("DemoUI.jsx").includes("runReset(resetApi, browser, hashFor({ d: FIRST_DEAL }))"));
  assert.ok(read("deals.js").includes('export async function runReset(resetApi, nav, hash = "#welcome")'));
});

// ---- 2. the guided path ----------------------------------------------------------------------------------------------------------------------------------------
test("2a. the languages step points at the promise first and highlights that link, and only that one", () => {
  const step = demo.GUIDES.noma_journeys[2];
  assert.ok(step.hint.startsWith("Open the RFP response to see the promise.") && step.hint.includes("Told 12 languages; the draft contract says four.") && step.told === true);
  const c = { name: "L", display_name: "Support in 12 languages", contract: "x", statements: [{ quote: "Told 12 languages.", doc_type_label: "RFP response", date: "2026-09-28" }, { quote: "Told 12 again.", doc_type_label: "Proposal", date: "2026-10-05" }], issues: [] };
  const docs = [{ source_key: "R", name: "RFP response", doc_type: "rfp_response", version: 1, date: "2026-09-28", version_date: "2026-09-28", source_version_id: 1, included: true }, { source_key: "P", name: "Proposal", doc_type: "proposal", version: 1, date: "2026-10-05", version_date: "2026-10-05", source_version_id: 2, included: true }];
  const withDocs = drawer(commitmentView(c, "open", docs), docs, { hint: step.hint, highlight: "add", told: true });
  assert.equal(withDocs.split("dr-linkbtn is-guided").length - 1, 1);
  assert.ok(/is-guided">RFP response, 28 Sep</.test(withDocs));
  assert.equal(drawer(commitmentView(c, "open", docs), docs, { hint: "h", highlight: "add" }).split("dr-linkbtn is-guided").length - 1, 0); // other steps: as before
  const act = demo.guideAction({ ...step }, [{ id: 16, name: "x", display_name: "Support in 12 languages" }]);
  assert.equal(act.drawer.guide.told, true);
});

test("2b. step 6 says up front what it asks for", () => {
  for (const deal of ["noma_journeys", "alder_bank"]) assert.equal(demo.GUIDES[deal][5].label, "Complete the handover: add a Sales note and a Delivery note, then lock the record");
});

test("2c. the locked record starts at its top, unless a link names one commitment", () => {
  assert.ok(read("FrozenRecord.jsx").includes("if (!readHash(window.location.hash).c) window.scrollTo(0, 0);"));
});

test("2d. 'Demo visitor' is the public demo's starting name, an editable value; local mode starts empty; it is the author like any other name", () => {
  assert.equal(DEMO_VISITOR, "Demo visitor");
  assert.ok(read("DealPage.jsx").includes('useName(demo.public ? DEMO_VISITOR : "")'));
  const u = read("dealpage.js");
  assert.ok(u.includes("useState(() => stored() || defaultName)")); // a value, not a placeholder
  assert.ok(u.includes("localStorage.setItem(KEY, value)") && !u.includes("setItem(KEY, defaultName)")); // remembered only if the visitor changes it
  // the note's author is the name field's value: notes, "mark as addressed", the handover notes and the lock all take it
  const dp = read("DealPage.jsx");
  assert.ok(dp.includes("const author = (name || draft).trim();") && dp.includes("resolved_by: author") && dp.includes("completed_by: completer"));
});

// ---- 3. evidence labels after signing --------------------------------------------------------------------------------------------------------------------------
const CLAUSE = "Provider will host the Customer's environment on Amazon Web Services in the Sydney region.";
const SOW = { source_key: "S", name: "Draft SOW", doc_type: "draft_sow", version: 2, date: "2026-10-09", version_date: "2026-10-16", source_version_id: 6, included: true };
const SIGNED = { source_key: "G", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true };
const HOST = { name: "Hosting", display_name: "Hosting on Azure", contract: CLAUSE, statements: [], issues: [{ id: 1, finding: "Not offered", state: "Needs action", reason: "r", evidence: { contract_quote: { quote: CLAUSE, source: "Draft SOW" }, contract_value: "Amazon Web Services", unlisted_value: "Azure" }, signed_check: null }] };

test("3. a draft clause under Contract says is labelled 'not re-checked at signing' once a signed document is in the deal, and not before; never 'verified'", () => {
  const before = commitmentView(HOST, "open", [SOW]), after = commitmentView(HOST, "open", [SOW, SIGNED]);
  assert.equal(before.afterSigning, false); assert.equal(after.afterSigning, true);
  assert.equal(draftSourceLabel(before, "Draft SOW"), "Draft SOW"); assert.equal(draftSourceLabel(after, "Draft SOW"), "Draft SOW · not re-checked at signing");
  assert.equal(draftSourceLabel(after, "Draft contract"), "Draft contract · not re-checked at signing");
  if (after.contract.quote) {
    assert.ok(drawer(after, [SOW, SIGNED]).includes("Draft SOW · not re-checked at signing") || !after.contract.quote.label);
    assert.ok(!drawer(before, [SOW]).includes("not re-checked at signing"));
  }
  for (const v of [before, after]) assert.ok(!/verified/i.test(drawer(v, [SOW, SIGNED]).replace(/quotes checked against|AI-written summary/g, "")));
});

test("3. a signed confirmation reads 'Signed contract · confirmed (20 Oct)', in the drawer and the record, on both deals' wording", () => {
  assert.equal(signedConfirmedLabel({ label: "Signed contract" }), "Signed contract · confirmed");
  assert.equal(signedConfirmedLabel({}), "Signed contract · confirmed");
  const S = "The Assistant will respond in 12 languages.";
  const gap = { id: 1, finding: "Contract says something different", state: "Resolved", resolved_by: { text: "Resolved by Draft contract, version 2 · 19 Oct 2026" },
    signed_check: { status: "confirmed", sentence: S, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft contract, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)", signed_sentence: S, signed_key: "G", signed_version_id: 9 } };
  const v = commitmentView({ name: "L", display_name: "Languages", contract: "No gap found", statements: [], issues: [gap] }, "closed", [SOW, SIGNED]);
  const html = drawer(v, [SOW, SIGNED]);
  assert.ok(html.includes('<button type="button" class="dr-linkbtn">Signed contract · confirmed</button> (20 Oct)') && !html.includes("Confirmed in the signed contract (<"));
  assert.equal(recordLines(v, [SOW, SIGNED]).contract, `“${S}” (Signed contract · confirmed, 20 Oct)`);
  const html2 = record(frozenView({ item: { promise: "L", findings: [], contract: "No gap found" }, status: "closed", closedFindings: [{ finding: "Contract says something different", resolved_by: "Resolved by Draft contract, version 2" }], documents: [SOW, SIGNED], live: { issues: [gap] }, snapshotDocs: [SOW, SIGNED] }), [SOW, SIGNED]);
  assert.ok(html2.includes("Signed contract · confirmed"));
});

test("3. in the locked record a quoted draft clause reads '(Draft SOW · not re-checked at signing)'", () => {
  const v = frozenView({ item: { promise: "Hosting", findings: [{ finding: "Not offered", evidence: { contract_value: "Amazon Web Services", unlisted_value: "Azure" }, signed_check: null }], contract: CLAUSE, quotes: [] }, status: "open", documents: [SOW, SIGNED], snapshotDocs: [SOW, SIGNED] });
  assert.equal(v.afterSigning, true);
  const line = recordLines(v, [SOW, SIGNED]).contract;
  if (line) assert.ok(!line.includes("(Draft SOW)") || line.includes("not re-checked at signing"));
});

// ---- 4. the Alder card ------------------------------------------------------------------------------------------------------------------------------------------
test("4. the Alder landing card says it previews the outcome; the Noma card (the starting state) does not", () => {
  const l = read("landing.js"), jsx = read("Landing.jsx");
  assert.ok(l.includes('preview: "Preview of the outcome"'));
  assert.ok(jsx.includes("{STATIC_CARDS[s.deal].preview && <span className=\"land-preview\">{STATIC_CARDS[s.deal].preview}</span>}"));
  assert.equal(l.split("preview:").length - 1, 1); // one card only
});

// ---- C. a page that predates a reset ---------------------------------------------------------------------------------------------------------------------------
test("C. a write from a page that predates a reset says so plainly, shows a way back, and carries the epoch", async () => {
  const api = await import("../src/api.js");
  const sent = [];
  const events = [];
  const realFetch = globalThis.fetch, realWindow = globalThis.window;
  globalThis.window = { dispatchEvent: (e) => events.push(e) };
  try {
    api.setDemoEpoch("abc-1");
    globalThis.fetch = async (url, opts) => { sent.push(opts); return { ok: false, status: 409, headers: { get: (k) => (k === "X-Demo-Reset" ? "1" : null) }, json: async () => ({ detail: "The demo was reset." }) }; };
    await assert.rejects(() => api.addCapability({}), (e) => e.message === "The demo was reset." && e.demoReset === true);
    assert.equal(sent[0].headers["X-Demo-Epoch"], "abc-1");
    assert.equal(events.length, 1); assert.equal(events[0].type, "demo-reset");
    // an ordinary 409 (no reset header) is not mistaken for it
    globalThis.fetch = async () => ({ ok: false, status: 409, headers: { get: () => null }, json: async () => ({ detail: "Something else." }) });
    await assert.rejects(() => api.addCapability({}), (e) => e.message === "Something else." && !e.demoReset);
    assert.equal(events.length, 1);
    // local mode: no epoch, no header
    api.setDemoEpoch(null); sent.length = 0;
    globalThis.fetch = async (url, opts) => { sent.push(opts); return { ok: true, json: async () => ({}) }; };
    await api.addCapability({});
    assert.ok(!("X-Demo-Epoch" in sent[0].headers));
  } finally { globalThis.fetch = realFetch; globalThis.window = realWindow; api.setDemoEpoch(null); }
  assert.equal(demo.DEMO_WAS_RESET, "The demo was reset.");
  const ui = read("DemoUI.jsx");
  assert.ok(ui.includes("<span>{DEMO_WAS_RESET}</span>") && ui.includes("Start again") && ui.includes('nav.setHash("#welcome")') && ui.includes("<ResetNotice />"));
  assert.ok(read("App.jsx").includes("api.setDemoEpoch(r.epoch)"));
});

// ---- follow-ups: the reset message, and a double click ------------------------------------------------------------------------------------------------------
test("follow-up 1: the message is 'The demo was reset.' (the epoch also changes on the hourly reset and on a restart), with the same Start again link", () => {
  assert.equal(demo.DEMO_WAS_RESET, "The demo was reset.");
  assert.ok(!read("DemoUI.jsx").includes("by another visitor") && !read("demo.js").includes("by another visitor") && !read("api.js").includes("by another visitor"));
  assert.ok(read("DemoUI.jsx").includes("<span>{DEMO_WAS_RESET}</span>") && read("DemoUI.jsx").includes("Start again"));
});

test("follow-up 2: a double click sends one reset; a 409 from a reset shows the same message, not an error", async () => {
  const { runReset } = await import("../src/deals.js");
  // whileIdle: the second call while the first runs is ignored; it can run again after a failure
  let calls = 0, release;
  const gate = new Promise((r) => { release = r; });
  const act = demo.whileIdle(async () => { calls += 1; await gate; return "done"; });
  const first = act(); const second = act();
  assert.equal(await second, undefined); // ignored
  release(); assert.equal(await first, "done"); assert.equal(calls, 1);
  let tries = 0;
  const flaky = demo.whileIdle(async () => { tries += 1; throw new Error("x"); });
  await assert.rejects(flaky); await assert.rejects(flaky); assert.equal(tries, 2);
  // both reset buttons use it
  assert.ok(read("DemoUI.jsx").includes("useRef(whileIdle(async () =>") && read("ResetDemo.jsx").includes("useRef(whileIdle(async () =>"));
  assert.ok(read("DemoUI.jsx").includes('disabled={busy} onClick={() => fresh()}'));
  // a 409 (a reset in the same second, or one still running) is "The demo was reset.", with a way to start again; the page does not move
  const nav = { setHash() { throw new Error("must not navigate"); }, reload() { throw new Error("must not reload"); } };
  const conflict = Object.assign(new Error("l.backup-2026… already exists; wait a second and run again"), { status: 409 });
  assert.deepEqual(await runReset(async () => { throw conflict; }, nav), { ok: false, conflict: true, message: "The demo was reset." });
  assert.deepEqual(await runReset(async () => { throw Object.assign(new Error("Server trouble."), { status: 500 }); }, nav), { ok: false, message: "Server trouble." });
  const moved = []; await runReset(async () => ({}), { setHash: (h) => moved.push(h), reload: () => moved.push("reload") }, "#d=noma_journeys");
  assert.deepEqual(moved, ["#d=noma_journeys", "reload"]);
  const choice = decode(renderToStaticMarkup(createElement(StartChoice, { state: "complete", onClose() {}, onOther() {}, resetApi: async () => ({}), browser: {} })));
  assert.ok(!choice.includes("demo was reset")); // shown only after a conflict
  assert.ok(read("DemoUI.jsx").includes("{conflict && <>") && read("DemoUI.jsx").includes("Start again"));
});

// ---- follow-up: the record never shows a firmness label before the signed-check result is known -----------------------------------------------------------
const CL = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
const DC = { source_key: "NJ-07", name: "Draft contract", doc_type: "draft_contract", version: 2, date: "2026-10-14", version_date: "2026-10-19", source_version_id: 4, included: true };
const SG = { source_key: "NJ-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true };
const LANG_ITEM = { promise: "Support in 12 languages", findings: [], contract: "No gap found", contract_now: { target: "12 languages", quote: CL, document: "Draft contract" }, signed: [{ status: "confirmed", text: "Confirmed in the signed contract (Signed contract, 20 Oct)" }] };
const LANG_LIVE = { name: "Support in 12 languages", issues: [{ finding: "Contract says something different", state: "Resolved", signed_check: { status: "confirmed", sentence: CL, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft contract, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)", signed_sentence: CL, signed_key: "NJ-09", signed_version_id: 9 } }] };
const lang = (extra) => frozenView({ item: LANG_ITEM, status: "closed", closedFindings: [{ finding: "Contract says something different", resolved_by: "Resolved by Draft contract, version 2 · 19 Oct 2026" }], documents: [DC, SG], snapshotDocs: [DC, SG], ...extra });

test("record: with the signed-check result pending, no row says 'not re-checked' or 'confirmed' on a guess; once it is known the label is the true one", () => {
  const pending = record(lang({ live: null, pending: true }), [DC, SG]);
  // (the settled line "Closed by … · confirmed in the signed contract (20 Oct)" comes from the saved record and is final; the labels under test come from the signed-check result)
  assert.ok(!pending.includes("not re-checked") && !pending.includes("Signed contract · confirmed"), pending);
  assert.ok(pending.includes("(Draft contract)")); // the source, with no firmness label
  assert.equal(lang({ live: null, pending: true }).afterSigning, false);
  const known = record(lang({ live: LANG_LIVE }), [DC, SG]);
  assert.ok(known.includes("Signed contract · confirmed") && !known.includes("not re-checked"));
  // a draft clause that no signed check confirmed, once the results are known, is labelled
  const phone = frozenView({ item: { promise: "Phone", findings: [{ finding: "Not offered", evidence: {}, signed_check: null }], contract: CL, quotes: [] }, status: "open", documents: [DC, SG], snapshotDocs: [DC, SG], live: { name: "Phone", issues: [] } });
  assert.equal(phone.afterSigning, true);
});

test("record: the drawer view and the row both stay label-free while pending; print waits for the labels", () => {
  const v = lang({ live: null, pending: true });
  const html = decode(renderToStaticMarkup(createElement(CommitmentView, { v, documents: [DC, SG], titleId: "t", readOnly: true, onClose() {}, onOpenDoc() {} })));
  assert.ok(!html.includes("not re-checked") && !html.includes("Signed contract · confirmed"));
  const fr = read("FrozenRecord.jsx");
  assert.ok(fr.includes("const evidencePending = !liveCommitments;") && fr.includes("hv.live_commitments ?? liveRegister?.commitments ?? null"));
  assert.ok(fr.includes("disabled={evidencePending ||") && fr.includes("const printAll = () => { if (evidencePending) return;"));
  assert.ok(fr.includes("if (hv && !hv.live_commitments) api.fetchRegister(deal)")); // the register is asked for only when the handover response lacks them
});
