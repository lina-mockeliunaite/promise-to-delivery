// Round 7 (13 Nov): ten small fixes from a live walkthrough. Display only: no engine, snapshot, fingerprint, golden or cache change.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { APPROVAL_SCOPE_LABEL, catalogueLabel, changeView, commitmentView, confirmedTitle, frozenView, recordBriefNotice, recordLines, recordPills } from "../src/dealpage.js";
import * as demo from "../src/demo.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/round7-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const abs = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { CatalogueNamesContext, CommitmentView } from ${abs("Drawer.jsx")};\nexport { RecordDetail } from ${abs("FrozenRecord.jsx")};\nexport { ChangeDialog } from ${abs("DealPage.jsx")};\nexport { default as BriefCard } from ${abs("BriefCard.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CatalogueNamesContext, CommitmentView, RecordDetail, ChangeDialog, BriefCard } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&rsquo;/g, "’");
const drawer = (v, docs, names = {}) => decode(renderToStaticMarkup(createElement(CatalogueNamesContext.Provider, { value: names }, createElement(CommitmentView, { v, documents: docs, titleId: "t", me: "", onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} }))));
const record = (v, docs) => decode(renderToStaticMarkup(createElement(RecordDetail, { v, documents: docs, onOpenDoc() {} })));

// 1. the guide bar's label is the next step, in sync with the dots
test("1. a deal worked without the tour: the label names the next step to do, the same one the dots mark as current", () => {
  const SAMPLES = (deal) => [{ version_of: "A" }, { version_of: "B" }, { doc_type: "signed_contract" }];
  const steps = demo.guideSteps("alder_bank", SAMPLES(), [{ source_key: "A", version: 2, doc_type: "pricing_services_note" }], [], false, false);
  assert.deepEqual(steps.map((s) => s.state), ["done", "done", "current", "later", "later", "later"]);
  assert.deepEqual([demo.barStepText(steps).label, demo.barStepText(steps).text], ["Step 3 of 6", "Scam-call alerts: add the revised statement of work"]);
  const fresh = demo.guideSteps("alder_bank", SAMPLES(), [], [], false, false);
  assert.equal(demo.barStepText(fresh).label, "Step 1 of 6"); // nothing done: still the tour
});

// 2. footnote last (pinned in round6.test.mjs for both pages)
// 3. zero pills
test("3. the record's summary pills hide a zero count", () => {
  assert.deepEqual(recordPills({ open: 1, noted: 1, closed: 1 }).map((p) => p.text), ["1 needing attention", "1 addressed by note", "1 closed by documents"]); // Noma
  assert.deepEqual(recordPills({ open: 1, noted: 1, closed: 0 }).map((p) => p.text), ["1 needing attention", "1 addressed by note"]); // Alder
  assert.deepEqual(recordPills({ open: 2, noted: 0, closed: 0 }).map((p) => p.text), ["2 needing attention"]);
  assert.deepEqual(recordPills({ open: 0, noted: 0, closed: 0 }), []);
  assert.ok(read("FrozenRecord.jsx").includes("recordPills(counts)") && !read("FrozenRecord.jsx").includes("{counts.noted} addressed by note"));
});

// 4. the brief notice in the record
test("4. the record states the stale brief as a fact; the live page keeps its note; a note that does not parse is shown as stored", () => {
  const brief = { needs_reconfirmation: true, basis: "draft SOW, 9 Oct", reconfirm_note: "Confirmed against Draft SOW version 1; version 2 has arrived since. The deal owner should reconfirm this brief.", summary: "S", deliverables: [], confirmed_by: "Priya Nair, Head of Delivery", go_live: "" };
  assert.equal(recordBriefNotice(brief), "Brief confirmed against Draft SOW v1 (9 Oct); not reconfirmed after v2.");
  assert.equal(recordBriefNotice({ ...brief, basis: "draft SOW" }), "Brief confirmed against Draft SOW v1; not reconfirmed after v2."); // no date in the basis: none invented
  assert.equal(recordBriefNotice({ ...brief, reconfirm_note: "Something else." }), "Something else.");
  assert.equal(recordBriefNotice({ ...brief, needs_reconfirmation: false }), "");
  const live = decode(renderToStaticMarkup(createElement(BriefCard, { brief })));
  const locked = decode(renderToStaticMarkup(createElement(BriefCard, { brief, record: true })));
  assert.ok(live.includes("The deal owner should reconfirm this brief.")); // the live page is unchanged
  assert.ok(locked.includes("Brief confirmed against Draft SOW v1 (9 Oct); not reconfirmed after v2.") && !locked.includes("should reconfirm"));
});

