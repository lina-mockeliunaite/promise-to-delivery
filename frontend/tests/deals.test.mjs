// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { FILTERS, SORTS, VENDOR_KEY, counts, initials, lastVendor, page, relativeTime, rememberVendor, vendorsOf, visibleDeals } from "../src/deals.js";

const deal = (name, o) => ({ deal: name.toLowerCase(), name, owner: null, stage_label: "Contracting", open_gaps: 0,
  in_handover: true, handover_complete: false, last_updated: "2026-10-16T01:00:00Z", ...o });

const deals = [
  deal("Harbour Bank", { open_gaps: 3, owner: "Maya Tan", last_updated: "2026-10-16T03:00:00Z" }),
  deal("Coral Pay", { open_gaps: 1, stage_label: "Signed" }),
  deal("Atlas Remit", { open_gaps: 2, handover_complete: true, stage_label: "Handover", last_updated: "2026-10-10T00:00:00Z" }),
  deal("New Prospect", { in_handover: false, stage_label: "Discovery", last_updated: null }),
];

test("filters count only what they say", () => {
  assert.deepEqual(counts(deals), { handover: 3, open: 2, complete: 1, earlier: 1 });
});

test("search matches name, owner or stage; sort by last updated puts the newest first", () => {
  assert.deepEqual(visibleDeals(deals, { query: "maya" }).map((d) => d.name), ["Harbour Bank"]);
  assert.deepEqual(visibleDeals(deals, { query: "signed" }).map((d) => d.name), ["Coral Pay"]);
  assert.deepEqual(visibleDeals(deals).map((d) => d.name), ["Harbour Bank", "Coral Pay", "Atlas Remit"]);
  assert.deepEqual(visibleDeals(deals, { sort: "gaps" }).map((d) => d.name), ["Harbour Bank", "Atlas Remit", "Coral Pay"]);
  assert.deepEqual(visibleDeals(deals, { filter: "earlier" }).map((d) => d.name), ["New Prospect"]);
});

test("paging keeps the page in range", () => {
  const rows = Array.from({ length: 60 }, (_, i) => i);
  assert.equal(page(rows, 1).rows.length, 25);
  assert.equal(page(rows, 3).rows.length, 10);
  assert.equal(page(rows, 9).page, 3);
  assert.equal(page([], 1).pages, 1);
});

test("times read as people say them", () => {
  const now = new Date("2026-10-16T12:00:00Z");
  assert.equal(relativeTime("2026-10-16T11:59:40Z", now), "Just now");
  assert.equal(relativeTime("2026-10-16T11:48:00Z", now), "12 min ago");
  assert.equal(relativeTime("2026-10-16T09:00:00Z", now), "3 hours ago");
  assert.equal(relativeTime("2026-10-15T10:00:00Z", now), "Yesterday");
  assert.equal(relativeTime("2026-10-12T10:00:00Z", now), "4 days ago");
  assert.match(relativeTime("2026-09-28T10:00:00Z", now), /28 Sep 2026/);
  assert.equal(relativeTime(null, now), "Not yet");
});

test("the filter and sort say what they count, not 'open gaps'", () => {
  assert.equal(FILTERS.find((f) => f.key === "open").label, "Deals needing attention");
  assert.equal(SORTS.find((x) => x.key === "gaps").label, "Most commitments needing attention");
});

test("initials", () => {
  assert.equal(initials("Maya Tan"), "MT");
  assert.equal(initials("Sam (delivery)"), "S");
  assert.equal(initials(""), "?");
});

test("the home catalogue switch lists the vendors in use, Elva first, and opens on the vendor of the deal opened last", () => {
  const deals = [{ vendor: "aivuna", vendor_name: "Aivuna" }, { vendor: "elva", vendor_name: "Elva" }, { vendor: "elva", vendor_name: "Elva" }];
  const vendors = vendorsOf(deals);
  assert.deepEqual(vendors, [{ id: "elva", name: "Elva" }, { id: "aivuna", name: "Aivuna" }]);
  const store = (() => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) }; })();
  assert.equal(lastVendor(vendors, store), "elva"); // a fresh start
  rememberVendor("aivuna", store);
  assert.equal(lastVendor(vendors, store), "aivuna");
  store.setItem(VENDOR_KEY, "acme"); // a vendor no deal uses is ignored
  assert.equal(lastVendor(vendors, store), "elva");
  const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };
  assert.equal(lastVendor(vendors, broken), "elva");
  assert.doesNotThrow(() => rememberVendor("aivuna", broken));
  assert.deepEqual(vendorsOf(undefined), []);
  assert.deepEqual(vendorsOf([{ deal: "x" }]), []); // an older server sends no vendor: no switch, Elva's catalogue
});
