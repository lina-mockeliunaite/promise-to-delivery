// Public demo pieces (10 Nov): the demo bar, the note under a name field, and the sample-file list that replaces uploading.
import { useContext, useEffect, useRef, useState } from "react";
import * as api from "./api.js";
import ResetDemo from "./ResetDemo.jsx";
import { ALL_ADDED, BAR_DONE, BAR_NOTE_FALLBACK, GUIDES, GuideStateContext, NAME_NOTE, NO_SAMPLES, addSample, barStepText, filingLine, guideSteps, sampleSteps, useDemo } from "./demo.js";

export function DemoNameNote() {
  return useDemo().public ? <p className="dp-faint dp-small demo-name-note">{NAME_NOTE}</p> : null;
}

// The demo bar (11 Nov): one sticky bar at the top of every public page. Deal pages with a guide: the status | "Step N of 5: <step>"
// + "Do step N" | "All steps ▾" and "Reset demo". Other pages: the status and "Reset demo". "All steps" opens a small dropdown under the bar with the
// five steps (done, current, later) and the shared-demo note. With all five done the step reads "Done · Reset demo to try again". The step logic
// (which step is current, where "Do step N" goes) is the same as before the guide moved here: guideSteps and guideAction, with the deal page's doStep.
export function DemoBar({ initialSamples = null, initialOpen = false }) {
  const demo = useDemo();
  const guide = useContext(GuideStateContext);
  const [samples, setSamples] = useState(initialSamples);
  const [open, setOpen] = useState(initialOpen);
  const bar = useRef(null);
  const deal = guide?.deal;
  useEffect(() => {
    if (!demo.public || !deal || guide.handoverComplete || initialSamples) return undefined;
    let alive = true;
    api.fetchSamples(deal).then((r) => alive && setSamples(r.samples), () => alive && setSamples([]));
    return () => { alive = false; };
  }, [demo.public, deal, guide?.handoverComplete, initialSamples]);
  useEffect(() => { setOpen(false); }, [deal]);
  // The page's own sticky bars and drawers sit below this bar: tell them how tall it is (0 when there is none, so local mode is as it was).
  useEffect(() => {
    const root = document.documentElement;
    if (!demo.public || !bar.current) { root.style.removeProperty("--demo-bar-h"); return undefined; }
    const set = () => root.style.setProperty("--demo-bar-h", `${bar.current.offsetHeight}px`);
    set();
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(set);
    ro?.observe(bar.current);
    return () => { ro?.disconnect(); root.style.removeProperty("--demo-bar-h"); };
  }, [demo.public]);
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    const onDown = (e) => { if (bar.current && !bar.current.contains(e.target)) setOpen(false); };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onDown);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("mousedown", onDown); };
  }, [open]);
  if (!demo.public) return null;
  const steps = guide && GUIDES[deal] && (guide.handoverComplete || samples) ? guideSteps(deal, samples, guide.documents, guide.commitments, guide.handoverComplete) : null;
  const allDone = !!steps && steps.every((s) => s.state === "done");
  const now = steps && !allDone ? barStepText(steps) : null;
  return (
    <div className="demo-bar" ref={bar} role="region" aria-label="Public demo">
      <div className="demo-bar-row">
        <strong className="demo-bar-status">{demo.banner}</strong>
        {steps && <span className="demo-bar-step" role="status">{allDone ? BAR_DONE : now.text}</span>}
        {now && <button type="button" className="demo-bar-do" onClick={() => { setOpen(false); guide.onDo(now.step); }}>Do step {now.n}</button>}
        <span className="demo-bar-right">
          {steps && <button type="button" className="demo-bar-link" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}>All steps ▾</button>}
          <ResetDemo variant="bar" />
        </span>
      </div>
      {steps && open && (
        <div className="demo-bar-menu" role="group" aria-label="All steps">
          <ol className="demo-guide-list">
            {steps.map((s) => (
              <li key={s.n} className={`is-${s.state}`}>
                <span className="demo-guide-n" aria-hidden="true">{s.state === "done" ? "✓" : s.n}</span>
                <span className="demo-guide-label">{s.label}<span className="dp-sr">{s.state === "done" ? " (done)" : s.state === "current" ? " (current)" : ""}</span></span>
              </li>
            ))}
          </ol>
          <p className="demo-bar-note">{demo.note ?? BAR_NOTE_FALLBACK}</p>
        </div>
      )}
    </div>
  );
}

// A quiet link under a note box (public mode only): it fills the box; the visitor still saves.
export function UseSampleText({ onUse }) {
  return <button type="button" className="dp-link-btn dp-brand demo-sample-text" onClick={onUse}>Use sample text</button>;
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
      {samples && samples.length > 0 && sampleSteps(samples, documents).every((x) => x.state === "done") && <p className="demo-all-added" role="status">{ALL_ADDED[deal] ?? ""}</p>}
      <ol className="demo-sample-list">
        {sampleSteps(samples ?? [], documents).map(({ sample: s, n, state, after }) => (
          <li key={s.file} className={`is-${state}`}>
            <span className="demo-sample-n" aria-hidden="true">{n}</span>
            <div>
              <strong>{s.title}</strong>
              <span className="dp-small dp-block">{s.summary}</span>
              <span className="dp-faint dp-small dp-block">{filingLine(s, documents, labels)}</span>
            </div>
            {state === "next" && <button type="button" className="dp-btn dp-btn-dark" disabled={!!busy} onClick={() => add(s)}>{busy === s.file ? "Checking…" : "Add and check"}</button>}
            {state === "later" && <button type="button" className="dp-btn dp-btn-dark" disabled>After step {after}</button>}
            {state === "done" && <span className="demo-sample-done">Added</span>}
          </li>
        ))}
      </ol>
      <div className="dp-actions">
        {error && <span className="dp-error" role="alert">{error}</span>}
        <button type="button" className="dp-btn dp-btn-ghost" onClick={onClose} disabled={!!busy}>Cancel</button>
      </div>
    </div>
  );
}
