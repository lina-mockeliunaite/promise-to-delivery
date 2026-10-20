// The right-hand drawer (20 Oct). A commitment, a document, the add-document form and the note form open here instead of
// expanding the list in place, so the deal's shape stays in view. The same shell serves the locked record, read-only.
import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import { STAGE_LABELS, STATUS_CHIP, plainName, recordedBy, short } from "./dealpage.js";
import { renderDocument } from "./markdown.js";

export const Icon = ({ d, size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
    <path d={d} />
  </svg>
);
export const ICON = {
  close: "M6 6l12 12M18 6L6 18",
  back: "M19 12H5M11 18l-6-6 6-6",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  chevron: "M9 6l6 6-6 6",
};

const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input:not([type="hidden"]), select, [tabindex]:not([tabindex="-1"])';

// The shell: fixed to the right below the top bar, 520px (full width on a phone), slides in over 200ms, dims the page.
// Closes on Esc, the backdrop and the close button. Focus moves in and returns to what opened it. `focusKey` refocuses when
// the content changes (commitment to document and back).
export function Drawer({ labelledBy, onClose, focusKey, flush = false, children }) {
  const panel = useRef(null);
  const opener = useRef(null);
  useEffect(() => {
    opener.current = document.activeElement;
    return () => { const el = opener.current; if (el && document.contains(el)) el.focus(); };
  }, []);
  useEffect(() => {
    panel.current?.focus();
    panel.current?.querySelector(".dr-body")?.scrollTo?.(0, 0); // a new view always starts at its top, whatever the last one scrolled to
  }, [focusKey]);
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); return; }
      if (e.key !== "Tab" || !panel.current) return;
      const items = [...panel.current.querySelectorAll(FOCUSABLE)].filter((x) => x.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className={`dr-backdrop ${flush ? "is-flush" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside ref={panel} className={`dr ${flush ? "is-flush" : ""}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy} tabIndex={-1}>
        {children}
      </aside>
    </>
  );
}

// Title row for every drawer state: optional "← Back to commitment", the title, an optional status chip, and the ×.
export function DrawerHead({ id, title, sub, chip, backLabel, onBack, onClose }) {
  const st = chip ? STATUS_CHIP[chip] : null;
  return (
    <header className="dr-head">
      {backLabel && <button type="button" className="dr-back" onClick={onBack}><Icon d={ICON.back} size={14} /> {backLabel}</button>}
      <div className="dr-head-row">
        <div className="dr-head-title">
          <h2 id={id}>{title}</h2>
          {st && (
            <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
              {chip === "closed" ? <span className="dp-dot dp-dot-green" /> : <span className={`dp-dot ${chip === "noted" ? "dp-dot-grey" : ""}`} />}
              {st.label}
            </span>
          )}
        </div>
        <button type="button" className="dp-x" onClick={onClose} aria-label="Close"><Icon d={ICON.close} size={16} /></button>
      </div>
      {sub && <p className="dr-sub">{sub}</p>}
    </header>
  );
}

const NOTE_KIND = {
  addressed: "Addressed by note · not in the documents · reopens if the documents change",
  reopened: "Was addressed by a note · reopened because the documents changed since",
  reconfirm: "Note needs re-confirming: the documents changed since",
  kept: "",
};

function Source({ label, date, doc, onOpen }) {
  const text = `${label}${date ? `, ${short(date)}` : ""}`;
  return (
    <p className="dr-source">
      Source:{" "}
      {doc && onOpen ? <button type="button" className="dr-linkbtn" onClick={onOpen}>{text}</button> : <span>{text}</span>}
    </p>
  );
}

