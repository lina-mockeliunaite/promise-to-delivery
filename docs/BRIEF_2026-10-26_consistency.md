# Brief: final consistency pass before the public video (26 Oct 2026)

*Written by Claude (reviewer) for Lina. Documentation only: no application code, no data, no tests changed, no model calls. Do not run any git command; Lina handles git.*

## Why
Tomorrow Lina records a video for her website that links to this public repo. A visitor must find the same story in the video, the README and the docs. The main demo is **Noma Journeys** (`docs/DEMO_SCRIPT_2026-10-21_noma.md`); Alder Bank is the second scenario. The README still leads with Alder, and several docs are stale.

## Ground rules
- One bounded change set. **First reply with a plan only:** the files, the exact edits (old → new for short lines), and your proposed Current / Historical list for step 5. Wait for Lina's go-ahead.
- Keep every honest qualifier that is there today (limitations, "demonstration, not a measurement", "small, synthetic sample", "prompt still names the original vendor", sealed results describing the tested versions). Do not strengthen any claim.
- Never touch: `data/` (any deal, label, seal, catalogue), `results/`, sealed results docs' numbers, `LEARNING_LOG.md` (Lina's own words), application code, tests.
- Do not move or rename files (DECISIONS.md links to them). Add banners and an index instead.

## Part A (now)

1. **README: Noma leads.**
   - Replace the hero image line with a placeholder comment `<!-- screenshot: Noma deal page, added in Part B -->` for now (Part B adds the image).
   - Make the first scenario section **"What it shows (Noma Journeys, the main demo deal)"** with the existing Noma table and its text, keeping the "two vendors' catalogues, one pipeline" paragraph and every qualifier in it.
   - Make Alder the second section: **"A second scenario: a draft fix that didn't survive signing (Alder Bank)"**, with the existing Alder table. Make the second section's text work without assuming the reader saw the first.
   - Directly under the first paragraph, add one line: *"Built as the project From Promise to Delivery (hence the repository name); the product is Dealshape."*
   - "Run it locally": name `docs/DEMO_SCRIPT_2026-10-21_noma.md` (main) and `docs/DEMO_SCRIPT_2026-10-20_alder.md` (second). Remove the reference to the superseded 20 Oct Noma script from that paragraph (keep it in "Where to look", marked superseded).
   - "Where to look": list the Noma script first; add `docs/README.md` (the index from step 5).
2. **Alder script setup** (`docs/DEMO_SCRIPT_2026-10-20_alder.md`, "Before the demo"): replace the two key lines (`read -s …` and the `[ -n … ]` check) with `unset ANTHROPIC_API_KEY`, matching the Noma script and the README's "no API key" claim. Before proposing this, **name the test(s) that prove the Alder script runs with no key**, filed as the script says. If none exists, say so; do not write one in this change set.
3. **Repeated claims check.** Report (do not fix unless listed here) any place in README.md and the two current scripts where these disagree: product name, tagline, "AI surfaces gaps. Code checks sources. Teams decide the response.", the four gap labels as shown on screen, test counts, sealed results numbers, Noma run cost and counts. Lina decides.
4. **Stale "frozen" wording in current docs:** wherever README.md or the two current scripts call `detect_v2.py` or `ledger_v2.py` "frozen", replace with the CLAUDE.md wording: changes are allowed and raise `v2_version`; the published sealed results describe `v2_version` 2. (The primer outside the repo is Claude's to fix.)
5. **`docs/README.md` (new): an index.** Two short sections:
   - **Current:** the two current demo scripts, the two `RESULTS_*` files, and any spec that still describes built behaviour (justify each in the plan).
   - **Historical (kept for the record):** everything else in `docs/`, grouped (briefs, Stitch briefs and HTML, catch-ups, checkpoint notes, drafts, mocks, plans, superseded scripts), one line each at most. Say plainly that they reflect the build at the time and may use the earlier name "From Promise to Delivery" or the earlier stablecoin storyline.
6. **Banners on stale root files.** Add one italic line at the top of `WHERE_I_STOPPED.md` and `DESIGN.md`: *"Historical: written during the build (30 Sep 2026) and not updated since. The current description is README.md; decisions are in DECISIONS.md."* Same banner, adapted, at the top of `docs/DEMO_SCRIPT_15Oct.md`, `docs/DEMO_SCRIPT_2026-10-20_noma.md` and `docs/PLAN_v3.4.md`. Change nothing else in those files.
7. **DECISIONS.md:** one short entry dated 26 Oct: README leads with Noma to match the main demo and the public video; repository name kept, explained in one line; history kept in place with an index and banners rather than moved, so existing links hold. Rejected: renaming the repo (changes the clone path in every script); moving history to `docs/archive/` (breaks links).
8. **Checks, then report:** both test suites (`.venv/bin/python -m unittest discover -s tests`, `cd frontend && node --test tests/*.mjs`), quoting the last line of each. Confirm every relative link in README.md and `docs/README.md` resolves to an existing file. List every file changed. Then stop.

## Part B (after Lina's timed rehearsal; Lina will give you the result)

9. Replace the three "not yet rehearsed" statements (Noma script header, and anything equivalent in README) with what Lina reports, in her terms: date, total time, and any step that needed care. Do not invent a time.
10. **Screenshot:** after Lina confirms her rehearsal servers are stopped, run `reset_demo.py`, start the app, and capture the Noma deal page (desktop, full width, as first opened) to `docs/screens/2026-10-26/noma_deal.png`. Open the image and describe what it shows before using it. Replace the README placeholder with it. Stop the servers you started.
11. Re-run both test suites and the link check; report.
