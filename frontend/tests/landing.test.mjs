// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { SAMPLES, SEEN_KEY, availableSamples, landingSeen, markLandingSeen, pickMismatch } from "../src/landing.js";
import { TAGLINE, DESCRIPTION, AUDIENCE } from "../src/brand.js";
import { partsText } from "../src/dealpage.js";

const store = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, v) }; };
const broken = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); } };

test("the landing page shows on the first visit, then not; broken storage always shows it", () => {
  const s = store();
  assert.equal(landingSeen(s), false);
  markLandingSeen(s);
  assert.equal(s.getItem(SEEN_KEY), "1");
  assert.equal(landingSeen(s), true);
  assert.equal(landingSeen(broken), false);
  assert.doesNotThrow(() => markLandingSeen(broken));
  assert.equal(landingSeen(undefined), false); // no storage at all
});

test("the example mismatch comes from the stored register: the not-offered commitment first", () => {
  const reg = { commitments: [
    { name: "Coaching", display_name: "Coaching-scam detection live at launch", contract: "Not included",
      issues: [{ finding: "No approval recorded", state: "Needs action", evidence: {} }] },
    { name: "Hosting", display_name: "Hosting on Microsoft Azure", contract: "Amazon Web Services in the Sydney region",
      issues: [{ finding: "Not offered", state: "Needs action", evidence: {} }, { finding: "Contract says something different", state: "Needs action", evidence: {} }] },
  ] };
  const m = pickMismatch(reg);
  assert.equal(m.title, "Hosting on Microsoft Azure");
  assert.deepEqual(m.badges, ["Not offered"]); // a finding about the promise is a badge beside the title
  assert.equal(partsText(m.parts), "Contract says Amazon Web Services in the Sydney region"); // the contract line stands alone
  assert.equal(pickMismatch({ commitments: [] }), null);
  assert.equal(pickMismatch(null), null);
  const closedOnly = { commitments: [{ name: "X", contract: "", issues: [{ finding: "Not offered", state: "Resolved" }] }] };
  assert.equal(pickMismatch(closedOnly), null);
});

test("the positioning copy is the agreed text", () => {
  assert.equal(TAGLINE, "Catch deal surprises before you sign.");
  assert.equal(AUDIENCE, "For B2B Sales and Delivery teams.");
  assert.match(DESCRIPTION, /^Dealshape compares what the customer was promised with the contract and your product catalogue\./);
});

test("the landing page offers the two sample scenarios, AI support first, each only when its deal exists", () => {
  assert.deepEqual(SAMPLES.map((s) => [s.deal, s.title, s.parties]), [
    ["noma_journeys", "AI support assistant", "Aivuna / Noma Journeys"],
    ["alder_bank", "Financial services, scam protection", "Elva / Alder Bank"],
  ]);
  const both = [{ deal: "alder_bank" }, { deal: "harbour_bank" }, { deal: "noma_journeys" }];
  assert.deepEqual(availableSamples(both).map((s) => s.deal), ["noma_journeys", "alder_bank"]);
  assert.deepEqual(availableSamples([{ deal: "alder_bank" }]).map((s) => s.deal), ["alder_bank"]);
  assert.deepEqual(availableSamples([]), []);
  assert.deepEqual(availableSamples(null), []); // the server could not be reached
});

test("Aivuna's card shows the commitment the product does not offer, read from its own register", () => {
  const reg = { commitments: [
    { name: "Support in 12 languages", display_name: "Support in 12 languages at launch", contract: "four languages",
      issues: [{ finding: "Contract says something different", state: "Needs action", evidence: {} }] },
    { name: "Phone", display_name: "AI answers customers' phone calls at launch", contract: "chat and email",
      issues: [{ finding: "Not offered", state: "Needs action", evidence: {} }, { finding: "Contract says something different", state: "Needs action", evidence: {} }] },
  ] };
  const m = pickMismatch(reg);
  assert.equal(m.title, "AI answers customers' phone calls at launch");
  assert.deepEqual(m.badges, ["Not offered"]);
  assert.equal(partsText(m.parts), "Contract says chat and email"); // not "chat and email · not offered"
});

test("the home header carries the shared-view line, not the old eyebrow, and no count badge", async () => {
  const { HOME_LINE } = await import("../src/brand.js");
  const fs = await import("node:fs");
  assert.equal(HOME_LINE, "A shared view of what’s promised, agreed and deliverable.");
  const jsx = fs.readFileSync(new URL("../src/Deals.jsx", import.meta.url), "utf8");
  const css = fs.readFileSync(new URL("../src/Deals.css", import.meta.url), "utf8");
  assert.ok(!jsx.includes("Before signing and at handover") && !css.includes("dl-eyebrow"));
  assert.ok(jsx.includes("{HOME_LINE}") && !jsx.includes("{DESCRIPTION}"));
  assert.ok(!jsx.includes("dl-count") && !css.includes(".dl-count")); // no deal-count badge beside the heading (21 Oct); the tabs carry the counts
  const landing = fs.readFileSync(new URL("../src/Landing.jsx", import.meta.url), "utf8");
  assert.ok(landing.includes("{DESCRIPTION}"));
});

test("#welcome shows the landing page even after it has been seen; a normal visit after it has been seen goes to the deals list", async () => {
  const { isWelcome, showLanding, markLandingSeen, landingSeen, WELCOME_HASH } = await import("../src/landing.js");
  const store = new Map();
  const storage = { getItem: (k) => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, v) };
  assert.equal(landingSeen(storage), false);
  assert.equal(showLanding("", landingSeen(storage), null), true); // first visit
  markLandingSeen(storage);
  assert.equal(landingSeen(storage), true);
  assert.equal(showLanding("", landingSeen(storage), null), false); // normal visit after it was seen: the deals list
  assert.equal(showLanding("#d=alder_bank", landingSeen(storage), "alder_bank"), false); // a shared deal link still opens the deal
  assert.equal(WELCOME_HASH, "#welcome");
  assert.equal(isWelcome("#welcome"), true);
  assert.equal(showLanding("#welcome", landingSeen(storage), null), true); // whatever is stored
  assert.equal(isWelcome(""), false);
  assert.equal(isWelcome("#d=welcome"), false);
});

test("the deals-list footer carries a muted About Dealshape link, and leaving #welcome clears the hash", async () => {
  const fs = await import("node:fs");
  const deals = fs.readFileSync(new URL("../src/Deals.jsx", import.meta.url), "utf8");
  const app = fs.readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");
  assert.ok(deals.includes('className="dl-about"') && deals.includes("About Dealshape"));
  assert.ok(app.includes("onAbout={about}") && app.includes("if (isWelcome(window.location.hash)) clearHash();"));
});
