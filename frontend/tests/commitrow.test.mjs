// The commitment row on the live deal page: every status shows its chip (the 30 Oct dot-only open row was reverted on 31 Oct), and the row's
// spacing and text weights (31 Oct). DealPage.jsx is bundled with Vite and CommitRow rendered to static markup,
// on a row from the saved Noma register. FrozenRecord has its own row and keeps the chip for every status (source guard).
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
const REG = JSON.parse(fs.readFileSync(new URL("./fixtures/noma_register.json", import.meta.url), "utf8"));

const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("DealPage.jsx", SRC)), formats: ["es"], fileName: "dealpage" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
// Written under node_modules/.cache so the bundle can resolve react; nothing lands in src/ or tests/.
const dir = fileURLToPath(new URL("../node_modules/.cache/commitrow-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "dealpage.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitRow } = await import(file);
const c = REG.commitments.find((x) => x.issues.some((i) => i.state !== "Resolved"));
const row = (status) => renderToStaticMarkup(createElement(CommitRow, { c, status, active: false, onOpen() {} }));

test("an open row shows the amber Needs attention chip, exactly like the other statuses: no dot-only marker, no hidden text", () => {
  const html = row("open");
  assert.match(html, /<span class="dp-chip dp-chip-amber" title="[^"]*"><span class="dp-dot "><\/span>Needs attention<\/span>/);
  assert.ok(!html.includes("dp-rowdot") && !html.includes("dp-sr"));
  assert.equal(html.split("Needs attention").length - 1, 1);
  assert.ok(html.indexOf("dp-chip") < html.indexOf("dp-chevron")); // the chip sits before the chevron
});

test("a noted row keeps its outlined chip and grey dot; a closed row keeps its green chip", () => {
  const noted = row("noted");
  assert.match(noted, /<span class="dp-chip dp-chip-note"[^>]*><span class="dp-dot dp-dot-grey"><\/span>Addressed by note<\/span>/);
  const closed = row("closed");
  assert.match(closed, /<span class="dp-chip dp-chip-green"[^>]*><span class="dp-dot dp-dot-green"><\/span>Closed by documents<\/span>/);
  for (const html of [noted, closed]) assert.ok(!html.includes("dp-rowdot") && !html.includes("dp-sr"));
});

test("the locked record still renders a chip for every status, and the print and drawer chips are not touched", () => {
  const fr = read("FrozenRecord.jsx");
  assert.match(fr, /<span className=\{`dp-chip dp-chip-\$\{st\.tone\}`\}/);
  assert.ok(!fr.includes("dp-rowdot") && !read("DealPage.jsx").includes("dp-rowdot"));
  assert.match(read("Drawer.jsx"), /STATUS_CHIP\[chip\]/);
});

test("rows are separated by space (31 Oct): the title stays 14px, the key words are 500, the head's padding carries the separation", () => {
  const css = read("DealPage.css");
  assert.ok(!/\.dp-prow \.dp-prow-title \{[^}]*font-size/.test(css)); // no 15px override: the base 14px stands
  assert.match(css, /\.dp-prow-title \{ font-size: 14px; font-weight: 600;/);
  assert.match(css, /\.dp-prow\.is-noted \.dp-prow-title, \.dp-prow\.is-closed \.dp-prow-title \{ font-weight: 500; \}/);
  assert.match(css, /\.dp-prow \.dp-prow-line strong \{ font-weight: 500; \}/);
  assert.match(css, /\.dp-prow \.dp-titleline \{ margin-bottom: 2px; \}/);
  assert.match(css, /\.dp-prow-main \{[^}]*gap: 2px; \}/); // 2px between the lines, 4px from the title line to the first
  assert.match(css, /\.dp-prow-head \{ display: flex; align-items: center; gap: 12px; padding: 14px 20px;/);
  assert.match(css, /\.fr \.dp-prow-head \{ padding: 9px 20px; \}/);
  assert.ok(!/\.fr \.dp-prow-head \{ padding: 8px/.test(css)); // print follows the screen value (the print rule itself is pinned in dochash.test.mjs)
  assert.ok(!css.includes(".dp-rowdot"));
  // the landing cards and the drawer keep their rules
  assert.match(css, /\.dp-prow-line strong \{ color: var\(--ink\); font-weight: 600; \}/);
  assert.match(read("Landing.css"), /\.land-example \.dp-prow-title \{ font-size: 16px; \}/);
  assert.match(css, /\.dr-mismatch \.dp-prow-line \{ font-size: 13px; \}/);
  assert.ok(!read("Landing.jsx").includes("dp-prow\""));
});

test("the row markup is unchanged: the same title line, badges and lines in the same order", () => {
  const html = row("open");
  assert.match(html, /<li class="dp-prow is-open "><div class="dp-prow-head"[^>]*><span class="dp-prow-main"><span class="dp-titleline"><span class="dp-prow-title">/);
});
