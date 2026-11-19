// "About this prototype" (19 Nov): one footer link that opens a short panel. It replaces the "About Dealshape" button, which led to the landing page; the
// logo now links there. Closes with the Close button, Esc or a click outside; focus moves into the panel and goes back to the link. Never on the locked record.
import { useEffect, useId, useRef, useState } from "react";
import { ABOUT_LABEL } from "./brand.js";
import { aboutKeyAction, aboutNext, aboutSections } from "./about.js";
import { useDemo } from "./demo.js";
import "./AboutPrototype.css";

// The panel itself, with no state: the page renders it open or not at all. onAction gets "button" (Close), "overlay" (a click outside).
export function AboutPanel({ sections, titleId, onAction, panelRef }) {
  return (
    <div className="about-overlay" onClick={() => onAction("overlay")}>
      <div className="about-panel" role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1} ref={panelRef} onClick={(e) => e.stopPropagation()}>
        <div className="about-head">
          <h2 id={titleId}>{ABOUT_LABEL}</h2>
          <button type="button" className="about-close" onClick={() => onAction("button")}>Close</button>
        </div>
        <div className="about-body">
          {sections.map((s) => (
            <section key={s.key} className={`about-sec about-${s.key}`}>
              {s.heading && <h3>{s.heading}</h3>}
              {s.items && <ul>{s.items.map((t) => <li key={t}>{t}</li>)}</ul>}
              {s.text && <p>{s.lead && <><strong>{s.lead}</strong>{" "}</>}{s.text}</p>}
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}

// Keep Tab inside the panel while it is open.
function trapTab(e, root) {
  if (!root) return;
  const items = [...root.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')].filter((el) => !el.disabled);
  const at = document.activeElement;
  if (!items.length) { e.preventDefault(); return; }
  const first = items[0];
  const last = items[items.length - 1];
  if (!root.contains(at) || (e.shiftKey && (at === first || at === root))) { e.preventDefault(); (e.shiftKey ? last : first).focus(); }
  else if (!e.shiftKey && at === last) { e.preventDefault(); first.focus(); }
}

export default function AboutPrototype({ className = "" }) {
  const demo = useDemo();
  const [open, setOpen] = useState(false);
  const titleId = useId();
  const linkRef = useRef(null);
  const panelRef = useRef(null);
  const act = (action) => setOpen((s) => aboutNext(s, action));
  useEffect(() => {
    if (!open) return undefined;
    const link = linkRef.current;
    panelRef.current?.focus();
    const onKey = (e) => {
      const action = aboutKeyAction(e);
      if (action) { e.stopPropagation(); setOpen((s) => aboutNext(s, action)); return; }
      if (e.key === "Tab") trapTab(e, panelRef.current);
    };
    document.addEventListener("keydown", onKey, true);
    return () => { document.removeEventListener("keydown", onKey, true); link?.focus(); };
  }, [open]);
  return (
    <>
      <button type="button" ref={linkRef} className={`about-link ${className}`.trim()} aria-haspopup="dialog" onClick={() => act("open")}>{ABOUT_LABEL}</button>
      {open && <AboutPanel sections={aboutSections(!!demo.public)} titleId={titleId} onAction={act} panelRef={panelRef} />}
    </>
  );
}
