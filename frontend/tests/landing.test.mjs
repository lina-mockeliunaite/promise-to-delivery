// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { SEEN_KEY, landingSeen, markLandingSeen, pickMismatch } from "../src/landing.js";
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
  assert.match(partsText(m.parts), /not offered/i);
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
