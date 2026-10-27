// Helpers for the deal page (16 Oct). Pure where possible, so they are tested without a browser.
import { useState } from "react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const short = (iso) => {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? "");
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]}` : "";
};

// "Proposal (10 Oct) · RFP response (6 Oct)": where the customer was told, newest first, each document once.
export function sourcesLine(statements) {
  const seen = new Map();
  for (const s of statements ?? []) {
    const key = `${s.doc_type_label}|${s.date}`;
    if (!seen.has(key)) seen.set(key, s);
  }
  return [...seen.values()]
    .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
    .map((s) => (s.date ? `${s.doc_type_label} (${short(s.date)})` : s.doc_type_label))
    .join(" · ");
}

// The check's reason without its status preamble: the card already says the gap is open.
export function cleanReason(reason) {
  return (reason ?? "").replace(/^Still holds on the current documents\.\s*/, "").trim();
}

export function firstDocDate(stage) {
  return (stage.documents ?? []).map((d) => d.date).filter(Boolean).sort()[0] ?? "";
}

// The viewer's name, remembered in this browser only, so nobody retypes it for every note or "seen".
const KEY = "ptd.name";
export function useName() {
  const [name, setName] = useState(() => {
    try {
      return window.localStorage.getItem(KEY) ?? "";
    } catch {
      return "";
    }
  });
  const update = (value) => {
    setName(value);
    try {
      window.localStorage.setItem(KEY, value);
    } catch {
      /* private window: the name lasts for this page only */
    }
  };
  return [name, update];
}

// What a new document changed (16 Oct): compare the deal before and after the check, by finding.
// closed: open before, resolved now. opened: open now, not open before. stillOpen: open gaps on the promises touched.
export function whatChanged(before, after) {
  const rows = (reg) => (reg?.commitments ?? []).flatMap((c) => c.issues.map((i) => ({ ...i, promise: c.name })));
  const wasOpen = new Map(rows(before).filter((i) => i.state !== "Resolved").map((i) => [i.id, i]));
  const now = rows(after);
  const nowById = new Map(now.map((i) => [i.id, i]));
  const closed = [...wasOpen.values()]
    .filter((i) => !nowById.has(i.id) || nowById.get(i.id).state === "Resolved")
    .map((i) => {
      const n = nowById.get(i.id) ?? i;
      const why = (n.reason ?? "").replace(/^Closed:\s*/, "");
      return { promise: i.promise, finding: i.finding, why: why.charAt(0).toUpperCase() + why.slice(1),
               by: n.resolved_by?.text ?? "" };
    });
  const opened = now.filter((i) => i.state !== "Resolved" && !wasOpen.has(i.id)).map((i) => ({ promise: i.promise, finding: i.finding }));
  const touched = new Set([...closed, ...opened].map((x) => x.promise));
  const stillOpen = now.filter((i) => i.state !== "Resolved" && touched.has(i.promise) && wasOpen.has(i.id))
    .map((i) => ({ promise: i.promise, finding: i.finding }));
  // A gap resolved by a current note is not open on screen either (one truth with the deal list and the page).
  const openPromises = new Set(now.filter((i) => i.state !== "Resolved" && !i.note_resolution?.current).map((i) => i.promise)).size;
  return { closed, opened, stillOpen, openPromises };
}

// Which document usually resolves a gap: the pricing note for an approval, the SOW for the contract, the promise itself
// when the product doesn't offer it. A suggestion only; the person can pick any document.
export function suggestFix(open, documents) {
  const byType = (t) => documents.find((d) => d.doc_type === t);
  const kinds = open.map((i) => i.finding);
  // Not offered first: no approval or contract change can fix it, and aligning the SOW would contract the unofferable.
  if (kinds.includes("Not offered")) {
    return { source_key: "", doc_type: "proposal",
             hint: "The product doesn't offer this, so no approval can fix it. Only changing the promise resolves it: add a new version of the proposal or RFP response that withdraws or changes it." };
  }
  if (kinds.includes("No approval recorded")) {
    const d = byType("pricing_services_note");
    const alsoContract = kinds.includes("Missing from contract") || kinds.includes("Contract says something different");
    return { source_key: d?.source_key ?? "", doc_type: "pricing_services_note",
             hint: "A named approval in the approvals note can close the approval gap." +
                   (alsoContract ? " The contract gap needs a contract or SOW update; it stays open until then." : " Add the new version of the approvals note.") };
  }
  // A contract conflict is fixed in the document its contract-side quote comes from (20 Oct): a revised contract is a new version of the
  // contract, not of the SOW. The stored evidence names that document.
  const conflict = open.find((i) => i.finding === "Contract says something different" && i.evidence?.contract_quote?.source);
  const home = conflict ? documents.find((d) => d.name === conflict.evidence.contract_quote.source) : null;
  if (home) {
    return { source_key: home.source_key, doc_type: home.doc_type,
             hint: `The contract wording behind this conflict is in ${home.name}. Add the new version of ${home.name}.` };
  }
  if (kinds.includes("Missing from contract") || kinds.includes("Contract says something different")) {
    const d = byType("draft_sow") ?? byType("draft_contract");
    return { source_key: d?.source_key ?? "", doc_type: "draft_sow",
             hint: "A contract gap closes when the SOW or contract says what was promised. Add the new version of the SOW." };
  }
  return { source_key: "", doc_type: "draft_sow", hint: "" };
}


// --- Evidence-first view (17 Oct, after the UI review) ----------------------------------------------------------------
// Everything below is built only from parts of a gap that code verified: exact quotes, the contract wording behind a
// conflict, the phrases searched for, the pricing-note line and catalogue facts. The AI's own sentence is kept apart.

// The contract column's short term, worded as what the check can actually establish.
export function contractText(term) {
  if (term === "Not included") return "No matching wording found in the draft contract or SOW";
  return term ?? "";
}

const n = (x) => Number(x).toLocaleString("en-GB");
const regionOf = (path) => (path ?? "").split("/")[1] ?? "";

// One plain line per gap, from verified facts only.
export function gapLine(finding, ev = {}, path = null) {
  ev = ev ?? {};
  switch (finding) {
    case "Not offered":
      return ev.unlisted_value
        ? `The catalogue has no ${ev.unlisted_value} option for this capability${regionOf(path) ? ` in ${regionOf(path)}` : ""}. No exception can sell it.`
        : `The catalogue has no entry for this${regionOf(path) ? ` in ${regionOf(path)}` : ""}. No exception can sell it.`;
    case "No approval recorded":
      if (ev.limit_name && ev.promised_quantity) {
        const limit = ev.limit_value ? `the catalogue limit of ${n(ev.limit_value)}` : "the catalogue limit";
        return `${n(ev.promised_quantity)} is above ${limit}; a named approval is needed and the approvals note records none.`;
      }
      return "The catalogue needs a named approval for this, and the approvals note records none.";
    case "Missing from contract":
      return ""; // title only (21 Oct): "Contract says" carries "No matching wording found …" and the searched-for phrases
    case "Contract says something different":
      // The told side only (21 Oct): the title and "Contract says" already show the contract's term.
      return ev.promised_value ? `Told "${ev.promised_value}".` : "The contract covers this on different terms.";
    default:
      return "";
  }
}

// What the contract column shows for a promise: the verified contract wording if a conflict has one, otherwise the
// phrases searched for and not found, otherwise the short term.
export function contractSide(issues, term) {
  const withQuote = issues.find((i) => i.evidence?.contract_quote);
  if (withQuote) return { quote: withQuote.evidence.contract_quote.quote, source: withQuote.evidence.contract_quote.source };
  const missing = [...new Set(issues.flatMap((i) => i.evidence?.missing_phrases ?? []))];
  if (missing.length) return { missing };
  return { text: contractText(term) };
}

// The customer's words: each verified quote once, newest first.
export function toldQuotes(statements) {
  const seen = new Set();
  return (statements ?? [])
    .filter((s) => s.quote && !seen.has(s.quote) && seen.add(s.quote))
    .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
    .map((s) => ({ quote: s.quote, source: s.doc_type_label ?? s.source, date: s.date ?? "" }));
}

// What is still missing before the handover can be completed, in the order a person would do it. No name is listed: the
// name is asked for when the button is pressed. The deal is signed only by a signed contract or SOW in the documents (19 Oct).
export function missingForHandover({ isSigned, notes }) {
  const out = [];
  if (!isSigned) out.push("upload the signed contract");
  if (!notes?.sales) out.push("add the Sales note");
  if (!notes?.delivery) out.push("add the Delivery note");
  return out;
}

// The three things a handover needs, in the order a person would do them, built from missingForHandover. done = not missing.
export function handoverChecklist({ isSigned, notes }) {
  const missing = new Set(missingForHandover({ isSigned, notes }));
  return [
    { key: "signed", label: "Signed contract · from the documents", done: !missing.has("upload the signed contract") },
    { key: "sales", label: "Sales · deal owner's handoff note", done: !missing.has("add the Sales note") },
    { key: "delivery", label: "Delivery · acceptance note", done: !missing.has("add the Delivery note") },
  ];
}

// The one-line lead for "What changed": gaps closed, and what is still open on the promises touched.
export function changeHeadline({ closed, opened, stillOpen }) {
  const parts = [];
  if (closed.length) parts.push(`${closed.length} ${closed.length === 1 ? "gap" : "gaps"} closed`);
  if (opened.length) parts.push(`${opened.length} new ${opened.length === 1 ? "gap" : "gaps"} found`);
  if (!parts.length) return "Nothing closed and nothing new.";
  const tail = stillOpen.length
    ? ` This promise still has ${stillOpen.length} open ${stillOpen.length === 1 ? "gap" : "gaps"}.`
    : closed.length && !opened.length ? " Nothing else is open on this promise." : "";
  return `${parts.join(" · ")}.${tail}`;
}

// "What changed" leads with the result (20 Oct): what was found, then what is still open on the commitment. Built from the
// finding labels only. A closed gap is never worded as "resolved"; the check found wording or an approval.
const CLOSED_PHRASE = {
  "No approval recorded": "Approval found",
  "Missing from contract": "Contract wording found",
  "Contract says something different": "Contract wording now matches the promise",
};
const OPEN_NOUN = {
  "No approval recorded": "the approval gap",
  "Missing from contract": "the contract gap",
  "Contract says something different": "the contract difference",
  "Not offered": "the not-offered gap",
};
export function changeResult({ closed = [], opened = [], stillOpen = [] }) {
  const done = [...new Set(closed.map((x) => CLOSED_PHRASE[x.finding] ?? `${FINDING_SHORT[x.finding] ?? x.finding}: closed`))];
  const nouns = [...new Set(stillOpen.map((x) => OPEN_NOUN[x.finding] ?? `the ${(FINDING_SHORT[x.finding] ?? x.finding).toLowerCase()} gap`))];
  const promises = new Set(stillOpen.map((x) => x.promise)).size;
  const parts = [...done];
  if (nouns.length) {
    const list = nouns.length > 1 ? `${nouns.slice(0, -1).join(", ")} and ${nouns[nouns.length - 1]}` : nouns[0];
    parts.push(promises > 1 ? `${list} ${nouns.length > 1 ? "are" : "is"} still open on ${promises} commitments`
      : `${list} on this commitment ${nouns.length > 1 ? "are" : "is"} still open`);
  }
  if (opened.length) parts.push(`${opened.length} new ${opened.length === 1 ? "gap" : "gaps"} found`);
  if (!parts.length) return "Nothing closed and nothing new: the document did not change any gap.";
  return `${parts.join(" · ")}${done.length && !nouns.length && !opened.length ? "" : "."}`;
}

// The one muted line under "Commitments" when proposed findings failed verification (20 Oct). Neutral: not a status, and it
// changes no count or verdict. Nothing when there were none, or when the record does not hold the count.
export function coverageLine(n) {
  const k = Number(n);
  if (!Number.isInteger(k) || k <= 0) return "";
  return `${k} proposed ${k === 1 ? "finding" : "findings"} couldn't be verified against the documents and ${k === 1 ? "isn't" : "aren't"} shown.`;
}

