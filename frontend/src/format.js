// Display formats: '28 Sep 2026' for dates, '5 Oct 2026, 11:02' (the viewer's local time) for timestamps.
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? "");
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : (iso ?? "");
}

export function fmtDateTime(iso) {
  const d = new Date(iso);
  if (!iso || Number.isNaN(d.getTime())) return iso ?? "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// "Recheck: closed — A, B. Still open — C." `before` are the issues that were open when the fix was recorded,
// `after` the commitment's issues once the recheck has run (each with id, label and state).
export function recheckLine(before, after) {
  const list = (items) => items.map((i) => i.label).join(", ");
  const stateById = new Map(after.map((i) => [i.id, i.state]));
  const closed = before.filter((i) => !stateById.has(i.id) || stateById.get(i.id) === "Resolved");
  const stillOpen = after.filter((i) => i.state !== "Resolved");
  const first = closed.length ? `closed — ${list(closed)}.` : "nothing closed.";
  const second = stillOpen.length ? `Still open — ${list(stillOpen)}.` : "Nothing still open.";
  return `Recheck: ${first} ${second}`;
}

// Uploads: PDF, Word, Excel and PowerPoint travel as base64 inside the JSON body; Markdown and text as text. The server checks again.
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export function uploadKind(name) {
  const ext = (/\.[^./\\]+$/.exec(name ?? "")?.[0] ?? "").toLowerCase();
  if (ext === ".md" || ext === ".txt") return "text";
  if (ext === ".pdf" || ext === ".docx" || ext === ".xlsx" || ext === ".pptx") return "binary";
  return null;
}

export function checkUpload(name, size) {
  if (/\.doc$/i.test(name ?? "")) return "Older Word files (.doc) are not supported. Save the document as .docx and upload that.";
  if (/\.(xls|xlsm|xlsb)$/i.test(name ?? "")) return "This build reads Excel files saved as .xlsx (no macros). Save the workbook as .xlsx and upload that.";
  if (/\.(ppt|pptm|pps|ppsx)$/i.test(name ?? "")) return "This build reads PowerPoint files saved as .pptx (no macros). Save the deck as .pptx and upload that.";
  if (!uploadKind(name)) return "This build reads PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), Markdown and text files.";
  if (size > MAX_UPLOAD_BYTES) return "The file is larger than 10 MB.";
  return null;
}

// --- Fix inside the finding (layout redesign, 9 Oct) ---------------------------------------------------------------
// What a document of each type counts as, in the words the confirm-type step shows before anything is saved.
export const TYPE_EFFECT = {
  pricing_services_note: "Counts as approval evidence",
  draft_sow: "Counts as contract terms (the contract incorporates the SOW)",
  draft_contract: "Counts as contract terms",
  proposal: "Read for promises; not approval, not contract terms",
  rfp_response: "Read for promises; not approval, not contract terms",
  call_transcript: "Read for promises; not approval, not contract terms",
  customer_email: "Read for promises; not approval, not contract terms",
  security_questionnaire: "Read for promises; not approval, not contract terms",
};

// The type a file name points to, or null. Only a hint: the person confirms the type.
export function typeFromName(name) {
  const n = (name ?? "").toLowerCase();
  if (/pricing|exception|approval/.test(n)) return "pricing_services_note";
  if (/\bsow\b|sow[_-]|annex|statement.of.work/.test(n)) return "draft_sow";
  if (/contract|agreement|\bmsa\b/.test(n)) return "draft_contract";
  if (/proposal/.test(n)) return "proposal";
  if (/rfp/.test(n)) return "rfp_response";
  if (/transcript|call/.test(n)) return "call_transcript";
  if (/email/.test(n)) return "customer_email";
  if (/questionnaire/.test(n)) return "security_questionnaire";
  return null;
}

// Pre-selected type: the file name first, then what usually closes this kind of finding.
export function guessType(name, findingType) {
  return (
    typeFromName(name) ??
    (findingType === "approval" ? "pricing_services_note" : findingType === "contract_gap" || findingType === "conflicting_terms" ? "draft_sow" : "proposal")
  );
}

// "Checked Pricing and services note, version 2. Closed: No approval recorded. Still open: Missing from contract."
export function checkLine(result) {
  const closed = result.closed.length ? `Closed: ${result.closed.join("; ")}.` : "Nothing closed.";
  const open = result.still_open.length ? `Still open: ${result.still_open.join("; ")}.` : "Nothing still open on this commitment.";
  return `Checked ${result.document}. ${closed} ${open}`;
}

// Cross-finding effects, stated: the other findings the same document closed (here, then anywhere else in the deal).
export function alsoLine(result, findingLabel) {
  const here = result.closed.filter((label) => label !== findingLabel);
  const parts = [...here, ...result.closed_elsewhere.map((x) => `${x.finding} (${x.commitment})`)];
  return parts.length ? `This document also resolved: ${parts.join("; ")}.` : "";
}

// "8 findings unresolved", "1 finding unresolved"
export const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
