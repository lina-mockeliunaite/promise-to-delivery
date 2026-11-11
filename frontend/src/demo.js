// Public demo mode (10 Nov). The server says whether it is on (GET /api/demo/config); everything here is off otherwise.
import { createContext, useContext } from "react";

export const DEMO_OFF = { public: false, banner: null, note_max: null };
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
