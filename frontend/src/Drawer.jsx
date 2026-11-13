// The right-hand drawer (20 Oct). A commitment, a document, the add-document form and the note form open here instead of
// expanding the list in place, so the deal's shape stays in view. The same shell serves the locked record, read-only.
import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import { STAGE_LABELS, STATUS_CHIP, alsoIn, catalogueLabel, closedSettled, draftSourceLabel, plainName, recordedBy, relatedHeading, short, signedConfirmedLabel } from "./dealpage.js";
import { renderDocument } from "./markdown.js";
import { shortHash, verifyText } from "./docHash.js";

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

// The catalogue's entry names, { CAP-027: "Scam-call alerts" }, for the drawer's "Catalogue:" line (13 Nov, Round 7). Provided by the deal page and the locked record; empty until loaded.
export const CatalogueNamesContext = createContext({});
export function CatalogueNames({ deal, children }) {
  return <CatalogueNamesContext.Provider value={useCatalogueNames(deal)}>{children}</CatalogueNamesContext.Provider>;
}
export function useCatalogueNames(deal) {
  const [names, setNames] = useState({});
  useEffect(() => {
    let live = true;
    if (deal) api.fetchCatalogue({ deal }).then((c) => live && setNames(Object.fromEntries((c.capabilities ?? []).map((x) => [x.id, x.name]))), () => {});
    return () => { live = false; };
  }, [deal]);
  return names;
}

// "Confirmed in the signed contract (Signed contract, 20 Oct)": the parenthesis is the link to the signed document when it is known.
// 13 Nov, Round 8: "Signed contract · confirmed (20 Oct)": the signed document's own label and date, and what the check found; the label is the link when the document is known.
function ConfirmedStatus({ signed, onOpen }) {
  const label = signedConfirmedLabel(signed);
  return <>{signed.doc && onOpen ? <button type="button" className="dr-linkbtn" onClick={onOpen}>{label}</button> : label}{signed.date ? ` (${short(signed.date)})` : ""}</>;
}

// A reference-back ("RFP response, 29 Sep, above") has no Source line of its own: the reference is the link to that document when it is known (13 Nov, Round 7).
function Ref({ text, doc, onOpen }) {
  return <p className="dr-muted">{doc && onOpen ? <button type="button" className="dr-linkbtn" onClick={onOpen}>{text}</button> : text}</p>;
}

function Source({ label, date, doc, onOpen, also, guided = false }) {
  const text = `${label}${date ? `, ${short(date)}` : ""}`;
  return (
    <p className="dr-source">
      Source:{" "}
      {doc && onOpen ? <button type="button" className={`dr-linkbtn${guided ? " is-guided" : ""}`} onClick={onOpen}>{text}</button> : <span>{text}</span>}
      {alsoIn(also) && <span className="dr-also"> · {alsoIn(also)}</span>}
    </p>
  );
}