// The sidebar journey (20 Oct): only the current stage starts expanded; a click toggles any stage. Counts stay visible on every
// stage, so "which documents were checked" is answerable at a glance.
export const journeyOpen = (stages) => new Set((stages ?? []).filter((s) => s.state === "current").map((s) => s.key));
export const docCount = (n) => `${n} ${n === 1 ? "document" : "documents"}`;

// The closing reason the check wrote when a gap closed ("the pricing note now records an approval..."), as a sentence.
export function closingLine(reason) {
  const why = (reason ?? "").replace(/^Closed:\s*/, "").trim();
  return why ? why.charAt(0).toUpperCase() + why.slice(1) : "";
}


// --- Simplified deal page (19 Oct) ------------------------------------------------------------------------------------
// Everything below is built only from verified finding labels, stored terms and owner-confirmed wording, never from AI text.

export const FINDING_SHORT = {
  "No approval recorded": "No approval found",
  "Missing from contract": "Not in the contract",
  "Contract says something different": "Contract differs",
  "Not offered": "Not offered",
};
const FINDING_DETAIL = {
  "No approval recorded": "No approval found in the supplied documents",
  "Missing from contract": "Not in the draft contract or SOW",
  "Not offered": "Not offered: no exception can fix this; only changing the promise can",
};
const SHORT_TERM = 80; // a stored contract term longer than this is left to the drawer (28 Oct: was 45, before the contract line had its own line)

