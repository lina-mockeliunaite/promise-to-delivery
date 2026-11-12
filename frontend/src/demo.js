// Public demo mode (10 Nov). The server says whether it is on (GET /api/demo/config); everything here is off otherwise.
import { createContext, useContext } from "react";

export const DEMO_OFF = { public: false, banner: null, note: null, note_max: null };
export const DemoContext = createContext(DEMO_OFF);
export const useDemo = () => useContext(DemoContext);

export const NAME_NOTE = "Your name and notes are visible to other visitors of this public demo.";
export const NO_SAMPLES = "This deal has no sample files in the public demo.";

// The longest note a box takes: the public cap when on, else the box's own limit.
export const noteLimit = (demo, own = 2000) => (demo?.public && demo.note_max ? Math.min(demo.note_max, own) : own);

// What the add-document form would send for a sample: the same body as an upload, so the existing add-and-check path is unchanged.
export function sampleBody(sample, text) {
  if (sample.version_of) return { source_key: sample.version_of, filename: sample.file, text };
  return { name: sample.file, filename: sample.file, doc_type: sample.doc_type, doc_date: sample.doc_date, text };
}

// What onDone is told, as for an upload: the document's plain name, the source it replaced, and its date.
export function sampleDone(sample, documents, labels) {
  const existing = sample.version_of ? documents.find((d) => d.source_key === sample.version_of) : null;
  return { name: existing ? existing.name : (labels[sample.doc_type] ?? sample.file), source_key: existing ? existing.source_key : null,
           date: sample.doc_date ?? "" };
}

// Fetch a sample's text and send it through the existing add-and-check call, exactly as the form sends an upload.
export async function addSample(client, deal, sample, documents, labels) {
  const { text } = await client.fetchSample(deal, sample.file);
  const r = await client.addDocumentAndCheck(deal, sampleBody(sample, text));
  return { review: r.review, added: sampleDone(sample, documents, labels) };
}

// How the form would file a sample, in plain words, with no dates: a new version of a named document, or a new document of a type.
export function filingLine(sample, documents, labels) {
  if (sample.version_of) {
    const existing = documents.find((d) => d.source_key === sample.version_of);
    return `Filed as a new version of: ${existing ? existing.name : sample.version_of}`;
  }
  return `Filed as a new document, type ${labels[sample.doc_type] ?? sample.doc_type}`;
}

// Public mode wording (11 Nov).
export const RESET_QUESTION_PUBLIC = "Restore both sample deals to the start? This resets the demo for everyone.";
export const REFUSED_FINDINGS = "Dealshape's checks can propose findings that the documents don't back up. Code tests every one against the documents and refuses any it can't support, so those are never shown and never counted.";
export const ALL_ADDED = {
  noma_journeys: "All samples added. Next: record a note on the phone row, then complete the handover.",
  alder_bank: "All samples added. Next: record a note on the hosting row, then complete the handover.",
};

// The guided path through a deal's samples (11 Nov): which are already in the deal, which one is next, which wait. A new-version sample is in the
// deal once its document is past version 1; a new-document sample once a document of its type is there. The samples are steps 2, 3 and 4 of the
// guide (step 1 is "Get the picture"), so n is the guide's step number and "later" says which step it waits for ("After step N").
export const FIRST_SAMPLE_STEP = 2;
export function sampleSteps(samples, documents) {
  const docs = documents ?? [];
  const used = (s) => (s.version_of ? docs.some((d) => d.source_key === s.version_of && d.version > 1) : docs.some((d) => d.doc_type === s.doc_type));
  const next = samples.findIndex((s) => !used(s));
  return samples.map((s, i) => ({ sample: s, n: i + FIRST_SAMPLE_STEP,
    state: next === -1 || i < next ? "done" : i === next ? "next" : "later", after: i + FIRST_SAMPLE_STEP - 1 })); // the step before it
}

// "Use sample text" (11 Nov, public mode only): the visitor clicks the link, the text fills the box, and the visitor still clicks Save; nothing is saved
// for them. One note on one commitment per deal (the phone row, the hosting row), and both handover notes.
export const NOTE_SAMPLES = {
  noma_journeys: { match: /phone/i, addressed: true, text: "Noma agreed on 19 Oct to launch on chat and email; voice is not offered." },
  alder_bank: { match: /hosting/i, addressed: true, text: "Customer agreed AWS Sydney on the 14 Oct call." },
};
export const HANDOVER_SAMPLES = {
  noma_journeys: {
    sales: "Signed. Noma was promised a launch specialist for the first 30 days; it's approved as a named exception at no charge, but it isn't in the contract. Noma expects it: provide it, and get it into writing at kickoff. Noma launches on chat and email; voice isn't offered.",
    delivery: "Accepted. We start on chat and email as contracted and provide the launch specialist for 30 days as approved; putting it in writing goes on the kickoff agenda.",
  },
  alder_bank: {
    sales: "Coaching-scam detection moves to 1 May in the signed SOW. Confirm the revised launch scope with Alder before kickoff.",
    delivery: "Accepted. We start on AWS Sydney as contracted; coaching detection and the volume limit go on the kickoff agenda.",
  },
};
export const noteSampleFor = (demo, deal, commitment) => {
  const s = demo?.public ? NOTE_SAMPLES[deal] : null;
  return s && s.match.test(`${commitment?.display_name ?? ""} ${commitment?.name ?? ""}`) ? s : null;
};
export const handoverSampleFor = (demo, deal, role) => (demo?.public ? HANDOVER_SAMPLES[deal]?.[role] ?? null : null);

