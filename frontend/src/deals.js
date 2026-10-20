// Deal list logic (16 Oct, Stitch screen 1). Pure functions, so they are tested without a browser.
// open_gaps counts commitments that need attention, as the stage bar does; addressed_by_note counts those a note settled.
// Every figure on the home screen is computed here from /api/workspace/deals: nothing is invented or estimated.

export const FILTERS = [
  { key: "handover", label: "In handover", test: (d) => d.in_handover },
  { key: "open", label: "Deals needing attention", test: (d) => d.in_handover && !d.handover_complete && d.open_gaps > 0 },
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

export function visibleDeals(deals, { filter = "handover", query = "", sort = "updated" } = {}) {
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
export function vendorsOf(deals) {
  const seen = new Map();
  for (const d of deals ?? []) if (d.vendor && !seen.has(d.vendor)) seen.set(d.vendor, { id: d.vendor, name: d.vendor_name || d.vendor });
  return [...seen.values()].sort((a, b) => (a.id === "elva" ? -1 : b.id === "elva" ? 1 : a.name.localeCompare(b.name)));
}
export function lastVendor(vendors, storage = globalThis.localStorage) {
  let id = null;
  try { id = storage.getItem(VENDOR_KEY); } catch { /* storage blocked */ }
  return vendors.some((v) => v.id === id) ? id : vendors.find((v) => v.id === "elva")?.id ?? vendors[0]?.id;
}
export function rememberVendor(id, storage = globalThis.localStorage) {
  try { storage.setItem(VENDOR_KEY, id); } catch { /* the choice lasts for this page only */ }
}
