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
// deal once its document is past version 1; a new-document sample once a document of its type is there. "later" says which step it waits for.
export function sampleSteps(samples, documents) {
  const docs = documents ?? [];
  const used = (s) => (s.version_of ? docs.some((d) => d.source_key === s.version_of && d.version > 1) : docs.some((d) => d.doc_type === s.doc_type));
  const next = samples.findIndex((s) => !used(s));
  return samples.map((s, i) => ({ sample: s, n: i + 1,
    state: next === -1 || i < next ? "done" : i === next ? "next" : "later", after: i })); // "After step N": the step before it
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
    sales: "Signed with coaching-scam detection and the 750,000 daily volume still open; the signed contract incorporates the 9 October SOW. Hosting agreed as AWS Sydney on the 14 Oct call. Raise both open items at kickoff.",
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
export const GUIDE_TITLE = "Try it in 5 steps";
export const GUIDE_DONE = "Done. Reset demo to try again.";
export const GUIDES = {
  noma_journeys: [
    { label: "Launch specialist: add the approval", kind: "sample", sample: 0, row: /launch specialist/i },
    { label: "Support in 12 languages: add the revised contract", kind: "sample", sample: 1, row: /12 languages/i },
    { label: "Add the signed contract", kind: "sample", sample: 2, row: null },
    { label: "Phone calls: record the customer's agreement as a note", kind: "note", row: /phone/i },
    { label: "Complete the handover", kind: "handover", row: null },
  ],
  alder_bank: [
    { label: "Coaching-scam detection: add the BioCatch connector approval", kind: "sample", sample: 0, row: /coaching/i },
    { label: "Coaching-scam detection: add the revised SOW", kind: "sample", sample: 1, row: /coaching/i },
    { label: "Add the signed contract", kind: "sample", sample: 2, row: null },
    { label: "Hosting on Microsoft Azure: record the customer's agreement as a note", kind: "note", row: /hosting/i },
    { label: "Complete the handover", kind: "handover", row: null },
  ],
};
export const findGuideRow = (commitments, re) => (re ? (commitments ?? []).find((c) => re.test(`${c.display_name ?? ""} ${c.name ?? ""}`)) ?? null : null);

export function guideSteps(deal, samples, documents, commitments, handoverComplete = false) {
  const list = GUIDES[deal] ?? [];
  const added = sampleSteps(samples ?? [], documents);
  const done = list.map((g, i) => {
    if (handoverComplete) return true;
    if (g.kind === "sample") return added[g.sample]?.state === "done";
    if (g.kind === "note") return (findGuideRow(commitments, g.row)?.noted_count ?? 0) > 0;
    return false; // "Complete the handover" is done only when the record is locked
  });
  const current = done.indexOf(false);
  return list.map((g, i) => ({ ...g, n: i + 1, state: done[i] ? "done" : i === current ? "current" : "later" }));
}

// Where "Do step N" goes: the drawer to open (the sample panel from that commitment, the sample panel from + Add, or that row's note form),
// the row to scroll to and highlight, or the Handover card to expand and scroll to.
export function guideAction(step, commitments) {
  const row = findGuideRow(commitments, step.row);
  if (step.kind === "sample") return { drawer: { type: "add", fromId: row ? row.id : null }, row: row ? row.id : null, handover: false };
  if (step.kind === "note") return { drawer: row ? { type: "note", id: row.id } : null, row: row ? row.id : null, handover: false };
  return { drawer: null, row: null, handover: true };
}

// The deal page tells the demo bar which step the visitor is on (11 Nov). Two contexts so the page, which only publishes, does not re-render when the
// bar's copy changes: PUBLISH is a stable setter, STATE is what the bar reads: null (no guide on this page) or
// { deal, documents, commitments, handoverComplete, onDo }.
export const GuidePublishContext = createContext(() => {});
export const GuideStateContext = createContext(null);
export const BAR_NOTE_FALLBACK = "Shared with other visitors. If a deal has already been worked through, click Reset demo.";
export const barStepText = (steps) => {
  const current = steps.find((s) => s.state === "current");
  return current ? { n: current.n, text: `Step ${current.n} of ${steps.length}: ${current.label}`, step: current } : null;
};
export const BAR_DONE = "Done · Reset demo to try again";
