// 12 Nov, round 2: the landing page's guided-demo button, the bar without its own there, and guided steps that close what covers their target.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const read = (f) => fs.readFileSync(new URL(`../src/${f}`, import.meta.url), "utf8");

test("landing (public mode): the guided-demo button is first and primary, the cards' buttons are secondary, local mode is unchanged", () => {
  const jsx = read("Landing.jsx"), css = read("Landing.css");
  assert.match(jsx, /\{guided && <button type="button" className="land-start" onClick=\{\(\) => startGuidedDemo\(nav\)\}>\{START_LABEL\}<\/button>\}\s*<button type="button" className="dp-link-btn dp-brand" onClick=\{onList\}>/);
  assert.match(jsx, /const guided = !!demo\.public/);
  assert.match(jsx, /className=\{`dp-btn land-open \$\{guided \? "land-open-secondary" : "dp-btn-dark"\}`\}/); // local: the dark button as before
  assert.ok(!/land-start[^"]*dp-btn-dark/.test(jsx));
  assert.match(css, /\.land-start \{[^}]*background: #4f46e5; color: #ffffff;/); // the indigo of "Do step N"
  assert.match(read("App.css"), /\.demo-bar-do \{[^}]*background: #4f46e5; color: #ffffff;/);
  assert.match(css, /\.dp \.land-open-secondary \{ background: transparent;/);
});

test("the bar drops its guided-demo button on the landing page only; the deal list keeps it", () => {
  const ui = read("DemoUI.jsx");
  assert.match(ui, /\{!steps && !onLanding && <button type="button" className="demo-bar-do" onClick=\{\(\) => startGuidedDemo\(nav\)\}>/);
  assert.match(ui, /<ResetDemo variant="bar" \/>/); // Reset demo stays
  assert.match(ui, /demo\.banner/); // so does the status text
  assert.match(read("Landing.jsx"), /publishLanding\(guided\); return \(\) => publishLanding\(false\)/); // off again when the landing goes
  assert.match(read("App.jsx"), /<LandingStateContext\.Provider value=\{onLanding\}>/);
  assert.ok(!read("Deals.jsx").includes("LandingStateContext"));
});

test("a guided step closes the drawer and the dialog it does not replace, then scrolls once the page has settled", () => {
  const src = read("DealPage.jsx");
  assert.match(src, /const clearOverlays = \(keepDrawer\) => \{ setChange\(null\); if \(!keepDrawer\) \{ setDrawer\(null\); writeHash\(null\); \} \};/);
  assert.match(src, /const a = guideAction\(step, reg\.commitments\);\s*clearOverlays\(!!a\.drawer\);\s*if \(a\.drawer\) setDrawer\(a\.drawer\);/);
  assert.match(src, /requestAnimationFrame\(\(\) => find\(\)\?\.scrollIntoView/);
  assert.match(src, /if \(key\) \{ clearOverlays\(false\);/); // the tour too
});
