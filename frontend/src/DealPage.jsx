// Deal page (16 Oct; simplified 19 Oct). Visibility, not workflow:
// what the customer was told, what the contract says, what the check found, who has seen it, both handover notes.
// The only way a gap closes is a new document version that the check confirms; notes and "seen" never close anything.
import { useCallback, useEffect, useState } from "react";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import * as api from "./api.js";
import { fmtDate, fmtDateTime, uploadKind } from "./format.js";
import {
  CLOSING_ONE_LINE, STATUS_CHIP, cleanReason, contractSide, contractText, toldQuotes, countsLine, extractedAs, findingDetail, firstPromised, groupByStage,
  SIGNED_NOTE, docLabel, isSignedDoc, mismatchLine, missingForHandover, plainName, recordedBy, rowTitle, sentence, sourcesLine, stageLine, suggestFix, useName, whatChanged,
} from "./dealpage.js";
import FrozenRecord from "./FrozenRecord.jsx";
import { NAME, TAGLINE } from "./brand.js";
import CatalogueModal from "./CatalogueModal.jsx";
import "./DealPage.css";

const Icon = ({ d, size = 15 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor"
       strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}>
    <path d={d} />
  </svg>
);
const I = {
  doc: "M14 3H6v18h12V7zM14 3v4h4M9 13h6M9 17h6",
  link: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
  eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
  check: "M5 12l5 5L20 7",
  lock: "M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z",
  plus: "M12 5v14M5 12h14",
  calendar: "M4 6h16v14H4zM4 10h16M9 3v4M15 3v4",
  back: "M19 12H5M11 18l-6-6 6-6",
  close: "M6 6l12 12M18 6L6 18",
  info: "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  arrow: "M5 12h14M13 6l6 6-6 6",
};

