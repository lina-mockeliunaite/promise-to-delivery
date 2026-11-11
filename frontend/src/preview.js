// The sample preview's reader (11 Nov): a sample's Markdown as a formatted document, read-only, with every block and table row remembering the source line it
// came from, so the lines the check uses (reported by the sample route as line numbers) can be highlighted on the formatted text. Headings, paragraphs (a line
// break inside a paragraph is kept), bullet lists, rules and tables; inline bold, italics and code through the drawer's own reader. Pure and safe: only text
// nodes carry the document, and React escapes them.
import { inline } from "./markdown.js";

const HEADING = /^(#{1,6})\s+(.*?)\s*#*\s*$/;
const BULLET = /^\s*[-*+]\s+(.*)$/;
const RULE = /^\s*([-*_])(\s*\1){2,}\s*$/;
const cells = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
const isSeparator = (line) => /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(line) && line.includes("-");

export function parsePreview(text) {
  const lines = String(text ?? "").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    let m = HEADING.exec(line);
    if (m) { blocks.push({ t: "h", level: m[1].length, nodes: inline(m[2], 0), line: i }); i += 1; continue; }
    if (RULE.test(line)) { blocks.push({ t: "hr", line: i }); i += 1; continue; }
    if (line.trim().startsWith("|")) {
      const start = i;
      const rows = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) { rows.push({ text: lines[i], line: i }); i += 1; }
      const head = rows.length > 1 && isSeparator(rows[1].text) ? rows[0] : null;
      const body = rows.filter((r, k) => !(head && (k === 0 || k === 1)));
      blocks.push({ t: "table", line: start, head: head ? { cells: cells(head.text).map((c) => inline(c, 0)), line: head.line } : null,
        rows: body.filter((r) => !isSeparator(r.text)).map((r) => ({ cells: cells(r.text).map((c) => inline(c, 0)), line: r.line })) });
      continue;
    }
    if (BULLET.test(line)) {
      const items = [];
      while (i < lines.length && BULLET.test(lines[i])) { items.push({ nodes: inline(BULLET.exec(lines[i])[1], 0), line: i }); i += 1; }
      blocks.push({ t: "ul", items, line: items[0].line });
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !HEADING.test(lines[i]) && !RULE.test(lines[i]) && !lines[i].trim().startsWith("|") && !BULLET.test(lines[i])) {
      para.push({ nodes: inline(lines[i].trim(), 0), line: i });
      i += 1;
    }
    blocks.push({ t: "p", lines: para, line: para[0].line });
  }
  return blocks;
}

// Which source lines a block covers, for the highlight.
export const blockLines = (b) => (b.t === "table" ? [b.head?.line, ...b.rows.map((r) => r.line)].filter((x) => x != null)
  : b.t === "ul" ? b.items.map((x) => x.line) : b.t === "p" ? b.lines.map((x) => x.line) : [b.line]);