// The guide card, "Try it in 5 steps" (11 Nov, public mode, Noma and Alder). Step numbers are the sample panel's numbers (1-3), so "After step N" there
// refers to the card. A step is done when the deal shows it: a sample is in the deal (the same test the sample list uses), a note is recorded on
// its row, or the handover is complete. The current step is the first one not done.
// Step 1 is a tour of the page; 2-4 add the sample documents; 5 records the note; 6 completes the handover. Each action step opens its commitment's drawer
// on the evidence with one hint line (a fact about the findings: tests/test_guide_facts.py checks each against the deal's data).
export const GUIDES = {
  noma_journeys: [
    { label: "Get the picture", kind: "tour", row: null },
    { label: "Launch specialist: add the approval", kind: "sample", sample: 0, row: /launch specialist/i, highlight: "add",
      hint: "Promised in the RFP and again in the proposal, never approved, not in the contract. Add the approval and see what closes." },
    { label: "Support in 12 languages: add the revised contract", kind: "sample", sample: 1, row: /12 languages/i, highlight: "add",
      hint: "Told 12 languages; the draft contract says four. Add the revised contract." },
    { label: "Add the signed contract", kind: "sample", sample: 2, row: null,
      hint: "The signed contract decides what Delivery inherits. Add it and see which fixes survive." },
    { label: "Phone calls: record the customer's agreement as a note", kind: "note", row: /phone/i, highlight: "note",
      hint: "Aivuna doesn't offer voice, so no document can fix this. Noma agreed on a call: record it as a note." },
    { label: "Complete the handover", kind: "handover", row: null },
  ],
  alder_bank: [
    { label: "Get the picture", kind: "tour", row: null },
    { label: "Coaching-scam detection: add the BioCatch connector approval", kind: "sample", sample: 0, row: /coaching/i, highlight: "add",
      hint: "Coaching detection depends on the BioCatch connector, which is in beta and needs a named approval; the SOW doesn't mention it. Add the approval and see what closes." },
    { label: "Coaching-scam detection: add the revised SOW", kind: "sample", sample: 1, row: /coaching/i, highlight: "add",
      hint: "The approval closed one gap, but the SOW still doesn't mention coaching detection. Add the revised SOW." },
    { label: "Add the signed contract", kind: "sample", sample: 2, row: null,
      hint: "The signed contract decides what Delivery inherits. Add it and see which fixes survive. Its Statement of Work sets a later date for coaching detection (1 May 2027), and the wording that closed the gap isn't in it, so the fix can't be confirmed and the gap reopens." },
    { label: "Hosting on Microsoft Azure: record the customer's agreement as a note", kind: "note", row: /hosting/i, highlight: "note",
      hint: "Elva doesn't offer Azure hosting, so no document can fix this. The customer agreed AWS Sydney on a call: record it as a note." },
    { label: "Complete the handover", kind: "handover", row: null },
  ],
};
export const findGuideRow = (commitments, re) => (re ? (commitments ?? []).find((c) => re.test(`${c.display_name ?? ""} ${c.name ?? ""}`)) ?? null : null);

// "Get the picture" (11 Nov): a 3-part tour in the bar. Its done state is the browser's only (sessionStorage), never the server's; Reset demo clears it.
export const TOUR_KEYS = ["brief", "journey", "commitments"];
const TOUR_STORE = "ptd.tour.";
export function tourDone(deal, storage = globalThis.sessionStorage) {
  try { return storage?.getItem(`${TOUR_STORE}${deal}`) === "1"; } catch { return false; }
}
export function markTourDone(deal, storage = globalThis.sessionStorage) {
  try { storage?.setItem(`${TOUR_STORE}${deal}`, "1"); } catch { /* private window: the tour is offered again on a reload */ }
}
export function clearTourDone(storage = globalThis.sessionStorage) {
  try { for (const deal of Object.keys(GUIDES)) storage?.removeItem(`${TOUR_STORE}${deal}`); } catch { /* nothing stored */ }
}
// Who the deal is with and who the go-live was promised to: the documents say it (Noma's discovery call: "We have already told our leadership that date";
// Alder's: "We've told our board that date"). The date, the stage and the count come from the deal itself.
export const TOUR_FACTS = {
  noma_journeys: { vendor: "Aivuna", customer: "Noma", audience: "its leadership" },
  alder_bank: { vendor: "Elva", customer: "Alder Bank", audience: "its board" },
};
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const NUMBER_WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];
export const dayMonth = (iso) => { const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? ""); return m ? `${+m[3]} ${MONTHS[+m[2] - 1]}` : ""; };
export const needAttention = (n) => (n === 0 ? "Nothing needs attention." : `${NUMBER_WORDS[n] ?? n} ${n === 1 ? "needs" : "need"} attention.`);
// The three captions, in order. facts: { goLive: "2027-02-01", stage: "contracting", stageLabel: "Contracting", open: 3 }.
export function tourCaptions(deal, facts) {
  const t = TOUR_FACTS[deal];
  const when = dayMonth(facts?.goLive);
  return [
    `What ${t.vendor} is delivering, and the ${when ? `${when} ` : ""}go-live ${t.customer} has promised ${t.audience}.`,
    `Every document so far, by stage. We're at ${facts?.stageLabel}${facts?.stage === "contracting" ? ": the last point to fix gaps cheaply" : ""}.`,
    `What the customer was told that the contract or catalogue doesn't back up. ${needAttention(facts?.open ?? 0)}`,
  ];
}