// The contract's own wording for a conflict, when it is short enough to sit on a one-line row.
function shortTerm(issue, contract) {
  const term = String(issue?.evidence?.contract_value || contract || "").trim();
  return term && term.length <= SHORT_TERM && !/^(not included|no matching wording found)$/i.test(term) ? term : "";
}

// What a finding is about (27 Oct). A finding about the promise ("Not offered", "No approval found", and any label not listed here) sits with
// the promise: a badge beside the title. A finding about the contract sits on the contract line. They are never joined into one sentence.
const CONTRACT_FINDINGS = ["Contract says something different", "Missing from contract"];

// The short labels of the findings about the promise, in the existing finding order, each once.
export function promiseLabels(issues) {
  const seen = new Set();
  const out = [];
  for (const i of issues ?? []) {
    if (CONTRACT_FINDINGS.includes(i.finding) || seen.has(i.finding)) continue;
    seen.add(i.finding);
    out.push(FINDING_SHORT[i.finding] ?? i.finding);
  }
  return out;
}

// The plain-text form (the locked record's printed line): "Promise: Not offered. Contract says: chat and email." It labels itself, so
// the relationship is explicit. The contract part follows the screen: a conflict takes precedence over a missing finding.
// issues: the findings still showing; contract: the row's stored contract term.
export function mismatchLine(issues, contract = "") {
  const list = issues ?? [];
  const promise = promiseLabels(list);
  const conflict = list.find((i) => i.finding === "Contract says something different");
  const missing = list.find((i) => i.finding === "Missing from contract");
  const out = [];
  if (promise.length) out.push(`Promise: ${promise.join(", ")}.`);
  if (conflict) {
    const term = shortTerm(conflict, contract);
    out.push(term ? `Contract says: "${term}".` : "Contract differs.");
  } else if (missing) {
    out.push("Contract has no matching wording.");
  }
  return out.join(" ");
}

