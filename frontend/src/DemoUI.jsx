// Public demo pieces (10 Nov): the banner, the note under a name field, and the sample-file list that replaces uploading.
import { useEffect, useState } from "react";
import * as api from "./api.js";
import { NAME_NOTE, NO_SAMPLES, addSample, useDemo } from "./demo.js";

export function DemoBanner() {
  const demo = useDemo();
  return demo.public ? <div className="demo-banner" role="note">{demo.banner}</div> : null;
}

export function DemoNameNote() {
  return useDemo().public ? <p className="dp-faint dp-small demo-name-note">{NAME_NOTE}</p> : null;
}

export function SamplePicker({ deal, documents, labels, onDone, onClose, initialSamples = null }) {
  const [samples, setSamples] = useState(initialSamples);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => { api.fetchSamples(deal).then((r) => setSamples(r.samples), (e) => { setSamples([]); setError(e.message); }); }, [deal]);
  const add = async (s) => {
    setBusy(s.file);
    setError(null);
    try {
      const { review, added } = await addSample(api, deal, s, documents, labels); // the same call, and the same checks, as an upload
      onDone(review, added);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="dp-add demo-samples">
      <span className="dp-field-label">Use a sample file</span>
      <p className="dp-faint dp-small">This public demo takes its own sample files, not uploads.</p>
      {samples && samples.length === 0 && !error && <p className="dp-faint dp-small">{NO_SAMPLES}</p>}
      <ul className="demo-sample-list">
        {(samples ?? []).map((s) => (
          <li key={s.file}>
            <div><strong>{s.file}</strong><br /><span className="dp-faint dp-small">{s.description}</span></div>
            <button type="button" className="dp-btn dp-btn-dark" disabled={!!busy} onClick={() => add(s)}>{busy === s.file ? "Checking…" : "Add and check"}</button>
          </li>
        ))}
      </ul>
      <div className="dp-actions">
        {error && <span className="dp-error" role="alert">{error}</span>}
        <button type="button" className="dp-btn dp-btn-ghost" onClick={onClose} disabled={!!busy}>Cancel</button>
      </div>
    </div>
  );
}
