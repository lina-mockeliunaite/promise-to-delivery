// The result dialog (11 Nov): "What changed" as a centred dialog over the dimmed page, and the indigo highlights. Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { changeTitle, changedPromises, changeView, whatChanged } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/result-dialog-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
fs.writeFileSync(entry, `export { ChangeDialog } from ${JSON.stringify(fileURLToPath(new URL("DealPage.jsx", SRC)))};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { ChangeDialog } = await import(file);

const iss = (id, finding, state, extra = {}) => ({ id, finding, state, ...extra });
const reg = (...rows) => ({ commitments: rows.map(([name, issues]) => ({ name, issues })) });
const SPEC = "Dedicated launch specialist", PHONE = "AI answers customers' phone calls at launch", LANG = "Support in 12 languages at launch";
const titleOf = (n) => n;
const dialog = (change, extra = {}) => renderToStaticMarkup(createElement(ChangeDialog, { change, titleOf, onClose() {}, onGotIt() {}, ...extra }));
const decode = (t) => t.replace(/&#x27;/g, "'");

// sample 1 on Noma: the specialist's approval closes, its contract gap stays, the phone row is untouched
const afterSample1 = () => whatChanged(
  reg([SPEC, [iss(10, "No approval recorded", "Needs action"), iss(11, "Missing from contract", "Needs action")]], [PHONE, [iss(2, "Not offered", "Needs action")]]),
  reg([SPEC, [iss(10, "No approval recorded", "Resolved", { resolved_by: { text: "Resolved by Internal approvals note, version 2 · checked 11 Nov 2026" } }), iss(11, "Missing from contract", "Needs action")]], [PHONE, [iss(2, "Not offered", "Needs action")]]));
const change1 = () => ({ ...afterSample1(), doc: "Internal approvals note, new version (v2, 18 Oct)", title: "Rechecked after adding Internal approvals note v2 (18 Oct)", acted: SPEC, modelCalls: 0, openPromises: 2 });

test("the title reads 'Rechecked after adding <document> <version> (<date>)'", () => {
  assert.equal(changeTitle({ name: "Internal approvals note", existing: true, version: 2, date: "2026-10-18" }), "Rechecked after adding Internal approvals note v2 (18 Oct)");
  assert.equal(changeTitle({ name: "Signed contract", existing: false, date: "2026-10-20" }), "Rechecked after adding Signed contract (20 Oct)");
  const html = dialog(change1());
  assert.match(html, /<h2 id="[^"]+">Rechecked after adding Internal approvals note v2 \(18 Oct\)<\/h2>/);
  assert.ok(decode(dialog({ ...change1(), title: undefined })).includes("Rechecked after adding Internal approvals note, new version (v2, 18 Oct)")); // a fallback, never blank
});

test("it is a modal dialog over a dimmed page, labelled by its title, with the X and Got it", () => {
  const html = dialog(change1());
  assert.match(html, /^<div class="dp-cd">/);
  assert.match(html, /<div class="dp-cd-panel" role="dialog" aria-modal="true" aria-labelledby="([^"]+)">/);
  const id = html.match(/aria-labelledby="([^"]+)"/)[1];
  assert.ok(html.includes(`<h2 id="${id}">`));
  assert.ok(html.includes('aria-label="Close"') && html.includes(">Got it</button>"));
});

test("one line per change, grouped by commitment: a green closed line with its muted detail, an amber still-open line; no headline sentence repeating the first item", () => {
  const html = dialog(change1());
  assert.deepEqual([...html.matchAll(/<h3 class="dp-change-title">([^<]*)<\/h3>/g)].map((m) => m[1]), [SPEC]); // only the commitment that changed
  assert.ok(html.includes('<strong>Approval found</strong><span class="dp-change-closed"> · closed by documents</span>'));
  assert.ok(html.includes('<p class="dp-change-by">Closed by Internal approvals note, version 2 · checked 11 Nov 2026</p>')); // the detail line, kept (smaller and muted in CSS)
  assert.ok(html.includes('<strong>Not in the contract</strong><span class="dp-change-still"> · still open</span>'));
  assert.ok(!html.includes("dp-change-result")); // no headline: "Approval found · the contract gap on this commitment is still open."
  assert.equal(html.split("Approval found").length - 1, 1);
  assert.ok(html.includes("2 commitments still need attention."));
  assert.match(read("DealPage.css"), /\.dp-change-row p\.dp-change-by \{ font-size: 11\.5px; color: var\(--muted\); \}/);
});

test("a new gap carries the New tag; confirmed and reopened read as before", () => {
  const before = reg([LANG, [iss(1, "Contract says something different", "Resolved")]], [PHONE, [iss(2, "Missing from contract", "Resolved")]]);
  const after = reg([LANG, [iss(1, "Contract says something different", "Resolved", { signed_check: { status: "confirmed" } }), iss(3, "Missing from contract", "Needs action")]],
    [PHONE, [iss(2, "Missing from contract", "Needs action", { signed_check: { status: "not_found", reason: "Not found in the signed contract." } })]]);
  const html = dialog({ ...whatChanged(before, after), title: "Rechecked after adding Signed contract (20 Oct)", acted: null, modelCalls: 0, openPromises: 2 });
  assert.ok(html.includes('<strong>Contract wording matches</strong><span class="dp-change-closed"> · confirmed in the signed contract</span>'));
  assert.ok(html.includes("<strong>Contract wording missing from the signed contract</strong>") && html.includes("Reopened"));
  assert.match(html, /<strong>Not in the contract<\/strong><span class="dp-chip dp-chip-amber"><span class="dp-dot"><\/span>New<\/span>/);
});

test("with nothing changed the single line says so (the headline is only for an empty result); the model line and Got it sit at the bottom", () => {
  const same = whatChanged(reg([LANG, [iss(1, "Missing from contract", "Needs action")]]), reg([LANG, [iss(1, "Missing from contract", "Needs action")]]));
  const html = dialog({ ...same, title: "Rechecked after adding Draft SOW v2 (19 Oct)", acted: null, modelCalls: 0, openPromises: 1 });
  assert.equal(html.split("Nothing closed and nothing new").length - 1, 1);
  assert.ok(html.includes("No model call was needed: code checked every finding again."));
  assert.ok(html.indexOf("dp-cd-foot") > html.indexOf("Nothing closed") && html.indexOf("No model call was needed") > html.indexOf("dp-cd-foot")); // in the footer
  assert.ok(dialog({ ...change1(), modelCalls: 1 }).includes("The model read the new document; code checked every finding again."));
});

test("Escape, the X and a click on the dimmed page close it; only Got it highlights the changed rows", () => {
  const src = read("DealPage.jsx");
  const body = src.slice(src.indexOf("export function ChangeDialog"), src.indexOf("function Modal("));
  assert.match(body, /e\.key === "Escape" && onClose\(\)/);
  assert.match(body, /<div className="dp-cd" onClick=\{onClose\}>/);
  assert.match(body, /onClick=\{\(e\) => e\.stopPropagation\(\)\}/); // a click inside the panel does not close it
  assert.match(body, /<button type="button" className="dp-x" onClick=\{onClose\} aria-label="Close">/);
  assert.match(body, /ref=\{gotIt\} onClick=\{onGotIt \?\? onClose\}>Got it</);
  assert.match(body, /gotIt\.current\?\.focus\(\)/); assert.match(body, /before\?\.focus\?\.\(\)/); // focus in, and back where it was
});

test("'Got it' highlights the rows that changed for about two seconds and scrolls to the first; no inline card is left on the page", () => {
  assert.deepEqual(changedPromises(afterSample1(), titleOf, SPEC), [SPEC]); // the phone row did not change: not highlighted
  const both = whatChanged(reg([SPEC, [iss(10, "No approval recorded", "Needs action")]], [LANG, [iss(1, "Contract says something different", "Needs action")]]),
    reg([SPEC, [iss(10, "No approval recorded", "Resolved")]], [LANG, [iss(1, "Contract says something different", "Resolved")]]));
  assert.deepEqual(changedPromises(both, titleOf, null).sort(), [LANG, SPEC].sort());
  const page = read("DealPage.jsx");
  assert.match(page, /setFlash\(\{ row: null, handover: false, rows: ids \}\);/);
  assert.match(page, /setTimeout\(\(\) => setFlash\(\{ row: null, handover: false, rows: \[\] \}\), 2200\);/);
  assert.match(page, /querySelectorAll\("#dp-commitments \.dp-plist > li"\)\[first\]\?\.scrollIntoView\(\{ behavior: "smooth", block: "center" \}\)/);
  assert.match(page, /flash=\{flash\.row === c\.id \|\| flash\.rows\.includes\(c\.id\)\}/);
  assert.match(page, /\{change && <ChangeDialog change=\{change\} titleOf=\{titleOfChange\} onClose=\{closeChange\} onGotIt=\{gotIt\} \/>\}/);
  assert.ok(!page.includes("<ChangePanel") && !page.includes('className="dp-card dp-change"') && !read("DealPage.css").includes(".dp-change {"));
  // a recheck opens the dialog; it no longer scrolls the page to the top for a card that is not there
  const docDone = page.slice(page.indexOf("const docDone"), page.indexOf("const closeChange"));
  assert.ok(docDone.includes("setChange({ ...whatChanged(reg, after), doc: label, title,") && !docDone.includes("scrollTo"));
});

test("the dialog is centred on desktop and a full-width bottom sheet below 640px, scrollable, with Got it always visible, above the demo bar", () => {
  const css = read("DealPage.css");
  assert.match(css, /\.dp-cd \{ position: fixed; inset: 0; z-index: 80; display: flex; align-items: center; justify-content: center;/);
  assert.match(css, /\.dp-cd-panel \{ display: flex; flex-direction: column; width: min\(560px, 100%\); max-height: min\(85vh, 720px\);/);
  assert.match(css, /\.dp-cd-body \{ flex: 1; min-height: 0; overflow-y: auto;/); // the body scrolls
  assert.match(css, /\.dp-cd-foot \{ flex: none;/); // the footer (Got it) does not
  const narrow = css.slice(css.indexOf("@media (max-width: 639px) {\n  .dp-cd {"));
  assert.match(narrow, /\.dp-cd \{ align-items: flex-end; padding: 0; \}/);
  assert.match(narrow, /\.dp-cd-panel \{ width: 100%; max-height: 88vh; border-radius: 16px 16px 0 0; \}/);
  assert.match(narrow, /\.dp-cd-foot \.dp-btn \{ width: 100%; \}/);
  assert.match(read("App.css"), /\.demo-bar \{ position: sticky; top: 0; z-index: 70;/); // 70 < 80: the dialog covers the bar too
  assert.match(css, /@media print \{ \.dp-cd \{ display: none; \} \}/);
});

test("the tour outline, the highlighted button and the row flash use the brand indigo, not amber", () => {
  const dp = read("DealPage.css"), app = read("App.css");
  assert.match(dp, /outline: 3px solid var\(--accent\); outline-offset: -3px; box-shadow: 0 0 0 6px var\(--tint-line\);/);
  assert.match(dp, /\.dr-actions \.dp-btn\.is-guided \{ box-shadow: 0 0 0 2px var\(--card\), 0 0 0 5px var\(--accent\);/);
  assert.match(app, /@keyframes demo-flash \{ 0%, 55% \{ background: var\(--tint, #eef2ff\); box-shadow: 0 0 0 2px var\(--accent, #4f46e5\); \}/);
  for (const block of [dp.slice(dp.indexOf("The demo bar's \"Get the picture\" tour")), app.slice(app.indexOf("@keyframes demo-flash"), app.indexOf("@keyframes demo-flash") + 260)]) {
    assert.ok(!/f59e0b|fde68a|245, 158, 11/i.test(block), "no amber in the highlights");
  }
  assert.match(dp, /--accent: #4f46e5;/); // the primary button's colour
});

test("nothing else leans on the inline card: the guide's Do step flow, the bar and the tour do not mention it", () => {
  for (const f of ["DemoUI.jsx", "demo.js"]) assert.ok(!/ChangePanel|What changed|dp-change\b/.test(read(f)), f);
  const run = (f) => fs.readFileSync(fileURLToPath(new URL(`../../docs/${f}`, import.meta.url)), "utf8");
  for (const f of ["DEMO_SCRIPT_2026-10-21_noma.md", "DEMO_SCRIPT_2026-10-20_alder.md", "DEMO_SCRIPT_2026-10-20_noma.md"]) {
    assert.ok(!/Point at What changed/.test(run(f)), f);
    assert.ok(/Point at the result dialog/.test(run(f)), f);
  }
});
