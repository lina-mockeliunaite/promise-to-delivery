// Deal list logic (16 Oct, Stitch screen 1). Pure functions, so they are tested without a browser.
// open_gaps counts promises with an open gap, as the stage bar does.
// Every figure on the home screen is computed here from /api/workspace/deals: nothing is invented or estimated.

export const FILTERS = [
  { key: "handover", label: "All in handover", test: (d) => d.in_handover },
  { key: "open", label: "Open gaps", test: (d) => d.in_handover && !d.handover_complete && d.open_gaps > 0 },
  { key: "complete", label: "Handover complete", test: (d) => d.handover_complete },
  { key: "earlier", label: "Earlier stages", test: (d) => !d.in_handover },
];

export const SORTS = [
  { key: "updated", label: "Last updated" },
  { key: "gaps", label: "Open gaps" },
  { key: "name", label: "Deal name" },
];

export function counts(deals) {
  return Object.fromEntries(FILTERS.map((f) => [f.key, deals.filter(f.test).length]));
}

// The four tiles. Live deals only for open gaps: a completed handover is a frozen record, not live work.
export function metrics(deals) {
  const inHandover = deals.filter((d) => d.in_handover);
  const live = inHandover.filter((d) => !d.handover_complete);
  const withGaps = live.filter((d) => d.open_gaps > 0);
  const share = (n, of) => (of ? Math.round((n / of) * 100) : 0);
  return {
    inHandover: { value: inHandover.length, of: deals.length, pct: share(inHandover.length, deals.length) },
    openGaps: { value: withGaps.reduce((s, d) => s + d.open_gaps, 0), deals: withGaps.length },
    withGaps: { value: withGaps.length, of: live.length, pct: share(withGaps.length, live.length) },
    complete: { value: inHandover.length - live.length, of: inHandover.length, pct: share(inHandover.length - live.length, inHandover.length) },
  };
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

export const gapText = (n) => (n === 0 ? "No open gaps" : `${n} open ${n === 1 ? "gap" : "gaps"}`);