const fmtSize = (bytes) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`);

// The info box at the top of a dialog: what will happen, in our existing wording.
function Hint({ children }) {
  const lines = [].concat(children).filter(Boolean);
  if (!lines.length) return null;
  return (
    <div className="dp-hintbox">
      <Icon d={I.info} size={16} />
      <div>{lines.map((l) => <p key={l}>{l}</p>)}</div>
    </div>
  );
}

function readUpload(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    const binary = uploadKind(file.name) === "binary";
    reader.onload = () => resolve(binary ? { file_base64: String(reader.result).split(",", 2)[1] ?? "" } : { text: String(reader.result) });
    reader.onerror = () => reject(new Error("The file could not be read."));
    if (binary) reader.readAsDataURL(file);
    else reader.readAsText(file);
  });
}

// One row per commitment in a single list: collapsed it tells the story (title, what does not line up, where it was first
// promised, status); open shows the three columns. Only updated documents close a commitment; notes and "seen" never do.
function PromiseRow({ c, status, onSeen, onCatalogue, onAct, me = "", expanded = false, onToggle }) {
  const unresolved = c.issues.filter((i) => i.state !== "Resolved");
  const closedIssues = c.issues.filter((i) => i.state === "Resolved");
  const shown = status === "closed" ? closedIssues : unresolved;
  const seen = [...new Map(unresolved.flatMap((i) => i.seen || []).map((s) => [s.by, s])).values()];
  const told = toldQuotes(c.statements);
  const theirs = contractSide(c.issues, c.contract);
  const st = STATUS_CHIP[status];
  const noteRes = unresolved.find((i) => i.note_resolution)?.note_resolution;
  const mismatch = status === "closed" ? "" : mismatchLine(unresolved, c.contract);
  const first = firstPromised(c.statements);
  return (
    <li className={`dp-prow is-${status} ${expanded ? "is-open" : ""}`}>
      <div className="dp-prow-head" onClick={onToggle} role="button" tabIndex={0} aria-expanded={expanded}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onToggle())}>
        <span className={`dp-chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">›</span>
        <span className="dp-prow-main">
          <span className="dp-prow-title">{rowTitle(c)}</span>
          {mismatch && <span className="dp-prow-line">{mismatch}</span>}
          {first && <span className="dp-prow-first">{first}</span>}
          {status === "noted" && noteRes && <span className="dp-prow-note">{recordedBy(noteRes.by, noteRes.at, fmtDate)}</span>}
        </span>
        <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
          {status === "open" ? <span className="dp-dot" /> : status === "closed" ? <Icon d={I.check} size={12} /> : <span className="dp-dot dp-dot-grey" />}
          {st.label}
        </span>
      </div>
      {expanded && (
        <div className="dp-prow-body">
          <div className="dp-three">
            <div className="dp-fact">
              <span className="dp-fact-label">Customer was told</span>
              {told.length ? told.map((t) => <blockquote key={t.quote} className="dp-quote">“{t.quote}”</blockquote>) : <p>{c.told}</p>}
              <span className="dp-fact-src">{sourcesLine(c.statements)}</span>
            </div>
            <div className="dp-fact dp-fact-contract">
              <span className="dp-fact-label">Contract says</span>
              <p>{contractText(c.contract)}</p>
              {theirs.quote && <blockquote className="dp-quote">“{theirs.quote}”</blockquote>}
              {theirs.quote && theirs.source && <span className="dp-fact-src">{theirs.source}</span>}
              {theirs.missing && <span className="dp-fact-src">Searched for: {theirs.missing.map((m) => `“${m}”`).join(", ")}</span>}
            </div>
            <div className="dp-fact dp-fact-found">
              <span className="dp-fact-label">{status === "closed" ? "What was found, and what closed it" : "What we found"}</span>
              {shown.map((i) => (
                <p key={i.id} className="dp-finding">
                  <strong>{status === "closed" ? `${i.finding}.` : sentence(findingDetail(i, c.contract))}</strong>{" "}
                  {status === "closed" ? (i.resolved_by?.text || "Closed in the documents") : cleanReason(i.reason)}
                </p>
              ))}
              {[...new Set(shown.map((i) => i.catalogue_path).filter(Boolean))].map((p) => (
                <button key={p} type="button" className="cat-open" onClick={() => onCatalogue(p)} title="Open the product catalogue at this entry">
                  Catalogue: {p.split("/").slice(0, 2).join(" · ")}{p.split("/").length > 2 ? ` · ${p.split("/").slice(2).join(" ").replace(/_/g, " ")}` : ""}
                </button>
              ))}
              {status !== "closed" && (
                <span className="dp-fact-src" title="The sentence is written by the AI model and is not checked. The quotes, catalogue entry and missing words behind it were checked by code against the documents before this was shown.">AI-written summary · the quotes behind it are checked against the documents</span>
              )}
            </div>
          </div>
          {extractedAs(c) && <span className="dp-extracted"><b>Extracted as</b> {c.name}</span>}
          {status !== "closed" && closedIssues.length > 0 && (
            <div className="dp-decision is-done">
              <span className="dp-kicker">Already closed by the documents</span>
              {closedIssues.map((i) => <span key={i.id}><strong>{i.finding}.</strong> {i.resolved_by?.text || ""}</span>)}
            </div>
          )}
          {status === "noted" && noteRes && (
            <div className="dp-decision is-done is-note">
              <span className="dp-kicker">Addressed by note · not in the documents · reopens if the documents change</span>
              <span>“{noteRes.reason}”</span>
              <span className="dp-faint dp-small">{recordedBy(noteRes.by, noteRes.at, fmtDate)}</span>
            </div>
          )}
          {status === "open" && noteRes && !noteRes.current && (
            <div className="dp-decision is-stale">
              <span className="dp-kicker">Was addressed by a note · reopened because the documents changed since</span>
              <span>“{noteRes.reason}”</span>
              <span className="dp-faint dp-small">{recordedBy(noteRes.by, noteRes.at, fmtDate)} · use Add updated document or Record a note to re-confirm</span>
            </div>
          )}
          {status === "open" && [...new Map(unresolved.filter((i) => i.decision && i.decision.status !== "none")
            .map((i) => [`${i.decision.by}|${i.decision.reason}`, i.decision])).values()].map((d) => (
            <div key={`${d.by}|${d.reason}`} className={`dp-decision ${d.status === "reconfirm" ? "is-stale" : ""}`}>
              <span className="dp-kicker">{d.status === "reconfirm" ? "Note needs re-confirming: the documents changed since" : "Note · still needs attention"}</span>
              <span>“{d.reason}”</span>
              <span className="dp-faint dp-small">{recordedBy(d.by, d.at, fmtDate)}</span>
            </div>
          ))}
          {status === "open" && (
            <footer className="dp-gap-foot">
              <span>
                <span className="dp-faint">Seen by:</span>{" "}
                {seen.length ? seen.map((s) => `${plainName(s.by)} (${fmtDate(s.at).replace(/ \d{4}$/, "")})`).join(" · ") : <span className="dp-faint">nobody yet</span>}
                {" "}
                {seen.some((x) => x.by === me.trim()) ? (
                  <span className="dp-seen-me"><Icon d={I.check} size={13} /> Seen by you</span>
                ) : (
                  <button type="button" className="dp-link-btn dp-quiet" onClick={() => onSeen(unresolved)}
                          title="Records that you have looked at this. It does not close or change anything.">Mark as seen</button>
                )}
              </span>
              <span className="dp-row">
                <button type="button" className="dp-btn" onClick={() => onAct(c, "note")}>Record a note</button>
                <button type="button" className="dp-btn dp-btn-dark" onClick={() => onAct(c, "doc")}>Add updated document</button>
              </span>
            </footer>
          )}
        </div>
      )}
    </li>
  );
}

// Asks for a name only when one is needed and none is stored (19 Oct: no name box, no gate). Used inside forms.
function NameField({ stored, draft, onDraft }) {
  if (stored.trim()) return null;
  return (
    <label className="dp-name-field">
      <span>Your name</span>
      <input value={draft} onChange={(e) => onDraft(e.target.value)} placeholder="e.g. Sam (Delivery)" maxLength={120} required />
    </label>
  );
}

