// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { blockNodes, parseMarkdown, plainText, renderDocument } from "../src/markdown.js";

const DOC = [
  "# Response to RFP ALD-03",
  "",
  "Date: 29 September 2026",
  "",
  "**Section 2.1 — Behavioural signals**",
  "",
  "*Question 2.1.1: Describe how you detect.*",
  "",
  "Through its connector to BioCatch, Elva will use **behavioural signals** from Alder's banking.",
  "",
  "- Dedicated environment on AWS",
  "- Up to 200,000 payments a day",
  "",
  "1. First step",
  "2. Second step",
].join("\n");

const text = (blocks) => blocks.map((b) => plainText(blockNodes(b))).join("\n");

test("headings, bold, italics, lists and paragraphs are read, and the markers are not text", () => {
  const blocks = parseMarkdown(DOC);
  assert.deepEqual(blocks.map((b) => b.t), ["h", "p", "p", "p", "p", "ul", "ol"]);
  assert.equal(blocks[0].level, 1);
  assert.equal(plainText(blocks[0].children), "Response to RFP ALD-03");
  assert.equal(blocks[2].children[0].t, "strong");
  assert.equal(plainText(blocks[2].children), "Section 2.1 — Behavioural signals");
  assert.equal(blocks[3].children[0].t, "em");
  assert.equal(blocks[5].items.length, 2);
  assert.equal(plainText(blocks[5].items[1]), "Up to 200,000 payments a day");
  assert.ok(!/[#*]/.test(text(blocks)));
});

test("an unmatched marker stays as the literal character", () => {
  const [p] = parseMarkdown("2 * 3 is six and *this never closes");
  assert.equal(plainText(p.children), "2 * 3 is six and *this never closes");
});

test("raw HTML is only text: nothing is parsed as markup", () => {
  const blocks = parseMarkdown('<script>alert(1)</script>\n\n<img src=x onerror=alert(1)> and **<b>bold</b>**');
  assert.equal(plainText(blocks[0].children), "<script>alert(1)</script>");
  assert.equal(blocks[1].children.find((n) => n.t === "strong").children[0].text, "<b>bold</b>");
  const kinds = new Set();
  const walk = (ns) => ns.forEach((n) => { kinds.add(n.t); if (n.children) walk(n.children); });
  blocks.forEach((b) => { kinds.add(b.t); walk(blockNodes(b)); });
  assert.deepEqual([...kinds].sort(), ["p", "strong", "text"]); // no element a document could introduce
});

test("a quote in a paragraph is highlighted on the rendered text", () => {
  const q = "Elva will use **behavioural signals** from Alder's banking.";
  const { blocks, found } = renderDocument(DOC, q);
  assert.equal(found, true);
  const marked = blocks.map((b) => plainText(blockNodes(b), true)).join("");
  assert.equal(marked, "Elva will use behavioural signals from Alder's banking."); // markers are not highlighted, text is
  assert.equal(text(blocks), text(parseMarkdown(DOC))); // highlighting never changes the text
});

test("a quote inside bold, a heading and a list item is highlighted", () => {
  for (const [quote, shown] of [
    ["Behavioural signals", "Behavioural signals"],
    ["Response to RFP ALD-03", "Response to RFP ALD-03"],
    ["Up to 200,000 payments a day", "Up to 200,000 payments a day"],
    ["Describe how you detect.", "Describe how you detect."],
  ]) {
    const { blocks, found } = renderDocument(DOC, quote);
    assert.equal(found, true, quote);
    assert.equal(blocks.map((b) => plainText(blockNodes(b), true)).join(""), shown);
  }
});

test("a quote that crosses blocks is highlighted in each", () => {
  const { blocks, found } = renderDocument(DOC, "Dedicated environment on AWS\n- Up to 200,000");
  assert.equal(found, true);
  assert.equal(blocks.map((b) => plainText(blockNodes(b), true)).join("|"), "|||||Dedicated environment on AWSUp to 200,000|");
});

test("a quote that is not in the document gives no highlight, and the document still renders", () => {
  const r = renderDocument(DOC, "Elva will host on Azure");
  assert.equal(r.found, false);
  assert.equal(r.blocks.map((b) => plainText(blockNodes(b), true)).join(""), "");
  assert.equal(text(r.blocks), text(parseMarkdown(DOC)));
  assert.equal(renderDocument(DOC, "").found, false);
  assert.equal(renderDocument("", "x").found, false);
});

test("a quote made only of marker characters is not highlighted", () => {
  assert.equal(renderDocument("# Title\n\nbody", "# ").found, false);
});
