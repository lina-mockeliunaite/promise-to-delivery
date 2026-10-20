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
  if (/signed[\s_.-]*(sow|statement)/.test(n)) return "signed_sow";
  if (/signed[\s_.-]*(contract|agreement|msa)/.test(n)) return "signed_contract";
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

// What the start of a text file says it is (its first heading or line, or a signature block), or null. Only a hint.
export function typeFromText(head) {
  const text = String(head ?? "");
  const first = (text.split(/\r?\n/).find((l) => l.trim()) ?? "").replace(/^#+\s*/, "").toLowerCase();
  const signedClue = /\bsigned (copy|version)\b|\(signed\)|\bexecuted (copy|version)\b/.test(first)
    || (/^#{1,3}\s*signatures?\b/im.test(text) && /signed for and on behalf of/i.test(text));
  if (signedClue) return /statement of work|\bsow\b/.test(first) ? "signed_sow" : "signed_contract";
  return typeFromName(first);
}

const SIGNED_TYPES = ["signed_contract", "signed_sow"];
const lowerFirst = (t) => (/^[A-Z][a-z]/.test(t) ? t[0].toLowerCase() + t.slice(1) : t);
const withArticle = (t) => `${/^(RFP|[AEIOU])/.test(t) ? "an" : "a"} ${t}`;

// A light, non-blocking question when the file and the chosen type clearly disagree: a signed document going in as a draft, a
// draft going in as signed, or the file's name and its own heading agreeing on a different type. "" when nothing looks wrong.
// target: { type, name } where name is set when the file is a new version of an existing document. labels: { type: "Label" }.
export function uploadMismatch({ fileName, head, target, labels }) {
  const byName = typeFromName(fileName);
  const byText = typeFromText(head);
  const guess = byText && SIGNED_TYPES.includes(byText) ? byText : byName && SIGNED_TYPES.includes(byName) ? byName : byText && byText === byName ? byText : null;
  if (!guess || !target?.type || guess === target.type) return "";
  const label = (t) => lowerFirst(labels?.[t] ?? t);
  const asWhat = target.name ? `a new version of ${target.name}` : withArticle(label(target.type));
  return `This looks like ${withArticle(label(guess))}. Add it as ${asWhat} anyway?`;
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
