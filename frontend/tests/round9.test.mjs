// Round 9 (14 Nov): the guided path (away state and "Back to step N", plain blocks), the mobile handover notes, and a cleaner Print or save as PDF.
// Display and flow only: no engine, snapshot, fingerprint, golden, cache or sealed change.
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
import { readHash } from "../src/dealpage.js";
import { appendixEntries } from "../src/docHash.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/round9-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { DemoBar } from ${abs("DemoUI.jsx")};\nexport { NoteForm } from ${abs("DealPage.jsx")};\nexport { PlainText, APPENDIX_NOTE } from ${abs("FrozenRecord.jsx")};\nexport { PreviewDoc } from ${abs("DemoUI.jsx")};\nexport { DemoContext, GuideStateContext, LandingStateContext, DemoNavContext } from ${abs("demo.js")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { DemoBar, NoteForm, PlainText, APPENDIX_NOTE, PreviewDoc, DemoContext, GuideStateContext, LandingStateContext, DemoNavContext } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&");

// ---- A. the active path ------------------------------------------------------------------------------------------------------------------------------------------
const mem = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v), removeItem: (k) => m.delete(k) }; };

test("A. the active path: Noma by default, another guided deal when started, remembered in the browser tab only; a reset forgets it", () => {
  const st = mem();
  assert.equal(demo.activeGuide(st), "noma_journeys");
  demo.setActiveGuide("alder_bank", st); assert.equal(demo.activeGuide(st), "alder_bank");
  demo.setActiveGuide("no_such_deal", st); assert.equal(demo.activeGuide(st), "alder_bank"); // only guided deals
  demo.requestStep("noma_journeys", st);
  assert.equal(demo.takePendingStep("alder_bank", st), false); assert.equal(demo.takePendingStep("noma_journeys", st), true); assert.equal(demo.takePendingStep("noma_journeys", st), false); // single use
  demo.requestStep("noma_journeys", st); demo.clearTourDone(st);
  assert.equal(demo.activeGuide(st), "noma_journeys"); assert.equal(demo.takePendingStep("noma_journeys", st), false);
  // nothing here touches the server: the module keeps the choice in sessionStorage only
  const src = read("demo.js");
  const block = src.slice(src.indexOf("export const ACTIVE_KEY"), src.indexOf("export const GUIDE_DEAL_NAME"));
  assert.ok(!/fetch|api\./.test(block));
});

const NOMA_COMMITMENTS = [{ id: 17, name: "Dedicated launch specialist", display_name: "Dedicated launch specialist for the first 30 days" }, { id: 16, name: "Support", display_name: "Support in 12 languages at launch" }, { id: 15, name: "Phone", display_name: "AI answers customers' phone calls at launch" }];
const step = (deal, n) => demo.GUIDES[deal][n - 1];

test("A. 'here': the step's own row, the add panel for the signed contract, or nothing open; any other drawer, the catalogue or another page is away", () => {
  const lang = step("noma_journeys", 3), signed = step("noma_journeys", 4), note = step("noma_journeys", 5), handover = step("noma_journeys", 6);
  assert.equal(demo.stepHere(lang, NOMA_COMMITMENTS, { drawer: null }), true);                                          // on the page, nothing open
  assert.equal(demo.stepHere(lang, NOMA_COMMITMENTS, { drawer: { type: "commitment", id: 16 } }), true);                // the languages row
  assert.equal(demo.stepHere(lang, NOMA_COMMITMENTS, { drawer: { type: "add", id: 16 } }), true);                       // its add panel
  assert.equal(demo.stepHere(lang, NOMA_COMMITMENTS, { drawer: { type: "commitment", id: 15 } }), false);               // another commitment
  assert.equal(demo.stepHere(lang, NOMA_COMMITMENTS, { drawer: null, catalogueOpen: true }), false);                    // the catalogue
  assert.equal(demo.stepHere(signed, NOMA_COMMITMENTS, { drawer: { type: "add", id: null } }), true);                   // the sample panel
  assert.equal(demo.stepHere(signed, NOMA_COMMITMENTS, { drawer: { type: "commitment", id: 16 } }), false);
  assert.equal(demo.stepHere(note, NOMA_COMMITMENTS, { drawer: { type: "note", id: 15 } }), true);                      // the phone row's note form
  assert.equal(demo.stepHere(note, NOMA_COMMITMENTS, { drawer: { type: "note", id: 16 } }), false);
  assert.equal(demo.stepHere(handover, NOMA_COMMITMENTS, { drawer: { type: "commitment", id: 16 } }), false);
  assert.equal(demo.stepHere(null, NOMA_COMMITMENTS, { drawer: { type: "commitment", id: 1 } }), true);                 // no current step: nothing to be away from
});

