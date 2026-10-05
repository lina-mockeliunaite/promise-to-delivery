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