// A commitment, read from the view built in dealpage.js (live register or locked snapshot). readOnly: no footer, no actions.
export function CommitmentView({ v, titleId, readOnly, me = "", onOpenDoc, onSeen, onNote, onAddDoc, onCatalogue, onClose }) {
  const seenByMe = v.seen.some((x) => x.by === me.trim());
  return (
    <>
      <DrawerHead id={titleId} title={v.title} chip={v.status} onClose={onClose} />
      <div className="dr-body">
        <section className="dr-sec">
          <h3 className="dr-label">Customer was told</h3>
          {v.told.map((t) => (
            <div key={t.quote} className="dr-block">
              <blockquote className="dr-quote">{t.quote}</blockquote>
              <Source label={t.label} date={t.date} doc={t.doc} onOpen={() => onOpenDoc?.(t.doc, t.quote)} />
            </div>
          ))}
          {!v.told.length && (v.toldFallback ? <p className="dr-plain">{v.toldFallback}</p> : <p className="dr-muted">No checked quote is stored for this commitment.</p>)}
        </section>

        <section className="dr-sec">
          <h3 className="dr-label">Contract says</h3>
          {v.contract.text && <p className="dr-plain">{v.contract.text}</p>}
          {v.contract.quote && (
            <div className="dr-block">
              <blockquote className="dr-quote">{v.contract.quote.quote}</blockquote>
              <Source label={v.contract.quote.label} doc={v.contract.quote.doc} onOpen={() => onOpenDoc?.(v.contract.quote.doc, v.contract.quote.quote)} />
            </div>
          )}
          {v.contract.missing && <p className="dr-muted">Searched for: {v.contract.missing.map((m) => `“${m}”`).join(", ")}</p>}
        </section>

        <section className="dr-sec">
          <h3 className="dr-label">{v.status === "closed" ? "What closed it" : "What we found"}</h3>
          {v.found.map((f) => (
            <div key={f.label} className="dr-row">
              <strong>{f.label}</strong>
              {f.fact && <span>{f.fact}</span>}
            </div>
          ))}
          {v.catalogue.map((p) => (
            <button key={p} type="button" className="cat-open" onClick={() => onCatalogue?.(p)} title="Open the product catalogue at this entry">
              Catalogue: {p.split("/").slice(0, 2).join(" · ")}{p.split("/").length > 2 ? ` · ${p.split("/").slice(2).join(" ").replace(/_/g, " ")}` : ""}
            </button>
          ))}
          {v.closed.length > 0 && (
            <div className="dr-closed">
              {v.status !== "closed" && <span className="dr-label">Already closed by the documents</span>}
              {v.closed.map((c) => <p key={c.label}><strong>{c.label}.</strong> {c.by}</p>)}
            </div>
          )}
          {v.ai.length > 0 && (
            <div className="dr-ai">
              <span className="dr-ailabel">AI-written summary · quotes checked against the documents</span>
              {v.ai.map((t) => <p key={t}>{t}</p>)}
            </div>
          )}
          {v.extracted && <p className="dr-muted">Extracted as: {v.extracted}</p>}
        </section>

        <section className="dr-sec">
          <h3 className="dr-label">Notes</h3>
          {v.notes.length === 0 && <p className="dr-muted">No notes yet</p>}
          {v.notes.map((n) => (
            <div key={`${n.by}|${n.text}`} className={`dr-note ${n.kind === "reconfirm" || n.kind === "reopened" ? "is-stale" : ""}`}>
              <span className="dr-note-by">{recordedBy(n.by, n.at, fmtDate)}</span>
              <p>“{n.text}”</p>
              {NOTE_KIND[n.kind] && <span className="dr-muted">{NOTE_KIND[n.kind]}</span>}
            </div>
          ))}
          {readOnly && v.status === "open" && (
            <p className="dr-muted">Seen before handover by: {v.seen.length ? v.seen.map((s) => plainName(s.by)).join(" · ") : "nobody"}</p>
          )}
        </section>
      </div>
      {!readOnly && v.status === "open" && (
        <footer className="dr-foot">
          <p className="dr-seen">
            Seen by: {v.seen.length ? v.seen.map((s) => `${plainName(s.by)} (${short((s.at || "").slice(0, 10))})`).join(" · ") : "nobody yet"}
            {" · "}
            {seenByMe ? <span>Seen by you</span> : <button type="button" className="dr-textlink" onClick={onSeen} title="Records that you have looked at this. It does not close or change anything.">Mark as seen</button>}
          </p>
          <div className="dr-actions">
            <button type="button" className="dp-btn" onClick={onNote}>Record a note</button>
            <button type="button" className="dp-btn dp-btn-dark" onClick={onAddDoc}>Add updated document</button>
          </div>
        </footer>
      )}
    </>
  );
}