const stepsAt = (current, done = []) => demo.GUIDES.noma_journeys.map((g, i) => ({ ...g, n: i + 1, state: done.includes(i + 1) ? "done" : i + 1 === current ? "current" : "later" }));

test("A. away state: only when something has been done, the guide is not finished, and the visitor is not where the step is", () => {
  const steps = stepsAt(3, [1, 2]);
  assert.deepEqual([demo.awayFrom({ steps, complete: false, here: false }).line, demo.awayFrom({ steps, complete: false, here: false }).button], ["You're on step 3 of 6", "Back to step 3"]);
  assert.equal(demo.awayFrom({ steps, complete: false, here: true }), null);                       // where the step is
  assert.equal(demo.awayFrom({ steps, complete: true, here: false }), null);                       // a locked deal's guide is finished: never "Back to step N"
  assert.equal(demo.awayFrom({ steps: stepsAt(1, []), complete: false, here: false }), null);      // nothing started
  assert.equal(demo.awayFrom({ steps: null, complete: false, here: false }), null);
  assert.equal(demo.awayFrom({ steps: demo.GUIDES.noma_journeys.map((g, i) => ({ ...g, n: i + 1, state: "done" })), complete: false, here: false }), null); // every step done
});

const ctx = (guide, { onLanding = false, pub = true } = {}) => createElement(DemoContext.Provider, { value: { public: pub, banner: "Public demo · fictional data", note: null, note_max: null } },
  createElement(LandingStateContext.Provider, { value: onLanding }, createElement(DemoNavContext.Provider, { value: { current: null } },
    createElement(GuideStateContext.Provider, { value: guide }, createElement(DemoBar, { initialSamples: SAMPLES, toured: true })))));
const SAMPLES = [{ file: "NJ-05.md", version_of: "NJ-05", title: "Approval" }, { file: "NJ-07.md", version_of: "NJ-07", title: "Revised contract" }, { file: "NJ-09.md", doc_type: "signed_contract", title: "Signed" }];
const docs = (...versions) => versions.map(([k, v, t]) => ({ source_key: k, name: k, doc_type: t ?? "draft_sow", version: v, included: true }));
const guideState = (extra = {}) => ({ deal: "noma_journeys", documents: docs(["NJ-05", 2, "pricing_services_note"]), commitments: NOMA_COMMITMENTS.map((c) => ({ ...c, noted_count: 0 })), handoverComplete: false, facts: {}, onDo() {}, onTour() {}, ...extra });

test("A. the bar: 'Step 3 of 6 · Do step 3' where the step is; 'You're on step 3 of 6 · Back to step 3' when not; a finished guide shows neither", () => {
  const here = decode(renderToStaticMarkup(ctx(guideState({ here: true }))));
  assert.ok(here.includes("Step 3 of 6") && here.includes("Do step 3") && !here.includes("Back to step"));
  const away = decode(renderToStaticMarkup(ctx(guideState({ here: false }))));
  assert.ok(away.includes("You&#x27;re on step 3 of 6".replace("&#x27;", "'")) && away.includes("Back to step 3") && !away.includes("Do step 3"));
  assert.ok(away.includes("Support in 12 languages: add the revised contract") && away.includes("Reset demo") && away.includes("All steps"));
  const finished = decode(renderToStaticMarkup(ctx(guideState({ here: false, handoverComplete: true, documents: docs(["NJ-05", 2], ["NJ-07", 2], ["NJ-09", 1, "signed_contract"]) }))));
  assert.ok(!finished.includes("Back to step") && !finished.includes("You're on step"));
  assert.equal(renderToStaticMarkup(ctx(guideState({ here: false }), { pub: false })), ""); // local mode: no bar at all
  // the welcome page and the other deal's page get the away state from a read of the active deal's state (useRemoteGuide), never from the page's own guide
  const ui = read("DemoUI.jsx");
  assert.ok(ui.includes("const remote = useRemoteGuide(active, demo.public && !onActivePage"));
  assert.ok(ui.includes("{away && <button type=\"button\" className=\"demo-bar-do\" onClick={goBack}>{away.button}</button>}"));
});

