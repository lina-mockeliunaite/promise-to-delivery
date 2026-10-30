// The Handover card on the live deal page is folded until the deal is Signed or a note exists (31 Oct). The open/fold rule is a pure helper;
// the header (chip + Show/Hide button) is rendered from the bundled DealPage.jsx. The card's body is pinned by source guards, as the
// locked record has its own card and is not touched.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { handoverChecklist, handoverOpen, missingForHandover } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("DealPage.jsx", SRC)), formats: ["es"], fileName: "dealpage" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/handover-card-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "dealpage.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { HandoverHead } = await import(file);

const NOTE = { note: "x", by: "Sam" };
const NONE = { sales: null, delivery: null };

test("folded at Contracting with no notes; open at Signed and at Handover", () => {
  assert.equal(handoverOpen({ isSigned: false, notes: NONE, manual: null, stage: "contracting" }), false);
  assert.equal(handoverOpen({ isSigned: true, notes: NONE, manual: null, stage: "signed" }), true);
  assert.equal(handoverOpen({ isSigned: true, notes: NONE, manual: null, stage: "handover" }), true);
  assert.equal(handoverOpen({ isSigned: false, notes: undefined, manual: null, stage: null }), false); // a deal with no documents yet
});

test("open when any note already exists, even before signing, so written content is never hidden", () => {
  assert.equal(handoverOpen({ isSigned: false, notes: { sales: NOTE, delivery: null }, manual: null, stage: "contracting" }), true);
  assert.equal(handoverOpen({ isSigned: false, notes: { sales: null, delivery: NOTE }, manual: null, stage: "contracting" }), true);
});

test("a person's choice holds for the stage it was made at and no longer once the stage changes", () => {
  const open = { stage: "contracting", open: true };
  assert.equal(handoverOpen({ isSigned: false, notes: NONE, manual: open, stage: "contracting" }), true); // opened early
  assert.equal(handoverOpen({ isSigned: false, notes: NONE, manual: open, stage: "signed" }), false); // stale choice ignored: back to the stage's default (false here, as isSigned is false)
  assert.equal(handoverOpen({ isSigned: true, notes: NONE, manual: { stage: "signed", open: false }, stage: "signed" }), false); // folded by hand at Signed
  assert.equal(handoverOpen({ isSigned: true, notes: NONE, manual: { stage: "contracting", open: false }, stage: "signed" }), true); // stage moved on: default again
  assert.equal(handoverOpen({ isSigned: false, notes: { sales: NOTE, delivery: null }, manual: { stage: "contracting", open: false }, stage: "contracting" }), false); // a person can fold it
});

test("the header: the chip stays, and the Show / Hide button has the right aria attributes and points at the body", () => {
  const props = { checklist: handoverChecklist({ isSigned: false, notes: NONE }), missing: missingForHandover({ isSigned: false, notes: NONE }), bodyId: "ho-body", onToggle() {} };
  const folded = renderToStaticMarkup(createElement(HandoverHead, { ...props, open: false }));
  assert.match(folded, /<button type="button" class="dp-link-btn dp-handover-toggle" aria-expanded="false" aria-controls="ho-body">Show<\/button>/);
  assert.ok(folded.includes("<h2>Handover</h2>") && folded.includes("0 of 3 ready"));
  const open = renderToStaticMarkup(createElement(HandoverHead, { ...props, open: true }));
  assert.match(open, /aria-expanded="true" aria-controls="ho-body">Hide<\/button>/);
});

test("the body stays in the DOM and is hidden by the attribute; print shows it in full; the locked record and the lock flow are untouched", () => {
  const jsx = read("DealPage.jsx"), css = read("DealPage.css");
  assert.match(jsx, /<div className="dp-handover-body" id=\{handoverBodyId\} hidden=\{!handoverIsOpen\}>/);
  assert.match(jsx, /const isSigned = STAGE_ORDER\.indexOf\(reg\.stage\.current\)/); // the one stage source, not computed a second way
  assert.match(css, /\.dp-handover-body\[hidden\] \{ display: none; \}/); // the body's own display would otherwise win over hidden
  assert.match(css, /\.dp-handover-toggle \{ min-height: 0; \}/);
  assert.match(css, /@media print \{ \.dp-handover \.dp-handover-body\[hidden\] \{ display: flex !important; \} \.dp-handover-toggle \{ display: none; \} \}/);
  const fr = read("FrozenRecord.jsx");
  assert.ok(!fr.includes("HandoverHead") && !fr.includes("handoverOpen") && !fr.includes("dp-handover-toggle"));
  assert.match(jsx, /Lock handover record/);
  assert.match(jsx, /disabled=\{missing\.length > 0\}/); // the lock guard is as before
});