// The rendered tree as React elements. Only text nodes carry document content, and React escapes it: nothing is injected.
function Nodes({ nodes, markRef }) {
  return nodes.map((n, k) => {
    if (n.t === "strong") return <strong key={k}><Nodes nodes={n.children} markRef={markRef} /></strong>;
    if (n.t === "em") return <em key={k}><Nodes nodes={n.children} markRef={markRef} /></em>;
    if (n.t === "code") return <code key={k}>{n.text}</code>;
    if (n.t === "mark") {
      const first = !markRef.taken && (markRef.taken = true);
      return <mark key={k} ref={first ? markRef : undefined}><Nodes nodes={n.children} markRef={markRef} /></mark>;
    }
    return n.text;
  });
}

function Block({ b, markRef }) {
  if (b.t === "hr") return <hr />;
  if (b.t === "ul" || b.t === "ol") {
    const List = b.t;
    return <List>{b.items.map((it, k) => <li key={k}><Nodes nodes={it} markRef={markRef} /></li>)}</List>;
  }
  if (b.t === "h") {
    const H = `h${Math.min(b.level + 2, 6)}`; // the drawer's own title is the h2
    return <H><Nodes nodes={b.children} markRef={markRef} /></H>;
  }
  return <p><Nodes nodes={b.children} markRef={markRef} /></p>;
}

// A document: label, date and stage in the header, the stored text rendered as formatted text in a reading column, the quoted
// sentence in soft amber when it was opened from a quote and can be placed on the rendered text. Read-only.
export function DocumentView({ deal, doc, quote, titleId, backLabel, onBack, onClose }) {
  const [state, setState] = useState({ loading: true });
  const mark = useRef(null);
  useEffect(() => {
    let live = true;
    setState({ loading: true });
    api.fetchDocumentText(deal, doc.source_version_id).then((r) => live && setState(r), (err) => live && setState({ error: err.message }));
    return () => { live = false; };
  }, [deal, doc.source_version_id]);
  const ready = !state.loading && !state.error;
  const rendered = useMemo(() => (ready ? renderDocument(state.text, quote) : null), [ready, state.text, quote]);
  useEffect(() => { mark.current?.scrollIntoView({ block: "center" }); }, [rendered]);
  const stage = STAGE_LABELS[doc.stage];
  const markRef = mark;
  markRef.taken = false;
  return (
    <>
      <DrawerHead id={titleId} title={doc.name} backLabel={backLabel} onBack={onBack} onClose={onClose}
                  sub={[fmtDate(doc.version_date || doc.date), stage, doc.version > 1 ? `v${doc.version}` : ""].filter(Boolean).join(" · ")} />
      <div className="dr-body">
        {doc.link && (
          <a className="dr-drive" href={doc.link} target="_blank" rel="noopener noreferrer" aria-label="Open in Drive" title="Opens where the document lives">
            <Icon d={ICON.link} size={14} /> Open in Drive
          </a>
        )}
        {quote && rendered && !rendered.found && <p className="dr-muted">The quoted sentence is not in this version of the document.</p>}
        {state.error ? <p className="dp-error">{state.error}</p> : !ready ? <p className="dr-muted">Loading…</p> : (
          <div className="dr-doc">{rendered.blocks.map((b, k) => <Block key={k} b={b} markRef={markRef} />)}</div>
        )}
      </div>
    </>
  );
}

// Used by both: the line the sentence-style mismatch is rendered with (dark terms, muted connecting words).
export function MismatchSentence({ parts }) {
  if (!parts.length) return null;
  return (
    <span className="dp-prow-line">
      {parts.map((p, n) => (p.strong ? <strong key={n}>{p.text}</strong> : <span key={n}>{p.text}</span>))}
    </span>
  );
}