function NotePanel({ role, label, who, note, name, setName, onSave }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [draft, setDraft] = useState("");
  const [error, setError] = useState(null);
  const author = (name || draft).trim();
  const save = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await onSave(role, text, author);
      if (!name.trim()) setName(author);
      setEditing(false);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div className="dp-note">
      <div className="dp-note-head">
        <div className="dp-note-id">
          <span className="dp-avatar" aria-hidden="true">{who[0]}</span>
          <div>
            <span className="dp-note-who">{note ? plainName(note.by) : who}</span>
            <span className="dp-note-role">{label}</span>
          </div>
        </div>
        <span className={`dp-chip ${note ? "dp-chip-green" : "dp-chip-grey"}`}>{note ? "Note added" : "No note yet"}</span>
      </div>
      {editing ? (
        <form onSubmit={save} className="dp-note-form">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000} autoFocus
                    placeholder={role === "sales" ? "What Delivery should know: commitments needing attention, side promises, people to talk to" : "What you accept, what you need before kick-off"} />
          <NameField stored={name} draft={draft} onDraft={setDraft} />
          <div className="dp-row">
            <button type="submit" className="dp-btn dp-btn-dark" disabled={!text.trim() || !author}>Save note</button>
            <button type="button" className="dp-btn" onClick={() => setEditing(false)}>Cancel</button>
            {error && <span className="dp-error">{error}</span>}
          </div>
        </form>
      ) : note ? (
        <p className="dp-note-text">{`“${note.note}”`}</p>
      ) : null}
      {!editing && !note ? (
        <div className="dp-note-empty">
          <span>Not written yet.</span>
          <button type="button" className="dp-link-btn dp-brand" onClick={() => { setText(""); setEditing(true); }}>Add note</button>
        </div>
      ) : (
        <div className="dp-note-foot">
          <span>{note ? recordedBy(note.by, note.at, fmtDateTime) : ""}</span>
          {!editing && (
            <button type="button" className="dp-link-btn dp-brand" onClick={() => { setText(note?.note ?? ""); setEditing(true); }}>Update note</button>
          )}
        </div>
      )}
    </div>
  );
}

function ChangePanel({ change, onClose }) {
  const { closed, opened, stillOpen, openPromises } = change;
  const nothing = !closed.length && !opened.length;
  return (
    <section className="dp-card dp-change" role="status" aria-live="polite">
      <div className="dp-change-head">
        <div>
          <span className="dp-kicker">What changed</span>
          <h2>After adding {change.doc}</h2>
          <span className="dp-faint dp-small">
            {change.modelCalls ? "The model read the new document; code checked every finding again." : "No model call was needed: code checked every finding again."}
          </span>
        </div>
        <button type="button" className="dp-btn" onClick={onClose}>Done</button>
      </div>
      {closed.length > 0 && (
        <div className="dp-change-block is-closed">
          <span className="dp-change-label">Closed ({closed.length})</span>
          {closed.map((x) => (
            <div key={`${x.promise}|${x.finding}`} className="dp-change-item">
              <strong>{x.promise}: {x.finding}</strong>
              <span>{x.why}</span>
              {x.by && <span className="dp-faint dp-small">{x.by}</span>}
            </div>
          ))}
        </div>
      )}
      {stillOpen.length > 0 && (
        <div className="dp-change-block is-open">
          <span className="dp-change-label">Still needs attention on the same commitment</span>
          {stillOpen.map((x) => <div key={`${x.promise}|${x.finding}`} className="dp-change-item"><strong>{x.promise}: {x.finding}</strong></div>)}
        </div>
      )}
      {opened.length > 0 && (
        <div className="dp-change-block is-new">
          <span className="dp-change-label">New gap{opened.length === 1 ? "" : "s"} found ({opened.length})</span>
          {opened.map((x) => <div key={`${x.promise}|${x.finding}`} className="dp-change-item"><strong>{x.promise}: {x.finding}</strong></div>)}
        </div>
      )}
      <p className="dp-small dp-change-foot">
        {nothing ? "Nothing closed and nothing new: the document did not change any gap. " : "Nothing else changed. "}
        {openPromises} {openPromises === 1 ? "commitment still needs" : "commitments still need"} attention.
      </p>
    </section>
  );
}

function Modal({ title, sub, dot, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="dp-modal" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="dp-modal-body dp-pop" onClick={(e) => e.stopPropagation()}>
        <div className="dp-modal-head">
          <div className="dp-modal-title">{dot && <span className={`dp-title-dot is-${dot}`} aria-hidden="true" />}<div><strong>{title}</strong>{sub && <span className="dp-faint dp-small dp-block">{sub}</span>}</div></div>
          <button type="button" className="dp-x" onClick={onClose} aria-label="Close dialog"><Icon d={I.close} size={16} /></button>
        </div>
        <div className="dp-pop-body">{children}</div>
      </div>
    </div>
  );
}

