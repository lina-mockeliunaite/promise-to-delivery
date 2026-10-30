// Batch A (31 Oct): the "What changed" card says what a signed contract confirmed or reopened, leads with the commitment acted on and groups the rest
// per commitment, names the document by its plain name and date, and the add form's "Dated" starts from the file's own date.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { changeDocLabel, changeView, datePrefill, statedDate, whatChanged } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const scenario = (f) => fs.readFileSync(fileURLToPath(new URL(`../../data/scenarios/${f}`, import.meta.url)), "utf8");
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("DealPage.jsx", SRC)), formats: ["es"], fileName: "dealpage" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/change-card-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "dealpage.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { ChangePanel } = await import(file);

const LANG = "Support in 12 languages at launch", PHONE = "AI answers customers' phone calls at launch", SPEC = "Dedicated launch specialist";
const iss = (id, finding, state, extra = {}) => ({ id, finding, state, ...extra });
const reg = (...cs) => ({ commitments: cs.map(([name, issues]) => ({ name, issues })) });
const titleOf = (n) => n;

// --- 1: the signed contract's confirmations and reopenings ---------------------------------------------------------------
test("a signed contract that confirms an earlier fix says so, once, and is not 'nothing closed'", () => {
  const before = reg([LANG, [iss(1, "Contract says something different", "Resolved")]]);
  const after = reg([LANG, [iss(1, "Contract says something different", "Resolved", { signed_check: { status: "confirmed" } })]]);
  const c = whatChanged(before, after);
  assert.deepEqual(c.confirmed, [{ promise: LANG, finding: "Contract says something different" }]);
  assert.equal(c.opened.length, 0);
  const v = changeView(c, titleOf, null);
  assert.equal(v.headline, `1 earlier fix confirmed in the signed contract: ${LANG}.`);
  assert.ok(!v.headline.includes("Nothing closed"));
  const html = renderToStaticMarkup(createElement(ChangePanel, { change: { ...c, doc: "Signed contract, 20 Oct", acted: null, modelCalls: 0 }, titleOf, onClose() {} }));
  assert.equal(html.split("earlier fix confirmed in the signed contract").length - 1, 1); // heading line only; the box says "Confirmed in the signed contract"
  assert.ok(html.includes("Confirmed in the signed contract") && !html.includes("Nothing closed"));
});

test("a fix the signed contract does not contain is reopened, not a new gap, and its reason is shown", () => {
  const before = reg([LANG, [iss(2, "Missing from contract", "Resolved")]]);
  const after = reg([LANG, [iss(2, "Missing from contract", "Needs action", { signed_check: { status: "not_found", reason: "The fix in Draft SOW, version 2 was not found in the signed contract." } })]]);
  const c = whatChanged(before, after);
  assert.equal(c.opened.length, 0);
  assert.equal(c.reopened.length, 1);
  const v = changeView(c, titleOf, null);
  assert.equal(v.headline, `1 earlier fix not found in the signed contract, reopened: ${LANG}.`);
  assert.ok(!/new gap/.test(v.headline));
  const html = renderToStaticMarkup(createElement(ChangePanel, { change: { ...c, doc: "Signed contract, 20 Oct", acted: null, modelCalls: 0 }, titleOf, onClose() {} }));
  assert.ok(html.includes("The fix in Draft SOW, version 2 was not found in the signed contract.") && html.includes("Reopened"));
});

test("nothing changed: the sentence appears once, in the heading line only", () => {
  const c = whatChanged(reg([LANG, [iss(1, "Missing from contract", "Needs action")]]), reg([LANG, [iss(1, "Missing from contract", "Needs action")]]));
  const html = renderToStaticMarkup(createElement(ChangePanel, { change: { ...c, doc: "Draft SOW, new version (v2, 19 Oct)", acted: null, modelCalls: 0 }, titleOf, onClose() {} }));
  assert.equal(html.split("Nothing closed and nothing new").length - 1, 1);
});

// --- 4: the commitment acted on leads, the rest is one line, the boxes are grouped -----------------------------------------
const revised = () => {
  const before = reg([LANG, [iss(1, "Contract says something different", "Needs action")]],
    [PHONE, [iss(2, "Not offered", "Needs action"), iss(3, "Contract says something different", "Needs action")]]);
  const after = reg([LANG, [iss(1, "Contract says something different", "Resolved", { reason: "Closed: the contract clause behind this conflict is no longer in Draft contract." })]],
    [PHONE, [iss(2, "Not offered", "Needs action"), iss(3, "Contract says something different", "Needs action"), iss(4, "Missing from contract", "Needs action")]]);
  return whatChanged(before, after);
};
test("the headline is the change on the commitment the document was added from; the others are one line naming them", () => {
  const v = changeView(revised(), titleOf, LANG);
  assert.equal(v.headline, "Contract wording now matches the promise.");
  assert.ok(!/not-offered|phone/i.test(v.headline)); // nothing from the other commitment in the headline
  assert.equal(v.elsewhere, `Elsewhere: ${PHONE}: 1 new gap, not in the contract.`); // its unchanged gaps (not offered, contract differs) are in the list below, not here
});

