// Deal page (16 Oct; design from Google Stitch, screen 2, adapted to real data). Visibility, not workflow:
// what the customer was told, what the contract says, what the check found, who has seen it, both handover notes.
// The only way a gap closes is a new document version that the check confirms; notes and "seen" never close anything.
import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime, uploadKind } from "./format.js";
import { cleanReason, firstDocDate, sourcesLine, suggestFix, useName, whatChanged } from "./dealpage.js";
import FrozenRecord from "./FrozenRecord.jsx";
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
};

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

function StageBar({ stage }) {
  if (!stage?.current) return null;
  return (
    <div className="dp-stages">
      {stage.stages.map((s, n) => (
        <div key={s.key} className={`dp-stage is-${s.state}`}>
          <div className="dp-stage-track" />
          <span className="dp-stage-name">
            {n + 1}. {s.label}
            {s.state === "current" && <span className="dp-pulse" aria-hidden="true" />}
          </span>
          <span className="dp-stage-sub">
            {s.state === "current" && s.note ? s.note
              : s.documents.length ? `${s.documents.length} ${s.documents.length === 1 ? "document" : "documents"} · ${fmtDate(firstDocDate(s)).replace(/ \d{4}$/, "")}`
              : s.state === "todo" ? (s.note || "Not yet") : "No documents"}
          </span>
          {s.gaps_started > 0 && <span className="dp-stage-gaps">{s.gaps_started} {s.gaps_started === 1 ? "gap" : "gaps"} started here</span>}
        </div>
      ))}
    </div>
  );
}

// One row per promise in a single list (16 Oct): collapsed it is the title and a status, open in amber, resolved in
// green. Clicking opens the detail. Open rows carry the actions; resolved rows say how they were resolved.
const STATUS = {
  open: { tone: "amber", label: (n) => `Open · ${n} ${n === 1 ? "gap" : "gaps"}` },
  noted: { tone: "note", label: () => "Resolved by note", title: "Settled by a named person without a document. Not in the documents; reopens if the documents change." },
  closed: { tone: "green", label: () => "Closed by documents", title: "The current documents no longer show the gap." },
};