function ActionModal({ deal, c, mode, documents, docTypes, name, setName, canDecide, freshnessLabel, message, checking, onCheckAgain, onDocDone, onNoted, onClose }) {
  const open = c.issues.filter((i) => i.state !== "Resolved");
  const [how, setHow] = useState("keep"); // keep: stays Needs attention, note shown in the row; addressed: settled without a document
  const [note, setNote] = useState("");
  const [draft, setDraft] = useState("");
  const [changing, setChanging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const author = (!name.trim() || changing ? draft : name).trim();
  const saveNote = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (how === "addressed") await api.resolveByNote(deal, { issue_ids: open.map((i) => i.id), resolved_by: author, reason: note });
      else for (const i of open) await api.recordDecision(deal, { kind: "okay_to_proceed", issue_id: i.id, by: author, reason: note });
      if (author !== name.trim()) setName(author);
      onNoted();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  const blocked = how === "keep" && !canDecide;
  return (
    <Modal title={mode === "doc" ? "Add updated document" : "Record a note"} dot={mode === "doc" ? "green" : "amber"} onClose={onClose}>
      <div className="dp-commit">
        <span className="dp-commit-dot" aria-hidden="true" />
        <div>
          <p className="dp-commit-title"><b>Commitment:</b> “{rowTitle(c)}”</p>
          <span className="dp-commit-sub">Needs attention: {mismatchLine(open, c.contract)}</span>
        </div>
      </div>
      {mode === "doc" ? (
        <AddDocument deal={deal} documents={documents} docTypes={docTypes} preset={suggestFix(open, documents)} lead={CLOSING_ONE_LINE} onDone={onDocDone} onClose={onClose} />
      ) : (
        <form className="dp-add" onSubmit={saveNote}>
          <Hint>{CLOSING_ONE_LINE}</Hint>
          <div className="dp-field"><span>What should happen to it?</span></div>
          <div className="dp-choice" role="radiogroup" aria-label="What to do with the note">
            <label className={how === "keep" ? "is-on" : ""}>
              <input type="radio" name="how" checked={how === "keep"} onChange={() => setHow("keep")} />
              <span><strong>Keep it open, add context.</strong> <em className="dp-default">Default</em><br />It stays under Needs attention with your note shown inside the row,
                for example "Delivery will raise it at kick-off".</span>
            </label>
            <label className={how === "addressed" ? "is-on" : ""}>
              <input type="radio" name="how" checked={how === "addressed"} onChange={() => setHow("addressed")} />
              <span><strong>Mark as addressed by note.</strong><br />The documents still differ. It moves to "Addressed by note", stays in
                the handover record, and reopens if the documents change.</span>
            </label>
          </div>
          <label className="dp-field">
            <span>Note</span>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} maxLength={2000} autoFocus
                      placeholder="What was agreed, and who will act on it" />
          </label>
          <div className="dp-author">
            {!name.trim() || changing ? (
              <label className="dp-name-field">
                <span>Your name</span>
                <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="e.g. Sam (Delivery)" maxLength={120} required />
              </label>
            ) : (
              <span>Recording as <strong>{plainName(name)}</strong> · <button type="button" className="dp-link-btn dp-brand" onClick={() => { setDraft(name); setChanging(true); }}>change</button></span>
            )}
          </div>
          {blocked && (
            <div className="dp-warn" role="alert">
              <span>A note can be kept on a gap only while the check is current ({freshnessLabel}). Check the deal again first.</span>
              <span className="dp-row">
                <button type="button" className="dp-btn" disabled={checking} onClick={onCheckAgain}>{checking ? "Checking…" : "Check again"}</button>
                {message?.kind === "error" && <span className="dp-error">{message.text}</span>}
              </span>
            </div>
          )}
          <div className="dp-actions">
            {error && <span className="dp-error" role="alert">{error}</span>}
            <button type="button" className="dp-btn dp-btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !note.trim() || !author || blocked}>{busy ? "Saving…" : <>Save note <Icon d={I.check} size={14} /></>}</button>
          </div>
        </form>
      )}
    </Modal>
  );
}

function NamePrompt({ initial, onSave, onClose }) {
  const [value, setValue] = useState(initial);
  return (
    <Modal title="Your name" sub="Recorded with what you add. Remembered in this browser only." onClose={onClose}>
      <form className="dp-add" onSubmit={(e) => { e.preventDefault(); onSave(value.trim()); }}>
        <input value={value} onChange={(e) => setValue(e.target.value)} placeholder="e.g. Sam (Delivery)" maxLength={120} autoFocus />
        <div className="dp-row">
          <button type="submit" className="dp-btn dp-btn-dark" disabled={!value.trim()}>Continue</button>
          <button type="button" className="dp-btn" onClick={onClose}>Cancel</button>
        </div>
      </form>
    </Modal>
  );
}

function ClosingHelp({ onClose }) {
  return (
    <Modal title="How closing works" onClose={onClose}>
      <ol className="dp-how-list">
        <li>Someone adds a document: a new version of one already here, or a new one.</li>
        <li>The check runs again on all the deal's documents.</li>
        <li>A commitment closes only when the paperwork now backs it, in one of three ways: the contract or SOW now says it, a named approval is recorded, or the promise itself is changed or withdrawn. The reason is shown.</li>
      </ol>
      <p className="dp-faint dp-small">Without a document, a named person can record a note. Marked as addressed, it is listed apart as "Addressed by note", marked not in the documents, and reopens if the documents change.</p>
      <p className="dp-faint dp-small">A new document can also uncover a new gap. Removing a document never closes one. "Mark as seen" and notes kept open never close anything.</p>
    </Modal>
  );
}

