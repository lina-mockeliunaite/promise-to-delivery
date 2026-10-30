// The commitments card's header takes the Deal brief card's pattern (31 Oct): an eyebrow above the heading, the chip beside the heading.
// CardHead is rendered from the bundled Drawer.jsx; the two pages' use of it and the CSS are pinned by source guards (the locked record loads its
// data in an effect, so it cannot be rendered statically).
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
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("Drawer.jsx", SRC)), formats: ["es"], fileName: "drawer" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/section-head-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "drawer.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CardHead } = await import(file);

test("CardHead: the eyebrow above the heading, the chip beside the heading", () => {
  const html = renderToStaticMarkup(createElement(CardHead, { eyebrow: "Commitments", title: "What the customer was promised" }, createElement("span", { className: "dp-chip" }, "3 need attention")));
  assert.equal(html, '<div class="dp-sec-head"><span class="dp-eyebrow">Commitments</span><div class="dp-sec-title"><h2>What the customer was promised</h2><span class="dp-chip">3 need attention</span></div></div>');
});

test("the live page says COMMITMENTS / What the customer was promised and the locked record COMMITMENTS / At handover; the old single headings are gone", () => {
  const live = read("DealPage.jsx"), locked = read("FrozenRecord.jsx");
  assert.match(live, /<CardHead eyebrow="Commitments" title="What the customer was promised">\s*<AttentionChip /);
  assert.match(locked, /<CardHead eyebrow="Commitments" title="At handover">\s*<span className=\{`dp-chip \$\{counts\.open/);
  assert.ok(!live.includes("<h2>Commitments needing attention</h2>") && !live.includes("Needing attention\">") && !locked.includes("<h2>Commitments at handover</h2>"));
  // the "N need attention" chip and the coverage line are as before, in the same place under the heading
  assert.match(live, /<\/CardHead>\s*\{coverageLine\(reg\.check_coverage\?\.rejected\) && <p className="dp-coverage">/);
  assert.match(locked, /<\/CardHead>\s*\{coverageLine\(s\.check_coverage\?\.rejected\) && <p className="dp-coverage">/);
  // the brief card keeps its own header markup, and the eyebrow is the same class
  assert.match(read("BriefCard.jsx"), /<span className="dp-eyebrow">Deal brief<\/span>\s*<h2>What we're delivering<\/h2>/);
});

test("the heading is 17px against 14px row titles, shared with the brief card; room under the header is a little more than between rows", () => {
  const css = read("DealPage.css");
  assert.match(css, /\.dp-brief-card \.dp-sec-head h2, \.dp-promises \.dp-sec-head h2 \{ font-size: 17px; \}/);
  assert.match(css, /\.dp-prow-title \{ font-size: 14px; font-weight: 600;/);
  assert.match(css, /\.dp-promises \.dp-sec-head \{ display: block; \}/);
  assert.match(css, /\.dp-promises \.dp-plist \{ margin-top: 8px; \}/); // live rows are 14px of padding apart
  assert.match(css, /\.fr \.dp-plist \{ margin-top: 4px; \}/); // locked rows are 9px apart, and print follows
  assert.match(css, /\.dp-eyebrow \{ display: block; font-size: 11px; font-weight: 600; text-transform: uppercase;/);
});
