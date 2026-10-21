// Document hashes and the "Gap closed" wording of the locked record (21 Oct).
import test from "node:test";
import assert from "node:assert/strict";
import { appendixEntries, hasStoredText, sha256Hex, shortHash, verifyText } from "../src/docHash.js";
import { gapClosed } from "../src/dealpage.js";

// Expected values come from Python: hashlib.sha256(text.encode("utf-8")).hexdigest() (the stored hash is made that way).
const CURLY = "The customer’s “go-live” is 1 Dec — café support included.\nSecond line.\n";
const CURLY_HEX = "3c441aad1f5902c65bd6ab41e6cf150dbfad544fe371cb1a0303a35020a81f19";
const CRLF_HEX = "ae2ddaef1bce3ea520ef4b9a8bd126f04a3065445460c2d3c489b5784c5ff815";

test("the browser hash equals the stored UTF-8 hash for curly quotes and an accented character", async () => {
  assert.equal(await sha256Hex(CURLY), CURLY_HEX);
  assert.deepEqual(await verifyText(CURLY, CURLY_HEX), { ok: true, actual: CURLY_HEX });
});

test("a stored text keeps its line endings: the text read is hashed as it is, with no re-ending", async () => {
  // The server stores text with LF endings (CRLF is converted when a document is read in); the text it returns is the text hashed.
  const crlf = CURLY.replace(/\n/g, "\r\n");
  assert.equal(await sha256Hex(crlf), CRLF_HEX);
  assert.notEqual(await sha256Hex(crlf), await sha256Hex(CURLY));
  assert.equal((await verifyText(crlf, CRLF_HEX)).ok, true);
});

test("a changed text does not match; the check never throws", async () => {
  const r = await verifyText(CURLY.replace("go-live", "go live"), CURLY_HEX);
  assert.equal(r.ok, false);
  assert.equal(r.expected, CURLY_HEX);
  assert.notEqual(r.actual, CURLY_HEX);
});

test("only documents with a stored version and hash are openable; older records stay plain", () => {
  assert.equal(hasStoredText({ name: "A", version: 1 }), false);
  assert.equal(hasStoredText({ name: "A", source_version_id: 3, sha256: "ab" }), true);
  assert.deepEqual(appendixEntries([{ name: "A", version: 1 }], {}), []);
});

test("the print appendix lists each stored document in order with name, version, date and hash, text exactly as read", () => {
  const docs = [
    { name: "Notes", version: 2, date: "2026-10-01", version_date: "2026-10-05", source_version_id: 7, sha256: "a".repeat(64) },
    { name: "Old", version: 1, date: "2026-09-01" },
    { name: "SOW", version: 1, date: "2026-10-02", source_version_id: 9, sha256: "b".repeat(64) },
  ];
  const a = appendixEntries(docs, { 7: "  keep\r\n spaces ", 9: CURLY });
  assert.deepEqual(a.map((x) => [x.name, x.version, x.date, x.sha256, x.text]),
    [["Notes", 2, "2026-10-05", "a".repeat(64), "  keep\r\n spaces "], ["SOW", 1, "2026-10-02", "b".repeat(64), CURLY]]);
  assert.equal(appendixEntries(docs, {})[0].text, null); // not yet fetched
});

test("the short hash is the first 12 and last 4 characters", () => {
  assert.equal(shortHash("0123456789abcdef".repeat(4)), "0123456789ab…cdef");
});

test("'Gap closed' names what was found and where, per kind, with the rest as separate muted lines", () => {
  const text = "Resolved by Pricing and services note, version 2 · Draft SOW, version 1 unchanged · 16 Oct 2026 · signed off by Dana Lee";
  assert.deepEqual(gapClosed("No approval recorded", text), {
    headline: "Gap closed: approval found in Pricing and services note, version 2",
    notes: ["Draft SOW, version 1: unchanged, checked with it", "Check on 16 Oct 2026", "Signed off by Dana Lee"],
  });
  assert.equal(gapClosed("Missing from contract", "Resolved by Draft SOW, version 2").headline, "Gap closed: contract wording found in Draft SOW, version 2");
  assert.equal(gapClosed("Contract says something different", "Resolved by Draft contract, version 3").headline, "Gap closed: contract wording now matches in Draft contract, version 3");
  assert.equal(gapClosed("Not offered", "Resolved by Email, version 2").headline, "Gap closed: promise changed in Email, version 2");
  assert.equal(gapClosed("No approval recorded", "").headline, "Gap closed in the documents");
  assert.ok(!/closed by|resolved by/i.test(gapClosed("No approval recorded", text).headline));
});