function AddDocument({ deal, documents, docTypes, onDone, onClose, preset, lead }) {
  const [form, setForm] = useState({ source_key: preset?.source_key ?? "", doc_type: preset?.doc_type ?? "draft_sow",
                                     doc_date: new Date().toISOString().slice(0, 10), file: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: k === "file" ? e.target.files[0] ?? null : e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (!uploadKind(form.file.name)) throw new Error("Upload Markdown, text, PDF, Word, Excel or PowerPoint.");
      const content = await readUpload(form.file);
      const body = form.source_key
        ? { source_key: form.source_key, filename: form.file.name, ...content }
        : { name: form.file.name, filename: form.file.name, doc_type: form.doc_type, doc_date: form.doc_date, ...content };
      await api.addDocument(deal, body);
      const r = await api.reviewDeal(deal);
      const existing = documents.find((d) => d.source_key === form.source_key);
      onDone(r.review, existing ? `${existing.name}, new version` : form.file.name);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="dp-add" onSubmit={submit}>
      <Hint>{[lead, preset?.hint]}</Hint>
      <p className="dp-faint dp-small dp-note-line">The check runs again on all the deal's documents. A gap closes only if the new paperwork shows it no longer holds.</p>
      <div className="dp-add-grid">
        <label>
          This is
          <select value={form.source_key} onChange={set("source_key")}>
            <option value="">A new document</option>
            {documents.map((d) => <option key={d.source_key} value={d.source_key}>A new version of: {d.name} (v{d.version} → v{d.version + 1})</option>)}
          </select>
        </label>
        {!form.source_key && (
          <>
            <label>
              Type
              <select value={form.doc_type} onChange={set("doc_type")}>
                {docTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </label>
            <label>
              Dated
              <input type="date" value={form.doc_date} onChange={set("doc_date")} />
            </label>
          </>
        )}
      </div>
      <div className="dp-field">
        <span>Document upload</span>
        <label className={`dp-drop ${over ? "is-over" : ""}`}
               onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
               onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) setForm((x) => ({ ...x, file: f })); }}>
          <span className="dp-drop-icon"><Icon d={I.upload} size={22} /></span>
          <span className="dp-drop-main">Drop file here or <u>browse files</u></span>
          <span className="dp-drop-sub">Markdown, text, PDF, Word, Excel or PowerPoint</span>
          <input type="file" accept=".md,.txt,.pdf,.docx,.xlsx,.pptx" onChange={set("file")} />
        </label>
        {form.file && (
          <div className="dp-file-chip">
            <Icon d={I.doc} size={16} />
            <span className="dp-file-name">{form.file.name}</span>
            <span className="dp-file-size">{fmtSize(form.file.size)}</span>
            <button type="button" className="dp-x" aria-label="Remove attached file" onClick={() => setForm((x) => ({ ...x, file: null }))}><Icon d={I.close} size={14} /></button>
          </div>
        )}
      </div>
      {!form.source_key && isSignedDoc(form.doc_type) && <p className="dp-faint dp-small">{SIGNED_NOTE}</p>}
      <div className="dp-actions">
        {error && <span className="dp-error" role="alert">{error}</span>}
        <button type="button" className="dp-btn dp-btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
        <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !form.file}>{busy ? "Checking…" : <>Add and check <Icon d={I.arrow} size={14} /></>}</button>
      </div>
    </form>
  );
}

