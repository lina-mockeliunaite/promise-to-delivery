// Signed documents state two dates (11 Nov): "Agreement dated 12 Oct · signed 20 Oct". Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { signedDatesLabel } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/signed-dates-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
fs.writeFileSync(entry, `export { DocumentList } from ${JSON.stringify(fileURLToPath(new URL("DealPage.jsx", SRC)))};\nexport { RecordBody } from ${JSON.stringify(fileURLToPath(new URL("FrozenRecord.jsx", SRC)))};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { DocumentList, RecordBody } = await import(file);

const ALDER = { source_key: "AB-09", name: "Signed contract", doc_type: "signed_contract", date: "2026-10-20", version_date: "2026-10-20", version: 1, included: true, stage: "signed",
  agreement_date: "2026-10-12", signed_on: "2026-10-20", source_version_id: 9 };
const NOMA = { ...ALDER, source_key: "NJ-09", agreement_date: "2026-10-20", signed_on: "2026-10-20" };
const EMAIL = { source_key: "AB-08", name: "Customer email", doc_type: "customer_email", date: "2026-10-14", version_date: "2026-10-14", version: 1, included: true, stage: "contracting" };

test("both dates are shown, labelled, only when they differ", () => {
  assert.equal(signedDatesLabel(ALDER), "Agreement dated 12 Oct · signed 20 Oct");
  assert.equal(signedDatesLabel(NOMA), ""); // header and signatures agree: nothing extra
  assert.equal(signedDatesLabel({ ...ALDER, agreement_date: null }), "");
  assert.equal(signedDatesLabel({ ...ALDER, signed_on: null }), "");
  assert.equal(signedDatesLabel(undefined), "");
});

const STAGES = [{ key: "contracting", label: "Contracting", state: "done", gaps_started: 0 }, { key: "signed", label: "Signed", state: "current", gaps_started: 0 }];
const journey = (docs) => renderToStaticMarkup(createElement(DocumentList, { deal: "alder_bank", stages: STAGES, documents: docs, name: "", setName() {}, onChanged() {}, onView() {}, onAdd() {}, onHelp() {} }));

test("the deal journey: the Signed milestone carries the signature date, the 14 Oct email sits before it, and the document says both dates", () => {
  const html = journey([ALDER, EMAIL]);
  assert.ok(html.indexOf("Customer email") < html.indexOf("Signed contract")); // the email's stage comes before Signed
  const signedRow = html.slice(html.indexOf("Signed contract"));
  assert.ok(signedRow.includes("20 Oct") && !signedRow.includes("12 Oct</span>")); // the date shown on the row is the signature date
  assert.ok(html.includes('<span class="dp-signed-dates">Agreement dated 12 Oct · signed 20 Oct</span>'));
  assert.ok(!journey([NOMA]).includes("dp-signed-dates")); // Noma's header and signatures agree
  assert.ok(!journey([{ ...EMAIL }]).includes("dp-signed-dates")); // not a signed document
});

test("the record's documents list says both dates beside the signed document, from the live documents; the saved record is not changed", () => {
  const s = { documents: [{ name: "Customer email", version: 1, date: "2026-10-14", sha256: "a".repeat(64), source_version_id: 8 },
    { name: "Signed contract", version: 1, date: "2026-10-20", sha256: "b".repeat(64), source_version_id: 9 }] };
  const html = renderToStaticMarkup(createElement(RecordBody, { s, hv: { fingerprint: "f".repeat(64) }, interactive: false, setDrawer() {}, copy() {}, copied: false, signedLabels: { 9: "Agreement dated 12 Oct · signed 20 Oct" } }));
  assert.ok(html.includes('<div class="dp-doc-row fr-signed-dates">Agreement dated 12 Oct · signed 20 Oct</div>'));
  assert.ok(html.indexOf("Customer email") < html.indexOf("Signed contract")); // sorted by date: the 14 Oct email, then the 20 Oct signature
  assert.ok(html.includes("b".repeat(64)) && html.includes("f".repeat(64))); // hashes as saved
  const src = read("FrozenRecord.jsx");
  assert.match(src, /const signedLabels = Object\.fromEntries\(documents\.filter\(\(d\) => signedDatesLabel\(d\)\)\.map\(\(d\) => \[d\.source_version_id, signedDatesLabel\(d\)\]\)\);/);
});