function PromiseRow({ c, status, frozen, onSeen, canAct, onCatalogue, onResolve, me = "", expanded = false, onToggle }) {
  const unresolved = c.issues.filter((i) => i.state !== "Resolved");
  const closedIssues = c.issues.filter((i) => i.state === "Resolved");
  const shown = status === "closed" ? closedIssues : unresolved;
  const seen = [...new Map(unresolved.flatMap((i) => i.seen || []).map((s) => [s.by, s])).values()];
  const detail = (c.presence_detail || "").startsWith("Not found anywhere") ? c.presence_detail : "";
  const st = STATUS[status];
  const noteRes = unresolved.find((i) => i.note_resolution)?.note_resolution;
  return (
    <li className={`dp-prow is-${status} ${expanded ? "is-open" : ""}`}>
      <div className="dp-prow-head" onClick={onToggle} role="button" tabIndex={0} aria-expanded={expanded}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onToggle())}>
        <span className={`dp-chevron ${expanded ? "is-open" : ""}`} aria-hidden="true">›</span>
        <span className="dp-prow-title">{c.name}</span>
        <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
          {status === "open" ? <span className="dp-dot" /> : <Icon d={I.check} size={12} />}
          {st.label(unresolved.length)}
        </span>
      </div>
      {expanded && (
        <div className="dp-prow-body">
          <span className="dp-kicker">{shown.map((i) => i.finding).join(" · ")}</span>
          <div className="dp-three">
            <div className="dp-fact">
              <span className="dp-fact-label">Customer was told</span>
              <p>{c.told}</p>
              <span className="dp-fact-src">{sourcesLine(c.statements)}</span>
            </div>
            <div className="dp-fact">
              <span className="dp-fact-label">Contract says</span>
              <p>{c.contract}</p>
              {detail && <span className="dp-fact-src">{detail}</span>}
            </div>
            <div className="dp-fact dp-fact-found">
              <span className="dp-fact-label">{status === "closed" ? "What was found, and what closed it" : "What we found"}</span>
              {shown.map((i) => (
                <p key={i.id} className="dp-finding"><strong>{i.finding}.</strong> {status === "closed" ? (i.resolved_by?.text || "Closed in the documents") : cleanReason(i.reason)}</p>
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
          {status !== "closed" && closedIssues.length > 0 && (
            <div className="dp-decision is-done">
              <span className="dp-kicker">Already closed by the documents</span>
              {closedIssues.map((i) => <span key={i.id}><strong>{i.finding}.</strong> {i.resolved_by?.text || ""}</span>)}
            </div>
          )}
          {status === "noted" && noteRes && (
            <div className="dp-decision is-done is-note">
              <span className="dp-kicker">Resolved by a note · not in the documents · reopens if the documents change</span>
              <span><strong>{noteRes.by}</strong> · {fmtDateTime(noteRes.at)}: “{noteRes.reason}”</span>
            </div>
          )}
          {status === "open" && noteRes && !noteRes.current && (
            <div className="dp-decision is-stale">
              <span className="dp-kicker">Was resolved by a note · reopened because the documents changed since</span>
              <span><strong>{noteRes.by}:</strong> {noteRes.reason} <span className="dp-faint">· use Resolve… to re-confirm</span></span>
            </div>
          )}
          {status === "open" && [...new Map(unresolved.filter((i) => i.decision && i.decision.status !== "none")
            .map((i) => [`${i.decision.by}|${i.decision.reason}`, i.decision])).values()].map((d) => (
            <div key={`${d.by}|${d.reason}`} className={`dp-decision ${d.status === "reconfirm" ? "is-stale" : ""}`}>
              <span className="dp-kicker">{d.status === "reconfirm" ? "Note needs re-confirming: the documents changed since" : "Note · gap still open"}</span>
              <span><strong>{d.by}:</strong> {d.reason}</span>
            </div>
          ))}
          {status === "open" && (
            <footer className="dp-gap-foot">
              <span>
                <span className="dp-faint">Seen by:</span>{" "}
                {seen.length ? seen.map((s) => `${s.by} (${fmtDate(s.at).replace(/ \d{4}$/, "")})`).join(" · ") : <span className="dp-faint">nobody yet</span>}
              </span>
              {!frozen && (
                <span className="dp-row">
                  {seen.some((x) => x.by === me.trim()) ? (
                    <span className="dp-seen-me"><Icon d={I.check} size={13} /> Seen by you</span>
                  ) : (
                    <button type="button" className="dp-link-btn" disabled={!canAct} onClick={() => onSeen(unresolved)}
                            title={canAct ? "Records that you have looked at this. It does not close the gap." : "Add your name at the top first"}>
                      <Icon d={I.eye} size={14} /> Mark as seen
                    </button>
                  )}
                  <button type="button" className="dp-btn dp-btn-dark dp-resolve" disabled={!canAct} onClick={() => onResolve(c)}
                          title={canAct ? "Add a document that fixes it, or record a note" : "Add your name at the top first"}>
                    Resolve…
                  </button>
                </span>
              )}
            </footer>
          )}
        </div>
      )}
    </li>
  );
}

function NotePanel({ role, label, who, note, frozen, canAct, onSave }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [error, setError] = useState(null);
  const save = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await onSave(role, text);
      setEditing(false);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div className="dp-note">
      <div className="dp-note-head">
        <div>
          <span className="dp-note-who">{note ? note.by : who}</span>
          <span className="dp-note-role">{label}</span>
        </div>
        <span className={`dp-chip ${note ? "dp-chip-green" : "dp-chip-grey"}`}>{note ? "Note added" : "No note yet"}</span>
      </div>
      {editing ? (
        <form onSubmit={save} className="dp-note-form">
          <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} maxLength={2000} autoFocus
                    placeholder={role === "sales" ? "What Delivery should know: open gaps, side promises, people to talk to" : "What you accept, what you need before kick-off"} />
          <div className="dp-row">
            <button type="submit" className="dp-btn dp-btn-dark" disabled={!text.trim()}>Save note</button>
            <button type="button" className="dp-btn" onClick={() => setEditing(false)}>Cancel</button>
            {error && <span className="dp-error">{error}</span>}
          </div>
        </form>
      ) : (
        <p className={`dp-note-text ${note ? "" : "is-empty"}`}>{note ? `“${note.note}”` : "Not written yet."}</p>
      )}
      <div className="dp-note-foot">
        <span>{note ? `Logged ${fmtDateTime(note.at)}` : ""}</span>
        {!frozen && !editing && (
          <button type="button" className="dp-link-btn dp-brand" disabled={!canAct}
                  onClick={() => { setText(note?.note ?? ""); setEditing(true); }}>
            {note ? "Update note" : "Add note"}
          </button>
        )}
      </div>
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
          <span className="dp-change-label">Still open on the same promise</span>
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
        {openPromises} {openPromises === 1 ? "promise still has" : "promises still have"} open gaps.
      </p>
    </section>
  );
}

