// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import { SAMPLES, SEEN_KEY, availableSamples, landingSeen, markLandingSeen, pickMismatch } from "../src/landing.js";
import { TAGLINE, DESCRIPTION, SUBHEAD, AUDIENCE_ITEMS, CARDS_LABEL } from "../src/brand.js";
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
  assert.equal(partsText(m.parts), "Contract specifies Amazon Web Services in the Sydney region"); // the contract line stands alone; the card is a summary, so "specifies"
  assert.equal(pickMismatch({ commitments: [] }), null);
  assert.equal(pickMismatch(null), null);
  const closedOnly = { commitments: [{ name: "X", contract: "", issues: [{ finding: "Not offered", state: "Resolved" }] }] };
  assert.equal(pickMismatch(closedOnly), null);
});

test("the positioning copy is the agreed text", () => {
  assert.equal(TAGLINE, "Catch deal surprises before you sign.");
  assert.equal(DESCRIPTION, "Dealshape checks promises made during the sales process against the contract and product catalogue, and flags mismatches with source links.");
  assert.deepEqual(SUBHEAD, ["Delivery inherits the contract.", "The customer remembers the proposal."]);
  assert.deepEqual(AUDIENCE_ITEMS, [["Sales", "fix mismatches before signing"], ["Delivery", "understand what you're taking on"], ["Product", "see promises the catalogue can't support"]]);
  assert.equal(CARDS_LABEL, "What it catches");
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
  assert.equal(partsText(m.parts), "Contract specifies chat and email"); // not "chat and email · not offered"
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

test("the landing page renders the headline, the two-line subhead, the description, the audience line and the cards label in order, with theme variables only", async () => {
  const fs = await import("node:fs");
  const jsx = fs.readFileSync(new URL("../src/Landing.jsx", import.meta.url), "utf8");
  const css = fs.readFileSync(new URL("../src/Landing.css", import.meta.url), "utf8");
  const at = (s) => jsx.indexOf(s);
  assert.ok(at("<h1>{TAGLINE}</h1>") < at('className="land-sub"') && at('className="land-sub"') < at('className="land-desc"') && at('className="land-desc"') < at('className="land-aud"'));
  assert.ok(jsx.includes("SUBHEAD.map((line) => <span key={line}>{line}</span>)")); // one block per line: exactly two lines
  assert.ok(jsx.includes("<li key={role}><strong>{role}</strong> {phrase}</li>")); // role emphasised, phrase muted
  assert.ok(at('className="land-cards"') < at("land-cards-label") && at("land-cards-label") < at("cards.map"));
  assert.ok(jsx.includes("dp-eyebrow land-cards-label")); // the existing eyebrow style
  const rules = css.split("\n").filter((l) => /^\.land-(sub|aud|cards-label)/.test(l)).join("\n");
  assert.ok(!/#[0-9a-fA-F]{3,8}\b|rgba?\(/.test(rules), "no literal colours");
  assert.match(css, /\.land-sub \{[^}]*color: var\(--ink\)/); // darker than the description (--body)
  assert.match(css, /\.land-aud \{[^}]*flex-direction: column;/); // a stacked list: one line per role
  assert.match(css, /\.land-aud li strong::after \{ content: " \\00b7"; color: var\(--muted\)/); // the dot follows the role
  assert.ok(!/white-space: nowrap/.test(css.slice(css.indexOf(".land-aud {"), css.indexOf(".land-cards-label"))));
  assert.ok(!jsx.includes("AUDIENCE}"));
});

// 28 Oct: the two sample cards show different kinds of mismatch, picked by a rule computed from the stored register.
import { pickMismatches } from "../src/landing.js";
const conflict = (promised, contract) => ({ finding: "Contract says something different", state: "Needs action", evidence: { promised_value: promised, contract_value: contract } });
const gap = (finding) => ({ finding, state: "Needs action", evidence: {} });
const NOMA = { commitments: [
  { name: "Lang", display_name: "Support in 12 languages at launch", contract: "four languages: English, Mandarin Chinese, Japanese and Korean", statements: [], issues: [conflict("12 languages", "four languages: English, Mandarin Chinese, Japanese and Korean")] },
  { name: "Specialist", display_name: "Dedicated launch specialist for the first 30 days, at no extra charge", contract: "Not included", statements: [], issues: [gap("No approval recorded"), gap("Missing from contract")] },
  { name: "Phone", display_name: "AI answers customers' phone calls at launch", contract: "chat and email", statements: [], issues: [gap("Not offered"), conflict("phone calls", "chat and email")] },
] };
const ALDER = { commitments: [
  { name: "Hosting", display_name: "Hosting on Microsoft Azure", contract: "Amazon Web Services in the Sydney region", statements: [], issues: [gap("Not offered"), conflict("Microsoft Azure in the Australia East region", "Amazon Web Services in the Sydney region")] },
  { name: "Coaching", display_name: "Coaching-scam detection live at launch", contract: "Not included", statements: [], issues: [gap("No approval recorded"), gap("Missing from contract")] },
  { name: "Volume", display_name: "750,000 payments a day by the end of year one", contract: "Not included", statements: [], issues: [gap("No approval recorded"), gap("Missing from contract")] },
] };

test("reset state: Noma shows the languages mismatch (the plainest, both terms stored), Alder keeps hosting with its Not offered badge", () => {
  const [noma, alder] = pickMismatches([NOMA, ALDER]);
  assert.equal(noma.title, "Support in 12 languages at launch");
  assert.deepEqual(noma.badges, []); // a contract difference only: nothing about the promise
  assert.equal(partsText(noma.told), "Customer was told 12 languages");
  assert.equal(partsText(noma.parts), "Contract specifies 4 languages"); // cut at the colon, number word as a digit
  assert.equal(alder.title, "Hosting on Microsoft Azure");
  assert.deepEqual(alder.badges, ["Not offered"]);
  assert.equal(partsText(alder.told), "Customer was told Microsoft Azure in the Australia East region");
});

test("the rule: only commitments with both terms; a kind not already shown first; then the fewest findings; then register order", () => {
  // only the commitments with a stored customer term and a stored contract term are eligible (not the specialist, which has neither)
  const only = pickMismatch({ commitments: [NOMA.commitments[1], NOMA.commitments[2]] });
  assert.equal(only.title, "AI answers customers' phone calls at launch");
  // fewest findings breaks a tie: languages (1 finding) over phone calls (2)
  assert.equal(pickMismatch(NOMA).title, "Support in 12 languages at launch");
  // a kind not already shown beats fewer findings: with "Contract says something different" already shown, phone calls adds "Not offered"
  assert.equal(pickMismatch(NOMA, new Set(["Contract says something different"])).title, "AI answers customers' phone calls at launch");
  // register order is the last tie-break
  const twin = { commitments: [{ ...NOMA.commitments[0], name: "A", display_name: "First" }, { ...NOMA.commitments[0], name: "B", display_name: "Second" }] };
  assert.equal(pickMismatch(twin).title, "First");
  // nothing eligible: the earlier rule (the not-offered commitment first, else the first open one)
  const none = { commitments: [{ name: "X", display_name: "X", contract: "Not included", statements: [], issues: [gap("No approval recorded")] }, { name: "Y", display_name: "Y", contract: "z", statements: [], issues: [gap("Not offered")] }] };
  assert.equal(pickMismatch(none).title, "Y");
  assert.equal(pickMismatch({ commitments: [none.commitments[0]] }).title, "X");
  assert.equal(pickMismatch({ commitments: [] }), null);
  // a card that cannot load leaves the other alone; a closed gap is never picked
  assert.deepEqual(pickMismatches([null, ALDER]).map((p) => p && p.title), [null, "Hosting on Microsoft Azure"]);
  const closed = { commitments: [{ ...NOMA.commitments[0], issues: [{ ...conflict("a", "b"), state: "Resolved" }] }] };
  assert.equal(pickMismatch(closed), null);
});

test("the cards' button says 'Open sample deal', and a wrapped comparison line is balanced", async () => {
  const fs = await import("node:fs");
  const jsx = fs.readFileSync(new URL("../src/Landing.jsx", import.meta.url), "utf8");
  const css = fs.readFileSync(new URL("../src/Landing.css", import.meta.url), "utf8");
  assert.ok(jsx.includes(">Open sample deal</button>") && !jsx.includes("Open this sample deal"));
  assert.match(css, /\.land-example \.dp-prow-line \{ text-wrap: balance; \}/);
});

// 28 Oct: the landing cards are a summary, not a quote. Only the cards are changed; every other screen keeps the exact stored wording.
import { cardTerm, cardParts } from "../src/landing.js";
import { mismatchParts, toldParts } from "../src/dealpage.js";

test("card terms: cut at the first colon, number words one to twelve as digits, whole words only", () => {
  assert.equal(cardTerm("four languages: English, Mandarin Chinese, Japanese and Korean"), "4 languages");
  assert.equal(cardTerm("twelve languages"), "12 languages");
  assert.equal(cardTerm("12 languages"), "12 languages");
  assert.equal(cardTerm("Four languages"), "4 languages"); // case-insensitive
  assert.equal(cardTerm("one to eleven seats"), "1 to 11 seats");
  assert.equal(cardTerm("thirteen languages"), "thirteen languages"); // only one to twelve
  assert.equal(cardTerm("a one-time fee"), "a one-time fee"); // not inside a hyphenated word
  assert.equal(cardTerm("someone phoned"), "someone phoned"); // whole words only
  assert.equal(cardTerm("chat and email"), "chat and email");
  assert.equal(cardTerm(""), "");
});

test("on the cards the contract label is 'Contract specifies' (a missing finding stays 'Contract has no matching wording') and the customer label stays 'Customer was told', for both terms", () => {
  const issues = [{ finding: "Contract says something different", state: "Needs action", evidence: { promised_value: "twelve languages", contract_value: "four languages: English, Korean" } }];
  const c = { name: "Lang", display_name: "Support in 12 languages at launch", contract: "four languages: English, Korean", statements: [], issues };
  const card = pickMismatch({ commitments: [c] });
  assert.equal(partsText(card.told), "Customer was told 12 languages");
  assert.equal(partsText(card.parts), "Contract specifies 4 languages");
  // the same findings on the deal page keep the exact stored wording and "Contract says"
  assert.equal(partsText(toldParts(issues, [], null)), "Customer was told twelve languages");
  assert.equal(partsText(mismatchParts(issues, c.contract)), "Contract says four languages: English, Korean");
  // the other contract wordings on a card are untouched
  assert.equal(partsText(cardParts([{ text: "Contract has ", strong: false }, { text: "no matching wording", strong: true }])), "Contract has no matching wording");
  assert.equal(partsText(cardParts([{ text: "Contract differs", strong: true }])), "Contract differs");
});