function DocumentList({ deal, stages, documents, name, setName, onChanged, onView, onAdd }) {
  const [draft, setDraft] = useState("");
  const [linking, setLinking] = useState(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState(null);
  const saveLink = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.setDocumentLink(deal, { source_key: linking, url, set_by: (name || draft).trim() });
      if (!name.trim()) setName(draft.trim());
      setLinking(null);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  const doc = (d) => (
    <li key={d.source_key} className={d.doc_type.startsWith("draft_") ? "is-contract" : ""}>
      <div className="dp-doc-row">
        {d.link ? (
          <a href={d.link} target="_blank" rel="noopener noreferrer" className="dp-doc-name" title="Opens where the document lives">
            {docLabel(d.name, d.date)}{d.version > 1 ? ` · v${d.version}` : ""}
          </a>
        ) : (
          <button type="button" className="dp-doc-name" onClick={() => onView(d)} title="Read the text the check used">
            {docLabel(d.name, d.date)}{d.version > 1 ? ` · v${d.version}` : ""}
          </button>
        )}
        <span className="dp-doc-meta">
          <span className="dp-mono">{fmtDate(d.date).replace(/ \d{4}$/, "")}</span>
          <button type="button" className={`dp-icon-btn ${d.link ? "is-set" : ""}`}
                  onClick={() => { setLinking(linking === d.source_key ? null : d.source_key); setUrl(d.link ?? ""); }}
                  title={d.link ? "Change the Drive link" : "Save a Drive link"} aria-label={d.link ? "Change the Drive link" : "Save a Drive link"}>
            <Icon d={I.link} size={13} />
          </button>
        </span>
      </div>
      {isSignedDoc(d.doc_type) && <span className="dp-signed-note">{SIGNED_NOTE}</span>}
      {linking === d.source_key && (
        <form className="dp-link-form" onSubmit={saveLink}>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://drive.google.com/…" autoFocus />
          <NameField stored={name} draft={draft} onDraft={setDraft} />
          <button type="submit" className="dp-btn dp-btn-dark" disabled={!url.trim() || !(name || draft).trim()}>Save</button>
          <button type="button" className="dp-btn" onClick={() => setLinking(null)}>Cancel</button>
          {error && <span className="dp-error">{error}</span>}
        </form>
      )}
    </li>
  );
  return (
    <div className="dp-card dp-side">
      <div className="dp-side-head">
        <span className="dp-side-title"><Icon d={I.doc} /> Documents checked <span className="dp-count">{documents.length}</span></span>
        <button type="button" className="dp-btn dp-btn-small" onClick={onAdd} title="Add a document or a new version">
          <Icon d={I.plus} size={13} /> Add
        </button>
      </div>
      <ol className="dp-timeline">
        {groupByStage(stages, documents).map((s) => (
          <li key={s.key} className={`dp-tl is-${s.state} ${s.gaps_started > 0 ? "has-gaps" : ""}`}>
            <span className="dp-tl-dot" aria-hidden="true" />
            <div className="dp-tl-body">
              <span className="dp-tl-name">
                {s.label}
                <span className="dp-tl-right">
                  {s.gaps_started > 0 && <span className="dp-stage-gaps">{s.gaps_started} {s.gaps_started === 1 ? "gap" : "gaps"} started here</span>}
                  {s.state === "current" && <span className="dp-tl-tag">Current stage</span>}
                  {s.state === "todo" && <span className="dp-tl-tag">Not yet</span>}
                </span>
              </span>
              {s.key === "contracting" && s.note && <span className="dp-tl-note">{s.note}</span>}
              {s.docs.length > 0 && <ul className="dp-docs">{s.docs.map(doc)}</ul>}
              {s.docs.length === 0 && s.state === "done" && <span className="dp-tl-empty">No documents</span>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function DocViewer({ deal, doc, onClose }) {
  const [state, setState] = useState({ loading: true });
  useEffect(() => {
    api.fetchDocumentText(deal, doc.source_version_id).then((r) => setState(r), (err) => setState({ error: err.message }));
  }, [deal, doc]);
  return (
    <div className="dp-modal" role="dialog" aria-modal="true" aria-label={doc.name} onClick={onClose}>
      <div className="dp-modal-body" onClick={(e) => e.stopPropagation()}>
        <div className="dp-modal-head">
          <strong>{state.name ?? doc.name}</strong>
          <button type="button" className="dp-btn" onClick={onClose}>Close</button>
        </div>
        {state.error ? <p className="dp-error">{state.error}</p> : <pre className="dp-doc-text">{state.loading ? "Loading…" : state.text}</pre>}
      </div>
    </div>
  );
}

// The pre-revamp detailed view stays in the code but off the demo path: its link shows only with ?detailed in the URL.
const SHOW_DETAILED = typeof window !== "undefined" && new URLSearchParams(window.location.search).has("detailed");

export default function DealPage({ deal, onBack, onDealsChanged, onClassic }) {
  const [reg, setReg] = useState(null);
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [name, setName] = useName();
  const [completing, setCompleting] = useState(false);
  const [completeDraft, setCompleteDraft] = useState("");
  const [catFocus, setCatFocus] = useState(null); // null = closed, "" = open unfocused, "CAP-…/AU" = open at an entry
  const [checking, setChecking] = useState(false);
  const [change, setChange] = useState(null); // the "What changed" panel after a document or a recheck
  const [acting, setActing] = useState(null); // { c, mode }: the commitment whose "Add updated document" / "Record a note" dialog is open
  const [askName, setAskName] = useState(null); // { fn, initial }: the name prompt, only for actions that have no form of their own
  const [help, setHelp] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set()); // rows shown in full; collapsed by default
  const toggleCard = (id) => setExpanded((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });

  const load = useCallback(() => {
    Promise.all([api.fetchRegister(deal), api.fetchDocuments(deal)]).then(
      ([r, d]) => { setReg(r); setDocs(d); setError(null); },
      (err) => setError(err.message),
    );
  }, [deal]);
  useEffect(load, [load]);

  const act = async (fn) => {
    setMessage(null);
    try {
      await fn();
      load();
      onDealsChanged?.();
    } catch (err) {
      setMessage({ kind: "error", text: err.message });
    }
  };
  // Runs fn with the stored name, asking for one first if there is none. Nothing is disabled for want of a name.
  const withName = (fn) => (name.trim() ? fn(name.trim()) : setAskName({ fn, initial: "" }));

  const checkAgain = () => {
    setChecking(true);
    return act(async () => {
      const r = await api.reviewDeal(deal);
      setMessage({ kind: "ok", text: `Checked again${r.review?.model_calls ? "" : " with no model call"}. Findings are current.` });
    }).finally(() => setChecking(false));
  };

  const docDone = async (review, doc) => {
    setAdding(false);
    setActing(null);
    setMessage(null);
    const after = await api.fetchRegister(deal);
    setChange({ ...whatChanged(reg, after), doc, modelCalls: review.model_calls });
    load();
    onDealsChanged?.();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (error) return <div className="dp"><p className="dp-error">{error}</p></div>;
  if (!reg || !docs) return <div className="dp"><p className="dp-faint">Loading…</p></div>;

  // Once the handover is complete the page shows the frozen record, read from the saved snapshot.
  if (reg.handover.complete) return <FrozenRecord deal={deal} onBack={onBack} />;
  const byId = (id) => reg.commitments.find((c) => c.id === id);
  const openRows = reg.open_rows.map(byId);
  // One list: those needing attention first (most gaps first), then those addressed by note, then closed by the documents.
  const closedIds = [...new Set(reg.resolved_findings.map((r) => r.commitment_id))]
    .filter((id) => !reg.open_rows.includes(id) && !(reg.noted_rows || []).includes(id));
  const promiseRows = [
    ...openRows.map((c) => ({ c, status: "open" })),
    ...(reg.noted_rows || []).map((id) => ({ c: byId(id), status: "noted" })),
    ...closedIds.map((id) => ({ c: byId(id), status: "closed" })),
  ].filter((r) => r.c);
  const notes = reg.handover.notes;
  const STAGE_ORDER = ["discovery", "evaluation", "proposal", "shortlisted", "contracting", "signed", "handover"];
  const isSigned = STAGE_ORDER.indexOf(reg.stage.current) >= STAGE_ORDER.indexOf("signed"); // from the documents only
  const included = docs.documents.filter((d) => d.included);
  const missing = missingForHandover({ isSigned, notes });
  const completer = (name || completeDraft).trim();

  return (
    <div className="dp">
      <div className="dp-topbar">
        <button type="button" className="dp-back" onClick={onBack}><Icon d={I.back} /> All deals</button>
        <span className="dp-wordmark" title={TAGLINE}>{NAME}</span>
        {name.trim() && (
          <span className="dp-me">
            Recording as <strong>{name.trim()}</strong> ·{" "}
            <button type="button" className="dp-link-btn dp-brand" onClick={() => setAskName({ fn: null, initial: name })}>change</button>
          </span>
        )}
      </div>

      <div className="dp-grid">
        <div className="dp-main">
          <section className="dp-card dp-head">
            <div className="dp-head-row">
              <div>
                <div className="dp-title-row">
                  <h1>{reg.name}</h1>
                  <span className="dp-stage-pill">Stage: {reg.stage.current_label}</span>
                  <button type="button" className="dp-btn dp-catalogue-btn" onClick={() => setCatFocus("")}>Product catalogue</button>
                </div>
                <div className="dp-meta">
                  {reg.brief?.go_live && <span className="dp-meta-strong"><Icon d={I.calendar} /> Target go-live: {fmtDate(reg.brief.go_live)}</span>}
                  <span className="dp-mono">Checked {fmtDate(reg.freshness.finished_at)} against {included.length} {included.length === 1 ? "document" : "documents"}</span>
                  {reg.freshness.state === "Review out of date" && <span className="dp-chip dp-chip-amber"><span className="dp-dot" />Review out of date</span>}
                  {reg.freshness.state === "Review out of date" && (
                    <button type="button" className="dp-link-btn dp-brand" disabled={checking} onClick={checkAgain}>
                      {checking ? "Checking…" : "Check again"}
                    </button>
                  )}
                  {stageLine(reg.stage) && <span className="dp-stageline">{stageLine(reg.stage)}</span>}
                </div>
              </div>
            </div>
            {reg.brief && (
              <div className="dp-delivering">
                <div className="dp-sec-head">
                  <h2 className="dp-upper">What we're delivering</h2>
                  <span className="dp-faint">Confirmed by <strong className="dp-ink">{plainName(reg.brief.confirmed_by)}</strong>{reg.brief.basis ? ` from ${reg.brief.basis}` : ""}</span>
                </div>
                <p className="dp-brief">{reg.brief.summary}</p>
                {reg.brief.deliverables.length > 0 && (
                  <div className="dp-deliverables">
                    {reg.brief.deliverables.map((d) => <span key={d}><span className="dp-dot dp-brand-bg" />{d}</span>)}
                  </div>
                )}
                {reg.brief.needs_reconfirmation && <div className="dp-warn">{reg.brief.reconfirm_note}</div>}
              </div>
            )}
          </section>

          {message && <div className={`dp-message is-${message.kind}`} role="status">{message.text}</div>}
          {change && <ChangePanel change={change} onClose={() => setChange(null)} />}

          <section className="dp-card dp-promises">
            <div className="dp-sec-head">
              <div className="dp-row">
                <h2>Commitments needing attention</h2>
                {promiseRows.length > 0 && (
                  <button type="button" className="dp-link-btn dp-brand"
                          onClick={() => setExpanded(expanded.size === promiseRows.length ? new Set() : new Set(promiseRows.map((r) => r.c.id)))}>
                    {expanded.size === promiseRows.length ? "Collapse all" : "Expand all"}
                  </button>
                )}
              </div>
              <span className="dp-counts">{countsLine({ open: openRows.length, noted: (reg.noted_rows || []).length, closed: closedIds.length })}</span>
            </div>
            {promiseRows.length === 0 && <p className="dp-faint">No commitments with gaps on the current documents.</p>}
            <ul className="dp-plist">
              {promiseRows.map(({ c, status }) => (
                <PromiseRow key={c.id} c={c} status={status} onCatalogue={setCatFocus} me={name}
                            onAct={(row, mode) => setActing({ c: row, mode })}
                            expanded={expanded.has(c.id)} onToggle={() => toggleCard(c.id)}
                            onSeen={(issues) => withName((who) => act(async () => { for (const i of issues) await api.markSeen(deal, { issue_id: i.id, seen_by: who }); }))} />
              ))}
            </ul>
          </section>

          <section className="dp-card">
            <div className="dp-sec-head">
              <h2>Handover</h2>
              <span className={`dp-chip ${notes.sales && notes.delivery ? "dp-chip-green" : "dp-chip-amber"}`}>
                {notes.sales && notes.delivery ? "Both notes in" : "Waiting for notes"}
              </span>
            </div>
            <div className="dp-notes">
              <NotePanel role="sales" label="Deal owner's handoff note" who="Sales" note={notes.sales} name={name} setName={setName}
                         onSave={(role, text, by) => api.saveHandoverNote(deal, { role, note: text, entered_by: by }).then(() => { load(); onDealsChanged?.(); })} />
              <NotePanel role="delivery" label="Delivery acceptance note" who="Delivery" note={notes.delivery} name={name} setName={setName}
                         onSave={(role, text, by) => api.saveHandoverNote(deal, { role, note: text, entered_by: by }).then(() => { load(); onDealsChanged?.(); })} />
            </div>
            <div className="dp-complete">
              <span className="dp-faint"><Icon d={I.lock} size={14} /> Completing the handover freezes this record. Commitments needing attention stay visible as they stood.</span>
              {completing ? (
                <span className="dp-row">
                  <span className="dp-small">Complete as</span>
                  {name.trim() ? <strong>{name.trim()}</strong>
                    : <input className="dp-inline-name" value={completeDraft} onChange={(e) => setCompleteDraft(e.target.value)} placeholder="Your name" maxLength={120} autoFocus />}
                  <span className="dp-small">?</span>
                  <button type="button" className="dp-btn dp-btn-dark" disabled={!completer}
                          onClick={() => { if (!name.trim()) setName(completer); act(() => api.completeHandover(deal, { completed_by: completer })).then(() => setCompleting(false)); }}>Yes, complete</button>
                  <button type="button" className="dp-btn" onClick={() => setCompleting(false)}>Cancel</button>
                </span>
              ) : (
                <button type="button" className="dp-btn dp-btn-dark" disabled={missing.length > 0} onClick={() => setCompleting(true)}>
                  <Icon d={I.check} /> Complete handover
                </button>
              )}
            </div>
            {missing.length > 0 && (
              <p className="dp-faint dp-small dp-hint">To complete the handover: {missing.join(" · ")}.</p>
            )}
          </section>

          <footer className="dp-foot">
            <strong>{NAME}</strong> · {TAGLINE}<br />
            Lists commitments where the customer's expectation, the contract and what we can sell don't line up. Checked against the documents listed and the product catalogue. All companies, people and deals are fictional.
            {onClassic && SHOW_DETAILED && <> · <button type="button" className="dp-link-btn" onClick={onClassic}>Open the detailed view</button></>}
          </footer>
        </div>

        <aside className="dp-aside">
          <DocumentList deal={deal} stages={reg.stage.stages} documents={included} name={name} setName={setName} onChanged={load} onView={setViewing}
                        onAdd={() => setAdding(true)} />
          <button type="button" className="dp-link-btn dp-brand dp-help-link" onClick={() => setHelp(true)}>How closing works</button>
        </aside>
      </div>

      {viewing && <DocViewer deal={deal} doc={viewing} onClose={() => setViewing(null)} />}
      {catFocus !== null && <CatalogueModal focus={catFocus} onClose={() => setCatFocus(null)} onChanged={load} />}
      {help && <ClosingHelp onClose={() => setHelp(false)} />}
      {askName && (
        <NamePrompt initial={askName.initial} onClose={() => setAskName(null)}
                    onSave={(who) => { const run = askName.fn; setName(who); setAskName(null); run?.(who); }} />
      )}
      {adding && (
        <Modal title="Add a document" sub="A new document, or a new version of one already in the deal" dot="green" onClose={() => setAdding(false)}>
          <AddDocument deal={deal} documents={docs.documents} docTypes={docs.doc_types} lead={CLOSING_ONE_LINE} onClose={() => setAdding(false)} onDone={docDone} />
        </Modal>
      )}
      {acting && (
        <ActionModal deal={deal} c={acting.c} mode={acting.mode} documents={docs.documents} docTypes={docs.doc_types}
                     name={name} setName={setName} canDecide={reg.can_decide} freshnessLabel={reg.freshness_label}
                     message={message} checking={checking} onCheckAgain={checkAgain}
                     onDocDone={docDone} onClose={() => setActing(null)}
                     onNoted={() => { setActing(null); load(); onDealsChanged?.(); }} />
      )}
    </div>
  );
}