test("the detail boxes are grouped per commitment, the acted-on one first, with no commitment title repeated inside a box", () => {
  const html = renderToStaticMarkup(createElement(ChangePanel, { change: { ...revised(), doc: "Draft contract, new version (v2, 19 Oct)", acted: LANG, modelCalls: 0 }, titleOf, onClose() {} }));
  const titles = [...html.matchAll(/<h3 class="dp-change-title">([^<]*)<\/h3>/g)].map((m) => m[1].replace(/&#x27;/g, "'"));
  assert.deepEqual(titles, [LANG, PHONE]);
  assert.ok(html.indexOf("Closed by documents") < html.indexOf("New"));
  assert.ok(!html.includes("Still needs attention")); // the phone commitment's unchanged gaps are not repeated
  assert.equal(html.split("<strong>" + PHONE).length - 1, 0);
});

test("acted on with nothing changed there: it says so, then the rest", () => {
  const v = changeView(revised(), titleOf, SPEC);
  assert.equal(v.headline, `Nothing changed on ${SPEC}.`);
});

// --- 2: documents are named by their plain name and date --------------------------------------------------------------------
test("the card names the added document by plain name and date, never by file name", () => {
  assert.equal(changeDocLabel({ name: "Signed contract", existing: false, date: "2026-10-20" }), "Signed contract, 20 Oct");
  assert.equal(changeDocLabel({ name: "Draft contract", existing: true, version: 2, date: "2026-10-19" }), "Draft contract, new version (v2, 19 Oct)");
  const jsx = read("DealPage.jsx");
  assert.match(jsx, /onDone\(r\.review, \{ name: existing \? existing\.name : \(labels\[form\.doc_type\] \?\? form\.file\.name\)/);
  assert.ok(!/onDone\(r\.review, [^{]*form\.file\.name\)/.test(jsx));
});

// --- 3: the add form's Dated starts from the file's own date ----------------------------------------------------------------
test("the signed contract states 20 October 2026; a file with no date falls back to today; the date can still be typed over", () => {
  assert.equal(statedDate(scenario("NJ-09_signed_contract.md")), "2026-10-20");
  assert.equal(datePrefill(scenario("NJ-09_signed_contract.md"), "2026-10-31"), "2026-10-20");
  assert.equal(statedDate(scenario("NJ-05_v2_named_exception.md")), "2026-10-18");
  assert.equal(statedDate("# Notes\n\nNo date is stated here. Date: 3 March 2026 in the middle of a sentence.\n"), null);
  assert.equal(datePrefill("# Notes\n\nnothing dated\n", "2026-10-31"), "2026-10-31");
  assert.equal(statedDate("Date: 2026-10-20\nbody"), "2026-10-20");
  assert.equal(statedDate("Date: 31 Febtember 2026\n"), null);
  const jsx = read("DealPage.jsx");
  assert.match(jsx, /setDateEdited\(true\)/); // a typed date wins over a later file pick
  assert.match(jsx, /if \(!dateEdited\) setForm\(\(f\) => \(\{ \.\.\.f, doc_date: datePrefill\(t, today\) \}\)\)/);
});

// --- 5: wording ---------------------------------------------------------------------------------------------------------------
test("a row with no stated term says 'Promised in', and the locked record's print uses the same line", () => {
  assert.match(read("dealpage.js"), /text: `Promised in \$\{source\}`/);
  assert.ok(!read("dealpage.js").includes("Customer was told in ${source}"));
});

// --- What the card shows: only what the added document changed (31 Oct) ---------------------------------------------------------
const SPEC_T = "Dedicated launch specialist for the first 30 days, at no extra charge";
const nj05 = () => whatChanged(
  reg([SPEC_T, [iss(10, "No approval recorded", "Needs action"), iss(11, "Missing from contract", "Needs action")]], [PHONE, [iss(2, "Not offered", "Needs action")]]),
  reg([SPEC_T, [iss(10, "No approval recorded", "Resolved"), iss(11, "Missing from contract", "Needs action")]], [PHONE, [iss(2, "Not offered", "Needs action")]]));

test("a partial fix on the commitment acted on keeps its still-open item: approval found, the contract gap still open", () => {
  const v = changeView(nj05(), titleOf, SPEC_T);
  assert.equal(v.headline, "Approval found · the contract gap on this commitment is still open.");
  assert.deepEqual(v.groups.map((g) => g.promise), [SPEC_T]); // the phone commitment did not change: not on the card
  assert.equal(v.groups[0].stillOpen.length, 1);
  assert.equal(v.elsewhere, "");
});

test("added from the sidebar: still-open items show on the commitment the document closed, and on no other", () => {
  const v = changeView(nj05(), titleOf, null);
  assert.equal(v.headline, "Approval found · the contract gap on this commitment is still open.");
  assert.deepEqual(v.groups.map((g) => g.promise), [SPEC_T]);
});

test("a commitment the person did not act on keeps no still-open item, even with a new gap on it; a confirmation shows no still-open boxes", () => {
  const v = changeView(revised(), titleOf, LANG);
  const phone = v.groups.find((g) => g.promise === PHONE);
  assert.equal(phone.stillOpen.length, 0);
  assert.equal(phone.opened.length, 1);
  const before = reg([LANG, [iss(1, "Contract says something different", "Resolved")]], [PHONE, [iss(2, "Not offered", "Needs action")]]);
  const after = reg([LANG, [iss(1, "Contract says something different", "Resolved", { signed_check: { status: "confirmed" } })]], [PHONE, [iss(2, "Not offered", "Needs action")]]);
  const sc = changeView(whatChanged(before, after), titleOf, null);
  assert.deepEqual(sc.groups.map((g) => g.promise), [LANG]);
  assert.equal(sc.headline, `1 earlier fix confirmed in the signed contract: ${LANG}.`);
});

test("the footer count and the model line are unchanged by what the card hides", () => {
  const html = renderToStaticMarkup(createElement(ChangePanel, { change: { ...revised(), openPromises: 2, doc: "Draft contract, new version (v2, 19 Oct)", acted: LANG, modelCalls: 0 }, titleOf, onClose() {} }));
  assert.ok(html.includes("2 commitments still need attention.") && html.includes("View commitments below") && html.includes(">Done<"));
  assert.ok(html.includes("No model call was needed: code checked every finding again."));
});
