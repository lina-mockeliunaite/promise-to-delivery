// Evidence in the drawer and the record (11 Nov): the signed clause, what was searched, where it stands first, the collapsed AI reading with the code's Evidence line, and the reopen history.
// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { EVIDENCE_LINE, cleanReason, commitmentView, frozenView, recordLines, historyLines, searchedLines, signedClauseOf, statusText } from "../src/dealpage.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/evidence-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
fs.writeFileSync(entry, `export { CommitmentView } from ${JSON.stringify(fileURLToPath(new URL("Drawer.jsx", SRC)))};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" }, rollupOptions: { external: ["react", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { CommitmentView } = await import(file);
const decode = (t) => t.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&");
const drawer = (v) => decode(renderToStaticMarkup(createElement(CommitmentView, { v, documents: DOCS, titleId: "t", me: "", onOpenDoc() {}, onSeen() {}, onNote() {}, onAddDoc() {}, onCatalogue() {}, onClose() {} })));

const DOCS = [
  { source_key: "NJ-06", name: "Draft SOW", doc_type: "draft_sow", version: 1, date: "2026-10-12", version_date: "2026-10-12", source_version_id: 3, included: true },
  { source_key: "NJ-07", name: "Draft contract", doc_type: "draft_contract", version: 2, date: "2026-10-14", version_date: "2026-10-19", source_version_id: 4, included: true },
  { source_key: "NJ-05", name: "Internal approvals note", doc_type: "pricing_services_note", version: 2, date: "2026-10-08", version_date: "2026-10-18", source_version_id: 5, included: true },
  { source_key: "NJ-09", name: "Signed contract", doc_type: "signed_contract", version: 1, date: "2026-10-20", version_date: "2026-10-20", source_version_id: 9, included: true },
];
const CLAUSE = "The Assistant will respond to Guest enquiries in 12 languages, listed in Schedule 1.";
const CONFIRMED = { status: "confirmed", sentence: CLAUSE, signed: "Signed contract", date: "2026-10-20", closed_by: "Draft contract, version 2", text: "Confirmed in the signed contract (Signed contract, 20 Oct)",
  signed_sentence: CLAUSE, signed_key: "NJ-09", signed_version_id: 9 };
const LANGS = { name: "Assistant will support guest conversations in 12 languages at launch", display_name: "Support in 12 languages at launch", contract: "No gap found", statements: [],
  contract_now: { target: "12 languages", quote: CLAUSE, document: "Draft contract" },
  issues: [{ id: 1, finding: "Contract says something different", state: "Resolved", resolved_by: { text: "Resolved by Draft contract, version 2 · 19 Oct 2026" }, signed_check: CONFIRMED }] };

test("C1: confirmed in the signed contract shows the signed clause, its date and a source link; the draft quote moves into the history", () => {
  const v = commitmentView(LANGS, "closed", DOCS);
  assert.deepEqual([v.signed.quote, v.signed.label, v.signed.date, v.signed.doc?.source_key], [CLAUSE, "Signed contract", "2026-10-20", "NJ-09"]);
  const html = drawer(v);
  // 13 Nov, Round 7: the status line carries its own source: "(Signed contract, 20 Oct)" is the link that opens the signed document on that clause, and there is no second "Source:" line
  assert.ok(html.includes('<span class="dr-confirmed"><button type="button" class="dr-linkbtn">Signed contract · confirmed</button> (20 Oct)</span>'));
  assert.ok(html.includes(`<blockquote class="dr-quote">${CLAUSE}</blockquote>`));
  assert.ok(!html.includes("Source: ") || !/Source: <button[^>]*>Signed contract, 20 Oct/.test(html));
  assert.ok(!html.includes("that mentions")); // the draft lookup is not what "Contract says" shows any more
  // 13 Nov, Round 6: the draft wording is the same sentence as the signed clause shown above, so the history says so instead of repeating it
  assert.ok(!html.includes("Draft wording that closed it") && !html.includes("with the same wording"));
  assert.ok(!html.includes('class="dr-history"') && !html.includes(">History<")); // 13 Nov, Round 7: History's only line said the same wording, which "What closed it" already says once
  assert.equal(html.split("confirmed in the signed contract (20 Oct)").length - 1, 1); // "Closed by … · confirmed in the signed contract" appears once
  assert.equal(html.split(CLAUSE).length - 1, 1); // the sentence is on the screen once
  // without a signed confirmation the drawer is as it was
  const plain = commitmentView({ ...LANGS, issues: [{ ...LANGS.issues[0], signed_check: undefined }] }, "closed", DOCS);
  assert.equal(plain.signed, null);
  assert.ok(drawer(plain).includes("Wording in Draft contract (19 Oct) that mentions “12 languages”:")); // 13 Nov: the lookup line names the document and its date
  assert.equal(signedClauseOf([{ signed_check: { status: "confirmed" } }], DOCS), null); // an older result without the clause: nothing invented
});

const SPECIALIST = { name: "Dedicated launch specialist", contract: "Not included", statements: [], issues: [
  { id: 1, finding: "No approval recorded", state: "Resolved", resolved_by: { text: "Resolved by Internal approvals note, version 2 · 18 Oct 2026" } },
  { id: 2, finding: "Missing from contract", state: "Needs action", reason: "The launch specialist was promised repeatedly but never appears in the SOW or contract, leaving it unenforceable.", evidence: { missing_phrases: ["launch specialist"] } }] };

test("C2: an open finding names the documents searched, labelled draft or signed; the signed contract is 'checked only for earlier fixes'", () => {
  const live = searchedLines([SPECIALIST.issues[1]], DOCS);
  assert.deepEqual(live, ["Searched: Draft SOW v1 (draft), Draft contract v2 (draft).", "Signed contract: checked only for earlier fixes."]);
  // from the versions captured in the locked handover (the snapshot names the type, not the stored type)
  const snap = [{ name: "Draft SOW", type: "Draft SOW", version: 1 }, { name: "Draft contract", type: "Draft contract", version: 2 }, { name: "Signed contract", type: "Signed contract", version: 1 },
    { name: "Internal approvals note", type: "Pricing and services note", version: 2 }];
  assert.deepEqual(searchedLines([SPECIALIST.issues[1]], snap), live);
  assert.deepEqual(searchedLines([{ finding: "No approval recorded" }], snap), ["Searched: Internal approvals note v2."]);
  assert.deepEqual(searchedLines([{ finding: "Not offered" }], snap), []); // a catalogue finding is not a document search
  assert.deepEqual(searchedLines([SPECIALIST.issues[1]], DOCS.filter((d) => d.doc_type !== "signed_contract")), ["Searched: Draft SOW v1 (draft), Draft contract v2 (draft)."]); // no signed document, no signed line
  const html = drawer(commitmentView(SPECIALIST, "open", DOCS));
  assert.ok(html.includes('<p class="dr-muted dr-searched">Searched: Draft SOW v1 (draft), Draft contract v2 (draft).</p>'));
  assert.ok(html.includes("Signed contract: checked only for earlier fixes."));
  const locked = frozenView({ status: "open", documents: DOCS, titles: {}, snapshotDocs: snap, closedFindings: [{ finding: "No approval recorded", resolved_by: "Resolved by Internal approvals note, version 2 · 18 Oct 2026" }],
    item: { promise: "Dedicated launch specialist", contract: "Not included", findings: [{ finding: "Missing from contract", evidence: { missing_phrases: ["launch specialist"] }, why: "r", seen: [] }], quotes: [] } });
  assert.deepEqual(locked.searched, live); // the locked record names the same documents, from the captured versions
});

test("C4: where it stands and any note come first; the AI reading is last, collapsed, text unchanged; the Evidence line is the code's own and shows only for a missing-from-contract finding", () => {
  const noted = { ...SPECIALIST, issues: [SPECIALIST.issues[1]] };
  const v = commitmentView(noted, "open", DOCS);
  v.notes = [{ by: "Maya Tan (Sales)", at: "2026-11-11T10:00:00Z", text: "Noma agreed on a call.", kind: "kept" }];
  const html = drawer(v);
  assert.ok(html.indexOf("Where it stands") < html.indexOf("Noma agreed on a call.") && html.indexOf("Noma agreed on a call.") < html.indexOf("Customer was told"));
  assert.ok(html.includes("<strong>Needs attention</strong>"));
  assert.ok(html.indexOf("Customer was told") < html.indexOf("Initial AI reading")); // the reading is below everything else
  assert.match(html, /<details class="dr-ai-details"><summary>Initial AI reading<\/summary>/); // collapsed: no "open" attribute
  assert.ok(!/<details class="dr-ai-details" open/.test(html));
  assert.ok(html.includes("The launch specialist was promised repeatedly but never appears in the SOW or contract, leaving it unenforceable.")); // the saved reading, untouched
  assert.deepEqual(v.ai, [cleanReason(noted.issues[0].reason)]);
  assert.ok(html.includes(`<p class="dr-evidence"><strong>Evidence</strong> ${EVIDENCE_LINE}</p>`));
  assert.ok(html.indexOf("dr-evidence") < html.indexOf("Initial AI reading")); // above the reading
  assert.equal(EVIDENCE_LINE, "No matching wording found in the reviewed draft contract or statement of work.");
  assert.ok(!/dr-ailabel[^>]*>[^<]*Evidence/.test(html) && !html.includes("AI-written summary · quotes checked against the supplied documents</span><p>No matching")); // never labelled AI
  // no missing-from-contract finding: no Evidence line
  const other = commitmentView({ ...SPECIALIST, issues: [{ id: 3, finding: "No approval recorded", state: "Needs action", reason: "Needs a named approval.", evidence: {} }] }, "open", DOCS);
  assert.equal(other.evidence, "");
  assert.ok(!drawer(other).includes("dr-evidence"));
  // a closed commitment has no AI reading and no Evidence line
  assert.equal(commitmentView(LANGS, "closed", DOCS).evidence, "");
  assert.equal(statusText("open", 1, 2), "Needs attention · 1 of 2 gaps closed");
  assert.equal(statusText("noted", 0, 2), "Addressed by note");
});

const REOPENED = { name: "BioCatch-based coaching detection", contract: "Not included", statements: [], issues: [
  { id: 4, finding: "Missing from contract", state: "Needs action", reason: "The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed.", evidence: { missing_phrases: ["BioCatch"] },
    signed_check: { status: "not_found", reason: "The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed.", closed_by: "Draft SOW, version 2", sentence: "Through its connector to BioCatch, Provider will use behavioural signals.",
      earlier: "Resolved by Draft SOW, version 2 · Draft contract, version 1 unchanged · 11 Nov 2026", signed_label: "Signed contract", signed_date: "2026-10-20", signed_key: "AB-09", signed_version_id: 9 } }] };
const ALDER_DOCS = [{ source_key: "AB-06", name: "Draft SOW", doc_type: "draft_sow", version: 2, date: "2026-10-09", version_date: "2026-10-16", source_version_id: 6, included: true }, DOCS[3]];

test("C5: a reopened finding explains itself in the rule's words and its history keeps the earlier closure, with the document's date and version", () => {
  assert.deepEqual(historyLines(REOPENED.issues, ALDER_DOCS), ["Closed by Draft SOW v2 (16 Oct), then reopened by the signed contract (20 Oct).",
    "Draft wording that closed it: \u201CThrough its connector to BioCatch, Provider will use behavioural signals.\u201D, in Draft SOW v2 (16 Oct)."]);
  const v = commitmentView(REOPENED, "open", ALDER_DOCS);
  const html = drawer(v);
  assert.ok(html.includes("The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed."));
  assert.ok(!/9 October|incorporate/i.test(html)); // the checker does not read SOW references; nor does the text claim it
  assert.match(html, /<details class="dr-history" open=""><summary class="dr-label">History<\/summary><p class="dr-muted">Closed by Draft SOW v2 \(16 Oct\), then reopened by the signed contract \(20 Oct\)\.<\/p>/); // open for a reopened gap
  // the draft wording is history, not "Contract says": a reopened gap has no contract wording that closes it
  const withNow = commitmentView({ ...REOPENED, contract_now: { target: "BioCatch", quote: "Through its connector to BioCatch, Provider will use behavioural signals.", document: "Draft SOW" } }, "open", ALDER_DOCS);
  assert.equal(withNow.contract.now, null);
  assert.ok(!drawer(withNow).includes("that mentions"));
  assert.ok(html.includes("Signed contract: checked only for earlier fixes.")); // and the signed contract is named for what it is
});

test("the drawer's pieces are shared by the live drawer and the locked record, and the saved record is not changed", () => {
  const fr = read("FrozenRecord.jsx");
  assert.match(fr, /const common = \{ documents, titles, snapshotDocs: s\.documents, relatedMap: hv\.related_clauses \?\? \{\}, approvalScopes: hv\.approval_scopes \?\? \{\}, pending: evidencePending \};/); // 12 Nov: the related clause and the approval-scope dates come beside the snapshot
  assert.match(fr, /api\.fetchRegister\(deal\)\.then\(setLiveRegister/); // only when the handover response does not carry live_commitments (Round 8c)
  assert.ok(!/signed_sentence|signed_label/.test(fr)); // nothing here writes into the saved record
  assert.match(read("dealpage.js"), /signed_check: liveOpen\.find\(\(l\) => l\.finding === f\.finding\)\?\.signed_check \?\? f\.signed_check/);
});

test("12 Nov: the record's Contract says is the signed clause, attributed to the signed contract; no draft attribution", () => {
  const v = commitmentView(LANGS, "closed", DOCS);
  const r = recordLines(v, DOCS);
  assert.equal(r.contract, `\u201C${CLAUSE}\u201D (Signed contract \u00B7 confirmed, 20 Oct)`); // Round 8
  assert.ok(!/Draft contract/.test(r.contract));
  assert.deepEqual(r.settled, ["Closed by Draft contract v2 (19 Oct) \u00B7 confirmed in the signed contract (20 Oct)"]);
  const src = read("FrozenRecord.jsx");
  assert.match(src, /v\.signed\?\.doc && onOpenDoc && .*className="dr-linkbtn fr-noprint"/); // a source link on screen, plain text in print
});

test("12 Nov: the drawer's What closed it reads like the record, without the check date or the unchanged-with-it line", () => {
  const html = drawer(commitmentView(LANGS, "closed", DOCS));
  assert.ok(html.includes("Closed by Draft contract v2 (19 Oct) \u00B7 confirmed in the signed contract (20 Oct)"));
  assert.ok(!/unchanged, checked with it|Check on |Gap closed/.test(html));
  const noSigned = { ...LANGS, issues: [{ ...LANGS.issues[0], signed_check: undefined }] };
  assert.ok(drawer(commitmentView(noSigned, "closed", DOCS)).includes("Closed by Draft contract v2 (19 Oct)"));
});

// ---- 12 Nov: the related clause for a reopened gap -------------------------------------------------------------------------------------------------------------------
const ONE_MAY = "Coaching-scam detection via BioCatch will be enabled from 1 May 2027.";
const withRelated = (related) => ({ ...REOPENED, issues: [{ ...REOPENED.issues[0], signed_check: { ...REOPENED.issues[0].signed_check, ...(related ? { related } : {}) } }] });
const RELATED = { sentence: ONE_MAY, key: "AB-09", version_id: 9, label: "Signed contract", in: "signed SOW" };

const WHY = "The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed.";
const labelOfFinding = "Not in the draft contract or SOW";
const sectionHeads = (html) => [...html.matchAll(/<h3 class="dr-label">([^<]*)<\/h3>/g)].map((m) => m[1]);

test("round 4: a reopened gap with a clause shows Why it reopened, then Signed statement of work > Related clause with its link; no Contract says", () => {
  const v = commitmentView(withRelated(RELATED), "open", ALDER_DOCS);
  assert.deepEqual({ ...v.related, doc: !!v.related.doc }, { quote: ONE_MAY, label: "Signed contract", date: "2026-10-20", in: "signed SOW", doc: true });
  assert.deepEqual([v.reopened, v.whyReopened], [true, WHY]); // the check's own reason, unchanged
  const html = drawer(v);
  const heads = sectionHeads(html);
  assert.deepEqual(heads.slice(0, 5), ["Where it stands", "Customer was told", "Why it reopened", "Signed statement of work", "What we found"]); // cause before evidence
  assert.ok(!heads.includes("Contract says"));
  assert.ok(decode(html).includes(`<h3 class="dr-label">Why it reopened</h3><p class="dr-plain">${WHY}</p>`));
  assert.ok(decode(html).includes(`<span class="dr-muted">Related clause</span><blockquote class="dr-quote">${ONE_MAY}</blockquote>`)); // the exact clause, sub-label "Related clause"
  assert.match(html, /Related clause[\s\S]*?Source:[\s\S]*?<button type="button" class="dr-linkbtn">Signed contract, 20 Oct<\/button>/); // the link that opens the viewer on the clause
  assert.match(fs.readFileSync(new URL("../src/Drawer.jsx", import.meta.url), "utf8"), /onOpen=\{\(\) => onOpenDoc\?\.\(v\.related\.doc, v\.related\.quote\)\}/);
  assert.ok(html.includes("Customer was told")); // the heading is kept
});

test("round 4: the heading follows the clause's source; reopened without a clause has Why it reopened only; the reason is not repeated and the false label is hidden in What we found", () => {
  assert.ok(sectionHeads(drawer(commitmentView(withRelated({ ...RELATED, in: "signed contract" }), "open", ALDER_DOCS))).includes("Signed contract"));
  assert.ok(drawer(commitmentView(withRelated({ ...RELATED, in: "signed contract" }), "open", ALDER_DOCS)).includes("Related clause")); // the sub-label stays in both
  const none = drawer(commitmentView(withRelated(null), "open", ALDER_DOCS));
  assert.deepEqual(sectionHeads(none).slice(0, 4), ["Where it stands", "Customer was told", "Why it reopened", "What we found"]); // no clause section at all
  assert.ok(!none.includes("Related clause") && !none.includes("Signed statement of work"));
  for (const v of [commitmentView(withRelated(RELATED), "open", ALDER_DOCS), commitmentView(withRelated(null), "open", ALDER_DOCS)]) {
    const html = decode(drawer(v));
    assert.deepEqual(v.found, []); // nothing left in What we found for the reopened gap
    assert.ok(!html.includes(labelOfFinding)); // the finding label, false for a reopened gap, is hidden (not reworded)
    assert.equal(html.split("fix can't be confirmed").length - 1, 1); // the reason is shown once
  }
  assert.equal(commitmentView(withRelated(RELATED), "open", ALDER_DOCS).searched.length > 0, true); // "Searched: …" and the rest of the section stay
});

test("round 4: every other state keeps Contract says exactly as before, and its finding label", () => {
  const never = commitmentView({ ...REOPENED, issues: [{ ...REOPENED.issues[0], signed_check: null }] }, "open", ALDER_DOCS);
  assert.equal(never.reopened, false);
  const html = drawer(never);
  assert.ok(sectionHeads(html).includes("Contract says") && !sectionHeads(html).includes("Why it reopened"));
  assert.equal(never.contract.text, "No matching wording found in the draft contract or SOW");
  assert.ok(decode(html).includes(labelOfFinding)); // the label shows for a gap that was never closed
  const closed = commitmentView(LANGS, "closed", DOCS);
  assert.equal(closed.reopened, false);
  assert.ok(sectionHeads(drawer(closed)).includes("Contract says"));
  assert.equal(closed.related, null);
});

// ---- 12 Nov, follow-ups: Contract says for a reopened gap, the row's history line, and the clause in the locked record ------------------------------------------------
import { earlierLine, reopenedLines, relatedFromRecord } from "../src/dealpage.js";

test("12 Nov: the row's history line for a reopened gap: closing document with its date, then the signed document that reopened it; no unchanged or check date", () => {
  const sc = { status: "not_found", reason: "r", closed_by: "Draft SOW, version 2", earlier: "Resolved by Draft SOW, version 2 · Draft contract, version 1 unchanged · 11 Nov 2026", signed_label: "Signed contract", signed_date: "2026-10-20" };
  assert.equal(earlierLine(sc, ALDER_DOCS), "Earlier closed by Draft SOW v2 (16 Oct) · reopened by the signed contract (20 Oct)");
  assert.deepEqual(reopenedLines([{ signed_check: sc }], ALDER_DOCS), ["r", "Earlier closed by Draft SOW v2 (16 Oct) · reopened by the signed contract (20 Oct)"]);
  assert.ok(!/unchanged|checked/.test(earlierLine(sc, ALDER_DOCS)));
  // a saved record keeps four fields: it says what it has
  assert.equal(earlierLine({ status: "not_found", earlier: sc.earlier }, []), "Earlier closed by Draft SOW v2 · reopened by the signed contract");
  assert.equal(earlierLine({ status: "not_found" }, []), "");
});

test("round 4: the locked record reads cause first: Why it reopened, then the related clause under its source-based heading; no Contract says line; screen and print share one markup", () => {
  const map = { "BioCatch-based coaching detection|Missing from contract": { sentence: ONE_MAY, key: "AB-09", version_id: 9, label: "Signed contract", in: "signed SOW", date: "2026-10-20" } };
  const item = { promise: "BioCatch-based coaching detection", contract: "Not included", quotes: [], findings: [{ finding: "Missing from contract", evidence: { missing_phrases: ["BioCatch"] }, signed_check: { status: "not_found", reason: REASON_SENTENCE, earlier: "Resolved by Draft SOW, version 2 · 11 Nov 2026" } }] };
  const v = frozenView({ item, status: "open", documents: ALDER_DOCS, titles: {}, live: null, snapshotDocs: null, relatedMap: map });
  assert.deepEqual({ ...v.related, doc: !!v.related.doc }, { quote: ONE_MAY, label: "Signed contract", date: "2026-10-20", in: "signed SOW", doc: true });
  assert.deepEqual([v.reopened, v.whyReopened, v.found], [true, REASON_SENTENCE, []]);
  const r = recordLines(v, ALDER_DOCS);
  assert.equal(r.why, REASON_SENTENCE);
  assert.equal(r.contract, ""); // no "Contract says" line for a reopened gap
  assert.deepEqual([r.related.heading, r.related.text], ["Signed statement of work", `\u201C${ONE_MAY}\u201D (Signed contract, 20 Oct)`]);
  // no map entry (an older record, or a text that no longer matches): the reason alone
  const bare = frozenView({ item, status: "open", documents: ALDER_DOCS, titles: {}, relatedMap: {} });
  assert.equal(bare.related, null);
  assert.equal(recordLines(bare, ALDER_DOCS).why, REASON_SENTENCE);
  assert.equal(relatedFromRecord(null, "x", [], []), null);
  const fr = read("FrozenRecord.jsx");
  const why = fr.indexOf('<p className="fr-why"><strong>Why it reopened:</strong> {r.why}</p>'), rel = fr.indexOf('<p className="fr-related"><strong>{r.related.heading}</strong> \u00B7 Related clause: {r.related.text}');
  const says = fr.indexOf("<strong>Contract says:</strong>");
  assert.ok(why > 0 && rel > why && says > 0 && says < why); // the record's order: what the customer was told, Contract says (other states), then why it reopened, then the clause
  assert.match(fr, /className="dr-linkbtn fr-noprint"[\s\S]*?>Open the clause<\/button>/); // the link is screen-only; the clause text prints
});
const REASON_SENTENCE = "The signed contract doesn't contain the wording that closed this gap, so the fix can't be confirmed.";