test("A. 'Back to step N' only opens: it never adds a document, saves a note or locks anything", () => {
  const ui = read("DemoUI.jsx"), page = read("DealPage.jsx"), dm = read("demo.js");
  assert.ok(ui.includes("const goBack = () => { setOpen(false); if (awayHere) guide.onDo(awayHere.step); else goBackRemote(); };"));
  assert.ok(ui.includes("const goBackRemote = () => { requestStep(active); nav?.current?.(active); };"));
  // what it runs is guideAction's description (a drawer, a row, the handover card) and doStep, which opens and scrolls
  const doStep = page.slice(page.indexOf("  const doStep = (step) => {"), page.indexOf("  // The demo bar (public mode) shows the guide"));
  assert.ok(doStep.includes("guideAction(step, reg.commitments)") && !/api\.|act\(|complete|resolveByNote|saveHandoverNote|addDocument/.test(doStep));
  const fn = dm.slice(dm.indexOf("export function guideAction"), dm.indexOf("// The deal page tells the demo bar"));
  assert.ok(!/api\.|fetch|post/i.test(fn));
  for (const deal of Object.keys(demo.GUIDES)) for (const s of demo.GUIDES[deal]) {
    const a = demo.guideAction(s, deal === "noma_journeys" ? NOMA_COMMITMENTS : []);
    for (const v of Object.values(a)) assert.ok(typeof v !== "function"); // plain descriptions only
  }
  // the pending request is consumed by the deal page once, and only calls doStep
  const eff = page.slice(page.indexOf("  // \"Back to step N\" from another page"), page.indexOf("  const markActive"));
  assert.ok(eff.includes("doStepRef.current(current)") && !/api\./.test(eff));
  // a step that has nothing to open (the tour) is not run
  assert.ok(eff.includes('current.kind !== "tour"'));
});

test("A. hash links switch deals: a hash naming another deal opens it (it used to change the address and stay put)", () => {
  assert.equal(readHash("#d=alder_bank&c=abc").d, "alder_bank");
  const app = read("App.jsx");
  assert.ok(app.includes("const d = readHash(window.location.hash).d;") && app.includes("setCurrent((cur) => (cur === d ? cur : d))"));
  assert.ok(app.includes("if (isWelcome(window.location.hash)) { setCurrent(null); setClassic(false); setLanding(true); return; }")); // #welcome still works
});

test("A. the plain lines a block shows, and where", () => {
  assert.equal(demo.sampleBlockedLine("Revised draft contract", 3), "Add the revised draft contract first: step 3");
  assert.equal(demo.sampleBlockedLine("Approval for the launch specialist", 2), "Add the approval for the launch specialist first: step 2");
  assert.equal(demo.lockBlockedLine(["upload the signed contract", "add the Sales note", "add the Delivery note"]), "Add the signed contract first: step 4");
  assert.equal(demo.lockBlockedLine(["add the Sales note", "add the Delivery note"]), "Add the Sales note and the Delivery note first: step 6");
  assert.equal(demo.lockBlockedLine(["add the Delivery note"]), "Add the Delivery note first: step 6");
  assert.equal(demo.lockBlockedLine([]), "");
  assert.equal(demo.addressedBlockedLine("noma_journeys"), "In this guided demo, the agreement is recorded at step 5 (phone calls).");
  assert.equal(demo.addressedBlockedLine("alder_bank"), "In this guided demo, the agreement is recorded at step 5 (hosting).");
  // sample list: later samples are 'Not yet' with the line; navigation is never blocked
  assert.ok(read("DemoUI.jsx").includes("sampleBlockedLine(steps[idx - 1].sample.title, after)"));
  assert.ok(read("DealPage.jsx").includes("{demo.public && missing.length > 0 && <span className=\"demo-blocked dp-small\" role=\"note\">{lockBlockedLine(missing)}</span>}"));
  assert.ok(!/disabled=\{[^}]*guide/i.test(read("DemoUI.jsx").slice(read("DemoUI.jsx").indexOf("export function DemoBar"), read("DemoUI.jsx").indexOf("export function UseSampleText")))); // the bar blocks nothing
});

test("A. 'Mark as addressed by note' (public demo): only on the step-5 row and only once step 5 is current; keep-open notes are never blocked", () => {
  const noteStep = (state) => ({ ...step("noma_journeys", 5), n: 5, state });
  const at = (cur) => demo.GUIDES.noma_journeys.map((g, i) => ({ ...g, n: i + 1, state: i + 1 < cur ? "done" : i + 1 === cur ? "current" : "later" }));
  const phone = NOMA_COMMITMENTS[2], lang = NOMA_COMMITMENTS[1];
  assert.equal(demo.addressedAllowed("noma_journeys", at(5), phone), true);
  assert.equal(demo.addressedAllowed("noma_journeys", at(5), lang), false);       // elsewhere
  assert.equal(demo.addressedAllowed("noma_journeys", at(3), phone), false);      // before step 5
  assert.equal(demo.addressedAllowed("noma_journeys", at(6), phone), false);      // after it
  assert.equal(demo.addressedAllowed("noma_journeys", null, phone), false);       // steps not known yet: blocked, never guessed open
  void noteStep;
  const form = (blocked) => decode(renderToStaticMarkup(createElement(DemoContext.Provider, { value: { public: true, banner: null, note: null, note_max: 500 } },
    createElement(NoteForm, { deal: "noma_journeys", c: { id: 15, name: "Phone", display_name: "AI answers customers' phone calls at launch", issues: [{ id: 1, state: "Needs action", finding: "Not offered" }] }, titleId: "t", name: "Demo visitor", setName() {}, canDecide: true, freshnessLabel: "Up to date",
      message: null, checking: false, onCheckAgain() {}, onNoted() {}, onBack() {}, onClose() {}, addressedBlocked: blocked }))));
  const radios = (h) => [...h.matchAll(/<input type="radio"[^>]*name="how"[^>]*>/g)].map((m) => m[0]);
  const blocked = form("In this guided demo, the agreement is recorded at step 5 (phone calls).");
  assert.ok(!/disabled/.test(radios(blocked)[0]) && /disabled/.test(radios(blocked)[1])); // keep-open stays available; addressed is disabled
  assert.ok(blocked.includes("In this guided demo, the agreement is recorded at step 5 (phone calls).") && blocked.includes("Keep it open, add context."));
  const open = form("");
  assert.ok(!open.includes("In this guided demo") && !/disabled/.test(radios(open)[1]));
});

// ---- B. mobile handover notes --------------------------------------------------------------------------------------------------------------------------------
test("B. handover notes wrap fully on a phone: the column can shrink and a long unbroken word breaks (deal page and record)", () => {
  const css = read("DealPage.css");
  assert.match(css, /@media \(max-width: 760px\) \{ \.dp-notes \{ grid-template-columns: minmax\(0, 1fr\); \} \}/);
  assert.match(css, /\.dp-note \{[^}]*min-width: 0;[^}]*\}/);
  assert.match(css, /\.dp-note-text \{[^}]*overflow-wrap: anywhere;[^}]*\}/);
  assert.match(css, /\.fr-detail p, \.dr-note p \{ overflow-wrap: anywhere; \}/); // a note inside a record row or a drawer
  // the record's notes use the same classes
  assert.ok(read("FrozenRecord.jsx").includes('className="dp-notes"'));
});

