// Deal page (16 Oct; drawer layout 20 Oct). Visibility, not workflow: what the customer was told, what the contract says,
// what the check found, who has seen it, both handover notes. A commitment opens in a right-hand drawer, so the list and the
// deal's shape stay in view. The only way a gap closes is a new document version that the check confirms; notes and "seen"
// never close anything.
import { BrandBlock } from "./Logo.jsx";
import { useCallback, useEffect, useRef, useState } from "react";
import "@fontsource/inter/latin-400.css";
import "@fontsource/inter/latin-500.css";
import "@fontsource/inter/latin-600.css";
import "@fontsource/inter/latin-700.css";
import * as api from "./api.js";
import { addReady, fmtDate, fmtDateTime, mismatchNotice, newDocumentNotice, uploadKind } from "./format.js";
import {
  CLOSING_ONE_LINE, FINDING_SHORT, GAP_CLOSES, closedBy, closedLines, reopenedLines, signedConfirmations, SIGNED_NOTE, STATUS_CHIP, commitmentView, attentionText, changeResult, coverageLine, docCount, journeyOpen, docLabel, groupByStage, hashFor, isSignedDoc,
  mismatchParts, promiseLabels, missingForHandover, handoverChecklist, plainName, readHash, recordedBy, rowTitle, firstPromised, suggestFix, useName, whatChanged,
} from "./dealpage.js";
import FrozenRecord from "./FrozenRecord.jsx";
import BriefCard from "./BriefCard.jsx";
import { IdentityLine, useScrolledPast } from "./Identity.jsx";
import { Drawer, DrawerHead, CommitmentView, DocumentView, MismatchSentence, TitleLine, Icon as DIcon, ICON } from "./Drawer.jsx";
import { FICTIONAL } from "./brand.js";
import CatalogueModal from "./CatalogueModal.jsx";
import "./DealPage.css";

const Icon = ({ d, size = 15 }) => <DIcon d={d} size={size} />;
const I = {
  doc: "M14 3H6v18h12V7zM14 3v4h4M9 13h6M9 17h6",
  link: ICON.link,
  check: "M5 12l5 5L20 7",
  lock: "M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z",
  plus: "M12 5v14M5 12h14",
  calendar: "M4 6h16v14H4zM4 10h16M9 3v4M15 3v4",
  clock: "M12 7v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  files: "M9 3h7l4 4v11H9zM5 7v14h11",
  back: ICON.back,
  close: ICON.close,
  info: "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  arrow: "M5 12h14M13 6l6 6-6 6",
  alert: "M12 7v6M12 17h.01",
  sync: "M21 12a9 9 0 1 1-3-6.7M21 4v5h-5",
  chevron: ICON.chevron,
};

