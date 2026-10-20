// The landing page (20 Oct): shown on the first visit, then the home list straight away. Remembered per browser only, in
// localStorage; when storage is unavailable the landing page shows. Pure helpers, so they are tested without a browser.
import { mismatchParts, rowTitle } from "./dealpage.js";

export const SEEN_KEY = "ptd.landingSeen";
export const SAMPLE_DEAL = "alder_bank";

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
  return { title: rowTitle(pick.c), parts: mismatchParts(pick.issues, pick.c.contract) };
}