function Modal({ title, sub, onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="dp-modal" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="dp-modal-body dp-pop" onClick={(e) => e.stopPropagation()}>
        <div className="dp-modal-head">
          <div><strong>{title}</strong>{sub && <span className="dp-faint dp-small dp-block">{sub}</span>}</div>
          <button type="button" className="dp-btn" onClick={onClose}>Close</button>
        </div>
        <div className="dp-pop-body">{children}</div>
      </div>
    </div>
  );
}

function ResolveModal({ deal, c, documents, docTypes, name, canDecide, onDocDone, onNoted, onClose }) {
  const open = c.issues.filter((i) => i.state !== "Resolved");
  const [tab, setTab] = useState("doc");
  const [mode, setMode] = useState("resolve"); // resolve: settled without a document; keep: on record, gap stays open
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const saveNote = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "resolve") await api.resolveByNote(deal, { issue_ids: open.map((i) => i.id), resolved_by: name, reason: note });
      else for (const i of open) await api.recordDecision(deal, { kind: "okay_to_proceed", issue_id: i.id, by: name, reason: note });
      onNoted();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title={c.name} sub={`Open: ${open.map((i) => i.finding).join(" · ")}`} onClose={onClose}>
      <div className="dp-tabs" role="tablist">
        <button type="button" role="tab" aria-selected={tab === "doc"} className={tab === "doc" ? "is-on" : ""} onClick={() => setTab("doc")}>Add a document</button>
        <button type="button" role="tab" aria-selected={tab === "note"} className={tab === "note" ? "is-on" : ""} onClick={() => setTab("note")}>Record a note</button>
      </div>
      {tab === "doc" ? (
        <AddDocument deal={deal} documents={documents} docTypes={docTypes} preset={suggestFix(open, documents)} onDone={onDocDone} onClose={onClose} />
      ) : (
        <form className="dp-add" onSubmit={saveNote}>
          <div className="dp-choice">
            <label className={mode === "resolve" ? "is-on" : ""}>
              <input type="radio" name="mode" checked={mode === "resolve"} onChange={() => setMode("resolve")} />
              <span><strong>Resolve it with this note.</strong> No document is needed, for example "the customer agreed AWS on the 14 Oct call".
                It moves to "Resolved by a note", marked <em>not in the documents</em>, and reopens if the documents change.</span>
            </label>
            <label className={mode === "keep" ? "is-on" : ""}>
              <input type="radio" name="mode" checked={mode === "keep"} onChange={() => setMode("keep")} />
              <span><strong>Keep it open, note for the record.</strong> For example "Delivery will raise it at kick-off".</span>
            </label>
          </div>
          <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4} maxLength={2000} autoFocus
                    placeholder="What was agreed, and who will act on it" />
          {mode === "keep" && !canDecide && <p className="dp-error">The deal needs checking again before a note can be recorded. Close this and use "Check again".</p>}
          <div className="dp-row">
            <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !note.trim() || !name.trim() || (mode === "keep" && !canDecide)}>
              {busy ? "Saving…" : mode === "resolve" ? `Resolve as ${name || "…"}` : `Record note as ${name || "…"}`}
            </button>
            <button type="button" className="dp-btn" onClick={onClose}>Cancel</button>
            {error && <span className="dp-error" role="alert">{error}</span>}
          </div>
        </form>
      )}
    </Modal>
  );
}

function SignatureForm({ canAct, onSave }) {
  const [on, setOn] = useState(new Date().toISOString().slice(0, 10));
  return (
    <div className="dp-sign">
      <span className="dp-small"><strong className="dp-ink">Contract signed?</strong> Record the date. It is shown as recorded by you, not read from the documents.</span>
      <span className="dp-row">
        <input type="date" value={on} max={new Date().toISOString().slice(0, 10)} onChange={(e) => setOn(e.target.value)} />
        <button type="button" className="dp-btn" disabled={!canAct || !on} onClick={() => onSave(on)}
                title={canAct ? "" : "Add your name at the top first"}>Record signature</button>
      </span>
    </div>
  );
}

