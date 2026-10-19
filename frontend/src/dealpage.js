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
             hint: "A named approval in the pricing note can close the approval gap." +
                   (alsoContract ? " The contract gap needs a contract or SOW update; it stays open until then." : " Add the new version of the pricing note.") };
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
  if (term === "Not included") return "No matching wording found";
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
        return `${n(ev.promised_quantity)} is above ${limit}; a named approval is needed and the pricing note records none.`;
      }
      return "The catalogue needs a named approval for this, and the pricing note records none.";
    case "Missing from contract":
      return "No matching wording found in the draft contract or SOW.";
    case "Contract says something different":
      return ev.promised_value && ev.contract_value
        ? `Told "${ev.promised_value}"; the contract says "${ev.contract_value}".`
        : "The contract covers this on different terms.";
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
// name is asked for when the button is pressed (19 Oct).
export function missingForHandover({ isSigned, notes }) {
  const out = [];
  if (!isSigned) out.push("save the signing date");
  if (!notes?.sales) out.push("add the Sales note");
  if (!notes?.delivery) out.push("add the Delivery note");
  return out;
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

// The closing reason the check wrote when a gap closed ("the pricing note now records an approval..."), as a sentence.
export function closingLine(reason) {
  const why = (reason ?? "").replace(/^Closed:\s*/, "").trim();
  return why ? why.charAt(0).toUpperCase() + why.slice(1) : "";
}


// --- Simplified deal page (19 Oct) ------------------------------------------------------------------------------------
// Everything below is built only from verified finding labels, stored terms and owner-confirmed wording, never from AI text.

export const FINDING_SHORT = {
  "No approval recorded": "Not approved internally",
  "Missing from contract": "Not in the contract",
  "Contract says something different": "Contract differs",
  "Not offered": "Not offered",
};
const FINDING_DETAIL = {
  "No approval recorded": "No approval found in the supplied documents",
  "Missing from contract": "Not in the draft contract or SOW",
  "Not offered": "Not offered: no exception can fix this; only changing the promise can",
};
const SHORT_TERM = 45; // a stored contract term longer than this is left to the expanded row

// The contract's own wording for a conflict, when it is short enough to sit on a one-line row.
function shortTerm(issue, contract) {
  const term = String(issue?.evidence?.contract_value || contract || "").trim();
  return term && term.length <= SHORT_TERM && !/^(not included|no matching wording found)$/i.test(term) ? term : "";
}

// "Not approved internally · Not in the contract": the short form of each open finding, joined with " · ".
// issues: the findings still showing; contract: the row's stored contract term.
export function mismatchLine(issues, contract = "") {
  const seen = new Set();
  const parts = [];
  for (const i of issues ?? []) {
    const label = i.finding;
    if (seen.has(label)) continue;
    seen.add(label);
    const short = FINDING_SHORT[label] ?? label;
    const term = label === "Contract says something different" ? shortTerm(i, contract) : "";
    parts.push(term ? `${short}: ${term}` : short);
  }
  return parts.join(" · ");
}

// The long form, shown in front of the check's reason in the expanded row.
export function findingDetail(issue, contract = "") {
  if (issue.finding === "Contract says something different") {
    const term = String(issue.evidence?.contract_value || contract || "").trim();
    return term ? `The contract says something different: "${term}"` : "The contract says something different";
  }
  return FINDING_DETAIL[issue.finding] ?? issue.finding;
}

// "First promised in the RFP response, 29 Sep": the earliest statement's source label and date.
export function firstPromised(statements) {
  const dated = (statements ?? []).filter((s) => s.doc_type_label);
  if (!dated.length) return "";
  const first = [...dated].sort((a, b) => (a.date || "9999").localeCompare(b.date || "9999"))[0];
  const label = /^[A-Z][a-z]/.test(first.doc_type_label) ? first.doc_type_label[0].toLowerCase() + first.doc_type_label.slice(1) : first.doc_type_label;
  return `First promised in the ${label}${first.date ? `, ${short(first.date)}` : ""}`;
}

// The title shown for a commitment: the owner-confirmed plain title if there is one, otherwise the extracted name.
export const rowTitle = (c) => c.display_name || c.name;
export const extractedAs = (c) => (c.display_name && c.display_name !== c.name ? c.name : "");

// "3 need attention · 1 addressed by note · 1 closed by documents": zero parts are left out.
export function countsLine({ open = 0, noted = 0, closed = 0 }) {
  const parts = [];
  parts.push(open ? `${open} ${open === 1 ? "needs" : "need"} attention` : (noted || closed) ? "Nothing needs attention" : "");
  if (noted) parts.push(`${noted} addressed by note`);
  if (closed) parts.push(`${closed} closed by documents`);
  return parts.filter(Boolean).join(" · ");
}

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

// "Stage: Contracting · gaps first made at Proposal / RFP"
export function stageLine(stage) {
  if (!stage?.current) return "";
  const where = (stage.stages ?? []).filter((s) => s.gaps_started > 0).map((s) => s.label);
  return `Stage: ${stage.current_label}${where.length ? ` · gaps first made at ${where.join(" and ")}` : ""}`;
}

// "Recorded by Sam · 16 Oct 2026"; the date is left out when the saved record has none.
export function recordedBy(by, at, fmt) {
  return `Recorded by ${by}${at ? ` · ${fmt(at)}` : ""}`;
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