// ---- C. Print or save as PDF ----------------------------------------------------------------------------------------------------------------------------------
test("C. print: the Dealshape logo first, clear section headings, page margins, a document per page with its header, hash and the note about what the hash covers", () => {
  const fr = read("FrozenRecord.jsx"), css = read("DealPage.css");
  assert.ok(fr.includes('<div className="fr-print-head" aria-hidden="true"><Logo height={34} /></div>'));
  const heads = [...fr.matchAll(/<h2 className="fr-print-h">([^<]*)<\/h2>/g)].map((m) => m[1]);
  // one heading style for every section; no "Header and outcomes" heading; the cards' own headings stay on screen but are not printed
  assert.deepEqual([...heads].sort(), ["Commitments", "Deal brief", "Documents at handover", "Handover notes", "Record details"]);
  assert.ok(!fr.includes("Header and outcomes"));
  assert.ok(fr.includes("<h2>Commitments</h2>") && fr.includes("<h2>Handover notes</h2>"));
  assert.match(css, /\.fr \.dp-promises > \.dp-sec-head, \.fr \.fr-notes-card > \.dp-sec-head \{ display: none; \}/);
  assert.match(css, /\.fr \.fr-notes-card \{ break-inside: auto; \}/); // no forced page break before Handover notes
  assert.ok(!/fr-notes-card[^{]*\{[^}]*break-before/.test(css));
  assert.match(css, /\.fr \.dp-prow \{ break-inside: avoid; \}/); // only each commitment stays whole
  assert.match(css, /\.fr-print-head, \.fr-print-h \{ display: none; \}/); // print only
  assert.match(css, /@page \{ margin: 16mm 10mm 15mm;/); // Round 10: a little more at the top and bottom for the running header and the page number
  assert.match(css, /\.fr \.dp-topbar \{ display: none !important; \}/);
  assert.match(css, /\.fr \.dp-prow \{ break-inside: avoid; \}/); // each commitment stays on one page
  assert.match(css, /\.fr \.fr-appendix-doc \{ break-before: page; page-break-before: always; \}/);
  assert.equal(APPENDIX_NOTE, "SHA-256 covers the source text Dealshape read; formatting here is for reading.");
  assert.ok(fr.includes('<p className="fr-appendix-note">{APPENDIX_NOTE}</p>'));
  assert.ok(fr.includes("<p>Version {a.version} · {fmtDate(a.date)} · SHA-256 <code>{a.sha256}</code></p>")); // the hash line is as it was
});

test("C. print: Markdown documents are rendered as text (headings, lists, tables), other formats print as plain paragraphs, wide tables fit the page", () => {
  const md = "# Pricing note\n\nIntro line.\n\n| Capability | Scope | Approval |\n| --- | --- | --- |\n| CAP-008 | Singapore | Named exception approved |\n\n- one\n- two\n";
  const html = renderToStaticMarkup(createElement(PreviewDoc, { text: md }));
  assert.ok(html.includes("<table") && html.includes("<th>Capability</th>") && html.includes("<li") && html.includes("Pricing note"));
  assert.ok(!html.includes("| ---") && !html.includes("# Pricing"));  // no raw markdown
  const plain = renderToStaticMarkup(createElement(PlainText, { text: "First paragraph\nstill the first\n\nSecond paragraph" }));
  assert.equal((plain.match(/<p /g) || []).length, 2); assert.ok(plain.includes("First paragraph\nstill the first") && !plain.includes("<table"));
  const fr = read("FrozenRecord.jsx"), css = read("DealPage.css");
  assert.ok(fr.includes('a.format === "Markdown" ? <PreviewDoc text={a.text} marks={plan?.marks[a.key]} /> : <PlainText text={a.text} marks={plan?.marks[a.key]} />')); // Round 10: with the marks of the quoted places
  assert.match(css, /\.fr-appendix-text table \{[^}]*width: 100%;[^}]*table-layout: fixed;[^}]*\}/);
  assert.match(css, /\.fr-appendix-text th, \.fr-appendix-text td \{[^}]*overflow-wrap: anywhere;[^}]*\}/);
  // the format comes from the live document; unknown until the documents are known, and print waits for it (with the Round 8 label guard)
  const docsList = [{ source_version_id: 1, name: "A", version: 1, sha256: "a".repeat(64), version_date: "2026-10-01" }, { source_version_id: 2, name: "B", version: 1, sha256: "b".repeat(64) }];
  assert.deepEqual(appendixEntries(docsList, { 1: "x" }, [{ source_version_id: 1, format: "Markdown" }, { source_version_id: 2, format: "PDF" }]).map((e) => e.format), ["Markdown", "PDF"]);
  assert.deepEqual(appendixEntries(docsList, {}, []).map((e) => e.format), [null, null]);
  assert.ok(fr.includes("disabled={evidencePending || (withText && appendix.some((a) => a.text === null || a.format === null))}"));
});

