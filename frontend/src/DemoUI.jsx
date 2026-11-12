// Public demo pieces (10 Nov): the demo bar, the note under a name field, and the sample-file list that replaces uploading.
import { useContext, useEffect, useRef, useState } from "react";
import * as api from "./api.js";
import ResetDemo from "./ResetDemo.jsx";
import { blockLines, parsePreview } from "./preview.js";
import { ALL_ADDED, BAR_DONE, BAR_NOTE_FALLBACK, DemoNavContext, GUIDES, GuideStateContext, LandingStateContext, START_LABEL, NAME_NOTE, NO_SAMPLES, TOUR_KEYS, addSample, barStepText, centeredScrollTop, filingLine, guideSteps, markTourDone, sampleSteps, startGuidedDemo, tourCaptions, tourDone, useDemo } from "./demo.js";

export function DemoNameNote() {
  return useDemo().public ? <p className="dp-faint dp-small demo-name-note">{NAME_NOTE}</p> : null;
}

// The demo bar (11 Nov): one sticky bar at the top of every public page. Deal pages with a guide: the status | "Step N of 5: <step>"
// + "Do step N" | "All steps ▾" and "Reset demo". Other pages: the status and "Reset demo". "All steps" opens a small dropdown under the bar with the
// five steps (done, current, later) and the shared-demo note. With all five done the step reads "Done · Reset demo to try again". The step logic
// (which step is current, where "Do step N" goes) is the same as before the guide moved here: guideSteps and guideAction, with the deal page's doStep.
export function DemoBar({ initialSamples = null, initialOpen = false, initialTour = null, toured = null }) {
  const demo = useDemo();
  const guide = useContext(GuideStateContext);
  const nav = useContext(DemoNavContext);
  const onLanding = useContext(LandingStateContext);
  const [samples, setSamples] = useState(initialSamples);
  const [open, setOpen] = useState(initialOpen);
  const [tour, setTour] = useState(initialTour); // null, or the part (0-2) of the "Get the picture" tour being shown in the bar
  const [, setToured] = useState(0); // a re-render when the tour is marked done
  const bar = useRef(null);
  const deal = guide?.deal;
  useEffect(() => {
    if (!demo.public || !deal || guide.handoverComplete || initialSamples) return undefined;
    let alive = true;
    api.fetchSamples(deal).then((r) => alive && setSamples(r.samples), () => alive && setSamples([]));
    return () => { alive = false; };
  }, [demo.public, deal, guide?.handoverComplete, initialSamples]);
  useEffect(() => { setOpen(false); setTour(null); }, [deal]);
  const stopTour = (finished) => { setTour(null); guide?.onTour?.(null); if (finished) { markTourDone(deal); setToured((n) => n + 1); } };
  const goTour = (part) => { setOpen(false); setTour(part); guide?.onTour?.(TOUR_KEYS[part]); };
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
  const steps = guide && GUIDES[deal] && (guide.handoverComplete || samples) ? guideSteps(deal, samples, guide.documents, guide.commitments, guide.handoverComplete, toured ?? tourDone(deal)) : null;
  const allDone = !!steps && steps.every((s) => s.state === "done");
  const now = steps && !allDone ? barStepText(steps) : null;
  const captions = steps && tour != null ? tourCaptions(deal, guide.facts) : null; // while the tour runs, the bar's text is the caption
  return (
    <div className="demo-bar" ref={bar} role="region" aria-label="Public demo">
      <div className="demo-bar-row">
        {steps && <span className="demo-bar-pill">Demo guide</span>}
        {!steps && <strong className="demo-bar-status">{demo.banner}</strong>}
        {!steps && !onLanding && <button type="button" className="demo-bar-do" onClick={() => startGuidedDemo(nav)}>{START_LABEL}</button>}
        {steps && (
          <span className="demo-bar-stepblock" role="status">
            <span className="demo-bar-meta">
              <span className="demo-bar-n">{allDone ? `All ${steps.length} steps` : `Step ${now.n} of ${steps.length}`}</span>
              <span className="demo-bar-dots" role="img" aria-label={`${steps.filter((s) => s.state === "done").length} of ${steps.length} steps done`}>
                {steps.map((s) => <span key={s.n} className={`demo-bar-dot is-${s.state}`} />)}
              </span>
            </span>
            <span className="demo-bar-step">{captions ? captions[tour] : allDone ? BAR_DONE : now.text}</span>
          </span>
        )}
        {captions && <span className="demo-bar-tourn">{tour + 1} of {captions.length}</span>}
        {captions && <button type="button" className="demo-bar-do" onClick={() => (tour < captions.length - 1 ? goTour(tour + 1) : stopTour(true))}>{tour < captions.length - 1 ? "Next" : "Finish"}</button>}
        {captions && <button type="button" className="demo-bar-link" onClick={() => stopTour(true)}>Skip tour</button>}
        {!captions && now && <button type="button" className="demo-bar-do" onClick={() => { setOpen(false); if (now.step.kind === "tour") goTour(0); else guide.onDo(now.step); }}>{now.step.kind === "tour" ? "Show me" : `Do step ${now.n}`}</button>}
        <span className="demo-bar-right">
          {steps && <button type="button" className="demo-bar-link" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}>All steps ▾</button>}
          <ResetDemo variant="bar" />
        </span>
      </div>
      {steps && open && (
        <div className="demo-bar-menu" role="group" aria-label="All steps">
          <p className="demo-bar-menu-status">{demo.banner}</p>
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

// The sample as a formatted document, read-only (11 Nov): headings, paragraphs, bullet lists and tables from its Markdown, the lines the check uses
// highlighted (a highlighted table row for the pricing notes). `key` is the list of source line numbers from the sample route.
function Inline({ nodes }) {
  return nodes.map((n, k) => (n.t === "strong" ? <strong key={k}><Inline nodes={n.children} /></strong> : n.t === "em" ? <em key={k}><Inline nodes={n.children} /></em>
    : n.t === "code" ? <code key={k}>{n.text}</code> : n.text));
}

export function PreviewDoc({ text, keyLines = [] }) {
  const key = new Set(keyLines);
  const hit = (b) => blockLines(b).some((l) => key.has(l));
  return parsePreview(text).map((b, i) => {
    const cls = hit(b) && b.t !== "table" && b.t !== "p" ? " is-key" : "";
    if (b.t === "h") { const H = `h${Math.min(b.level + 2, 6)}`; return <H key={i} className={`demo-doc-h${cls}`}><Inline nodes={b.nodes} /></H>; }
    if (b.t === "hr") return <hr key={i} />;
    if (b.t === "ul") return <ul key={i}>{b.items.map((it, k) => <li key={k} className={key.has(it.line) ? "is-key" : ""}><Inline nodes={it.nodes} /></li>)}</ul>;
    if (b.t === "table") {
      return (
        <table key={i} className="demo-doc-table">
          {b.head && <thead><tr>{b.head.cells.map((c, k) => <th key={k}><Inline nodes={c} /></th>)}</tr></thead>}
          <tbody>{b.rows.map((r, k) => <tr key={k} className={key.has(r.line) ? "is-key" : ""}>{r.cells.map((c, j) => <td key={j}><Inline nodes={c} /></td>)}</tr>)}</tbody>
        </table>
      );
    }
    return <p key={i}>{b.lines.map((l, k) => <span key={k} className={`demo-doc-ln${key.has(l.line) ? " is-key" : ""}`}><Inline nodes={l.nodes} />{k < b.lines.length - 1 && <br />}</span>)}</p>;
  });
}

// preview/onPreview: the preview can be held by the panel around this list (so the drawer's one back link can say "Back to samples"); without them it is held here.
export function SamplePicker({ deal, documents, labels, onDone, onClose, initialSamples = null, hint = "", initialPreview = null, preview: controlled, onPreview }) {
  const [samples, setSamples] = useState(initialSamples);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [own, setOwn] = useState(initialPreview); // { sample, text, key: [line numbers] }: a sample read-only in this panel, before adding it
  const preview = onPreview ? controlled : own;
  const setPreview = onPreview ?? setOwn;
  const doc = useRef(null);
  useEffect(() => { api.fetchSamples(deal).then((r) => setSamples(r.samples), (e) => { setSamples([]); setError(e.message); }); }, [deal]);
  // On open the first highlighted line is brought to the middle of the preview.
  useEffect(() => {
    const c = doc.current;
    const el = c?.querySelector(".is-key");
    if (!c || !el) return;
    const cr = c.getBoundingClientRect(), er = el.getBoundingClientRect();
    c.scrollTop = centeredScrollTop({ scrollTop: c.scrollTop, containerTop: cr.top, containerHeight: c.clientHeight, elTop: er.top, elHeight: er.height });
  }, [preview]);
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
  // Preview: the existing sample text route, nothing stored; the route also says which lines the check uses.
  const show = async (s) => {
    setBusy(s.file);
    setError(null);
    try {
      const r = await api.fetchSample(deal, s.file);
      setPreview({ sample: s, text: r.text, key: r.key_lines ?? [] });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(null);
    }
  };
  const steps = sampleSteps(samples ?? [], documents);
  if (preview) {
    const step = steps.find((x) => x.sample.file === preview.sample.file);
    return (
      <div className="dp-add demo-samples demo-preview">
        <h3 className="demo-preview-title">{step ? `${step.n}. ` : ""}{preview.sample.title}</h3>
        <p className="dp-faint dp-small">{filingLine(preview.sample, documents, labels)}</p>
        {preview.key.length > 0 && <p className="dp-small demo-preview-legend"><mark>Highlighted</mark>: the lines the check will use.</p>}
        <div className="demo-preview-text demo-doc" ref={doc} role="document" aria-label={`${preview.sample.title}, read-only`}>
          <PreviewDoc text={preview.text} keyLines={preview.key} />
        </div>
        {error && <p className="dp-error" role="alert">{error}</p>}
        {step?.state === "next" && (
          <div className="demo-preview-foot">
            <button type="button" className="dp-btn dp-btn-dark" disabled={!!busy} onClick={() => add(preview.sample)}>{busy === preview.sample.file ? "Checking…" : "Add and check"}</button>
          </div>
        )}
      </div>
    );
  }
  return (
    <div className="dp-add demo-samples">
      <span className="dp-field-label">Use a sample file</span>
      {hint && <p className="demo-hint" role="note">{hint}</p>}
      <p className="dp-faint dp-small">This public demo takes its own sample files, not uploads.</p>
      {samples && samples.length === 0 && !error && <p className="dp-faint dp-small">{NO_SAMPLES}</p>}
      {samples && samples.length > 0 && steps.every((x) => x.state === "done") && <p className="demo-all-added" role="status">{ALL_ADDED[deal] ?? ""}</p>}
      <ol className="demo-sample-list">
        {steps.map(({ sample: s, n, state, after }) => (
          <li key={s.file} className={`is-${state}`}>
            <span className="demo-sample-n" aria-hidden="true">{n}</span>
            <div>
              <strong>{s.title}</strong>
              <span className="dp-small dp-block">{s.summary}</span>
              <span className="dp-faint dp-small dp-block">{filingLine(s, documents, labels)}</span>
            </div>
            <span className="demo-sample-actions">
              {state === "next" && <button type="button" className="dp-btn dp-btn-dark" disabled={!!busy} onClick={() => add(s)}>{busy === s.file ? "Checking…" : "Add and check"}</button>}
              {state === "later" && <button type="button" className="dp-btn dp-btn-dark" disabled>After step {after}</button>}
              {state === "done" && <span className="demo-sample-done">Added</span>}
              <button type="button" className="dp-link-btn dp-brand demo-sample-preview" disabled={!!busy} onClick={() => show(s)}>Preview</button>
            </span>
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
