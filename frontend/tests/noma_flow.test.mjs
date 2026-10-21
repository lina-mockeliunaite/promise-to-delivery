// A scripted replay of the Noma filing flow (20 Oct), on the saved run-1 reading (fixtures/noma_register.json, captured from the
// seeded ledger) and the real update files in data/scenarios. No model, and nothing typed in: the register is the app's own data.
// Right filing: each document goes to the document it revises, and nothing questions it. Wrong filing (a rehearsal mistake): the
// revised contract filed as a new version of the SOW and the revised pricing note as a new "Proposal": each must be questioned.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { suggestFix } from "../src/dealpage.js";
import { addReady, mismatchNotice, suggestVersionOf } from "../src/format.js";

const read = (rel) => fs.readFileSync(new URL(rel, import.meta.url), "utf8");
const REG = JSON.parse(read("./fixtures/noma_register.json"));
const FILES = {
  pricing: { name: "NJ-05_v2_named_exception.md", head: read("../../data/scenarios/NJ-05_v2_named_exception.md").slice(0, 6000) },
  contract: { name: "NJ-07_v2_languages_aligned.md", head: read("../../data/scenarios/NJ-07_v2_languages_aligned.md").slice(0, 6000) },
};
const LABELS = { draft_sow: "Draft SOW", draft_contract: "Draft contract", pricing_services_note: "Pricing and services note", proposal: "Proposal" };
const commitment = (word) => REG.commitments.find((c) => c.name.toLowerCase().includes(word));
const open = (c) => c.issues.filter((i) => i.state !== "Resolved");
const notice = (file, target) => mismatchNotice({ fileName: file.name, head: file.head, target, documents: REG.documents, labels: LABELS });
const named = (key) => { const d = REG.documents.find((x) => x.source_key === key); return { type: d.doc_type, name: d.name }; };

test("the right filing: the languages commitment points at the Draft contract, the specialist at the pricing note, and nothing is questioned", () => {
  const fixContract = suggestFix(open(commitment("languages")), REG.documents);
  assert.equal(fixContract.source_key, "NJ-07"); // not the SOW
  assert.equal(notice(FILES.contract, named(fixContract.source_key)), null);
  const fixPricing = suggestFix(open(commitment("specialist")), REG.documents);
  assert.equal(fixPricing.source_key, "NJ-05");
  assert.equal(notice(FILES.pricing, named(fixPricing.source_key)), null);
});

test("the wrong filing of the revised contract as a new version of the SOW is questioned, and the right action is offered first", () => {
  const n = notice(FILES.contract, named("NJ-06"));
  assert.ok(n, "the warning must appear");
  assert.equal(n.question, "This looks like a draft contract.");
  assert.match(n.consequence, /replaces Draft SOW's wording and can close gaps it shouldn't/);
  assert.equal(n.use.text, "Use “A new version of Draft contract”");
  assert.equal(n.use.source_key, "NJ-07");
  assert.equal(n.anyway, "Add as a new version of Draft SOW anyway");
});

test("the wrong filing of the revised pricing note as a new Proposal is questioned too", () => {
  const n = notice(FILES.pricing, { type: "proposal" });
  assert.ok(n, "the warning must appear");
  assert.equal(n.consequence, "Filed as a proposal, it won't close the approval gap.");
  assert.equal(n.use.text, "Use “A new version of Pricing and services note”");
  assert.equal(n.anyway, "Add as proposal anyway");
});

test("'+ Add' from the sidebar: nothing is chosen, the files suggest their own documents, and the add stays off until a choice is made", () => {
  for (const [file, key] of [[FILES.pricing, "NJ-05"], [FILES.contract, "NJ-07"]]) {
    assert.equal(suggestVersionOf({ fileName: file.name, head: file.head, documents: REG.documents }).source_key, key);
    assert.equal(notice(file, null), null); // no type chosen, so nothing to question yet
    assert.equal(addReady({ file, source_key: "", doc_type: "" }), false); // no silent default
    assert.equal(addReady({ file, source_key: key, doc_type: "" }), true); // accepting the suggestion
  }
});

import { newDocumentNotice } from "../src/format.js";

test("the mistaken path from the 21 Oct rehearsal: the pricing note filed as a new document is questioned before anything is added", () => {
  const n = newDocumentNotice({ fileName: FILES.pricing.name, head: FILES.pricing.head, documents: REG.documents, docType: "pricing_services_note", today: "21 Oct 2026" });
  assert.ok(n, "the warning must appear");
  assert.equal(n.use.text, "Use “A new version of Pricing and services note”"); // the right action first
  assert.match(n.consequence, /dated 21 Oct 2026 and sit beside Pricing and services note, not replace it/);
  assert.equal(n.anyway, "Add as a new document anyway");
  // the same for the contract, if it were filed as a new document
  const c = newDocumentNotice({ fileName: FILES.contract.name, head: FILES.contract.head, documents: REG.documents, docType: "draft_contract", today: "21 Oct 2026" });
  assert.equal(c.use.source_key, "NJ-07");
});
