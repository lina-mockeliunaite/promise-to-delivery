// The product's display name and lines (19 Oct; positioning 20 Oct: catch deal surprises before signing). Display only: repo,
// folders, files, code identifiers and routes keep their names. The tagline appears once, in the top bar. The description is
// for the landing page only; the home screen carries HOME_LINE under its heading (21 Oct).
export const NAME = "Dealshape";
export const TAGLINE = "Catch deal surprises before you sign.";
export const DESCRIPTION = "Dealshape checks promises made during the sales process against the contract and product catalogue, and flags mismatches with source links.";
export const HOME_LINE = "A shared view of what’s promised, agreed and deliverable.";
// 28 Oct: the landing page's subhead (two lines), its audience line (role, phrase) and the label above the sample cards.
export const SUBHEAD = ["Delivery inherits the contract.", "The customer remembers the proposal."];
export const AUDIENCE_ITEMS = [["Sales", "fix mismatches before signing"], ["Delivery", "understand what you're taking on"], ["Product", "see promises the catalogue can't support"]];
export const CARDS_LABEL = "What it catches";
export const FICTIONAL = "All companies, people and deals are fictional.";

// 19 Nov: the "About this prototype" panel (replaces the "About Dealshape" button). The wording is fixed; the setup section is shown in public mode only
// (about.js decides). The description sentence comes first, then this text.
export const ABOUT_LABEL = "About this prototype";
export const ABOUT_WHAT = { lead: "What this is.", text: "A working prototype of a deal workspace that reads a deal's paper trail before handover. All companies, people and deals are fictional." };
export const ABOUT_SHOWS = {
  heading: "What the demo shows",
  items: [
    "It flags promises that don't match what the company approved or what the contract says: a promise stronger than approved, a promise the contract doesn't include and nobody withdrew, or terms that contradict each other. When the documents can't settle it, it says it needs more evidence.",
    "Every finding is checked against the source documents before it appears in the workspace, and again on each re-check.",
    "Saved handoff records are locked. A change creates a new version and never edits the old one.",
  ],
};
export const ABOUT_SETUP = {
  heading: "How the demo is set up",
  items: [
    "No AI model runs live here. The findings come from saved v2 readings, made earlier, and are checked against the documents in the same way as above.",
    "Two sample deals are pre-loaded: Noma Journeys and Alder Bank. You can add extra documents only from a set of bundled samples; uploading your own files is switched off.",
    "Approvals are names typed in by hand. There are no sign-ins.",
    "This is one shared workspace. Everyone sees the same data. It resets every hour, whenever anyone clicks Reset demo, and when the app restarts, and resets clear saved records. Please don't enter real information.",
  ],
};
export const ABOUT_SCOPE = {
  heading: "Deliberately out of scope",
  text: "There are no connections to CRM, email or contract systems: documents come from files, not live sources. There are no user accounts or sign-in. Real use would need those connections, along with the security and data-access review they bring. This prototype focuses on the harder question first: can the documents be read reliably, and can every finding be proved against them?",
};
export const ABOUT_VERSION = "Prototype v2.";