// 5 and 7. repeated facts and reference-backs are covered in round6.test.mjs and evidence.test.mjs; here the Source rule
const SENT = "Scam-call alerts will be live from the 1 February 2027 launch.";
const DOCS = [
  { source_key: "AB-06", name: "Draft SOW", doc_type: "draft_sow", version: 2, date: "2026-10-09", version_date: "2026-10-16", source_version_id: 6, included: true },
  { source_key: "AB-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true },
];
const GAP = { id: 6, type: "contract_gap", finding: "Missing from contract", state: "Resolved", reason: "Closed.", evidence: { missing_phrases: ["scam-call alerts"] }, resolved_by: { text: "Resolved by Draft SOW, version 2" },
  signed_check: { status: "confirmed", sentence: SENT, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft SOW, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)", signed_sentence: SENT, signed_key: "AB-09", signed_version_id: 9 } };

test("7. a reference-back has no Source line of its own, and the lookup line's reference is a link", () => {
  const html = drawer(commitmentView({ name: "X", display_name: "Scam-call alerts", contract: "No gap found", statements: [{ quote: SENT, doc_type_label: "Draft SOW", date: "2026-10-16" }], contract_now: { target: "scam-call alerts", quote: SENT, document: "Draft SOW" },
    issues: [{ ...GAP, signed_check: undefined }] }, "closed", DOCS), DOCS);
  assert.ok(html.includes('<button type="button" class="dr-linkbtn">the clause shown above.</button>')); // the reference is the link (the lookup line already names document and date)
  const lookup = html.slice(html.indexOf("Wording in Draft SOW"), html.indexOf("What closed it"));
  assert.ok(lookup.includes("that mentions") && !lookup.includes("Source:")); // no Source line under the reference
});

// 6. catalogue line
test("6. the catalogue line names the entry and the region; the code stays on hover; without the catalogue it falls back to the code", () => {
  assert.equal(catalogueLabel("CAP-027/AU", { "CAP-027": "Scam-call alerts" }), "Scam-call alerts (Australia)");
  assert.equal(catalogueLabel("CAP-003/SG", { "CAP-003": "Support channels" }), "Support channels (Singapore)");
  assert.equal(catalogueLabel("CAP-019/AU/AWS_managed", { "CAP-019": "Regional cloud deployment" }), "Regional cloud deployment (Australia) · AWS managed");
  assert.equal(catalogueLabel("CAP-027/AU", {}), "CAP-027 · AU");
  assert.equal(catalogueLabel("CAP-099/ZZ", { "CAP-099": "Thing" }), "Thing (ZZ)");
  const c = { name: "Scam", display_name: "Scam-call alerts live at launch", contract: "Not included", statements: [], issues: [{ id: 5, finding: "No approval recorded", state: "Needs action", reason: "r", catalogue_path: "CAP-027/AU", evidence: {}, signed_check: null }] };
  const v = commitmentView(c, "open", DOCS);
  const named = drawer(v, DOCS, { "CAP-027": "Scam-call alerts" });
  assert.ok(named.includes("Catalogue: Scam-call alerts (Australia)") && named.includes('title="Open the product catalogue at this entry (CAP-027/AU)"'));
  assert.ok(drawer(v, DOCS).includes("Catalogue: CAP-027 · AU"));
});

// 8. Elsewhere
test("8. the result dialog never repeats a listed row in an 'Elsewhere' line", () => {
  const view = changeView({ closed: [{ promise: "L", finding: "Contract says something different", by: "Resolved by Draft contract, version 2" }], opened: [{ promise: "P", finding: "Missing from contract" }], stillOpen: [], reopened: [], confirmed: [], scopeHeld: [], acted: "L" }, (n) => n, "L");
  assert.ok(view.groups.some((g) => g.promise === "P" && g.opened.length)); // P is a row above
  assert.equal(view.elsewhere, "");
});

// 9. one link per clause in the record
test("9. the record has one link per clause: the start line's 'Open the clause' goes when Contract says already links the same signed text", () => {
  const SIGNED = "Scam-call alerts will be live from the 1 February 2027 launch: they warn the bank.";
  const scope = { status: "not_covered", reason: "The signed start date is earlier than the approved start date.", catalogue_path: "CAP-027/AU",
    approval: { date: "2027-05-01", line: "| x | Named exception approved by Arjun Rao from 1 May 2027 |", label: "Internal approvals note", key: "AB-05", version_id: 5, doc_date: "2026-10-16" },
    start: { source: "signed", sentence: SIGNED, label: "Signed contract", key: "AB-09", version_id: 9, date: "2027-02-01", in: "signed SOW" } };
  const docs = [...DOCS, { source_key: "AB-05", name: "Internal approvals note", doc_type: "pricing_services_note", version: 2, date: "2026-10-06", version_date: "2026-10-16", source_version_id: 5, included: true }];
  const live = { issues: [{ finding: "Missing from contract", state: "Resolved", signed_check: { ...GAP.signed_check, sentence: SIGNED, signed_sentence: SIGNED } }] };
  const v = frozenView({ item: { promise: "Alder scam", findings: [{ finding: APPROVAL_SCOPE_LABEL, evidence: {}, signed_check: null }], quotes: [{ quote: "We will detect scams.", source: "RFP response", date: "2026-09-29" }], contract: "Not included", signed: [] },
    status: "open", closedFindings: [{ finding: "Missing from contract", resolved_by: "Resolved by Draft SOW, version 2" }], documents: docs, live, snapshotDocs: docs, approvalScopes: { "Alder scam|Approval starts later": scope } });
  const html = record(v, docs);
  assert.equal(html.split("Open the signed clause").length - 1, 1);
  assert.equal(html.split("Open the clause").length - 1, 0);
  assert.equal(html.split("Open the approval").length - 1, 1); // a different text keeps its own link
  assert.equal(recordLines(v, docs).scope.startDoc, null);
});

// 10. one dialog phrase
test("10. one phrase for a signed confirmation of contract wording, for both deals", () => {
  assert.equal(confirmedTitle("Contract says something different"), "Contract wording found"); // Noma
  assert.equal(confirmedTitle("Missing from contract"), "Contract wording found"); // Alder
  const html = decode(renderToStaticMarkup(createElement(ChangeDialog, { change: { confirmed: [{ promise: "L", finding: "Contract says something different" }], closed: [], opened: [], stillOpen: [], reopened: [], scopeHeld: [], openPromises: 2, modelCalls: 0, doc: "Signed contract (20 Oct)" }, titleOf: (n) => n, onClose() {} })));
  assert.ok(html.includes('<strong>Contract wording found</strong><span class="dp-change-closed"> · confirmed in the signed contract</span>'));
});