// The long form, shown in front of the check's reason in the expanded row.
export function findingDetail(issue, contract = "") {
  if (issue.finding === "Contract says something different") {
    const term = String(issue.evidence?.contract_value || contract || "").trim();
    return term ? `The contract says something different: "${term}"` : "The contract says something different";
  }
  return FINDING_DETAIL[issue.finding] ?? issue.finding;
}

// "First found in the checked documents: RFP response, 29 Sep". `found` is the server's answer (workspace.first_found): the earliest
// dated checked document that contains one of the commitment's exact quoted sentences. Without it (a locked record, which holds no
// document text, or no current document contains the quote) it is the earliest statement's own source label and date, as before.
export function firstPromised(statements, found) {
  if (found?.doc_type_label) return `First found in the checked documents: ${found.doc_type_label}${found.date ? `, ${short(found.date)}` : ""}`;
  const dated = (statements ?? []).filter((s) => s.doc_type_label);
  if (!dated.length) return "";
  const first = [...dated].sort((a, b) => (a.date || "9999").localeCompare(b.date || "9999"))[0];
  return `First found in the checked documents: ${first.doc_type_label}${first.date ? `, ${short(first.date)}` : ""}`;
}

// The title shown for a commitment: the owner-confirmed plain title if there is one, otherwise the extracted name.
export const rowTitle = (c) => c.display_name || c.name;
export const extractedAs = (c) => (c.display_name && c.display_name !== c.name ? c.name : "");

// The handover record's honest verdict. "No open gaps" is never said when anything was addressed by note.
export function verdictLine({ open = 0, noted = 0, closed = 0 }) {
  if (!open) return noted ? `Handed over with no open gaps; ${noted} addressed by note${closed ? `, ${closed} closed by documents` : ""}.`
    : "Handed over with no open gaps on the documents checked.";
  const parts = [`${open} needing attention`];
  if (noted) parts.push(`${noted} addressed by note`);
  if (closed) parts.push(`${closed} closed by documents`);
  return `Handed over with ${parts.join(", ")}.`;
}

// The deal list's gap cell: "2 need attention", or "Nothing needs attention" with what a note settled.
export function attentionText(open, noted = 0) {
  if (open) return `${open} ${open === 1 ? "needs" : "need"} attention`;
  return noted ? `Nothing needs attention · ${noted} addressed by note` : "Nothing needs attention";
}

// The home list counts what it counts (20 Oct): tabs count deals, the column counts commitments.
export const dealsText = (n) => `${n} ${n === 1 ? "deal" : "deals"}`;
export function commitmentsNeedText(open, noted = 0) {
  if (open) return `${open} ${open === 1 ? "commitment needs" : "commitments need"} attention`;
  return attentionText(0, noted);
}

// Names are shown without the ", fictional" tag the demo data carries. Display only: nothing stored changes.
export const plainName = (name) => String(name ?? "").replace(/,\s*fictional\s*\)/gi, ")").replace(/\s*\(\s*fictional\s*\)/gi, "").trim();

// "Recorded by Sam · 16 Oct 2026"; the date is left out when the saved record has none.
export function recordedBy(by, at, fmt) {
  return `Recorded by ${plainName(by)}${at ? ` · ${fmt(at)}` : ""}`;
}

