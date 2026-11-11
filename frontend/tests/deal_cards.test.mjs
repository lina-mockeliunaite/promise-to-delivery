// Deal list below 640px (11 Nov): stacked cards in place of the table, and the public list's fixed order. Run with: node --test frontend/tests/
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
const dir = fileURLToPath(new URL("../node_modules/.cache/deal-cards-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { default as Deals } from ${abs("Deals.jsx")};\nexport * from ${abs("demo.js")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const m = await import(file);

const deal = (slug, name, o = {}) => ({ deal: slug, name, scope: `${name} scope line`, owner: "Sam", stage: "contracting", stage_label: "Contracting", open_gaps: 3,
  addressed_by_note: 0, in_handover: true, handover_complete: false, last_updated: "2026-11-10T10:00:00Z", kind: "development", vendor: "elva", vendor_name: "Elva", ...o });
const DEALS = [deal("noma_journeys", "Noma Journeys"), deal("alder_bank", "Alder Bank", { open_gaps: 0 })];
const render = (demo) => renderToStaticMarkup(createElement(m.DemoContext.Provider, { value: demo }, createElement(m.Deals, { deals: DEALS, onOpen() {}, onCreated() {}, onAbout() {} })));
const OFF = { public: false, banner: null, note_max: null }, ON = { public: true, banner: "b", note_max: 500 };
const cards = (html) => html.slice(html.indexOf('<ul class="dl-cards"'), html.indexOf("</ul>") + 5);

test("each deal is a stacked card: name, short description, stage, attention count, and the whole card is one button", () => {
  for (const demo of [OFF, ON]) {
    const html = cards(render(demo));
    const items = html.split("<li>").slice(1);
    assert.equal(items.length, 2);
    for (const name of ["Noma Journeys", "Alder Bank"]) {
      const li = items.find((x) => x.includes(`>${name}<`));
      assert.ok(li.startsWith(`<button type="button" class="dl-card `), "the card is a button: tapping anywhere on it opens the deal");
      assert.ok(li.includes(`${name} scope line`) && li.includes("Contracting"));
      assert.ok(li.includes(name === "Noma Journeys" ? "3 commitments need attention" : "Nothing needs attention"));
    }
    assert.equal((html.match(/<button/g) || []).length, 2); // one button per deal, none nested inside
  }
});

test("the cards are for narrow screens only: hidden by default, shown (and the table hidden) at 639px and below; desktop unchanged", () => {
  const css = read("Deals.css");
  assert.match(css, /\.dl-cards \{ display: none;/);
  const narrow = css.slice(css.indexOf("/* Narrow screens (11 Nov)"));
  assert.match(narrow, /@media \(max-width: 639px\) \{[\s\S]*?\.dl-scroll \{ display: none; \}[\s\S]*?\.dl-cards \{ display: block; \}/);
  assert.match(css, /\.dl-table \{ width: 100%; border-collapse: collapse;/); // the table's own rules are as they were
  assert.ok(render(OFF).includes('<table class="dl-table">'));
});

test("the public list shows the deals in the server's fixed order, with no tabs, search or sort; local mode still sorts", () => {
  const html = render(ON);
  assert.ok(html.indexOf("Noma Journeys") < html.indexOf("Alder Bank"));
  assert.ok(!html.includes("dl-tabs") && !html.includes("dl-search") && !html.includes("dl-sort"));
  assert.match(read("Deals.jsx"), /demo\.public \? deals : visibleDeals\(deals, \{ filter, query, sort \}\)/);
  const local = render(OFF);
  assert.ok(local.includes("dl-tabs") && local.includes("dl-sort"));
});
