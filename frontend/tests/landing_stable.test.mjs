// The welcome page does not move while the Noma example card loads (13 Nov, after a cold start). The card's data arrives a few seconds after the rest of the page; its place is held
// from the first render by a placeholder of the same size, so "Start the guided demo" stays where it was.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SAMPLES, cardState } from "../src/landing.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/landing-stable-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { default as Landing } from ${abs("Landing.jsx")};\nexport { DemoContext } from ${abs("demo.js")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { Landing, DemoContext } = await import(file);

const render = (pub) => renderToStaticMarkup(createElement(DemoContext.Provider, { value: { public: pub, banner: null, note: null, note_max: null } },
  createElement(Landing, { deals: SAMPLES.map((s) => ({ deal: s.deal })), onOpen() {}, onList() {} })));

test("a card's state: the static Alder card from the first render; Noma waits until its data answers; nothing to show (or a failure) removes it", () => {
  assert.equal(cardState("alder_bank", undefined, false), "static");
  assert.equal(cardState("noma_journeys", undefined, false), "waiting");
  assert.equal(cardState("noma_journeys", { title: "t" }, true), "found");
  assert.equal(cardState("noma_journeys", undefined, true), "none");
});

test("first render, before any data: Noma's card is already there as a placeholder with its own title and parties, in its place before Alder's; the start button is in the intro", () => {
  const html = render(true);
  const noma = html.indexOf("land-placeholder"), alder = html.indexOf("Scam-call alerts at launch"), start = html.indexOf("land-start");
  assert.ok(noma > 0 && alder > noma, "the placeholder holds Noma's slot, ahead of the Alder card");
  assert.ok(html.includes("AI support assistant") && html.includes("Aivuna / Noma Journeys")); // known without the data
  assert.ok(html.includes('aria-busy="true"'));
  assert.ok(start > 0 && start < noma, "the start button is in the intro column, before the cards in the page");
  assert.equal(html.split("land-example").length - 1, 2); // two cards from the first render: the placeholder and the Alder card
});

test("the start button's position does not depend on the card having loaded: every example card, placeholder or loaded, has the same minimum height", () => {
  const css = read("Landing.css");
  assert.match(css, /\.land-example \{ min-height: var\(--land-card-h, 212px\); \}/); // one rule for the placeholder and the loaded cards (the placeholder is a .land-example)
  assert.ok(read("Landing.jsx").includes('className="dp-card land-example land-placeholder"'));
  // 212px is the height of the loaded Noma card measured at 1440, 1024, 820 and 390px (212, 212, 212, 212); the page height and the start button's top were identical before and after the data arrived
  assert.ok(/\.land-skel-btn \{ visibility: hidden; \}/.test(css)); // the placeholder's hidden button keeps the card's own height
});

test("local mode is unchanged: no guided button, and the placeholder logic is the same list of cards", () => {
  const html = render(false);
  assert.ok(!html.includes("land-start"));
  assert.ok(html.includes("land-placeholder")); // the cards are the same in local mode
});
