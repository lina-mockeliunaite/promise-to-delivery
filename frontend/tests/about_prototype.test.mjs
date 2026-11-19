// "About this prototype" (19 Nov): the footer link, the panel, its public-mode-only setup section, and the logo as the route to the landing page.
// Run with: node --test frontend/tests/
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { build } from "vite";
import react from "@vitejs/plugin-react";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { aboutKeyAction, aboutNext, aboutSections } from "../src/about.js";
import { DESCRIPTION } from "../src/brand.js";
import { WELCOME_HASH } from "../src/landing.js";

const SRC = new URL("../src/", import.meta.url);
const read = (f) => fs.readFileSync(new URL(f, SRC), "utf8");
const dir = fileURLToPath(new URL("../node_modules/.cache/about-prototype-test/", import.meta.url));
fs.mkdirSync(dir, { recursive: true });
const entry = path.join(dir, "entry.jsx");
const at = (f) => JSON.stringify(fileURLToPath(new URL(f, SRC)));
fs.writeFileSync(entry, `export { default as AboutPrototype, AboutPanel } from ${at("AboutPrototype.jsx")};
export { BrandBlock, BrandLink } from ${at("Logo.jsx")};
export { DealFooter } from ${at("DealPage.jsx")};\n`);
const out = await build({
  configFile: false, logLevel: "silent", root: fileURLToPath(new URL("..", import.meta.url)), plugins: [react()],
  build: { write: false, minify: false, lib: { entry, formats: ["es"], fileName: "entry" },
    rollupOptions: { external: ["react", "react-dom", "react-dom/server", "react/jsx-runtime", "react/jsx-dev-runtime"] } },
});
const file = path.join(dir, "bundle.mjs");
fs.writeFileSync(file, (Array.isArray(out) ? out[0] : out).output[0].code);
const { AboutPrototype, AboutPanel, BrandBlock, BrandLink, DealFooter } = await import(file);

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#x27;");

// The approved wording, written out again here so a change to brand.js shows up as a failing test.
const WHAT = "A working prototype of a deal workspace that reads a deal's paper trail before handover. All companies, people and deals are fictional.";
const SHOWS = [
  "It flags promises that don't match what the company approved, what the product offers or what the contract says: a promise stronger than approved, a channel, region or option the product doesn't offer, a promise the contract doesn't include and nobody withdrew, or terms that contradict each other. When the documents can't settle it, it says it needs more evidence.",
  "Every finding is checked against the source documents before it appears in the workspace, and again on each re-check.",
  "Saved handoff records are locked. A change creates a new version and never edits the old one.",
];
const SETUP = [
  "No AI model runs live here. The findings were produced by AI in earlier runs and saved, and are checked against the documents in the same way as above.",
  "Two sample deals are pre-loaded: Noma Journeys and Alder Bank. You can add extra documents only from a set of bundled samples; uploading your own files is switched off.",
  "Approvals are names typed in by hand. There are no sign-ins.",
  "This is one shared workspace. Everyone sees the same data. It resets every hour, whenever anyone clicks Reset demo, and when the app restarts. Each reset clears saved records. Please don't enter real information.",
];
const SCOPE = "There are no connections to CRM, email or contract systems: documents come from files, not live sources. There are no user accounts or sign-in. Real use would need those connections, along with the security and data-access review they bring. This prototype focuses on the harder question first: can the documents be read reliably, and can every finding be proved against them?";

test("the panel state: open opens; the Close button, Esc and a click outside close; anything else changes nothing", () => {
  assert.equal(aboutNext(false, "open"), true);
  for (const a of ["button", "escape", "overlay"]) assert.equal(aboutNext(true, a), false, a);
  assert.equal(aboutNext(false, "escape"), false);
  assert.equal(aboutNext(true, "something else"), true);
  assert.equal(aboutNext(false, undefined), false);
  assert.equal(aboutKeyAction({ key: "Escape" }), "escape");
  assert.equal(aboutKeyAction({ key: "Enter" }), null);
  assert.equal(aboutKeyAction(null), null);
});