test("C. print: hashes and the fingerprint are exactly as stored; the text is carried unchanged into the rendering", () => {
  const d = [{ source_version_id: 7, name: "Contract", version: 2, sha256: "c".repeat(64), version_date: "2026-10-19", date: "2026-10-14" }];
  const e = appendixEntries(d, { 7: "# Title\n\nBody **bold**.\n" }, [{ source_version_id: 7, format: "Markdown" }])[0];
  assert.equal(e.sha256, "c".repeat(64));                     // the stored hash, untouched
  assert.equal(e.text, "# Title\n\nBody **bold**.\n");        // the text as read; only the rendering differs
  const fr = read("FrozenRecord.jsx");
  assert.ok(fr.includes("SHA-256 <span className=\"fr-h-short\">") || fr.includes("fr-h-full")); // the hash and fingerprint blocks are unchanged
});

// ---- follow-ups (14 Nov) -------------------------------------------------------------------------------------------------------------------------------------------
test("A. saving a note never switches the active path; adding a sample, starting a guide ('Do step', 'Show me') or 'Guide this deal' does", () => {
  const page = read("DealPage.jsx"), ui = read("DemoUI.jsx");
  const noted = page.slice(page.indexOf("onNoted={() =>"), page.indexOf("onBack={toCommitment}", page.indexOf("onNoted={() =>")));
  assert.ok(noted.includes("toCommitment(); load();") && !noted.includes("markActive")); // the note form
  const docDone = page.slice(page.indexOf("const docDone = async"), page.indexOf("const acted", page.indexOf("const docDone = async")));
  assert.ok(docDone.includes("markActive();")); // adding a sample
  assert.equal((page.match(/markActive\(\)/g) || []).length, 1); // called in one place only: after a sample is added
  assert.ok(ui.includes("setActiveGuide(deal); if (now.step.kind === \"tour\") goTour(0)")); // Do step / Show me on the deal's own bar
  assert.ok(ui.includes("const guideThisDeal = () => { setActiveGuide(deal); setToured((n) => n + 1); };"));
  // the handover notes and the lock do not touch it either
  assert.ok(!/NotePanel[^>]*markActive/.test(page));
  // the rules themselves: only an explicit choice writes the active deal
  const st = mem(); demo.setActiveGuide("alder_bank", st); assert.equal(demo.activeGuide(st), "alder_bank");
  const st2 = mem(); assert.equal(demo.activeGuide(st2), "noma_journeys"); // nothing writes it on its own
});

