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

// One concrete mismatch from the sample deal's stored register: the commitment the product doesn't offer if there is one, else
// the first with an open gap. Title and line come from the same helpers as the deal page rows; nothing is written by hand.
export function pickMismatch(register) {
  const open = (register?.commitments ?? []).map((c) => ({ c, issues: c.issues.filter((i) => i.state !== "Resolved") })).filter((x) => x.issues.length);
  const pick = open.find((x) => x.issues.some((i) => i.finding === "Not offered")) ?? open[0];
  if (!pick) return null;
  return { title: rowTitle(pick.c), badges: promiseLabels(pick.issues), // the landing cards carry the terms only (28 Oct); rows, the locked record, the drawer and print keep the sources
    told: toldParts(pick.issues, pick.c.statements, pick.c.first_found, { source: false }), parts: mismatchParts(pick.issues, pick.c.contract, { source: false }) };
}
