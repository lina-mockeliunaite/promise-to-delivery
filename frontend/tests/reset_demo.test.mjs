// "Reset demo" (10 Nov). Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RESET_IDLE, RESET_QUESTION, resetNext, runReset } from "../src/deals.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry: fileURLToPath(new URL("ResetDemo.jsx", SRC)), formats: ["es"], fileName: "reset" },
    rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const dir = fileURLToPath(new URL("../node_modules/.cache/reset-demo-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const file = path.join(dir, "reset.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { default: ResetDemo } = await import(file);

const nav = () => { const log = []; return { log, setHash: (h) => log.push(["hash", h]), reload: () => log.push(["reload"]) }; };

test("at rest the footer shows only a grey 'Reset demo' link; no confirm text", () => {
  const html = renderToStaticMarkup(createElement(ResetDemo));
  assert.match(html, /<button[^>]*class="dl-about dl-reset-link"[^>]*>Reset demo<\/button>/);
  assert.ok(!html.includes("Restore all sample deals"));
});

test("the confirm appears in the page with the exact words, Reset and Cancel; no browser dialog is used", () => {
  const html = renderToStaticMarkup(createElement(ResetDemo, { initial: { step: "confirming", message: "" } }));
  assert.equal(RESET_QUESTION, "Restore all sample deals to their starting point? Anything you changed is kept in a backup file.");
  assert.ok(html.includes(RESET_QUESTION));
  assert.match(html, />Reset<\/button>/);
  assert.match(html, />Cancel<\/button>/);
  const src = read("ResetDemo.jsx") + read("deals.js").slice(read("deals.js").indexOf('"Reset demo"'));
  assert.ok(!/window\.confirm|\balert\(|\bconfirm\(/.test(src));
  assert.deepEqual(resetNext(RESET_IDLE, "ask"), { step: "confirming", message: "" });
});

test("Cancel closes the confirm and nothing else happens: no call, no navigation", () => {
  const confirming = resetNext(RESET_IDLE, "ask");
  assert.deepEqual(resetNext(confirming, "cancel"), RESET_IDLE);
  assert.deepEqual(resetNext(RESET_IDLE, "cancel"), RESET_IDLE); // a stray cancel changes nothing
  // the Cancel button only dispatches "cancel"; the endpoint is called from the Reset handler alone
  assert.equal((read("ResetDemo.jsx").match(/runReset\(/g) || []).length, 1);
  assert.match(read("ResetDemo.jsx"), /onClick=\{\(\) => setState\(\(s\) => resetNext\(s, "cancel"\)\)\}/);
});

test("Reset calls the endpoint once, then sets #welcome and reloads the page", async () => {
  const n = nav();
  let calls = 0;
  const r = await runReset(async () => { calls += 1; return { deals_restored: 5, model_calls: 0 }; }, n);
  assert.equal(calls, 1);
  assert.deepEqual(r, { ok: true, message: "" });
  assert.deepEqual(n.log, [["hash", "#welcome"], ["reload"]]); // hash first, then the full reload
});

test("a failed reset shows the server's message, keeps the confirm open and neither navigates nor reloads", async () => {
  const n = nav();
  const r = await runReset(async () => { throw new Error("ledger.backup-x.sqlite already exists; wait a second and run again"); }, n);
  assert.deepEqual(r, { ok: false, message: "ledger.backup-x.sqlite already exists; wait a second and run again" });
  assert.deepEqual(n.log, []);
  const busy = resetNext(resetNext(RESET_IDLE, "ask"), "run");
  assert.equal(busy.step, "busy");
  const failed = resetNext(busy, "fail", r.message);
  assert.deepEqual(failed, { step: "confirming", message: r.message });
  const html = renderToStaticMarkup(createElement(ResetDemo, { initial: failed }));
  assert.match(html, /role="alert"[^>]*>ledger\.backup-x\.sqlite already exists/);
});

test("the endpoint is a guarded POST and the footer link is in the page footer", () => {
  assert.match(read("api.js"), /export const resetDemo = \(\) => postJson\("\/api\/demo\/reset"\)/);
  assert.match(read("Deals.jsx"), /<footer className="dl-pagefoot">[\s\S]*\{!demo\.public && <ResetDemo \/>\}<\/footer>/); // 11 Nov: public mode has Reset demo in the bar instead
});

test("the name ('Recording as', ptd.name in localStorage) is never touched by the reset path", () => {
  const src = read("ResetDemo.jsx") + read("deals.js").slice(read("deals.js").indexOf('"Reset demo"'));
  assert.ok(!/ptd\.name|removeItem|localStorage\.clear|sessionStorage/.test(src));
});
