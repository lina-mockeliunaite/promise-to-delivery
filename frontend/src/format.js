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

// The types whose own heading is clear enough to question a filing: a draft contract, a draft SOW, a pricing note, a proposal or an
// RFP response (20 Oct). A file's heading is its own statement of what it is, so it counts even when the file name is silent.
const HEADING_TYPES = ["draft_contract", "draft_sow", "pricing_services_note", "proposal", "rfp_response"];

// What a file says it is, or null. A signed document is recognised by its name or its heading. Otherwise the heading decides when it
// names one of the types above; failing that, the name and the heading must agree. The name alone is not enough, and a Word or PDF
// file has no readable heading here (the form reads the start of Markdown and text files only), so for those only a name-recognised
// signed document is questioned.
export function detectedType({ fileName, head }) {
  const byName = typeFromName(fileName);
  const byText = typeFromText(head);
  if (byText && SIGNED_TYPES.includes(byText)) return byText;
  if (byName && SIGNED_TYPES.includes(byName)) return byName;
  if (byText && HEADING_TYPES.includes(byText)) return byText;
  if (byText && byText === byName) return byText;
  return null;
}

// A light, non-blocking question when the file and the chosen type clearly disagree. "" when nothing looks wrong.
// target: { type, name } where name is set when the file is a new version of an existing document. labels: { type: "Label" }.
export function uploadMismatch({ fileName, head, target, labels }) {
  const guess = detectedType({ fileName, head });
  if (!guess || !target?.type || guess === target.type) return "";
  const label = (t) => lowerFirst(labels?.[t] ?? t);
  const asWhat = target.name ? `a new version of ${target.name}` : withArticle(label(target.type));
  return `This looks like ${withArticle(label(guess))}. Add it as ${asWhat} anyway?`;
}

const CONTRACT_TERMS = ["draft_contract", "draft_sow"];

// What filing it that way would do, in words (20 Oct): the consequence is stated, not just the disagreement.
function consequence(guess, target, asWhat, label) {
  const filed = `Filed as ${asWhat}, it`;
  if (target.name) return `${filed} replaces ${target.name}'s wording and can close gaps it shouldn't.`;
  if (target.type === "pricing_services_note") return `${filed} would count as approval evidence, which it isn't.`;
  if (SIGNED_TYPES.includes(target.type)) return `${filed} would mark the deal Signed, but it isn't signed.`;
  if (SIGNED_TYPES.includes(guess)) return `${filed} will be checked like a draft, and it won't mark the deal Signed.`;
  if (guess === "pricing_services_note") return `${filed} won't close the approval gap.`;
  if (CONTRACT_TERMS.includes(guess) && CONTRACT_TERMS.includes(target.type)) return `${filed} is read as that type rather than as ${withArticle(label(guess))}.`;
  if (CONTRACT_TERMS.includes(guess)) return `${filed} won't count as contract terms, so it won't close a contract gap.`;
  return `${filed} is read as that type rather than as ${withArticle(label(guess))}.`;
}

// The wrong-file notice (20 Oct): what the file looks like, what filing it that way would do, the right action as the primary button
// (a new version of the deal's own document of that type when there is exactly one, else that type), and a quiet way to go ahead anyway.
// null when nothing looks wrong. documents: the deal's documents ({ source_key, name, doc_type }).
export function mismatchNotice({ fileName, head, target, documents, labels }) {
  const guess = detectedType({ fileName, head });
  if (!guess || !target?.type || guess === target.type) return null;
  const label = (t) => lowerFirst(labels?.[t] ?? t);
  const asWhat = target.name ? `a new version of ${target.name}` : withArticle(label(target.type));
  const same = (documents ?? []).filter((d) => d.doc_type === guess);
  const use = same.length === 1
    ? { source_key: same[0].source_key, doc_type: "", text: `Use “A new version of ${same[0].name}”` }
    : { source_key: "", doc_type: guess, text: `Use “${labels?.[guess] ?? guess}” as the type` };
  return {
    guess,
    question: `This looks like ${withArticle(label(guess))}.`,
    consequence: consequence(guess, target, asWhat, label),
    use,
    anyway: target.name ? `Add as ${asWhat} anyway` : `Add as ${label(target.type)} anyway`,
  };
}

// "+ Add" from the sidebar has no commitment to take a document from, so it suggests (never applies) the document the file looks like
// a new version of: first by the file name starting with a document's source key ("NJ-07_…"), then by the heading's type when exactly one
// document of that type is in the deal. A signed document is never suggested as a new version of a draft. null when nothing is clear.
export function suggestVersionOf({ fileName, head, documents }) {
  const name = String(fileName ?? "").toLowerCase();
  const docs = documents ?? [];
  const byKey = docs.find((d) => d.source_key && name.startsWith(d.source_key.toLowerCase()) && !/^[a-z0-9]/.test(name.slice(d.source_key.length, d.source_key.length + 1)));
  if (byKey) return byKey;
  const type = typeFromText(head);
  if (!type || SIGNED_TYPES.includes(type)) return null;
  const same = docs.filter((d) => d.doc_type === type);
  return same.length === 1 ? same[0] : null;
}

// A new document needs a chosen type, or a chosen document to be a new version of: there is no silent default (20 Oct).
export const addReady = ({ file, source_key, doc_type }) => Boolean(file && (source_key || doc_type));

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
