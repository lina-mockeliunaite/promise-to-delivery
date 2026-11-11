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