// The three row states, worded once for the live page and the frozen record. "Addressed by note" is outlined, never solid.
export const STATUS_CHIP = {
  open: { tone: "amber", label: "Needs attention", title: "The documents still differ and nobody has settled it." },
  noted: { tone: "note", label: "Addressed by note", title: "Addressed by a named person without a document. Not in the documents; reopens if the documents change." },
  closed: { tone: "green", label: "Closed by documents", title: "The current documents no longer show the gap." },
};

// A sentence ends once: the wording of a finding sometimes already ends in a full stop or a quote.
export const sentence = (text) => (/[.!?"]$/.test(text) ? text : `${text}.`);

// The explanation of how a commitment closes, once, for the pop-up and the one-line version inside dialogs.
export const CLOSING_ONE_LINE = "A commitment closes only when the check on the updated documents shows it no longer holds. A note never closes anything.";


// The deal's stages in order, each with the included documents placed there (19 Oct). The backend places each document by
// the stage bar's own rule and sends it as `stage`; a stage with no documents keeps its place with an empty list.
export function groupByStage(stages, documents) {
  return (stages ?? []).map((s) => ({
    ...s,
    docs: (documents ?? []).filter((d) => d.included !== false && d.stage === s.key)
      .sort((a, b) => (a.date ?? "").localeCompare(b.date ?? "") || a.source_key.localeCompare(b.source_key)),
  }));
}

// Shown under a signed document: it marks the deal signed and nothing else.
export const STAGE_LABELS = { discovery: "Discovery", evaluation: "Evaluation", proposal: "Proposal / RFP", shortlisted: "Shortlisted",
  contracting: "Contracting", signed: "Signed", handover: "Handover" };

// The one explanation the add-document form gives about closing (the gap-specific hint, when there is one, comes before it).
export const GAP_CLOSES = "A gap closes only if the new paperwork shows it no longer holds.";

export const SIGNED_NOTE = "Marks the deal signed. Its wording isn't checked; the checks used the drafts.";
export const isSignedDoc = (docType) => docType === "signed_contract" || docType === "signed_sow";

// "Tom Fraser (Account Executive, fictional)" and "draft SOW, 9 Oct" as the brief's footer shows them: name, role, initials, basis.
export function confirmedBy(brief) {
  const full = plainName(brief?.confirmed_by);
  const m = /^(.*?)\s*\((.*)\)$/.exec(full);
  const name = (m ? m[1] : full).trim();
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("") || "?";
  return { name, role: m ? m[2].trim() : "", initials, basis: String(brief?.basis ?? "").trim() };
}

// A sidebar document name without a date that only repeats the date column: "Call transcript of 15 Sep 2026" with date
// 2026-09-15 shows as "Call transcript". Display only; the stored name is untouched, and a different date is kept.
export function docLabel(name, iso) {
  const label = String(name ?? "");
  const m = /^(.*?)\s+(?:of|dated|from|on)?\s*(\d{1,2} [A-Za-z]{3,9} \d{4})$/.exec(label);
  if (!m) return label;
  const shown = (iso ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!shown) return label;
  const full = `${Number(shown[3])} ${MONTHS[Number(shown[2]) - 1]} ${shown[1]}`;
  const given = m[2].replace(/^(\d+ [A-Za-z]{3})[A-Za-z]* /, "$1 ");
  return given === full ? m[1] : label;
}

// --- The drawer (20 Oct) ----------------------------------------------------------------------------------------------
// Everything here is built from stored data: verified finding labels, stored short terms, exact quotes. Never from AI text,
// except `ai`, which carries the stored explanation separately so the screen can label it.

// The contract line as segments: [{ text, strong }] (27 Oct: the contract part only; findings about the promise are badges, see
// promiseLabels). Dark (strong) term, muted connecting words. Empty when there is no contract finding.
export function mismatchParts(issues, contract = "") {
  const list = issues ?? [];
  const conflict = list.find((i) => i.finding === "Contract says something different");
  const missing = list.find((i) => i.finding === "Missing from contract");
  if (conflict) {
    const term = shortTerm(conflict, contract);
    return term ? [{ text: "Contract says ", strong: false }, { text: term, strong: true }] : [{ text: "Contract differs", strong: true }];
  }
  if (missing) return [{ text: "Contract has ", strong: false }, { text: "no matching wording", strong: true }];
  return [];
}
export const partsText = (parts) => parts.map((p) => p.text).join("");

// The address bar: #d=<deal>&c=<commitment key>. The locked record uses the promise name as the key.
export const hashFor = ({ d, c } = {}) => {
  const q = [d && `d=${encodeURIComponent(d)}`, c && `c=${encodeURIComponent(c)}`].filter(Boolean).join("&");
  return q ? `#${q}` : "";
};
export function readHash(hash) {
  const out = { d: null, c: null };
  for (const part of String(hash ?? "").replace(/^#/, "").split("&")) {
    const [k, ...rest] = part.split("=");
    if (k === "d" || k === "c") {
      try { out[k] = decodeURIComponent(rest.join("=")) || null; } catch { out[k] = null; }
    }
  }
  return out;
}

// Which document a source points at: by label and date. Exactly one match makes it a link; none or several, plain text.
// labels: the names the source may go by (document label, document type label). date: the source's date, if it has one.
export function matchDoc(documents, labels, date) {
  const names = (labels ?? []).filter(Boolean);
  const hits = (documents ?? []).filter((d) => names.includes(d.name) || names.includes(d.doc_type_label))
    .filter((d) => !date || d.date === date);
  return hits.length === 1 ? hits[0] : null;
}

// The text split around a quoted sentence, so the quote can be highlighted. Spaces may differ; null when it is not there.
export function splitQuote(text, quote) {
  const q = String(quote ?? "").trim();
  if (!q || !text) return null;
  const at = text.indexOf(q);
  if (at >= 0) return { before: text.slice(0, at), match: q, after: text.slice(at + q.length) };
  const pattern = q.split(/\s+/).map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("\\s+");
  const m = new RegExp(pattern).exec(text);
  return m ? { before: text.slice(0, m.index), match: m[0], after: text.slice(m.index + m[0].length) } : null;
}

const uniq = (xs) => [...new Set(xs.filter(Boolean))];

// The stored closing text reads "Resolved by Draft SOW, version 2 · 16 Oct 2026"; the screen says "Closed by …" (display only).
// The date on a closing line is the day the check ran, so it says so (20 Oct): "· 20 Oct 2026" reads "· checked 20 Oct 2026". Applied at
// display, to stored strings too, so records locked earlier read the same way. Idempotent.
export const closedBy = (text) => String(text ?? "").replace(/^Resolved by /, "Closed by ")
  .replace(/ · (\d{1,2} [A-Z][a-z]{2} \d{4})/g, " · checked $1");

// "Gap closed: approval found in Pricing and services note, version 2" (21 Oct), for the drawer's "What closed it" and for print; the
// rows keep the short "Closed by …". Built from the finding's label and the stored closing text ("Resolved by A; B · C unchanged ·
// 16 Oct 2026 · signed off by X"), so records locked earlier read the same way. The documents that changed are what closed the gap; the
// ones that were checked with them, the check date and the sign-off are separate muted lines.
const GAP_CLOSED = {
  "No approval recorded": "approval found in",
  "Missing from contract": "contract wording found in",
  "Contract says something different": "contract wording now matches in",
  "Not offered": "promise changed in",
};
export function gapClosed(finding, text) {
  const parts = closedBy(text).trim().replace(/^Closed by /, "").split(" · ");
  const changed = parts[0] && parts[0] !== "Closed in the documents" ? parts[0] : "";
  const notes = [];
  const unchanged = parts.find((p) => / unchanged$/.test(p));
  if (unchanged) notes.push(`${unchanged.replace(/ unchanged$/, "")}: unchanged, checked with it`);
  const checked = parts.find((p) => /^checked /.test(p));
  if (checked) notes.push(`Check ${checked.replace(/^checked /, "on ")}`);
  const signed = parts.find((p) => /^signed off by /.test(p));
  if (signed) notes.push(signed[0].toUpperCase() + signed.slice(1));
  const what = GAP_CLOSED[finding] ?? "closed in";
  return { headline: changed ? `Gap closed: ${what} ${changed}` : "Gap closed in the documents", notes };
}

// The muted "Closed by …" lines under a closed row (20 Oct): the full stored text of each distinct closing, so every closing
// document shows. Texts are the stored ones ("Resolved by Draft SOW, version 2 · 16 Oct 2026"), shown as "Closed by …".
export const closedLines = (texts) => [...new Set((texts ?? []).map((t) => closedBy(t).trim()).filter(Boolean))];

// Signed-paperwork check (21 Oct, signed_check.py): a gap closed by a draft is checked against the signed contract or SOW. Three outcomes
// per closed gap: confirmed ("Confirmed in the signed contract (Signed contract, 20 Oct)"), not found (the commitment is Needs attention
// again, with the reason and the earlier closure kept visible), and not confirmed (neutral: there was no wording to look for).
const lowerFirst = (t) => (/^[A-Z][a-z]/.test(t) ? t[0].toLowerCase() + t.slice(1) : t);
export const reopenedBySigned = (issues) => (issues ?? []).filter((i) => i.signed_check?.status === "not_found");
export const earlierLine = (sc) => (sc?.earlier ? `Earlier ${lowerFirst(closedBy(sc.earlier))}` : "");
// The lines under a closed commitment: what the signed paperwork says about its fixes.
export const signedConfirmations = (checks) => [...new Set((checks ?? []).filter((c) => c && (c.status === "confirmed" || c.status === "not_confirmed")).map((c) => c.text))];
// The lines under a commitment that is open again: why, and what closed it before.
export const reopenedLines = (issues) => reopenedBySigned(issues).flatMap((i) => [i.signed_check.reason, earlierLine(i.signed_check)]).filter(Boolean);

// No sentence is shown twice between "Contract says" and "What we found" (21 Oct). A finding's body is dropped, sentence by sentence, when it
// is the same sentence the contract side already says (case, quotes and punctuation aside); the finding then shows with its title only.
// Nothing is reworded: only exact or near-exact repeats go. Partial overlaps (a body that quotes the contract term inside a longer
// sentence) stay as they are.
const sentenceKey = (s) => String(s ?? "").replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const sentencesOf = (t) => String(t ?? "").split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);
export function contractSaid(c) {
  const searched = c.missing?.length ? `${c.missingLabel} ${c.missing.map((m) => `“${m}”`).join(", ")}` : "";
  return [c.text, searched, c.quote?.quote, c.now?.quote].filter(Boolean).flatMap(sentencesOf);
}
export function withoutRepeats(found, contract) {
  const said = new Set(contractSaid(contract).map(sentenceKey));
  return found.map((f) => ({ ...f, fact: sentencesOf(f.fact).filter((s) => !said.has(sentenceKey(s))).join(" ") }));
}

// One commitment, as the drawer shows it. status: "open" | "noted" | "closed".
export function commitmentView(c, status, documents) {
  const unresolved = c.issues.filter((i) => i.state !== "Resolved");
  const closedIssues = c.issues.filter((i) => i.state === "Resolved");
  const shown = status === "closed" ? closedIssues : unresolved;
  const noteRes = unresolved.find((i) => i.note_resolution)?.note_resolution ?? null;
  const side = contractSide(unresolved, c.contract); // a closed commitment has no open contract finding: its short term stands alone
  const contract = contractView(c.contract, side, documents, c.contract_now, missingPhrases(unresolved));
  const notes = [];
  if (noteRes) notes.push({ by: noteRes.by, at: noteRes.at, text: noteRes.reason, kind: status === "noted" ? "addressed" : "reopened" });
  for (const d of new Map(unresolved.filter((i) => i.decision && i.decision.status !== "none").map((i) => [`${i.decision.by}|${i.decision.reason}`, i.decision])).values()) {
    notes.push({ by: d.by, at: d.at, text: d.reason, kind: d.status === "reconfirm" ? "reconfirm" : "kept" });
  }
  return {
    key: c.ref ?? null, title: rowTitle(c), extracted: extractedAs(c), status,
    first: firstPromised(c.statements, c.first_found), mismatch: mismatchParts(unresolved, c.contract), badges: promiseLabels(unresolved), plain: mismatchLine(unresolved, c.contract),
    told: toldQuotesWithDocs(c.statements, documents),
    contract,
    found: status === "closed" ? [] : withoutRepeats(unresolved.map((i) => ({ label: findingDetail(i, c.contract),
      fact: i.signed_check?.status === "not_found" ? i.signed_check.reason : gapLine(i.finding, i.evidence, i.catalogue_path) })), contract),
    earlier: reopenedBySigned(unresolved).map((i) => earlierLine(i.signed_check)).filter(Boolean),
    signedLines: signedConfirmations(closedIssues.map((i) => i.signed_check)),
    reopenedLines: reopenedLines(unresolved),
    closedLines: closedLines(closedIssues.map((i) => i.resolved_by?.text)),
    closed: closedIssues.map((i) => ({ label: FINDING_SHORT[i.finding] ?? i.finding, by: closedBy(i.resolved_by?.text) || (status === "closed" ? "Closed in the documents" : ""),
      gap: gapClosed(i.finding, i.resolved_by?.text) })),
    catalogue: status === "closed" ? [] : uniq(unresolved.map((i) => i.catalogue_path)),
    ai: status === "closed" ? [] : uniq(shown.filter((i) => i.signed_check?.status !== "not_found").map((i) => cleanReason(i.reason))),
    notes, seen: [...new Map(unresolved.flatMap((i) => i.seen || []).map((s) => [s.by, s])).values()],
    issueIds: unresolved.map((i) => i.id),
  };
}

function toldQuotesWithDocs(statements, documents) {
  const seen = new Set();
  return (statements ?? []).filter((s) => s.quote && !seen.has(s.quote) && seen.add(s.quote))
    .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
    .map((s) => ({ quote: s.quote, label: s.doc_type_label ?? s.source, date: s.date ?? "", doc: matchDoc(documents, [s.source_name, s.doc_type_label], s.date) }));
}

// The phrases searched for and not found, from the open findings' verified evidence.
export const missingPhrases = (issues) => [...new Set((issues ?? []).flatMap((i) => i.evidence?.missing_phrases ?? []))];

// The contract side of a commitment. With a contract quote AND a missing-wording finding (a conflict and a gap on one promise), the
// quote comes first and the missing line says what was searched for, so the two never read as a contradiction (20 Oct). `now` is the
// contract wording found by lookup for a closed gap; it is labelled as a lookup, never as why the gap closed.
function contractView(term, side, documents, now = null, searched = []) {
  const quote = side.quote ? { quote: side.quote, label: side.source, doc: matchDoc(documents, [side.source], null) } : null;
  const missing = side.missing ?? (quote && searched.length ? searched : null);
  return {
    text: quote && missing ? "" : contractText(term),
    quote,
    missing,
    missingLabel: quote && missing ? "No matching wording found for" : "Searched for:",
    now: now?.quote ? { target: now.target, quote: now.quote, label: now.document, doc: matchDoc(documents, [now.document], null) } : null,
  };
}

// A commitment in the locked record, as the same view. The snapshot holds less than the live register, so what it lacks is
// left out, never invented. item: an open or addressed-by-note entry, or { promise } for one whose gaps all closed.
export function frozenView({ item, status, closedFindings = [], documents = [], titles = {} }) {
  const name = item.promise;
  const findings = item.findings ?? [];
  const quoted = (item.quotes ?? []).filter((q) => q.quote);
  const statements = quoted.length ? quoted.map((q) => ({ doc_type_label: q.source, date: q.date, quote: q.quote }))
    : (item.told_in ?? []).map(([label, date]) => ({ doc_type_label: label, date }));
  const issues = findings.map((f) => ({ finding: f.finding, evidence: f.evidence, catalogue_path: f.catalogue_path, signed_check: f.signed_check }));
  const side = contractSide(findings, item.contract);
  const notes = [];
  for (const n of new Map(findings.filter((f) => f.note).map((f) => [`${f.note.by}|${f.note.reason}`, f.note])).values()) {
    notes.push({ by: n.by, at: n.at, text: n.reason, kind: n.current ? "kept" : "reconfirm" });
  }
  const addressed = findings.find((f) => f.resolved_by_note)?.resolved_by_note;
  if (addressed) notes.push({ by: addressed.by, at: addressed.at, text: addressed.reason, kind: "addressed" });
  const seenAll = findings.flatMap((f) => f.seen ?? []);
  const contract = contractView(item.contract, side, documents, item.contract_now, missingPhrases(findings));
  const title = titles[name] || name;
  return {
    key: name, title, extracted: titles[name] && titles[name] !== name ? name : "", status,
    first: firstPromised(statements, item.first_found), mismatch: mismatchParts(issues, item.contract), badges: promiseLabels(issues), plain: mismatchLine(issues, item.contract),
    told: quoted.length ? quoted.map((q) => ({ quote: q.quote, label: q.source, date: q.date ?? "", doc: matchDoc(documents, [q.source], q.date) })) : [],
    toldFallback: item.told ?? "",
    contract,
    found: withoutRepeats(issues.map((i, n) => ({ label: findingDetail(i, item.contract),
      fact: i.signed_check?.status === "not_found" ? i.signed_check.reason : gapLine(i.finding, i.evidence, i.catalogue_path) })), contract),
    earlier: reopenedBySigned(issues).map((i) => earlierLine(i.signed_check)).filter(Boolean),
    signedLines: signedConfirmations(item.signed),
    reopenedLines: reopenedLines(issues),
    closedLines: closedLines(closedFindings.map((r) => r.resolved_by)),
    closed: closedFindings.map((r) => ({ label: FINDING_SHORT[r.finding] ?? r.finding, by: closedBy(r.resolved_by), gap: gapClosed(r.finding, r.resolved_by) })),
    catalogue: uniq(issues.map((i) => i.catalogue_path)),
    ai: status === "closed" ? [] : uniq(findings.filter((f) => f.signed_check?.status !== "not_found").map((f) => cleanReason(f.why))),
    notes, seen: [...new Map(seenAll.map((s) => [s.by, s])).values()], issueIds: [],
  };
}

// True while a header card has scrolled up out of view beneath the top bar (not while it is merely below the fold).
export const headerScrolledPast = (isIntersecting, bottom, rootTop = 0) => !isIntersecting && bottom <= rootTop + 1;