test("the sections: the description first, then the approved text; the setup section only in public mode", () => {
  const pub = aboutSections(true);
  const loc = aboutSections(false);
  assert.deepEqual(pub.map((s) => s.key), ["intro", "what", "shows", "setup", "scope", "version"]);
  assert.deepEqual(loc.map((s) => s.key), ["intro", "what", "shows", "scope", "version"]);
  assert.equal(pub[0].text, DESCRIPTION);
  const by = (list, k) => list.find((s) => s.key === k);
  for (const list of [pub, loc]) {
    assert.deepEqual([by(list, "what").lead, by(list, "what").text], ["What this is.", WHAT]);
    assert.equal(by(list, "shows").heading, "What the demo shows");
    assert.deepEqual(by(list, "shows").items, SHOWS);
    assert.equal(by(list, "scope").heading, "Deliberately out of scope");
    assert.equal(by(list, "scope").text, SCOPE);
    assert.equal(by(list, "version").text, "Prototype v2.");
  }
  assert.equal(by(pub, "setup").heading, "How the demo is set up"); // no parenthetical
  assert.deepEqual(by(pub, "setup").items, SETUP);
});

test("the footer link renders closed: a button named About this prototype, no dialog", () => {
  const html = renderToStaticMarkup(createElement(AboutPrototype));
  assert.match(html, />About this prototype<\/button>/);
  assert.match(html, /aria-haspopup="dialog"/);
  assert.doesNotMatch(html, /role="dialog"/);
  assert.match(renderToStaticMarkup(createElement(AboutPrototype, { className: "dl-about" })), /class="about-link dl-about"/);
});

test("the open panel: the heading, a dialog named by it, a Close button, and every line of the text exactly", () => {
  const html = renderToStaticMarkup(createElement(AboutPanel, { sections: aboutSections(true), titleId: "t1", onAction: () => {} }));
  assert.match(html, /role="dialog"/);
  assert.match(html, /aria-modal="true"/);
  assert.match(html, /aria-labelledby="t1"/);
  assert.match(html, /<h2 id="t1">About this prototype<\/h2>/);
  assert.match(html, />Close<\/button>/);
  for (const t of [DESCRIPTION, WHAT, ...SHOWS, ...SETUP, SCOPE, "Prototype v2."]) assert.ok(html.includes(esc(t)), t);
  for (const h of ["What the demo shows", "How the demo is set up", "Deliberately out of scope"]) assert.ok(html.includes(`<h3>${h}</h3>`), h);
  assert.ok(html.indexOf(esc(DESCRIPTION)) < html.indexOf(esc(WHAT)), "the description comes first");
  assert.ok(html.endsWith('<section class="about-sec about-version"><p>Prototype v2.</p></section></div></div></div>'), "Prototype v2. is the last thing in the panel");
  const local = renderToStaticMarkup(createElement(AboutPanel, { sections: aboutSections(false), titleId: "t2", onAction: () => {} }));
  assert.ok(!local.includes("How the demo is set up") && !local.includes("produced by AI in earlier runs"), "no setup section in local mode");
  for (const t of [WHAT, ...SHOWS, SCOPE]) assert.ok(local.includes(esc(t)), t);
});

test("the live deal page's footer carries the link", () => {
  assert.match(renderToStaticMarkup(createElement(DealFooter, {})), />About this prototype<\/button>/);
});

test("the logo is a link to the landing page, named Dealshape — overview; the plain brand block is not", () => {
  const html = renderToStaticMarkup(createElement(BrandLink, { className: "dp-brandline" }));
  assert.ok(html.includes(`href="${WELCOME_HASH}"`));
  assert.equal(WELCOME_HASH, "#welcome");
  assert.ok(html.includes('aria-label="Dealshape — overview"'));
  assert.match(html, /<a class="brand-link dp-brandline" href="#welcome"/); // React 19 puts an image preload link before it
  assert.ok(!renderToStaticMarkup(createElement(BrandBlock)).includes("<a "));
});

test("where it is and is not: the deal list, the landing page and the live deal page have it; the locked record and print do not", () => {
  assert.match(read("Deals.jsx"), /<AboutPrototype className="dl-about" \/>/);
  assert.match(read("Landing.jsx"), /<footer className="dp-foot">\{FICTIONAL\} <AboutPrototype \/><\/footer>/);
  assert.match(read("DealPage.jsx"), /<AboutPrototype \/>/);
  assert.match(read("Deals.jsx"), /<BrandLink \/>/);
  assert.match(read("DealPage.jsx"), /<BrandLink className="dp-brandline" \/>/);
  const frozen = read("FrozenRecord.jsx");
  assert.ok(!/AboutPrototype|BrandLink/.test(frozen), "the locked record is untouched");
  assert.match(frozen, /<BrandBlock className="dp-brandline" \/>/);
  assert.match(read("AboutPrototype.css"), /@media print \{ \.about-link, \.about-overlay \{ display: none !important; \} \}/);
  for (const f of ["Deals.jsx", "App.jsx", "Landing.jsx", "DealPage.jsx"]) assert.ok(!/About Dealshape|onAbout/.test(read(f)), f);
});