function AddDocument({ deal, documents, docTypes, onDone, onClose, preset }) {
  const [form, setForm] = useState({ source_key: preset?.source_key ?? "", doc_type: preset?.doc_type ?? "draft_sow",
                                     doc_date: new Date().toISOString().slice(0, 10), file: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
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
      <div className="dp-add-head">
        {preset?.hint && <p className="dp-add-hint">{preset.hint}</p>}
        <span className="dp-faint">The check runs again on all the deal's documents. A gap closes only if the new paperwork shows it no longer holds.</span>
      </div>
      <div className="dp-add-grid">
        <label>
          This is
          <select value={form.source_key} onChange={set("source_key")}>
            <option value="">A new document</option>
            {documents.map((d) => <option key={d.source_key} value={d.source_key}>A new version of: {d.name}</option>)}
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
        <label>
          File
          <input type="file" accept=".md,.txt,.pdf,.docx,.xlsx,.pptx" onChange={set("file")} />
        </label>
      </div>
      <div className="dp-row">
        <button type="submit" className="dp-btn dp-btn-dark" disabled={busy || !form.file}>{busy ? "Checking…" : "Add and check"}</button>
        <button type="button" className="dp-btn" onClick={onClose} disabled={busy}>Cancel</button>
        {error && <span className="dp-error" role="alert">{error}</span>}
      </div>
    </form>
  );
}

function DocumentList({ deal, documents, frozen, canAct, name, onChanged, onView, onAdd }) {
  const [linking, setLinking] = useState(null);
  const [url, setUrl] = useState("");
  const [error, setError] = useState(null);
  const saveLink = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.setDocumentLink(deal, { source_key: linking, url, set_by: name });
      setLinking(null);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div className="dp-card dp-side">
      <div className="dp-side-head">
        <span className="dp-side-title"><Icon d={I.doc} /> Documents checked <span className="dp-count">{documents.length}</span></span>
        {!frozen && (
          <button type="button" className="dp-btn dp-btn-small" disabled={!canAct} onClick={onAdd}
                  title={canAct ? "Add a document or a new version" : "Add your name at the top first"}>
            <Icon d={I.plus} size={13} /> Add
          </button>
        )}
      </div>
      <ul className="dp-docs">
        {documents.map((d) => (
          <li key={d.source_key} className={d.doc_type.startsWith("draft_") ? "is-contract" : ""}>
            <div className="dp-doc-row">
              {d.link ? (
                <a href={d.link} target="_blank" rel="noopener noreferrer" className="dp-doc-name" title="Opens where the document lives">
                  {d.name}{d.version > 1 ? ` · v${d.version}` : ""} <Icon d={I.link} size={12} />
                </a>
              ) : (
                <button type="button" className="dp-doc-name" onClick={() => onView(d)} title="Read the text the check used">
                  {d.name}{d.version > 1 ? ` · v${d.version}` : ""}
                </button>
              )}
              <span className="dp-doc-meta">
                <span className="dp-mono">{fmtDate(d.date).replace(/ \d{4}$/, "")}</span>
                {!frozen && (
                  <button type="button" className={`dp-icon-btn ${d.link ? "is-set" : ""}`} disabled={!canAct}
                          onClick={() => { setLinking(linking === d.source_key ? null : d.source_key); setUrl(d.link ?? ""); }}
                          title={d.link ? "Change the Drive link" : "Save a Drive link"} aria-label={d.link ? "Change the Drive link" : "Save a Drive link"}>
                    <Icon d={I.link} size={13} />
                  </button>
                )}
              </span>
            </div>
            {linking === d.source_key && (
              <form className="dp-link-form" onSubmit={saveLink}>
                <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://drive.google.com/…" autoFocus />
                <button type="submit" className="dp-btn dp-btn-dark" disabled={!url.trim()}>Save</button>
                <button type="button" className="dp-btn" onClick={() => setLinking(null)}>Cancel</button>
                {error && <span className="dp-error">{error}</span>}
              </form>
            )}
          </li>
        ))}
      </ul>
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
  const [catFocus, setCatFocus] = useState(null); // null = closed, "" = open unfocused, "CAP-…/AU" = open at an entry
  const [checking, setChecking] = useState(false);
  const [change, setChange] = useState(null); // the "What changed" panel after a document or a recheck
  const [resolving, setResolving] = useState(null); // the promise whose Resolve pop-up is open
  const [expanded, setExpanded] = useState(() => new Set()); // gap cards shown in full; collapsed by default
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

  const docDone = async (review, doc) => {
    setAdding(false);
    setResolving(null);
    setMessage(null);
    const after = await api.fetchRegister(deal);
    setChange({ ...whatChanged(reg, after), doc, modelCalls: review.model_calls });
    load();
    onDealsChanged?.();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  if (error) return <div className="dp"><p className="dp-error">{error}</p></div>;
  if (!reg || !docs) return <div className="dp"><p className="dp-faint">Loading…</p></div>;

  // Once the handover is complete the page shows the frozen record, read from the saved snapshot (screen 3).
  if (reg.handover.complete) return <FrozenRecord deal={deal} onBack={onBack} />;
  const frozen = false;
  const canAct = !!name.trim();
  const openRows = reg.open_rows.map((id) => reg.commitments.find((c) => c.id === id));
  // One list: open promises first (most gaps first), then resolved ones; a promise keeps its row when it is resolved.
  const byId = (id) => reg.commitments.find((c) => c.id === id);
  const closedIds = [...new Set(reg.resolved_findings.map((r) => r.commitment_id))]
    .filter((id) => !reg.open_rows.includes(id) && !(reg.noted_rows || []).includes(id));
  const promiseRows = [
    ...openRows.map((c) => ({ c, status: "open" })),
    ...(reg.noted_rows || []).map((id) => ({ c: byId(id), status: "noted" })),
    ...closedIds.map((id) => ({ c: byId(id), status: "closed" })),
  ].filter((r) => r.c);
  const resolvedCount = promiseRows.length - openRows.length;
  const notes = reg.handover.notes;
  const bothNotes = notes.sales && notes.delivery;
  const STAGE_ORDER = ["discovery", "evaluation", "proposal", "shortlisted", "contracting", "signed", "handover"];
  const isSigned = STAGE_ORDER.indexOf(reg.stage.current) >= STAGE_ORDER.indexOf("signed");
  const signed = reg.handover.signature;
  const included = docs.documents.filter((d) => d.included);

  return (
    <div className="dp">
      <div className="dp-topbar">
        <button type="button" className="dp-back" onClick={onBack}><Icon d={I.back} /> All deals</button>
        <label className="dp-me">
          <span>Your name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sam (Delivery)" maxLength={120} />
        </label>
      </div>

      {frozen && (
        <div className="dp-frozen">
          <Icon d={I.lock} /> Handover complete · frozen on {fmtDateTime(reg.handover.completed_at)} by {reg.handover.completed_by}. This record no longer changes.
        </div>
      )}

      <div className="dp-grid">
        <main className="dp-main">
          <section className="dp-card dp-head">
            <div className="dp-head-row">
              <div>
                <div className="dp-title-row">
                  <h1>{reg.name}</h1>
                  <span className="dp-chip dp-chip-green">{frozen ? "Handover snapshot" : "Live deal view"}</span>
                  <span className="dp-chip dp-chip-grey">{reg.stage.current_label}</span>
                  {signed && <span className="dp-chip dp-chip-green" title="Recorded by a person, not read from the documents">Signed {fmtDate(signed.signed_on)} · recorded by {signed.recorded_by}</span>}
                </div>
                <div className="dp-meta">
                  {reg.brief?.go_live && <span className="dp-meta-strong"><Icon d={I.calendar} /> Target go-live: {fmtDate(reg.brief.go_live)}</span>}
                  <span className="dp-mono">Last checked {fmtDateTime(reg.freshness.finished_at)}</span>
                  {reg.freshness_label !== "Up to date" && <span className="dp-chip dp-chip-amber">{reg.freshness_label}</span>}
                  {reg.freshness.state === "Review out of date" && (
                    <button type="button" className="dp-link-btn dp-brand" disabled={checking}
                            onClick={() => { setChecking(true); act(async () => {
                              const r = await api.reviewDeal(deal);
                              setMessage({ kind: "ok", text: `Checked again${r.review?.model_calls ? "" : " with no model call"}. Findings are current.` });
                            }).finally(() => setChecking(false)); }}>
                      {checking ? "Checking…" : "Check again"}
                    </button>
                  )}
                </div>
              </div>
              <div className="dp-row">
                <button type="button" className="dp-btn" onClick={() => setCatFocus("")}>Product catalogue</button>
              </div>
            </div>

            <div className="dp-summary">
              <div>
                <strong>{openRows.length} {openRows.length === 1 ? "promise has" : "promises have"} open gaps.</strong>
                {reg.stage.headline && <span className="dp-faint"> {reg.stage.headline}.</span>}
              </div>
              <div className="dp-row">
                <span className="dp-pill"><span className="dp-dot dp-amber" />Open: <strong>{openRows.length}</strong></span>
                <span className="dp-pill"><span className="dp-dot dp-green" />Closed by documents: <strong>{reg.resolved_findings.length}</strong></span>
                {reg.noted_rows?.length > 0 && <span className="dp-pill"><span className="dp-dot dp-green" />Resolved by note: <strong>{reg.noted_rows.length}</strong></span>}
              </div>
            </div>

            <StageBar stage={reg.stage} />
          </section>

          {message && <div className={`dp-message is-${message.kind}`} role="status">{message.text}</div>}
          {change && <ChangePanel change={change} onClose={() => setChange(null)} />}


          {reg.brief && (
            <section className="dp-card">
              <div className="dp-sec-head">
                <h2 className="dp-upper">The deal in brief</h2>
                <span className="dp-faint">Confirmed by <strong className="dp-ink">{reg.brief.confirmed_by}</strong>{reg.brief.basis ? ` from ${reg.brief.basis}` : ""}</span>
              </div>
              <p className="dp-brief">{reg.brief.summary}</p>
              {reg.brief.deliverables.length > 0 && (
                <div className="dp-deliverables">
                  {reg.brief.deliverables.map((d) => <span key={d}><span className="dp-dot dp-brand-bg" />{d}</span>)}
                </div>
              )}
              {reg.brief.needs_reconfirmation && <div className="dp-warn">{reg.brief.reconfirm_note}</div>}
            </section>
          )}

          <section className="dp-card dp-promises">
            <div className="dp-sec-head">
              <div className="dp-row">
                <h2>Promises</h2>
                {openRows.length > 0 && <span className="dp-chip dp-chip-amber"><span className="dp-dot" />{openRows.length} open</span>}
                {resolvedCount > 0 && <span className="dp-chip dp-chip-green"><Icon d={I.check} size={12} />{resolvedCount} resolved</span>}
                {promiseRows.length > 0 && (
                  <button type="button" className="dp-link-btn dp-brand"
                          onClick={() => setExpanded(expanded.size === promiseRows.length ? new Set() : new Set(promiseRows.map((r) => r.c.id)))}>
                    {expanded.size === promiseRows.length ? "Collapse all" : "Expand all"}
                  </button>
                )}
              </div>
              <span className="dp-faint dp-small">A gap closes on its own when a new document version shows it no longer holds.</span>
            </div>
            {promiseRows.length === 0 && <p className="dp-faint">No promises with gaps on the current documents.</p>}
            <ul className="dp-plist">
              {promiseRows.map(({ c, status }) => (
                <PromiseRow key={c.id} c={c} status={status} frozen={frozen} canAct={canAct} onCatalogue={setCatFocus} onResolve={setResolving} me={name}
                            expanded={expanded.has(c.id)} onToggle={() => toggleCard(c.id)}
                            onSeen={(issues) => act(async () => { for (const i of issues) await api.markSeen(deal, { issue_id: i.id, seen_by: name }); })} />
              ))}
            </ul>
          </section>

          <section className="dp-card">
            <div className="dp-sec-head">
              <h2>Handover notes</h2>
              <span className={`dp-chip ${frozen ? "dp-chip-grey" : bothNotes ? "dp-chip-green" : "dp-chip-amber"}`}>
                {frozen ? "Frozen" : bothNotes ? "Both notes in" : "Waiting for notes"}
              </span>
            </div>
            <div className="dp-notes">
              <NotePanel role="sales" label="Deal owner's handoff note" who="Sales" note={notes.sales} frozen={frozen} canAct={canAct}
                         onSave={(role, text) => api.saveHandoverNote(deal, { role, note: text, entered_by: name }).then(() => { load(); onDealsChanged?.(); })} />
              <NotePanel role="delivery" label="Delivery acceptance note" who="Delivery" note={notes.delivery} frozen={frozen} canAct={canAct}
                         onSave={(role, text) => api.saveHandoverNote(deal, { role, note: text, entered_by: name }).then(() => { load(); onDealsChanged?.(); })} />
            </div>
            {!frozen && !isSigned && (
              <SignatureForm canAct={canAct} onSave={(on) => act(() => api.recordSignature(deal, { signed_on: on, recorded_by: name }))} />
            )}
            {!frozen && (
              <div className="dp-complete">
                <span className="dp-faint"><Icon d={I.lock} size={14} /> Completing the handover freezes this record. Open gaps stay visible as they stood.</span>
                {completing ? (
                  <span className="dp-row">
                    <span className="dp-small">Complete as <strong>{name}</strong>?</span>
                    <button type="button" className="dp-btn dp-btn-dark" onClick={() => act(() => api.completeHandover(deal, { completed_by: name })).then(() => setCompleting(false))}>Yes, complete</button>
                    <button type="button" className="dp-btn" onClick={() => setCompleting(false)}>Cancel</button>
                  </span>
                ) : (
                  <button type="button" className="dp-btn dp-btn-dark" disabled={!bothNotes || !canAct || !isSigned} onClick={() => setCompleting(true)}
                          title={!isSigned ? "Record the signature first" : !bothNotes ? "Add both notes first" : !canAct ? "Add your name at the top first" : ""}>
                    <Icon d={I.check} /> Complete handover
                  </button>
                )}
              </div>
            )}
            {!frozen && (!bothNotes || !isSigned) && (
              <p className="dp-faint dp-small dp-hint">{!isSigned ? "The handover can be completed once the deal is signed." : "Add both notes first."}</p>
            )}
          </section>

          <footer className="dp-foot">
            Lists only promises that the paperwork doesn't back. Checked against the draft contract, SOW and product catalogue.
            {onClassic && SHOW_DETAILED && <> · <button type="button" className="dp-link-btn" onClick={onClassic}>Open the detailed view</button></>}
          </footer>
        </main>

        <aside className="dp-aside">
          <DocumentList deal={deal} documents={included} frozen={frozen} canAct={canAct} name={name} onChanged={load} onView={setViewing}
                        onAdd={() => setAdding(true)} />
          <div className="dp-card dp-side dp-how">
            <span className="dp-side-title">How a gap closes</span>
            <ol>
              <li>Someone adds a document: a new version of one already here, or a new one.</li>
              <li>The check runs again on all the deal's documents.</li>
              <li>A gap closes only when the paperwork now backs the promise, in one of three ways: the contract or SOW now says it, a named approval is recorded, or the promise itself is changed or withdrawn. The reason is shown.</li>
            </ol>
            <p className="dp-faint dp-small">Without a document, a named person can resolve a gap with a note. It is listed apart, marked "not in the documents", and reopens if the documents change.</p>
            <p className="dp-faint dp-small">A new document can also uncover a new gap. Removing a document never closes one.</p>
            <p className="dp-faint dp-small">"Mark as seen" and notes kept for the record never close a gap.</p>
          </div>
        </aside>
      </div>

      {viewing && <DocViewer deal={deal} doc={viewing} onClose={() => setViewing(null)} />}
      {catFocus !== null && <CatalogueModal focus={catFocus} onClose={() => setCatFocus(null)} onChanged={load} />}
      {adding && !frozen && (
        <Modal title="Add a document" sub="A new document, or a new version of one already in the deal" onClose={() => setAdding(false)}>
          <AddDocument deal={deal} documents={docs.documents} docTypes={docs.doc_types} onClose={() => setAdding(false)} onDone={docDone} />
        </Modal>
      )}
      {resolving && !frozen && (
        <ResolveModal deal={deal} c={resolving} documents={docs.documents} docTypes={docs.doc_types} name={name} canDecide={reg.can_decide}
                      onDocDone={docDone} onClose={() => setResolving(null)}
                      onNoted={() => { setResolving(null); load(); onDealsChanged?.(); }} />
      )}
    </div>
  );
}
