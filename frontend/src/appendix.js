// Round 10 (14 Nov): the print appendix's quote anchors. When "Include full document text" is ticked, each citation in the record links to the place in the
// appendix where the quoted sentence stands, and the sentence is marked there. A citation links only when its quoted text is found word for word in that
// document's text (spaces may differ, nothing else: the same rule the document view uses to highlight a quote); otherwise it shows with no link.
// Pure and display-only: nothing here is stored, hashed or sent anywhere.
import { splitQuote } from "./dealpage.js";

// Every quote a record row cites, with the document it names (null when the record could not tell which document). Same order as the row reads.
export function citationsOf(v) {
  const out = [];
  (v.told ?? []).forEach((t, k) => out.push({ kind: "told", n: k, doc: t.doc ?? null, quote: t.quote }));
  if (v.scope) {
    out.push({ kind: "scope-start", doc: v.scope.start.doc ?? null, quote: v.scope.start.quote });
    out.push({ kind: "scope-approval", doc: v.scope.approval.doc ?? null, quote: v.scope.approval.quote });
  }
  const c = v.signed?.quote ? { doc: v.signed.doc, quote: v.signed.quote } : v.contract?.now?.quote ? v.contract.now : v.contract?.quote?.quote ? v.contract.quote : null;
  if (c) out.push({ kind: "contract", doc: c.doc ?? null, quote: c.quote });
  if (v.related?.quote) out.push({ kind: "related", doc: v.related.doc ?? null, quote: v.related.quote });
  return out;
}

// The range [from, to) of the quote in the document's stored text, or null when it is not there word for word.
export function quoteRange(text, quote) {
  const s = splitQuote(String(text ?? ""), quote);
  return s ? { from: s.before.length, to: s.before.length + s.match.length } : null;
}

// entries: [{ id, text }] for the documents in the appendix (text null while it loads); cites: citationsOf() of every row, with the row's key added.
// Returns the marks to draw per document and a status for each (document, quote): { id } when it links, or { reason } when it does not.
//   "no-document": the record cannot tell which document the quote came from; "no-text": that document is not in the appendix; "not-found": the quote is not in its text.
// Quotes that overlap in one document share one mark (the union), so one place never carries two overlapping marks.
export function planAnchors(entries, cites) {
  const docs = new Map(entries.map((e, i) => [String(e.id), { index: i, text: e.text, ranges: [] }]));
  const found = new Map(); // `${docId}|${quote}` -> range
  const reasons = new Map();
  for (const c of cites) {
    const key = `${c.doc?.source_version_id}|${c.quote}`;
    if (!c.doc?.source_version_id) { reasons.set(key, "no-document"); continue; }
    const d = docs.get(String(c.doc.source_version_id));
    if (!d || d.text == null) { reasons.set(key, "no-text"); continue; }
    const r = quoteRange(d.text, c.quote);
    if (!r) { reasons.set(key, "not-found"); continue; }
    found.set(key, r);
    if (!d.ranges.some((x) => x.from === r.from && x.to === r.to)) d.ranges.push(r);
  }
  // merge overlapping ranges per document, then name each mark
  const marks = {};
  for (const [id, d] of docs) {
    const sorted = [...d.ranges].sort((a, b) => a.from - b.from || a.to - b.to);
    const merged = [];
    for (const r of sorted) {
      const last = merged[merged.length - 1];
      if (last && r.from < last.to) last.to = Math.max(last.to, r.to); else merged.push({ ...r });
    }
    d.merged = merged.map((m, n) => ({ ...m, id: `ap${d.index}-${n + 1}` }));
    marks[id] = d.merged;
  }
  const status = (doc, quote) => {
    const key = `${doc?.source_version_id}|${quote}`;
    const r = found.get(key);
    if (!r) return { reason: reasons.get(key) ?? "no-document" };
    const m = docs.get(String(doc.source_version_id)).merged.find((x) => r.from >= x.from && r.to <= x.to);
    return { id: m.id };
  };
  return { marks, status, anchorOf: (doc, quote) => status(doc, quote).id ?? null };
}

// Wrap the stored-text range of each mark in the rendered nodes (nodes carry their offsets in the stored text). The first node of a mark takes its id.
export function markNodes(nodes, marks, taken = new Set()) {
  return nodes.flatMap((n) => {
    if (n.children) return [{ ...n, children: markNodes(n.children, marks, taken) }];
    if (n.text == null || n.start == null) return [n];
    const end = n.start + n.text.length;
    const hits = marks.filter((m) => m.from < end && m.to > n.start);
    if (!hits.length) return [n];
    const out = [];
    let at = n.start;
    for (const m of hits) {
      const a = Math.max(m.from, n.start);
      const b = Math.min(m.to, end);
      if (a > at) out.push({ ...n, text: n.text.slice(at - n.start, a - n.start), start: at });
      const part = { ...n, text: n.text.slice(a - n.start, b - n.start), start: a };
      const first = !taken.has(m.id) && (taken.add(m.id), true);
      out.push({ t: "mark", id: first ? m.id : undefined, children: [part] });
      at = b;
    }
    if (at < end) out.push({ ...n, text: n.text.slice(at - n.start), start: at });
    return out;
  });
}

// parsePreview() blocks (read with offsets) with the marks drawn in.
export function markPreview(blocks, marks) {
  const taken = new Set();
  const mk = (nodes) => markNodes(nodes, marks, taken);
  return blocks.map((b) => {
    if (b.t === "h") return { ...b, nodes: mk(b.nodes) };
    if (b.t === "ul") return { ...b, items: b.items.map((it) => ({ ...it, nodes: mk(it.nodes) })) };
    if (b.t === "table") return { ...b, head: b.head && { ...b.head, cells: b.head.cells.map(mk) }, rows: b.rows.map((r) => ({ ...r, cells: r.cells.map(mk) })) };
    if (b.t === "p") return { ...b, lines: b.lines.map((l) => ({ ...l, nodes: mk(l.nodes) })) };
    return b;
  });
}

// A document that is not Markdown: its paragraphs (blank-line separated) with their offsets in the stored text.
export function plainParagraphs(text) {
  const src = String(text ?? "");
  const out = [];
  let at = 0;
  for (const part of src.split(/(\n{2,})/)) {
    if (!/^\n{2,}$/.test(part) && part.trim()) out.push({ text: part, at });
    at += part.length;
  }
  return out;
}
