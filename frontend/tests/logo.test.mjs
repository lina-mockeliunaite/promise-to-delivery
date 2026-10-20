// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { LOGO_ASPECT, TOP_BAR_LOGO_HEIGHT, logoSize } from "../src/logo.js";

const brand = (name) => fs.readFileSync(new URL(`../public/brand/${name}`, import.meta.url), "utf8");
const html = fs.readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("the logo image reserves its space from the wordmark's own viewBox, so nothing shifts when it loads", () => {
  const [, w, h] = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(brand("wordmark.svg")).map(Number);
  assert.ok(Math.abs(LOGO_ASPECT - w / h) < 1e-6);
  assert.deepEqual(logoSize(21), { height: 21, width: 101.8 });
  const big = logoSize(36);
  assert.equal(big.height, 36);
  assert.ok(Math.abs(big.width / big.height - LOGO_ASPECT) < 0.01);
});

test("the top-bar logo is sized so its wordmark keeps the cap height of the text it replaced", () => {
  const capNow = 0.727 * 15; // Inter's cap height at the old 15px wordmark text
  const capLogo = (33.6 / 64) * TOP_BAR_LOGO_HEIGHT; // the wordmark's caps span 33.6 of its 64 units
  assert.ok(Math.abs(capNow - capLogo) < 0.3, `${capNow} vs ${capLogo}`);
  assert.ok(TOP_BAR_LOGO_HEIGHT < 48); // inside the fixed 48px top bar
});

test("the three brand files are the approved ones: indigo mark in three pieces, ink wordmark, no live text", () => {
  const count = (s, re) => (s.match(re) ?? []).length;
  for (const f of ["mark.svg", "mark-small.svg"]) {
    const svg = brand(f);
    assert.equal(count(svg, /<path /g), 3, f);
    assert.ok(svg.includes('fill="#4f46e5"'), f);
    assert.ok(!/<text/.test(svg), f);
  }
  const word = brand("wordmark.svg");
  assert.equal(count(word, /<path /g), 3 + 9); // the mark's three pieces and the nine letters of "Dealshape"
  assert.ok(word.includes('fill="#4f46e5"') && word.includes('fill="#0f172a"'));
  assert.ok(!/<text/.test(word)); // outlines, so it looks the same through <img>, where web fonts do not load
  assert.match(word, /prefers-color-scheme: dark/); // the text takes the app's dark ink so it does not vanish on the dark canvas
});

test("the favicon is the small mark", () => {
  assert.match(html, /<link rel="icon" type="image\/svg\+xml" href="\/brand\/mark-small\.svg"/);
});
