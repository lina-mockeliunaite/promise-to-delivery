// A small, safe Markdown reader for the drawer's document view (20 Oct). It turns the stored text into a tree of headings,
// paragraphs, lists, bold, italics and code; the screen renders that tree as React elements, so nothing from a document is ever
// parsed as HTML or injected (a "<script>" in a document is just the characters). Every text node keeps its offset in the
// stored text, so a quoted sentence found in the stored text can be highlighted on the rendered text: the marks and the
// markers (#, **, *) never get in each other's way. Pure, so it is tested without a browser.
import { splitQuote } from "./dealpage.js";

// Inline: **bold**, *italic*, `code`. An unmatched marker stays as the literal character.
function inline(str, base) {
  const out = [];
  let buf = "";
  let bufAt = base;
  const flush = (upTo) => {
    if (buf) out.push({ t: "text", text: buf, start: bufAt });
    buf = "";
    bufAt = upTo;
  };
  let i = 0;
  while (i < str.length) {
    const rest = str.slice(i);
    let m = /^\*\*(?=\S)([\s\S]+?)(?<=\S)\*\*/.exec(rest);
    if (m) {
      flush(base + i + m[0].length);
      out.push({ t: "strong", children: inline(m[1], base + i + 2) });
      i += m[0].length;
      bufAt = base + i;
      continue;
    }
    m = /^\*(?=[^\s*])([^*]+?)(?<=\S)\*(?!\*)/.exec(rest);
    if (m) {
      flush(base + i + m[0].length);
      out.push({ t: "em", children: inline(m[1], base + i + 1) });
      i += m[0].length;
      bufAt = base + i;
      continue;
    }
    m = /^`([^`\n]+)`/.exec(rest);
    if (m) {
      flush(base + i + m[0].length);
      out.push({ t: "code", text: m[1], start: base + i + 1 });
      i += m[0].length;
      bufAt = base + i;
      continue;
    }
    if (!buf) bufAt = base + i;
    buf += str[i];
    i += 1;
  }
  flush(base + str.length);
  return out;
}

const HEADING = /^(#{1,6})\s+(.*?)\s*#*\s*$/;
const BULLET = /^(\s*)[-*+]\s+(.*)$/;
const NUMBER = /^(\s*)\d+[.)]\s+(.*)$/;
const RULE = /^\s*([-*_])(\s*\1){2,}\s*$/;

// Blocks: headings, rules, bulleted and numbered lists, paragraphs (a line break inside a paragraph is kept).
export function parseMarkdown(text) {
  const src = String(text ?? "");
  const lines = [];
  let at = 0;
  for (const line of src.split("\n")) {
    lines.push({ line: line.replace(/\r$/, ""), at });
    at += line.length + 1;
  }
  const blocks = [];
  let para = null;
  let list = null;
  const endPara = () => {
    if (para) blocks.push({ t: "p", children: inline(src.slice(para.start, para.end), para.start) });
    para = null;
  };
  const endList = () => { list = null; };
  for (const { line, at: start } of lines) {
    if (!line.trim()) { endPara(); endList(); continue; }
    let m;
    if ((m = HEADING.exec(line))) {
      endPara(); endList();
      const from = start + line.indexOf(m[2], m[1].length);
      blocks.push({ t: "h", level: m[1].length, children: inline(m[2], from) });
    } else if (RULE.test(line)) {
      endPara(); endList();
      blocks.push({ t: "hr" });
    } else if ((m = BULLET.exec(line)) || (m = NUMBER.exec(line))) {
      endPara();
      const kind = BULLET.test(line) ? "ul" : "ol";
      if (!list || list.t !== kind) { list = { t: kind, items: [] }; blocks.push(list); }
      list.items.push(inline(m[2], start + line.length - m[2].length));
    } else {
      endList();
      if (para) para.end = start + line.length;
      else para = { start, end: start + line.length };
    }
  }
  endPara();
  return blocks;
}

// Wrap the stored-text range [from, to) in marks on the rendered tree. Text outside the range is untouched.
function markNodes(nodes, from, to, hit) {
  return nodes.flatMap((n) => {
    if (n.t === "strong" || n.t === "em") return [{ ...n, children: markNodes(n.children, from, to, hit) }];
    const a = Math.max(from, n.start);
    const b = Math.min(to, n.start + n.text.length);
    if (a >= b) return [n];
    hit.count += 1;
    const cut = (x, y) => n.text.slice(x - n.start, y - n.start);
    return [
      ...(a > n.start ? [{ ...n, text: cut(n.start, a) }] : []),
      { t: "mark", children: [{ ...n, text: cut(a, b), start: a }] },
      ...(b < n.start + n.text.length ? [{ ...n, text: cut(b, n.start + n.text.length), start: b }] : []),
    ];
  });
}

// The document as rendered blocks, with the quote highlighted when it can be placed exactly on the rendered text. When it
// cannot (not in the text, or only marker characters), the document comes back without any highlight rather than a wrong
// one; `found` says which.
export function renderDocument(text, quote) {
  const blocks = parseMarkdown(text);
  const split = quote ? splitQuote(String(text ?? ""), quote) : null;
  if (!split) return { blocks, found: false };
  const from = split.before.length;
  const to = from + split.match.length;
  const hit = { count: 0 };
  const marked = blocks.map((b) => {
    if (b.t === "hr") return b;
    if (b.items) return { ...b, items: b.items.map((it) => markNodes(it, from, to, hit)) };
    return { ...b, children: markNodes(b.children, from, to, hit) };
  });
  return hit.count ? { blocks: marked, found: true } : { blocks, found: false };
}

// The visible text of nodes, optionally only what is inside marks: for tests and for the empty-highlight check.
export function plainText(nodes, onlyMarked = false, inMark = false) {
  return nodes.map((n) => {
    if (n.t === "mark") return plainText(n.children, onlyMarked, true);
    if (n.children) return plainText(n.children, onlyMarked, inMark);
    return !onlyMarked || inMark ? n.text : "";
  }).join("");
}
export const blockNodes = (b) => (b.items ? b.items.flat() : b.children ?? []);
