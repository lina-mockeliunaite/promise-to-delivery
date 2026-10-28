// The landing page (20 Oct): shown on the first visit, then the home list straight away. Remembered per browser only, in
// localStorage; when storage is unavailable the landing page shows. Pure helpers, so they are tested without a browser.
import { mismatchParts, promiseLabels, rowTitle, toldParts } from "./dealpage.js";

export const SEEN_KEY = "ptd.landingSeen";
// The two sample scenarios the landing page offers (20 Oct): same engine, two vendors' catalogues. Labels are fixed wording; each
// card's mismatch is read from that deal's own stored register.
export const SAMPLES = [
  { deal: "noma_journeys", title: "AI support assistant", parties: "Aivuna / Noma Journeys" },
  { deal: "alder_bank", title: "Financial services, scam protection", parties: "Elva / Alder Bank" },
];
// The landing cards are a summary, not a quote (28 Oct): a term is cut at its first colon, the number words one to twelve are shown as digits, and the
// contract line says "Contract has" instead of "Contract says". The deal page, the drawer, the locked record and print keep the exact stored wording
// and "Contract says"; the evidence lives there. Nothing stored is changed.
const NUMBER_WORDS = { one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10, eleven: 11, twelve: 12 };
export function cardTerm(term) {
  const cut = String(term ?? "").split(":")[0].trim();
  // whole words only, and not inside a hyphenated word ("one-time")
  return cut.replace(/(?<![-\w])(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)(?![-\w])/gi, (w) => String(NUMBER_WORDS[w.toLowerCase()]));
}
export const cardParts = (parts) => (parts ?? []).map((p) => (p.strong ? { ...p, text: cardTerm(p.text) } : p.text === "Contract says " ? { ...p, text: "Contract has " } : p));

export const availableSamples = (deals) => SAMPLES.filter((s) => (deals ?? []).some((d) => d.deal === s.deal));

// 21 Oct: #welcome always shows the landing page, whatever this browser has stored (a link for demos and for "About Dealshape").
// A normal visit is unchanged: the landing page shows on the first visit only.
export const WELCOME_HASH = "#welcome";
export const isWelcome = (hash) => String(hash ?? "").replace(/^#/, "").split("&").includes("welcome");
export const showLanding = (hash, seen, deal) => isWelcome(hash) || (!deal && !seen);

export function landingSeen(storage = globalThis.localStorage) {
  try { return storage.getItem(SEEN_KEY) === "1"; } catch { return false; }
}
export function markLandingSeen(storage = globalThis.localStorage) {
  try { storage.setItem(SEEN_KEY, "1"); } catch { /* private window: the landing page shows again next time */ }
}

// One concrete mismatch from the sample deal's stored register. Title and lines come from the same helpers as the deal page rows; nothing is
// written by hand. The rule (28 Oct), computed from the stored register only:
//  1. Eligible: an open commitment with a stored customer term and a stored contract term (a "Contract says something different" finding
//     that has both promised_value and contract_value). With none eligible, the earlier rule: the commitment the product doesn't offer if
//     there is one, else the first with an open gap.
//  2. Among the eligible, prefer one whose finding kinds are not already shown on an earlier card (`shown`), so the cards show different
//     kinds of mismatch; then the one with the fewest findings (the plainest comparison); then the register's order.
export function pickMismatch(register, shown = new Set()) {
  const open = (register?.commitments ?? []).map((c) => ({ c, issues: c.issues.filter((i) => i.state !== "Resolved") })).filter((x) => x.issues.length);
  const terms = (x) => x.issues.some((i) => i.finding === "Contract says something different"
    && String(i.evidence?.promised_value ?? "").trim() && String(i.evidence?.contract_value ?? "").trim());
  const eligible = open.map((x, order) => ({ ...x, order })).filter(terms);
  const fresh = (x) => (x.issues.some((i) => !shown.has(i.finding)) ? 0 : 1);
  const pick = eligible.length
    ? [...eligible].sort((a, b) => fresh(a) - fresh(b) || a.issues.length - b.issues.length || a.order - b.order)[0]
    : open.find((x) => x.issues.some((i) => i.finding === "Not offered")) ?? open[0];
  if (!pick) return null;
  return { title: rowTitle(pick.c), badges: promiseLabels(pick.issues), kinds: [...new Set(pick.issues.map((i) => i.finding))],
    // the landing cards carry the terms only (28 Oct); rows, the locked record, the drawer and print keep the sources
    told: cardParts(toldParts(pick.issues, pick.c.statements, pick.c.first_found, { source: false })), parts: cardParts(mismatchParts(pick.issues, pick.c.contract, { source: false })) };
}

// The picks for all cards, in card order, each avoiding the finding kinds already shown. registers: one register (or null) per card.
export function pickMismatches(registers) {
  const shown = new Set();
  return (registers ?? []).map((r) => {
    const pick = pickMismatch(r, shown);
    (pick?.kinds ?? []).forEach((k) => shown.add(k));
    return pick;
  });
}
