// The deal brief's deliverables fold on the live deal page only (30 Oct). BriefCard.jsx is bundled with Vite (no new dependency)
// and rendered to static markup; the click itself is checked by hand in the browser. FrozenRecord is a data-loading page, so its
// part is pinned two ways: BriefCard without `collapsible` (what it renders) and a source guard on the two call sites.
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

const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("BriefCard.jsx", SRC)), formats: ["es"], fileName: "briefcard" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/briefcard-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "briefcard.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { default: BriefCard } = await import(file);
const render = (brief, props = {}) => renderToStaticMarkup(createElement(BriefCard, { brief, ...props }));

const brief = (n) => ({
  summary: "Aivuna provides an assistant.",
  deliverables: Array.from({ length: n }, (_, i) => `Deliverable ${i + 1}`),
  confirmed_by: "Liam Hart (Account Executive)", basis: "draft SOW, 12 Oct",
});

test("collapsible (the deal page): the list starts hidden behind a button that shows the real count", () => {
  const html = render(brief(5), { collapsible: true });
  assert.match(html, /<button type="button" class="dp-link-btn dp-brief-toggle" aria-expanded="false" aria-controls="([^"]+)">Show deliverables \(5\)<\/button>/);
  const id = /aria-controls="([^"]+)"/.exec(html)[1];
  assert.match(html, new RegExp(`<ul class="dp-deliverables" id="${id.replace(/[:]/g, "\\$&")}" hidden="">`)); // the button points at the list
  assert.ok(!html.includes("Hide deliverables"));
});

test("the count follows the brief, and the summary and the Confirmed by footer stay visible", () => {
  assert.match(render(brief(3), { collapsible: true }), /Show deliverables \(3\)/);
  const html = render(brief(5), { collapsible: true });
  assert.ok(html.includes("Aivuna provides an assistant."));
  assert.ok(html.includes("Confirmed by"));
});

test("a collapsible brief with no deliverables has no button and no list", () => {
  const html = render({ ...brief(0), deliverables: [] }, { collapsible: true });
  assert.ok(!html.includes("<button") && !html.includes("dp-deliverables"));
});

test("not collapsible (the locked record): the list is shown, with no button and no hidden attribute", () => {
  const html = render(brief(5));
  assert.ok(!html.includes("<button") && !html.includes(`hidden=""`) && !html.includes("aria-expanded"));
  assert.equal((html.match(/<li>/g) || []).length, 5);
});

test("only the deal page asks for the fold, and print always shows the list", () => {
  assert.match(read("DealPage.jsx"), /<BriefCard brief=\{reg\.brief\} collapsible \/>/);
  assert.match(read("FrozenRecord.jsx"), /<BriefCard brief=\{s\.brief\} \/>/);
  assert.ok(!/collapsible/.test(read("FrozenRecord.jsx")));
  assert.match(read("DealPage.css"), /@media print \{ \.dp-brief-card \.dp-deliverables\[hidden\] \{ display: block !important; \}/);
});
