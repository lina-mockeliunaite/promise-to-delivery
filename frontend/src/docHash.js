// Document hashes for the locked handover record (21 Oct). The stored hash is the SHA-256 of the UTF-8 bytes of the text Dealshape
// read (source_versions.canonical_text, line endings already LF). The browser hashes the text it receives from the server the same
// way: TextEncoder gives UTF-8, nothing is trimmed, normalised or re-ended, so a correct document never shows a false mismatch.
// Pure apart from crypto.subtle, so it is tested without a browser.

export async function sha256Hex(text) {
  const bytes = new TextEncoder().encode(String(text ?? ""));
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// "3fa9c1d20b7e…91ac": the first 12 and the last 4 characters; the full hash goes in a title and in the print appendix.
export const shortHash = (h) => (h && h.length > 20 ? `${h.slice(0, 12)}…${h.slice(-4)}` : h || "");

// A document in a locked record is openable only when the record stored its version and hash (records locked from 21 Oct). Older
// records are left plain: no best-effort matching.
export const hasStoredText = (d) => Boolean(d && d.source_version_id && d.sha256);

// { ok: true } when the text received hashes to the stored hash; { ok: false, expected, actual } when it does not. Never throws.
export async function verifyText(text, stored) {
  try {
    const actual = await sha256Hex(text);
    return actual === String(stored).toLowerCase() ? { ok: true, actual } : { ok: false, expected: stored, actual };
  } catch {
    return { ok: false, expected: stored, actual: "", unavailable: true };
  }
}

// The print appendix: one entry per document with a stored hash, each starting on a new page. texts: { [source_version_id]: text }.
// The text is carried exactly as read, never reformatted.
export function appendixEntries(documents, texts) {
  return (documents ?? []).filter(hasStoredText).map((d) => ({
    key: `${d.source_version_id}`, name: d.name, version: d.version, date: d.version_date || d.date || "", sha256: d.sha256,
    text: texts?.[d.source_version_id] ?? null,
  }));
}