// A commitment, read from the view built in dealpage.js (live register or locked snapshot). readOnly: no footer, no actions.
// guide (public demo): { hint, highlight: "add" | "note" } from the demo bar's "Do step N": one hint line above the buttons, and the button to click highlighted.
export function CommitmentView({ v, documents = [], titleId, readOnly, me = "", guide = null, onOpenDoc, onSeen, onNote, onAddDoc, onCatalogue, onClose }) {
  const seenByMe = v.seen.some((x) => x.by === me.trim());
  const catNames = useContext(CatalogueNamesContext);
  return (
    <>
      <DrawerHead id={titleId} title={v.title} chip={v.status} onClose={onClose} />
      <div className="dr-body">
        {/* Where it stands first (11 Nov): the current status and any recorded note. The AI reading is last, collapsed. */}
        <section className="dr-sec dr-stands">
          <h3 className="dr-label">Where it stands</h3>
          <p className="dr-plain"><strong>{v.stands}</strong></p>
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

        <section className="dr-sec">
          <h3 className="dr-label">Customer was told</h3>
          {v.told.map((t, k) => (
            <div key={t.quote} className="dr-block">
              <blockquote className="dr-quote">{t.quote}</blockquote>
              <Source label={t.label} date={t.date} doc={t.doc} also={t.also} guided={!!guide?.told && k === 0} onOpen={() => onOpenDoc?.(t.doc, t.quote)} />
            </div>
          ))}
          {!v.told.length && (v.toldFallback ? <p className="dr-plain">{v.toldFallback}</p> : <p className="dr-muted">No checked quote is stored for this commitment.</p>)}
        </section>

        {v.scope && (
          <section className="dr-sec">
            {/* 12 Nov, Round 5: an approval that closed the gap starts later than the commitment. The reason first, then the two clauses with their dates. */}
            <h3 className="dr-label">Why it&rsquo;s open</h3>
            <p className="dr-plain">{v.scope.reason}</p>
            <div className="dr-block dr-related">
              <span className="dr-muted">{v.scope.start.heading}</span>
              {v.scope.start.ref
                ? <Ref text={v.scope.start.ref} doc={v.scope.start.doc} onOpen={() => onOpenDoc?.(v.scope.start.doc, v.scope.start.quote)} />
                : <><blockquote className="dr-quote">{v.scope.start.quote}</blockquote>
                  <Source label={v.scope.start.label} date={v.scope.start.date} doc={v.scope.start.doc} onOpen={() => onOpenDoc?.(v.scope.start.doc, v.scope.start.quote)} /></>}
            </div>
            <div className="dr-block dr-related">
              <span className="dr-muted">{v.scope.approval.heading}</span>
              {v.scope.approval.ref
                ? <Ref text={v.scope.approval.ref} doc={v.scope.approval.doc} onOpen={() => onOpenDoc?.(v.scope.approval.doc, v.scope.approval.quote)} />
                : <><blockquote className="dr-quote">{v.scope.approval.quote}</blockquote>
                  <Source label={v.scope.approval.label} date={v.scope.approval.date} doc={v.scope.approval.doc} onOpen={() => onOpenDoc?.(v.scope.approval.doc, v.scope.approval.quote)} /></>}
            </div>
          </section>
        )}
        {v.reopened ? (
          <>
            {/* 12 Nov, round 4: a gap the signed paperwork reopened shows its cause first (the check's own reason, unchanged), then the evidence: the related clause, under a heading that names where it sits. */}
            <section className="dr-sec">
              <h3 className="dr-label">Why it reopened</h3>
              <p className="dr-plain">{v.whyReopened}</p>
            </section>
            {v.related && (
              <section className="dr-sec">
                <h3 className="dr-label">{relatedHeading(v.related)}</h3>
                <div className="dr-block dr-related">
                  <span className="dr-muted">Related clause</span>
                  {v.related.ref
                    ? <Ref text={v.related.ref} doc={v.related.doc} onOpen={() => onOpenDoc?.(v.related.doc, v.related.quote)} />
                    : <><blockquote className="dr-quote">{v.related.quote}</blockquote>
                      <Source label={v.related.label} date={v.related.date} doc={v.related.doc} onOpen={() => onOpenDoc?.(v.related.doc, v.related.quote)} /></>}
                </div>
              </section>
            )}
          </>
        ) : (
        <section className="dr-sec">
          <h3 className="dr-label">Contract says</h3>
          {v.signed ? (
            <div className="dr-block dr-signed">
              {/* One line carries the status and its source: "(Signed contract, 20 Oct)" is the link to the signed document, so the section no longer prints its source twice. */}
              <span className="dr-confirmed"><ConfirmedStatus signed={v.signed} onOpen={() => onOpenDoc?.(v.signed.doc, v.signed.quote)} />{v.signed.ref ? `: ${v.signed.ref}.` : ""}</span>
              {!v.signed.ref && <blockquote className="dr-quote">{v.signed.quote}</blockquote>}
            </div>
          ) : (
            <>
              {v.contract.text && <p className="dr-plain">{v.contract.text}</p>}
              {v.contract.quote && (
                <div className="dr-block">
                  {v.contract.quote.ref
                    ? <Ref text={`${v.contract.quote.ref}.`} doc={v.contract.quote.doc} onOpen={() => onOpenDoc?.(v.contract.quote.doc, v.contract.quote.quote)} />
                    : <><blockquote className="dr-quote">{v.contract.quote.quote}</blockquote>
                      <Source label={draftSourceLabel(v, v.contract.quote.label)} doc={v.contract.quote.doc} onOpen={() => onOpenDoc?.(v.contract.quote.doc, v.contract.quote.quote)} /></>}
                </div>
              )}
              {v.contract.now && (
                <div className="dr-block">
                  <span className="dr-muted">Wording in {v.contract.now.label}{v.contract.now.date ? ` (${short(v.contract.now.date)})` : ""} that mentions “{v.contract.now.target}”:</span>
                  {v.contract.now.ref
                    ? <Ref text={`${v.contract.now.ref}.`} doc={v.contract.now.doc} onOpen={() => onOpenDoc?.(v.contract.now.doc, v.contract.now.quote)} />
                    : <><blockquote className="dr-quote">{v.contract.now.quote}</blockquote>
                      <Source label={draftSourceLabel(v, v.contract.now.label)} doc={v.contract.now.doc} onOpen={() => onOpenDoc?.(v.contract.now.doc, v.contract.now.quote)} /></>}
                </div>
              )}
            </>
          )}
        </section>
        )}

        <section className="dr-sec">
          <h3 className="dr-label">{v.status === "closed" ? "What closed it" : "What we found"}</h3>
          {v.found.map((f) => (
            <div key={f.label} className="dr-row">
              <strong>{f.label}</strong>
              {f.fact && <span>{f.fact}</span>}
              {f.sub?.map((l) => <span key={l} className="dr-sub">{l}</span>)}
            </div>
          ))}
          {v.searched?.map((l) => <p key={l} className="dr-muted dr-searched">{l}</p>)}
          {v.catalogue.map((p) => (
            <button key={p} type="button" className="cat-open" onClick={() => onCatalogue?.(p)} title={`Open the product catalogue at this entry (${p})`}>
              Catalogue: {catalogueLabel(p, catNames)}
            </button>
          ))}
          {v.closed.length > 0 && (
            <div className="dr-closed">
              {v.status !== "closed" && <span className="dr-label">Already closed by the documents</span>}
              {closedSettled(v, documents).map((l) => <div key={l} className="dr-gap"><p><strong>{l}</strong></p></div>)}
          {v.scopeNotes?.map((l) => <p key={l} className="dr-muted">{l}</p>)}
            </div>
          )}
        </section>

        {v.history?.length > 0 && (
          <details className="dr-history" open={v.status !== "closed"}>
            <summary className="dr-label">History</summary>
            {v.history.map((l) => <p key={l} className="dr-muted">{l}</p>)}
          </details>
        )}

        {v.ai.length > 0 && (
          <section className="dr-sec dr-ai-sec">
            {v.evidence && <p className="dr-evidence"><strong>Evidence</strong> {v.evidence}</p>}
            <details className="dr-ai-details">
              <summary>Initial AI reading</summary>
              <div className="dr-ai">
                <span className="dr-ailabel">AI-written summary · quotes checked against the supplied documents</span>
                {v.ai.map((t) => <p key={t}>{t}</p>)}
              </div>
            </details>
          </section>
        )}
      </div>
      {!readOnly && v.status === "open" && (
        <footer className="dr-foot">
          <p className="dr-seen">
            Seen by: {v.seen.length ? v.seen.map((s) => `${plainName(s.by)} (${short((s.at || "").slice(0, 10))})`).join(" · ") : "nobody yet"}
            {" · "}
            {seenByMe ? <span>Seen by you</span> : <button type="button" className="dr-textlink" onClick={onSeen} title="Records that you have looked at this. It does not close or change anything.">Mark as seen</button>}
          </p>
          {guide?.hint && <p className="dr-guide-hint" role="note">{guide.hint}</p>}
          <div className="dr-actions">
            <button type="button" className={`dp-btn${guide?.highlight === "note" ? " is-guided" : ""}`} onClick={onNote}>Record a note</button>
            <button type="button" className={`dp-btn dp-btn-dark${guide?.highlight === "add" ? " is-guided" : ""}`} onClick={onAddDoc}>Add updated document</button>
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
  // A document of a locked record carries the hash stored at handover. The browser hashes the text it received, byte for byte, and
  // compares. A mismatch is a visible warning; it never hides the text.
  const [check, setCheck] = useState(null);
  useEffect(() => {
    setCheck(null);
    if (!ready || !doc.sha256) return undefined;
    let live = true;
    verifyText(state.text, doc.sha256).then((r) => live && setCheck(r));
    return () => { live = false; };
  }, [ready, state.text, doc.sha256]);
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
        {doc.sha256 && (
          <div className={`dr-hash ${check && !check.ok ? "is-bad" : ""}`} role={check && !check.ok ? "alert" : undefined}>
            <span className="dr-muted">SHA-256 stored at handover</span>
            <code title={doc.sha256}>{shortHash(doc.sha256)}</code>
            {check?.ok && <span className="dr-hash-ok">Matches the text shown</span>}
            {check && !check.ok && (
              <strong className="dr-hash-warn">
                Warning: the text shown does not match the hash stored at handover. Do not rely on it as the text that was read.
              </strong>
            )}
            {!check && ready && <span className="dr-muted">Checking…</span>}
          </div>
        )}
        {quote && rendered && !rendered.found && <p className="dr-muted">The quoted sentence is not in this version of the document.</p>}
        {state.error ? <p className="dp-error">{state.error}</p> : !ready ? <p className="dr-muted">Loading…</p> : (
          <div className="dr-doc">{rendered.blocks.map((b, k) => <Block key={k} b={b} markRef={markRef} />)}</div>
        )}
      </div>
    </>
  );
}

// The findings about the promise, as small outlined tags (27 Oct). Not the status chip: square-cornered, no dot, no fill, so the text carries
// the meaning. Renders nothing when there are none.
export function PromiseBadges({ labels }) {
  if (!labels?.length) return null;
  return (
    <span className="dp-fbadges" role="list" title="About what the customer was promised">
      {labels.map((l) => <span key={l} role="listitem" className="dp-fbadge">{l}</span>)}
    </span>
  );
}

// The coverage lines under "Commitments" (13 Nov): the main line counts findings whose evidence failed verification; a quieter line counts the points the documents already answered.
// part: "main" (the warning, under the heading) or "quiet" (the footnote, the last line of the Commitments section, after the rows); no part: both (13 Nov, Round 7).
export function CoverageLines({ lines, part }) {
  return (
    <>
      {part !== "quiet" && lines.main && <p className="dp-coverage">{lines.main}</p>}
      {part !== "main" && lines.quiet && <p className="dp-coverage is-quiet">{lines.quiet}</p>}
    </>
  );
}

// The commitments card's header (31 Oct), the Deal brief card's pattern: a small eyebrow above the heading, with the status chip beside the heading.
export function CardHead({ eyebrow, title, children }) {
  return (
    <div className="dp-sec-head">
      <span className="dp-eyebrow">{eyebrow}</span>
      <div className="dp-sec-title">
        <h2>{title}</h2>
        {children}
      </div>
    </div>
  );
}

// A title with its promise findings beside it; the badges wrap directly beneath the title when there is no room, and never squeeze it.
// stacked (the landing cards): the badges always sit on their own line beneath the title, so every card has the same layout.
export function TitleLine({ title, labels, className = "dp-prow-title", stacked = false }) {
  return (
    <span className={`dp-titleline${stacked ? " is-stacked" : ""}`}>
      <span className={className}>{title}</span>
      <PromiseBadges labels={labels} />
    </span>
  );
}

// Used by all: the contract line (dark terms, muted connecting words).
export function MismatchSentence({ parts }) {
  if (!parts.length) return null;
  return (
    <span className="dp-prow-line">
      {parts.map((p, n) => (p.strong ? <strong key={n}>{p.text}</strong> : <span key={n}>{p.text}</span>))}
    </span>
  );
}
