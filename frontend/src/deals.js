// Deal list logic (16 Oct, Stitch screen 1). Pure functions, so they are tested without a browser.
// open_gaps counts commitments that need attention, as the stage bar does; addressed_by_note counts those a note settled.
// Every figure on the home screen is computed here from /api/workspace/deals: nothing is invented or estimated.

// 11 Nov: the first tab is every deal (it read "In handover" and counted deals still in Contracting), and "needing attention" is every deal
// whose handover is not complete and that has a commitment needing attention, at any stage.
export const FILTERS = [
  { key: "all", label: "All deals", test: () => true },
  { key: "open", label: "Deals needing attention", test: (d) => !d.handover_complete && d.open_gaps > 0 },
  { key: "complete", label: "Handover complete", test: (d) => d.handover_complete },
  { key: "earlier", label: "Earlier stages", test: (d) => !d.in_handover },
];

export const SORTS = [
  { key: "updated", label: "Last updated" },
  { key: "gaps", label: "Most commitments needing attention" },
  { key: "name", label: "Deal name" },
];

export function counts(deals) {
  return Object.fromEntries(FILTERS.map((f) => [f.key, deals.filter(f.test).length]));
}

export function matches(deal, query) {
  const q = (query ?? "").trim().toLowerCase();
  if (!q) return true;
  return [deal.name, deal.owner, deal.stage_label].some((v) => (v ?? "").toLowerCase().includes(q));
}

export function visibleDeals(deals, { filter = "all", query = "", sort = "updated" } = {}) {
  const f = FILTERS.find((x) => x.key === filter) ?? FILTERS[0];
  const rows = deals.filter((d) => f.test(d) && matches(d, query));
  const byName = (a, b) => a.name.localeCompare(b.name);
  const cmp = {
    updated: (a, b) => (b.last_updated ?? "").localeCompare(a.last_updated ?? "") || byName(a, b),
    gaps: (a, b) => b.open_gaps - a.open_gaps || byName(a, b),
    name: byName,
  }[sort] ?? byName;
  return [...rows].sort(cmp);
}

export function page(rows, n, size = 25) {
  const pages = Math.max(1, Math.ceil(rows.length / size));
  const current = Math.min(Math.max(1, n), pages);
  return { rows: rows.slice((current - 1) * size, current * size), page: current, pages };
}

// "Just now", "12 min ago", "3 hours ago", "Yesterday", "4 days ago", then "28 Sep 2026".
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function relativeTime(iso, now = new Date()) {
  const t = new Date(iso);
  if (!iso || Number.isNaN(t.getTime())) return "Not yet";
  const mins = Math.floor((now - t) / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ${hours === 1 ? "hour" : "hours"} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return `${t.getDate()} ${MONTHS[t.getMonth()]} ${t.getFullYear()}`;
}

export function initials(name) {
  const parts = (name ?? "").replace(/\(.*?\)/g, "").trim().split(/\s+/).filter(Boolean);
  return parts.slice(0, 2).map((p) => p[0].toUpperCase()).join("") || "?";
}

// The catalogue pop-up on the home screen (20 Oct): a vendor switch, preselected to the vendor of the deal opened last (Elva on a
// fresh start). Remembered in this browser only; when storage fails the first vendor shows.
export const VENDOR_KEY = "ptd.lastVendor";
// 12 Nov (Round 5): Alder is checked against its own copy of Elva's catalogue (vendor id "elva_alder", name "Elva"), so two ids can share one name. The switch lists a name once,
// under the default "elva" id when the deal list has it; with only the Alder copy (the public demo) Elva still comes first and is the default.
const isElva = (v) => v.name === "Elva";
export function vendorsOf(deals) {
  const seen = new Map();
  for (const d of deals ?? []) {
    if (!d.vendor) continue;
    const v = { id: d.vendor, name: d.vendor_name || d.vendor };
    const same = [...seen.values()].find((x) => x.name === v.name);
    if (!same) seen.set(v.id, v);
    else if (v.id === "elva" && same.id !== "elva") { seen.delete(same.id); seen.set(v.id, v); }
  }
  return [...seen.values()].sort((a, b) => (isElva(a) ? -1 : isElva(b) ? 1 : a.name.localeCompare(b.name)));
}
export function lastVendor(vendors, storage = globalThis.localStorage) {
  let id = null;
  try { id = storage.getItem(VENDOR_KEY); } catch { /* storage blocked */ }
  return vendors.some((v) => v.id === id) ? id : vendors.find(isElva)?.id ?? vendors[0]?.id;
}
export function rememberVendor(id, storage = globalThis.localStorage) {
  try { storage.setItem(VENDOR_KEY, id); } catch { /* the choice lasts for this page only */ }
}

// "Reset demo" (10 Nov): an inline confirm in the deal-list footer. The steps are plain data so they are tested without a browser.
export const RESET_QUESTION = "Restore all sample deals to their starting point? Anything you changed is kept in a backup file.";
export const RESET_IDLE = { step: "idle", message: "" };
export function resetNext(state, event, message = "") {
  if (event === "ask" && state.step === "idle") return { step: "confirming", message: "" };
  if (event === "cancel" && state.step === "confirming") return RESET_IDLE; // nothing else happens
  if (event === "run" && state.step === "confirming") return { step: "busy", message: "" };
  if (event === "fail" && state.step === "busy") return { step: "confirming", message }; // the server's words, inline
  return state;
}
// Calls the endpoint; on success sets #welcome and reloads the whole page, so no screen keeps stale state. The name
// ("Recording as", in localStorage) is not touched here and survives the reload. On failure returns the server's message.
export async function runReset(resetApi, nav) {
  const { setHash, reload } = nav;
  try {
    await resetApi();
  } catch (err) {
    return { ok: false, message: err?.message || "The reset failed." };
  }
  setHash("#welcome");
  nav.beforeReload?.(); // public mode: forget the browser-only "Get the picture" tour state
  reload();
  return { ok: true, message: "" };
}