test("A. a blocked 'Mark as addressed by note' is visibly disabled: greyed, not-allowed cursor, not selectable, with the demo line under it", () => {
  const form = (blocked) => decode(renderToStaticMarkup(createElement(DemoContext.Provider, { value: { public: true, banner: null, note: null, note_max: 500 } },
    createElement(NoteForm, { deal: "noma_journeys", c: { id: 15, name: "Phone", display_name: "AI answers customers' phone calls at launch", issues: [{ id: 1, state: "Needs action", finding: "Not offered" }] }, titleId: "t", name: "Demo visitor", setName() {}, canDecide: true, freshnessLabel: "Up to date",
      message: null, checking: false, onCheckAgain() {}, onNoted() {}, onBack() {}, onClose() {}, addressedBlocked: blocked }))));
  const b = form("In this guided demo, the agreement is recorded at step 5 (phone calls).");
  assert.ok(/<label class="is-disabled" aria-disabled="true"><input type="radio"[^>]*disabled/.test(b));
  assert.ok(b.includes('class="demo-blocked"') && b.indexOf("In this guided demo") > b.indexOf("Mark as addressed by note"));
  const o = form("");
  assert.ok(!o.includes("is-disabled") && !o.includes("aria-disabled"));
  const css = read("DealPage.css");
  assert.match(css, /\.dp-choice label\.is-disabled, \.dp-choice label\.is-disabled \* \{ cursor: not-allowed; \}/);
  assert.match(css, /\.dp-choice label\.is-disabled \{ background: var\(--soft\); border-color: var\(--line\); color: #94a3b8; \}/);
});

test("4. at 480px and below the demo bar's step label is clamped to two lines (the full wording is in All steps)", () => {
  const css = read("App.css");
  assert.match(css, /@media \(max-width: 480px\) \{ \.demo-bar-step \{ display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow: hidden; \} \}/);
  assert.ok(css.indexOf("max-width: 480px") > css.indexOf("max-width: 639px")); // later than the 639px wrap rule, so it wins
});