export function guideSteps(deal, samples, documents, commitments, handoverComplete = false, toured = false) {
  const list = GUIDES[deal] ?? [];
  const added = sampleSteps(samples ?? [], documents);
  const done = list.map((g) => {
    if (handoverComplete) return true;
    if (g.kind === "tour") return toured;
    if (g.kind === "sample") return added[g.sample]?.state === "done";
    if (g.kind === "note") return (findGuideRow(commitments, g.row)?.noted_count ?? 0) > 0;
    return false; // "Complete the handover" is done only when the record is locked
  });
  const current = done.indexOf(false);
  return list.map((g, i) => ({ ...g, n: i + 1, state: done[i] ? "done" : i === current ? "current" : "later" }));
}

// Where "Do step N" goes. The tour runs in the bar. The document steps and the note step open that commitment's drawer on its evidence, with one hint
// line above the buttons and the right button highlighted ("Add updated document", or "Record a note"); the visitor clicks it. The signed contract
// has no single commitment, so it opens the sample panel from + Add, with its hint. The handover step expands and scrolls to Handover.
export function guideAction(step, commitments) {
  const row = findGuideRow(commitments, step.row);
  const rowId = row ? row.id : null;
  if (step.kind === "tour") return { tour: true, drawer: null, row: null, handover: false };
  if (step.kind === "sample" && !step.row) return { drawer: { type: "add", fromId: null, hint: step.hint }, row: null, handover: false };
  if (step.kind === "handover") return { drawer: null, row: null, handover: true };
  return { drawer: row ? { type: "commitment", id: row.id, guide: { hint: step.hint, highlight: step.highlight } } : null, row: rowId, handover: false };
}

// The deal page tells the demo bar which step the visitor is on (11 Nov). Two contexts so the page, which only publishes, does not re-render when the
// bar's copy changes: PUBLISH is a stable setter, STATE is what the bar reads: null (no guide on this page) or
// { deal, documents, commitments, handoverComplete, facts, onDo, onTour }.
export const GuidePublishContext = createContext(() => {});
export const GuideStateContext = createContext(null);
export const BAR_NOTE_FALLBACK = "Shared with other visitors. If a deal has already been worked through, click Reset demo.";
// The current step for the bar: "Step N of 6" is shown above its text, the six progress dots beside it (11 Nov).
export const barStepText = (steps) => {
  const current = steps.find((s) => s.state === "current");
  return current ? { n: current.n, total: steps.length, label: `Step ${current.n} of ${steps.length}`, text: current.label, step: current } : null;
};
export const BAR_DONE = "Done · Reset demo to try again";

// "Start the guided demo →" on the landing page and the deal list (public mode): open Noma Journeys at step 1. The tour's browser-only done mark is cleared, so the
// deal opens on "Get the picture"; every other step is read from the deal itself.
export const FIRST_DEAL = "noma_journeys";
export const START_LABEL = "Start the guided demo \u2192";
// 12 Nov: the landing page has its own "Start the guided demo" button, so the bar drops its own there. The landing tells the app it is on screen.
export const LandingPublishContext = createContext(() => {});
export const LandingStateContext = createContext(false);
export const DemoNavContext = createContext({ current: null }); // .current is set by the app to openDeal(slug)
export function startGuidedDemo(nav, storage = globalThis.sessionStorage) {
  clearTourDone(storage);
  nav?.current?.(FIRST_DEAL);
}

// Scroll position that puts an element in the middle of its scroll container (the sample preview opens centred on its first highlighted line).
export const centeredScrollTop = ({ scrollTop, containerTop, containerHeight, elTop, elHeight }) =>
  Math.max(0, Math.round(scrollTop + (elTop - containerTop) - (containerHeight - elHeight) / 2));