const fmtSize = (bytes) => (bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`);

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


// The heading's chip: amber "N need attention" while any do, otherwise a neutral "Nothing needs attention" (+ addressed by note).
function AttentionChip({ open, noted }) {
  return (
    <span className={`dp-chip ${open ? "dp-chip-amber" : "dp-chip-grey"}`}>
      <span className={`dp-dot ${open ? "" : "dp-dot-grey"}`} />
      {attentionText(open, noted)}
    </span>
  );
}

// One row of the list: title, the sentence-style mismatch line, where it was first promised, the status, a chevron. Click opens
// the drawer; the row takes a soft accent tint while its commitment is open there.
function CommitRow({ c, status, active, onOpen }) {
  const unresolved = c.issues.filter((i) => i.state !== "Resolved");
  const st = STATUS_CHIP[status];
  const noteRes = unresolved.find((i) => i.note_resolution)?.note_resolution;
  const first = firstPromised(c.statements, c.first_found);
  return (
    <li className={`dp-prow is-${status} ${active ? "is-active" : ""}`}>
      <div className="dp-prow-head" onClick={onOpen} role="button" tabIndex={0} aria-haspopup="dialog" aria-expanded={active}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen())}>
        <span className="dp-prow-main">
          <TitleLine title={rowTitle(c)} labels={status !== "closed" ? promiseLabels(unresolved) : []} />
          {status !== "closed" && <MismatchSentence parts={mismatchParts(unresolved, c.contract)} />}
          {first && <span className="dp-prow-first">{first}</span>}
          {status === "closed" && closedLines(c.issues.filter((i) => i.state === "Resolved").map((i) => i.resolved_by?.text))
            .map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
          {status === "closed" && signedConfirmations(c.issues.filter((i) => i.state === "Resolved").map((i) => i.signed_check))
            .map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
          {status !== "closed" && reopenedLines(c.issues).map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
          {status === "noted" && noteRes && <span className="dp-prow-note">{recordedBy(noteRes.by, noteRes.at, fmtDate)}</span>}
        </span>
        <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
          <span className={`dp-dot ${status === "noted" ? "dp-dot-grey" : status === "closed" ? "dp-dot-green" : ""}`} />
          {st.label}
        </span>
        <span className="dp-chevron" aria-hidden="true"><Icon d={I.chevron} size={16} /></span>
      </div>
    </li>
  );
}

function NameField({ stored, draft, onDraft }) {
  if (stored.trim()) return null;
  return (
    <label className="dp-name-field">
      <span>Your name</span>
      <input value={draft} onChange={(e) => onDraft(e.target.value)} placeholder="e.g. Sam (Delivery)" maxLength={120} required />
    </label>
  );
}


// One handover note slot. Empty: the role, the note's name and an "Add note" link. Written: the note as a quote, who recorded it
// and when, and an "Update note" link.
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
  const open = () => { setText(note?.note ?? ""); setEditing(true); };
  return (
    <div className="dp-note">
      <div className="dp-note-head">
        <div>
          <span className="dp-note-who">{who}</span>
          <span className="dp-note-role">{label}</span>
        </div>
        {!editing && !note && <button type="button" className="dp-link-btn dp-brand" onClick={open}>Add note</button>}
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
        <>
          <p className="dp-note-text">{`“${note.note}”`}</p>
          <div className="dp-note-foot">
            <span>{recordedBy(note.by, note.at, fmtDate)}</span>
            <button type="button" className="dp-link-btn dp-brand" onClick={open}>Update note</button>
          </div>
        </>
      ) : null}
    </div>
  );
}

function ChangePanel({ change, titleOf, onClose }) {
  const { closed, opened, stillOpen, openPromises } = change;
  const nothing = !closed.length && !opened.length;
  const short = (f) => FINDING_SHORT[f] ?? f;
  return (
    <section className="dp-card dp-change" role="status" aria-live="polite">
      <div className="dp-change-body">
        <div className="dp-change-head">
          <h2><Icon d={I.sync} size={18} /> After adding {change.doc}</h2>
          <p className="dp-change-result">{changeResult(change)}</p>
        </div>
        <div className="dp-change-rows">
          {closed.map((x) => (
            <div key={`c|${x.promise}|${x.finding}`} className="dp-change-row is-closed">
              <span className="dp-change-mark"><Icon d={I.check} size={13} /></span>
              <div>
                <div className="dp-change-line">
                  <strong>{titleOf(x.promise)}: {short(x.finding)}</strong>
                  <span className="dp-chip dp-chip-green"><span className="dp-dot dp-dot-green" />Closed by documents</span>
                </div>
                <p>{x.why}</p>
                {x.by && <p className="dp-change-by">{closedBy(x.by)}</p>}
              </div>
            </div>
          ))}
          {stillOpen.map((x) => (
            <div key={`s|${x.promise}|${x.finding}`} className="dp-change-row is-open">
              <span className="dp-change-mark"><Icon d={I.alert} size={13} /></span>
              <div>
                <div className="dp-change-line"><strong>Still needs attention: {short(x.finding)}</strong></div>
                <p className="dp-change-by">{titleOf(x.promise)}</p>
              </div>
            </div>
          ))}
          {opened.map((x) => (
            <div key={`n|${x.promise}|${x.finding}`} className="dp-change-row is-open">
              <span className="dp-change-mark"><Icon d={I.alert} size={13} /></span>
              <div>
                <div className="dp-change-line">
                  <strong>{titleOf(x.promise)}: {short(x.finding)}</strong>
                  <span className="dp-chip dp-chip-amber"><span className="dp-dot" />New</span>
                </div>
              </div>
            </div>
          ))}
          {nothing && <p className="dp-change-nothing">Nothing closed and nothing new: the document did not change any gap.</p>}
        </div>
        <div className="dp-change-foot">
          <span className="dp-change-count">{openPromises} {openPromises === 1 ? "commitment still needs" : "commitments still need"} attention.</span>
          <span className="dp-row">
            <button type="button" className="dp-link-btn" onClick={() => document.getElementById("dp-commitments")?.scrollIntoView({ behavior: "smooth", block: "start" })}>View commitments below</button>
            <button type="button" className="dp-link-btn dp-done" onClick={onClose}>Done</button>
          </span>
        </div>
        <p className="dp-change-model">
          {change.modelCalls ? "The model read the new document; code checked every finding again." : "No model call was needed: code checked every finding again."}
        </p>
      </div>
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


// Record a note, in the drawer. Keep it open (default) or mark as addressed by note; the name is asked for only if none is stored.
function NoteForm({ deal, c, titleId, name, setName, canDecide, freshnessLabel, message, checking, onCheckAgain, onNoted, onBack, onClose }) {
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
    <>
      <DrawerHead id={titleId} title="Record a note" sub={rowTitle(c)} backLabel="Back to commitment" onBack={onBack} onClose={onClose} />
      <form className="dr-body dr-form" onSubmit={saveNote}>
        <Hint>{CLOSING_ONE_LINE}</Hint>
        <div className="dp-field"><span>What should happen to it?</span></div>
        <div className="dp-choice" role="radiogroup" aria-label="What should happen to it?">
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
          <span>Note or recorded agreement</span>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={5} maxLength={2000} autoFocus />
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
          <button type="button" className="dp-btn dp-btn-ghost" onClick={onBack}>Cancel</button>
          <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !note.trim() || !author || blocked}>{busy ? "Saving…" : "Save note"}</button>
        </div>
      </form>
    </>
  );
}

// Add updated document, in the drawer: the existing form, as it was.
function AddPanel({ deal, c, titleId, documents, docTypes, onDone, onBack, onClose }) {
  const open = c ? c.issues.filter((i) => i.state !== "Resolved") : [];
  return (
    <>
      <DrawerHead id={titleId} title={c ? "Add updated document" : "Add a document"} sub={c ? rowTitle(c) : "A new document, or a new version of one already in the deal"}
                  backLabel={c ? "Back to commitment" : null} onBack={onBack} onClose={onClose} />
      <div className="dr-body dr-form">
        <AddDocument deal={deal} documents={documents} docTypes={docTypes} preset={c ? suggestFix(open, documents) : undefined}
                     onDone={onDone} onClose={c ? onBack : onClose} />
      </div>
    </>
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


function AddDocument({ deal, documents, docTypes, onDone, onClose, preset }) {
  // No silent default type (20 Oct): a document opened from a commitment is pre-selected by what usually closes that gap; from the
  // sidebar nothing is chosen until the person chooses, or accepts the suggestion made from the file.
  const [form, setForm] = useState({ source_key: preset?.source_key ?? "", doc_type: preset?.doc_type ?? "",
                                     doc_date: new Date().toISOString().slice(0, 10), file: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);
  const [head, setHead] = useState(""); // the start of a text file, read when it is picked, to notice a wrong file
  const pick = (file) => {
    setForm((f) => ({ ...f, file }));
    setHead("");
    setError(null);
    if (file && uploadKind(file.name) !== "binary" && file.slice) file.slice(0, 6000).text().then(setHead, () => setHead(""));
  };
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const existingDoc = form.source_key ? documents.find((d) => d.source_key === form.source_key) : null;
  const labels = Object.fromEntries(docTypes.map((t) => [t.value, t.label]));
  // What filing it this way would do, with the right action as the primary button and a quiet way to go ahead anyway.
  const notice = form.file ? mismatchNotice({
    fileName: form.file.name, head, documents, labels,
    target: { type: existingDoc?.doc_type ?? form.doc_type, name: existingDoc?.name },
  }) : null;
  // A revision filed as "A new document" would sit beside the original, dated today: say so before anything is added (21 Oct).
  const revision = form.file && !form.source_key && !notice
    ? newDocumentNotice({ fileName: form.file.name, head, documents, docType: form.doc_type, today: fmtDate(form.doc_date) }) : null;
  const ready = addReady({ file: form.file, source_key: form.source_key, doc_type: form.doc_type });
  const submit = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (!uploadKind(form.file.name)) throw new Error("Upload Markdown, text, PDF, Word, Excel or PowerPoint.");
      const content = await readUpload(form.file);
      const body = form.source_key
        ? { source_key: form.source_key, filename: form.file.name, ...content }
        : { name: form.file.name, filename: form.file.name, doc_type: form.doc_type, doc_date: form.doc_date, ...content };
      const r = await api.addDocumentAndCheck(deal, body); // refused before writing if the model is needed and unavailable
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
      <Hint>{[preset?.hint, GAP_CLOSES]}</Hint>
      <div className="dp-add-grid">
        <label>
          This is
          <select value={form.source_key} onChange={set("source_key")}>
            <option value="">A new document</option>
            {documents.map((d) => <option key={d.source_key} value={d.source_key}>A new version of: {d.name} (currently v{d.version})</option>)}
          </select>
        </label>
        {!form.source_key && (
          <>
            <label>
              Type
              <select value={form.doc_type} onChange={set("doc_type")}>
                <option value="" disabled>Choose a type…</option>
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
               onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) pick(f); }}>
          <span className="dp-drop-icon"><Icon d={I.upload} size={22} /></span>
          <span className="dp-drop-main">Drop file here or <u>browse files</u></span>
          <span className="dp-drop-sub">Markdown, text, PDF, Word, Excel or PowerPoint</span>
          <input type="file" accept=".md,.txt,.pdf,.docx,.xlsx,.pptx" onChange={(e) => pick(e.target.files[0] ?? null)} />
        </label>
        {form.file && (
          <div className="dp-file-chip">
            <Icon d={I.doc} size={16} />
            <span className="dp-file-name">{form.file.name}</span>
            <span className="dp-file-size">{fmtSize(form.file.size)}</span>
            <button type="button" className="dp-x" aria-label="Remove attached file" onClick={() => pick(null)}><Icon d={I.close} size={14} /></button>
          </div>
        )}
      </div>
      {revision && (
        <div className="dp-warnbox dp-notice-box" role="status">
          <p><strong>{revision.question}</strong> {revision.consequence}</p>
          <div className="dp-row">
            <button type="button" className="dp-btn dp-btn-dark" onClick={() => setForm((f) => ({ ...f, source_key: revision.use.source_key }))}>{revision.use.text}</button>
            {revision.anyway && <button type="button" className="dp-link-btn" disabled={busy} onClick={() => submit(null)}>{revision.anyway}</button>}
          </div>
        </div>
      )}
      {notice && (
        <div className="dp-warnbox dp-notice-box" role="status">
          <p><strong>{notice.question}</strong> {notice.consequence}</p>
          <div className="dp-row">
            <button type="button" className="dp-btn dp-btn-dark"
                    onClick={() => setForm((f) => ({ ...f, source_key: notice.use.source_key, doc_type: notice.use.doc_type || f.doc_type }))}>{notice.use.text}</button>
            <button type="button" className="dp-link-btn" disabled={busy} onClick={() => submit(null)}>{notice.anyway}</button>
          </div>
        </div>
      )}
      {form.file && !ready && !revision && <p className="dp-faint dp-small">Choose a type, or a document this is a new version of.</p>}
      {!form.source_key && isSignedDoc(form.doc_type) && <p className="dp-faint dp-small">{SIGNED_NOTE}</p>}
      <div className="dp-actions">
        {error && <span className="dp-error" role="alert">{error}</span>}
        <button type="button" className="dp-btn dp-btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
        <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !ready || !!notice || !!revision}>{busy ? "Checking…" : <>Add and check <Icon d={I.arrow} size={14} /></>}</button>
      </div>
    </form>
  );
}


function DocumentList({ deal, stages, documents, name, setName, onChanged, onView, onAdd, onHelp, activeDoc }) {
  const [draft, setDraft] = useState("");
  const [toggled, setToggled] = useState({}); // stage key -> true/false once the person clicks it; until then only the current stage is open
  const open0 = journeyOpen(stages);
  const isOpen = (key) => toggled[key] ?? open0.has(key);
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
    <li key={d.source_key} className={`${d.doc_type.startsWith("draft_") ? "is-contract" : ""} ${activeDoc === d.source_key ? "is-active" : ""}`}>
      <div className="dp-doc-row">
        <button type="button" className="dp-doc-name" onClick={() => onView(d)} title="Read the text the check used">
          {docLabel(d.name, d.date)}{d.version > 1 ? ` · v${d.version}` : ""}
        </button>
        <span className="dp-doc-meta">
          <span className="dp-mono">{fmtDate(d.version_date || d.date).replace(/ \d{4}$/, "")}</span>
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
        <span className="dp-side-title">Deal journey · {documents.length} {documents.length === 1 ? "document" : "documents"}</span>
        <button type="button" className="dp-btn dp-btn-small" onClick={onAdd} title="Add a document or a new version">
          <Icon d={I.plus} size={13} /> Add
        </button>
      </div>
      <ol className="dp-timeline">
        {groupByStage(stages, documents).map((s) => (
          <li key={s.key} className={`dp-tl is-${s.state} ${s.gaps_started > 0 ? "has-gaps" : ""}`}>
            <span className="dp-tl-dot" aria-hidden="true" />
            <div className="dp-tl-body">
              <button type="button" className="dp-tl-name dp-tl-toggle" aria-expanded={isOpen(s.key)} disabled={s.docs.length === 0}
                      onClick={() => setToggled((t) => ({ ...t, [s.key]: !isOpen(s.key) }))}>
                <span>{s.label}<span className="dp-tl-count"> · {docCount(s.docs.length)}</span></span>
                <span className="dp-tl-right">
                  {s.gaps_started > 0 && <span className="dp-stage-gaps">{s.gaps_started} {s.gaps_started === 1 ? "gap" : "gaps"} started here</span>}
                  {s.state === "current" && <span className="dp-tl-tag">Current stage</span>}
                  {s.state === "todo" && <span className="dp-tl-tag">Not yet</span>}
                </span>
              </button>
              {s.key === "contracting" && s.note && <span className="dp-tl-note">{s.note}</span>}
              {s.docs.length > 0 && isOpen(s.key) && <ul className="dp-docs">{s.docs.map(doc)}</ul>}
            </div>
          </li>
        ))}
      </ol>
      <button type="button" className="dp-link-btn dp-brand dp-help-link" onClick={onHelp}>How closing works</button>
    </div>
  );
}

// The pre-revamp detailed view stays in the code but off the demo path: its link shows only with ?detailed in the URL.
const SHOW_DETAILED = typeof window !== "undefined" && new URLSearchParams(window.location.search).has("detailed");

export default function DealPage({ deal, onBack, onDealsChanged, onClassic }) {
  const [reg, setReg] = useState(null);
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [name, setName] = useName();
  const [completing, setCompleting] = useState(false);
  const [completeDraft, setCompleteDraft] = useState("");
  const [catFocus, setCatFocus] = useState(null); // null = closed, "" = open unfocused, "CAP-…/AU" = open at an entry
  const [checking, setChecking] = useState(false);
  const [change, setChange] = useState(null); // the "What changed" card after a document or a recheck
  const [askName, setAskName] = useState(null); // { fn, initial }: the name prompt, only for actions that have no form of their own
  const [help, setHelp] = useState(false);
  // The drawer: { type: "commitment", id } | { type: "doc", docKey, quote, fromId } | { type: "add", fromId } | { type: "note", id }
  const [drawer, setDrawer] = useState(null);
  const hashed = useRef(false);
  const [headRef, headerGone] = useScrolledPast();

  const load = useCallback(() => {
    Promise.all([api.fetchRegister(deal), api.fetchDocuments(deal)]).then(
      ([r, d]) => { setReg(r); setDocs(d); setError(null); },
      (err) => setError(err.message),
    );
  }, [deal]);
  useEffect(load, [load]);

  // The address bar keeps the deal and the open commitment (#d=<deal>&c=<key>), so a reload or a shared link reopens it.
  const writeHash = useCallback((key) => {
    window.history.replaceState(null, "", hashFor({ d: deal, c: key }) || `${window.location.pathname}${window.location.search}`);
  }, [deal]);
  useEffect(() => {
    if (!reg || reg.handover.complete || hashed.current) return;
    hashed.current = true;
    const { c } = readHash(window.location.hash);
    const found = c && reg.commitments.find((x) => x.ref === c);
    if (found) setDrawer({ type: "commitment", id: found.id });
    else writeHash(null);
  }, [reg, writeHash]);

  // Editing the address by hand, or the browser's back and forward, opens or closes the drawer to match.
  useEffect(() => {
    const onHash = () => {
      const { c } = readHash(window.location.hash);
      const found = c && reg?.commitments.find((x) => x.ref === c);
      setDrawer((cur) => (found ? { type: "commitment", id: found.id } : cur?.type === "commitment" ? null : cur));
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [reg]);

  const openCommitment = (c) => { setDrawer({ type: "commitment", id: c.id }); writeHash(c.ref); };
  const closeDrawer = useCallback(() => { setDrawer(null); writeHash(null); }, [writeHash]);

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
    closeDrawer();
    setMessage(null);
    const after = await api.fetchRegister(deal);
    setChange({ ...whatChanged(reg, after), doc, modelCalls: review.model_calls });
    load();
    onDealsChanged?.();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (error) return <div className="dp"><p className="dp-error">{error}</p></div>;
  if (!reg || !docs) return <div className="dp"><p className="dp-faint">Loading…</p></div>;

  // Once the handover is complete the page shows the locked record, read from the saved snapshot.
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
  const statusOf = (id) => promiseRows.find((r) => r.c.id === id)?.status ?? "open";
  const notes = reg.handover.notes;
  const STAGE_ORDER = ["discovery", "evaluation", "proposal", "shortlisted", "contracting", "signed", "handover"];
  const isSigned = STAGE_ORDER.indexOf(reg.stage.current) >= STAGE_ORDER.indexOf("signed"); // from the documents only
  const included = docs.documents.filter((d) => d.included);
  const missing = missingForHandover({ isSigned, notes });
  const checklist = handoverChecklist({ isSigned, notes });
  const completer = (name || completeDraft).trim();
  const fromId = drawer?.type === "commitment" || drawer?.type === "note" ? drawer.id : drawer?.fromId ?? null;
  const drawerC = fromId != null ? byId(fromId) : null;
  const toCommitment = () => setDrawer({ type: "commitment", id: fromId });
  const seenIssues = (c) => c.issues.filter((i) => i.state !== "Resolved");

  return (
    <div className="dp">
      <div className="dp-topbar">
        <span className="dp-topleft">
          <button type="button" className="dp-back" onClick={onBack}><Icon d={I.back} /> All deals</button>
          <IdentityLine name={reg.name} stage={reg.stage.current_label} goLive={reg.brief?.go_live} show={headerGone} />
        </span>
        <BrandBlock className="dp-brandline" />
        <span className="dp-topright">
          {name.trim() && (
            <span className="dp-me">
              Recording as <strong>{plainName(name)}</strong> ·{" "}
              <button type="button" className="dp-link-btn dp-brand" onClick={() => setAskName({ fn: null, initial: name })}>change</button>
            </span>
          )}
          <button type="button" className="dp-btn dp-btn-small" onClick={() => setCatFocus("")}>Product catalogue</button>
        </span>
      </div>

      <div className="dp-grid">
        <div className="dp-main">
          <section className="dp-card dp-head" ref={headRef}>
            <div className="dp-title-row">
              <h1>{reg.name}</h1>
              <span className="dp-stage-pill">{reg.stage.current_label}</span>
              {reg.freshness.state === "Review out of date" && <span className="dp-chip dp-chip-amber"><span className="dp-dot" />Review out of date</span>}
              {reg.freshness.state === "Review out of date" && (
                <button type="button" className="dp-link-btn dp-brand" disabled={checking} onClick={checkAgain}>
                  {checking ? "Checking…" : "Check again"}
                </button>
              )}
            </div>
            <ul className="dp-props">
              {reg.brief?.go_live && <li><Icon d={I.calendar} size={15} /><span>Target go-live</span><strong>{fmtDate(reg.brief.go_live)}</strong></li>}
              <li><Icon d={I.clock} size={15} /><span>Last checked</span><strong>{fmtDate(reg.freshness.finished_at)}</strong></li>
              <li><Icon d={I.files} size={15} /><span>Documents</span><strong>({included.length})</strong></li>
            </ul>
          </section>

          <BriefCard brief={reg.brief} />

          {message && <div className={`dp-message is-${message.kind}`} role="status">{message.text}</div>}
          {change && <ChangePanel change={change} titleOf={(n) => reg.commitments.find((c) => c.name === n)?.display_name || n} onClose={() => setChange(null)} />}

          <section className={`dp-card dp-promises ${openRows.length ? "is-attention" : "is-clear"}`} id="dp-commitments">
            <div className="dp-sec-head">
              <div className="dp-sec-title">
                <h2>Commitments needing attention</h2>
                <AttentionChip open={openRows.length} noted={(reg.noted_rows || []).length} />
              </div>
            </div>
            {coverageLine(reg.check_coverage?.rejected) && <p className="dp-coverage">{coverageLine(reg.check_coverage.rejected)}</p>}
            {promiseRows.length === 0 && <p className="dp-faint dp-pad">No commitments with gaps on the current documents.</p>}
            <ul className="dp-plist">
              {promiseRows.map(({ c, status }) => (
                <CommitRow key={c.id} c={c} status={status} active={fromId === c.id} onOpen={() => openCommitment(c)} />
              ))}
            </ul>
          </section>

          <section className="dp-card dp-handover">
            <div className="dp-sec-head">
              <div className="dp-sec-title">
                <h2>Handover</h2>
                <span className="dp-chip dp-chip-grey">
                  <span className="dp-segs" aria-hidden="true">{checklist.map((i) => <span key={i.key} className={i.done ? "is-done" : ""} />)}</span>
                  {missing.length ? `${checklist.filter((i) => i.done).length} of ${checklist.length} ready` : "Ready to complete"}
                </span>
              </div>
            </div>
            <div className="dp-handover-body">
              <div className="dp-notes">
                <NotePanel role="sales" label="Deal owner's handoff note" who="Sales" note={notes.sales} name={name} setName={setName}
                           onSave={(role, text, by) => api.saveHandoverNote(deal, { role, note: text, entered_by: by }).then(() => { load(); onDealsChanged?.(); })} />
                <NotePanel role="delivery" label="Delivery acceptance note" who="Delivery" note={notes.delivery} name={name} setName={setName}
                           onSave={(role, text, by) => api.saveHandoverNote(deal, { role, note: text, entered_by: by }).then(() => { load(); onDealsChanged?.(); })} />
              </div>
              <ul className="dp-checklist" aria-label="Before the handover can be completed">
                {checklist.map((i) => (
                  <li key={i.key} className={i.done ? "is-done" : ""}>
                    {i.done ? <Icon d={I.check} size={14} /> : <span className="dp-hollow" aria-hidden="true" />}
                    <span>{i.label}</span>
                    <span className="dp-sr">{i.done ? " (done)" : " (still to do)"}</span>
                  </li>
                ))}
              </ul>
              <div className="dp-complete">
                <span className="dp-faint">Completing locks this record. Anything still needing attention stays visible as it stood.</span>
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
                    <Icon d={I.check} /> Lock handover record
                  </button>
                )}
              </div>
            </div>
          </section>

          <footer className="dp-foot">
            Lists commitments where the customer's expectation, the contract and what we can sell don't line up. Checked against the documents listed and the product catalogue. {FICTIONAL}
            {onClassic && SHOW_DETAILED && <> · <button type="button" className="dp-link-btn" onClick={onClassic}>Open the detailed view</button></>}
          </footer>
        </div>

        <aside className="dp-aside">
          <DocumentList deal={deal} stages={reg.stage.stages} documents={included} name={name} setName={setName} onChanged={load}
                        onView={(d) => setDrawer({ type: "doc", docKey: d.source_key, quote: null, fromId: null })}
                        onAdd={() => setDrawer({ type: "add", fromId: null })} onHelp={() => setHelp(true)}
                        activeDoc={drawer?.type === "doc" ? drawer.docKey : null} />
        </aside>
      </div>

      {catFocus !== null && <CatalogueModal focus={catFocus} deal={deal} onClose={() => setCatFocus(null)} onChanged={load} />}
      {help && <ClosingHelp onClose={() => setHelp(false)} />}
      {askName && (
        <NamePrompt initial={askName.initial} onClose={() => setAskName(null)}
                    onSave={(who) => { const run = askName.fn; setName(who); setAskName(null); run?.(who); }} />
      )}
      {drawer && (
        <Drawer labelledBy="dr-title" onClose={closeDrawer} focusKey={`${drawer.type}:${drawer.id ?? drawer.docKey ?? ""}`}>
          {drawer.type === "commitment" && drawerC && (
            <CommitmentView v={commitmentView(drawerC, statusOf(drawerC.id), docs.documents)} titleId="dr-title" me={name}
                            onClose={closeDrawer} onCatalogue={setCatFocus}
                            onOpenDoc={(doc, quote) => doc && setDrawer({ type: "doc", docKey: doc.source_key, quote, fromId: drawerC.id })}
                            onSeen={() => withName((who) => act(async () => { for (const i of seenIssues(drawerC)) await api.markSeen(deal, { issue_id: i.id, seen_by: who }); }))}
                            onNote={() => setDrawer({ type: "note", id: drawerC.id })}
                            onAddDoc={() => setDrawer({ type: "add", fromId: drawerC.id })} />
          )}
          {drawer.type === "doc" && docs.documents.find((d) => d.source_key === drawer.docKey) && (
            <DocumentView deal={deal} doc={docs.documents.find((d) => d.source_key === drawer.docKey)} quote={drawer.quote} titleId="dr-title"
                          backLabel={drawer.fromId != null ? "Back to commitment" : null} onBack={toCommitment} onClose={closeDrawer} />
          )}
          {drawer.type === "add" && (
            <AddPanel deal={deal} c={drawerC} titleId="dr-title" documents={docs.documents} docTypes={docs.doc_types}
                      onDone={docDone} onBack={drawerC ? toCommitment : closeDrawer} onClose={closeDrawer} />
          )}
          {drawer.type === "note" && drawerC && (
            <NoteForm deal={deal} c={drawerC} titleId="dr-title" name={name} setName={setName} canDecide={reg.can_decide}
                      freshnessLabel={reg.freshness_label} message={message} checking={checking} onCheckAgain={checkAgain}
                      onNoted={() => { toCommitment(); load(); onDealsChanged?.(); }} onBack={toCommitment} onClose={closeDrawer} />
          )}
        </Drawer>
      )}
    </div>
  );
}
