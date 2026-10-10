import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import Handoff from "./Handoff.jsx";
import { TYPE_EFFECT, alsoLine, checkLine, checkUpload, fmtDate, fmtDateTime, guessType, plural, typeFromName, uploadKind } from "./format.js";

const OWNERS = ["Product", "Commercial", "Delivery", "Customer Success", "Support"];
const STATUS = {
  "Needs action": { icon: "●", cls: "s-action" },
  "Needs evidence": { icon: "◐", cls: "s-evidence" },
  "Not in current documents": { icon: "○", cls: "s-muted" },
  Resolved: { icon: "✓", cls: "s-ok" },
  "No issues raised": { icon: "–", cls: "s-muted" },
};

function Status({ value }) {
  const s = STATUS[value] ?? { icon: value.startsWith("Not checked") ? "–" : "", cls: "s-muted" };
  return (
    <span className={`status ${s.cls}`}>
      <span aria-hidden="true">{s.icon}</span> {value}
    </span>
  );
}

function Notice({ kind = "info", children }) {
  return (
    <div className={`notice notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

function DealList({ deals, current, onPick, onCreated }) {
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const create = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const { deal } = await api.createDeal(name);
      setName("");
      onCreated(deal);
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <nav className="deals" aria-label="Deals">
      <h2>Deals</h2>
      <ul>
        {deals.map((d) => (
          <li key={d.deal}>
            <button type="button" className={d.deal === current ? "deal active" : "deal"} onClick={() => onPick(d.deal)}>
              <span className="deal-name">{d.name}</span>
              <span className="deal-meta">
                {d.freshness.state} · {d.open_issues} open
              </span>
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={create} className="stack">
        <label>
          New deal
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Customer and deal name" />
        </label>
        <button type="submit" disabled={!name.trim()}>
          Create deal
        </button>
        {error && <Notice kind="error">{error}</Notice>}
      </form>
    </nav>
  );
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "");
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsDataURL(file);
  });
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("The file could not be read."));
    reader.readAsText(file);
  });
}

function Documents({ deal, data, onChanged, startOpen }) {
  const [open, setOpen] = useState(startOpen);
  const [form, setForm] = useState({ source_key: "", doc_type: "proposal", doc_date: "", file: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: k === "file" ? e.target.files[0] : e.target.value });
  const includedCount = data.documents.filter((d) => d.included).length;
  const excludedCount = data.documents.length - includedCount;

  const toggle = async (doc) => {
    setError(null);
    try {
      await api.setIncluded(deal, doc.source_key, !doc.included);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  const upload = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.file) return setError("Choose a PDF, Word, Excel, PowerPoint, Markdown or text file.");
    const refused = checkUpload(form.file.name, form.file.size);
    if (refused) return setError(refused);
    setBusy(true);
    try {
      const content = uploadKind(form.file.name) === "binary" ? { file_base64: await readBase64(form.file) } : { text: await readFile(form.file) };
      const body = form.source_key
        ? { source_key: form.source_key, filename: form.file.name, ...content }
        : { name: form.file.name, filename: form.file.name, doc_type: form.doc_type, doc_date: form.doc_date, ...content };
      await api.addDocument(deal, body);
      setForm({ ...form, file: null });
      e.target.reset();
      onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <h2>Documents</h2>
      <p className="docs-line">
        {includedCount} document{includedCount === 1 ? "" : "s"} included
        {excludedCount > 0 ? `, ${excludedCount} excluded` : ""} ·{" "}
        <button type="button" className="link" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Show"}
        </button>
      </p>
      {!open ? null : data.documents.length === 0 ? (
        <Notice>No documents yet. Upload the deal's paper trail: calls, RFP response, proposal, SOW, contract and the internal pricing note.</Notice>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Include</th>
                <th>Document</th>
                <th>Format</th>
                <th>Date</th>
                <th>Used as</th>
              </tr>
            </thead>
            <tbody>
              {data.documents.map((doc) => (
                <tr key={doc.source_key} className={doc.included ? "" : "excluded"}>
                  <td>
                    <input type="checkbox" checked={doc.included} onChange={() => toggle(doc)} aria-label={`Include ${doc.name}, version ${doc.version}`} />
                  </td>
                  <td>
                    {doc.name}, version {doc.version}
                    {doc.problems?.length > 0 && (
                      <ul className="doc-problems">
                        {doc.problems.map((p, n) => (
                          <li key={n}>{p}</li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td>{doc.format}</td>
                  <td className="nowrap">{fmtDate(doc.date)}</td>
                  <td>{doc.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {open && (
      <details className="upload">
        <summary>Upload a document or a new version</summary>
        <form onSubmit={upload} className="grid-form">
          <label>
            Upload as
            <select value={form.source_key} onChange={set("source_key")}>
              <option value="">A new document</option>
              {data.documents.map((doc) => (
                <option key={doc.source_key} value={doc.source_key}>
                  New version of {doc.name} (now version {doc.version})
                </option>
              ))}
            </select>
          </label>
          {!form.source_key && (
            <>
              <label>
                Type
                <select value={form.doc_type} onChange={set("doc_type")}>
                  {data.doc_types.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Document date
                <input type="date" value={form.doc_date} onChange={set("doc_date")} required />
              </label>
            </>
          )}
          <label>
            File (.pdf, .docx, .xlsx, .pptx, .md or .txt)
            <input type="file" accept=".pdf,.docx,.xlsx,.pptx,.md,.txt" onChange={set("file")} />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Uploading…" : "Upload"}
          </button>
        </form>
        <p className="hint">This build reads PDF (text layer only, no scans), Word (.docx), Excel (.xlsx: stored values only, hidden cells read and flagged), PowerPoint (.pptx: slide text, not speaker notes), Markdown and text. Office formats are checked on development documents only.</p>
      </details>
      )}
      {error && <Notice kind="error">{error}</Notice>}
    </section>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Layout redesign (built 9 Oct; docs/BRIEF_2026-10-06_layout.md). Level 1: the deal overview on one screen.
// Level 2: one commitment, one block per finding, with the fix inside the finding. Human decisions sit beside a finding
// and never change it: the server computes every state; this file only shows it.
// ---------------------------------------------------------------------------------------------------------------------

const today = () => new Date().toISOString().slice(0, 10);

// Put an element's top near the top of the viewport (16px of air), after it has rendered.
function scrollNearTop(id) {
  let second;
  const first = requestAnimationFrame(() => {
    second = requestAnimationFrame(() => {
      const el = document.getElementById(id);
      if (!el) return;
      window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - 16), behavior: "auto" });
      el.focus({ preventScroll: true });
    });
  });
  return () => {
    cancelAnimationFrame(first);
    if (second) cancelAnimationFrame(second);
  };
}

function FreshnessChip({ reg }) {
  const label = reg.freshness_label ?? reg.freshness.state;
  const ok = label === "Up to date";
  const reasons = (reg.freshness.reasons ?? []).filter(Boolean);
  return (
    <span className={`chip ${ok ? "chip-ok" : "chip-warn"}`} title={reasons.join(" · ")}>
      <span aria-hidden="true">{ok ? "✓" : "!"}</span> {label}
      {!ok && reasons.length > 0 && <span className="chip-why"> — {reasons.join("; ")}</span>}
    </span>
  );
}

function DealNote({ deal, note, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ note: note?.note ?? "", entered_by: "", deadline: note?.deadline ?? "" });
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.saveNote(deal, form);
      setEditing(false);
      onSaved();
    } catch (err) {
      setError(err.message);
    }
  };
  if (editing)
    return (
      <form onSubmit={save} className="note-form">
        <label className="wide">
          About this deal (one or two lines, typed by a person)
          <textarea rows={2} maxLength={300} value={form.note} onChange={set("note")} required />
        </label>
        <label>
          Decision deadline
          <input type="date" value={form.deadline} onChange={set("deadline")} />
        </label>
        <label>
          Your name
          <input value={form.entered_by} onChange={set("entered_by")} required />
        </label>
        <div className="row-actions">
          <button type="submit" className="primary">Save note</button>
          <button type="button" onClick={() => setEditing(false)}>Cancel</button>
        </div>
        {error && <Notice kind="error">{error}</Notice>}
      </form>
    );
  return (
    <div className="deal-note">
      {note ? (
        <>
          <p className="note-text">{note.note}</p>
          <p className="hint">
            Deal note · entered by {note.entered_by} ·{" "}
            <button type="button" className="link" onClick={() => setEditing(true)}>Edit</button>
          </p>
        </>
      ) : (
        <p className="hint">
          No deal note yet.{" "}
          <button type="button" className="link" onClick={() => setEditing(true)}>Add a two-line note and the decision deadline</button>
        </p>
      )}
    </div>
  );
}

function CountsLine({ counts }) {
  return (
    <div className="counts" role="status">
      <span className="count">
        <strong>{counts.unresolved}</strong> {counts.unresolved === 1 ? "finding" : "findings"} unresolved
      </span>
      <span className="count">
        <strong>{counts.awaiting_decision}</strong> awaiting decision
      </span>
      {counts.needs_reconfirmation > 0 && (
        <span className="count count-warn">{plural(counts.needs_reconfirmation, "decision")} need{counts.needs_reconfirmation === 1 ? "s" : ""} re-confirmation</span>
      )}
      {counts.must_fix_flags > 0 && <span className="count count-bad">{plural(counts.must_fix_flags, "must-fix flag")}</span>}
    </div>
  );
}

function DecisionCell({ c }) {
  const line = c.decision_line;
  return (
    <>
      {c.must_fix && <span className="tag tag-bad">Must fix before signing</span>}
      {line && (/re-confirmation/i.test(line) ? <span className="tag tag-warn">{line}</span> : <span className={/awaiting/i.test(line) ? "muted cell-line" : "cell-line"}>{line}</span>)}
    </>
  );
}

function Overview({ deal, reg, docs, onOpen, onChanged, busy, onReview }) {
  const byId = new Map(reg.commitments.map((c) => [c.id, c]));
  const rows = reg.open_rows.map((id) => byId.get(id));
  const others = reg.other_rows.map((id) => byId.get(id));
  const note = reg.deal_note;
  return (
    <>
      <section className="panel deal-head">
        <div className="deal-head-top">
          <div>
            <h2 className="deal-title">{reg.name}</h2>
            <p className="hint versions">Documents in use: {reg.versions_line || "none yet"}</p>
          </div>
          <div className="deal-head-right">
            <FreshnessChip reg={reg} />
            <p className="hint">
              {reg.freshness.finished_at ? `Last review ${fmtDateTime(reg.freshness.finished_at)}` : "Not reviewed yet"}
              {note?.deadline ? ` · Decision deadline ${fmtDate(note.deadline)}` : ""}
            </p>
            <button type="button" className="primary" onClick={onReview} disabled={busy || docs.documents.length === 0}>
              {busy ? "Reviewing…" : "Review deal"}
            </button>
          </div>
        </div>
        <DealNote key={note?.at ?? "none"} deal={deal} note={note} onSaved={onChanged} />
        <CountsLine counts={reg.finding_counts} />
      </section>

      <section className="panel">
        <div className="section-head">
          <h2>Commitments with open findings</h2>
          <span className="hint">Sorted by open findings</span>
        </div>
        {rows.length === 0 ? (
          <Notice>No open findings.</Notice>
        ) : (
          <div className="table-wrap">
            <table className="rows">
              <thead>
                <tr>
                  <th>Commitment</th>
                  <th>Told</th>
                  <th>Contract</th>
                  <th>Findings</th>
                  <th className="num">Open</th>
                  <th>Accountable</th>
                  <th>Decision</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} onClick={() => onOpen(c.id)}>
                    <td>
                      <button type="button" className="link">{c.name}</button>
                    </td>
                    <td>{c.told}</td>
                    <td>{c.contract}</td>
                    <td>{c.findings.join(" · ")}</td>
                    <td className="num">{c.open_count}</td>
                    <td>
                      {c.accountable ?? ""}
                      {c.confirm_owner.map((p) => (
                        <span key={p} className="tag tag-warn" title="The evidence or terms changed since this person was named">{p} · confirm</span>
                      ))}
                      {c.unassigned && <span className="tag tag-warn">{c.accountable || c.confirm_owner.length ? "+ Unassigned" : "Unassigned"}</span>}
                    </td>
                    <td>
                      <DecisionCell c={c} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <details className="panel fold">
        <summary>Resolved findings ({reg.resolved_findings.length})</summary>
        {reg.resolved_findings.length === 0 ? (
          <p className="hint">None yet.</p>
        ) : (
          <ul className="plain-list">
            {reg.resolved_findings.map((f) => (
              <li key={f.issue_id}>
                <span className="status s-ok">✓</span>{" "}
                <button type="button" className="link" onClick={() => onOpen(f.commitment_id)}>{f.commitment}</button> — {f.finding}.{" "}
                <span className="hint">{f.resolved_by}</span>
              </li>
            ))}
          </ul>
        )}
      </details>

      <details className="panel fold">
        <summary>Other commitments ({others.length}) · no issues raised or not checked</summary>
        <ul className="plain-list">
          {others.map((c) => (
            <li key={c.id}>
              <button type="button" className="link" onClick={() => onOpen(c.id)}>{c.name}</button> — <Status value={c.status} />
            </li>
          ))}
        </ul>
        <p className="hint">Only firm promises are checked against approval and the contract.</p>
      </details>

      <details className="panel fold">
        <summary>Review coverage, documents and saved handoff</summary>
        <p className="hint">{reg.scope_note}</p>
        {(reg.freshness.notes ?? []).map((n) => (
          <p key={n} className="hint">{n}</p>
        ))}
        <Documents deal={deal} data={docs} onChanged={onChanged} startOpen={docs.documents.length === 0} />
        <Handoff deal={deal} reg={reg} />
        <p className="hint">{reg.resolved_means}</p>
      </details>
    </>
  );
}

function AttachEvidence({ deal, issue, documents, docTypes, onResult }) {
  const [file, setFile] = useState(null);
  const [docType, setDocType] = useState(null);
  const [target, setTarget] = useState("");
  const [form, setForm] = useState({ note: "", signed_off_by: "", doc_date: today() });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const sameType = (t) => documents.filter((d) => d.doc_type === t);

  const chooseType = (t) => {
    setDocType(t);
    const existing = sameType(t);
    setTarget(existing.length === 1 ? existing[0].source_key : existing.length ? existing[existing.length - 1].source_key : "");
  };
  const pickFile = (e) => {
    const f = e.target.files[0] ?? null;
    setError(null);
    setFile(f);
    if (f) {
      const refused = checkUpload(f.name, f.size);
      if (refused) return setError(refused);
      chooseType(guessType(f.name, issue.type));
    }
  };
  const hint = file ? typeFromName(file.name) : null;
  const replacing = documents.find((d) => d.source_key === target);
  const typeLabel = (t) => docTypes.find((x) => x.value === t)?.label ?? t;

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!file) return setError("Attach the document first.");
    const refused = checkUpload(file.name, file.size);
    if (refused) return setError(refused);
    setBusy(true);
    try {
      const content = uploadKind(file.name) === "binary" ? { file_base64: await readBase64(file) } : { text: await readFile(file) };
      const body = {
        issue_id: issue.id,
        confirmed_doc_type: docType,
        filename: file.name,
        note: form.note,
        signed_off_by: form.signed_off_by,
        ...(target ? { source_key: target } : { name: file.name, doc_date: form.doc_date }),
        ...content,
      };
      const { check } = await api.checkFinding(deal, body);
      onResult(check);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="attach" onSubmit={submit}>
      <ol className="steps">
        <li>
          <label>
            <span className="step-title">Attach evidence to fix this finding</span>
            <input type="file" accept=".pdf,.docx,.xlsx,.pptx,.md,.txt" onChange={pickFile} />
          </label>
        </li>
        {file && (
        <>
        <li>
          <span className="step-title">Confirm what this document is</span>
          {file && docType && (
            <div className="confirm-type">
              <label>
                Document type
                <select value={docType} onChange={(e) => chooseType(e.target.value)}>
                  {docTypes.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </label>
              <label>
                It is
                <select value={target} onChange={(e) => setTarget(e.target.value)}>
                  {sameType(docType).map((d) => (
                    <option key={d.source_key} value={d.source_key}>
                      A new version of {d.name} (replaces version {d.version})
                    </option>
                  ))}
                  <option value="">A new document</option>
                </select>
              </label>
              {!target && (
                <label>
                  Document date
                  <input type="date" value={form.doc_date} onChange={set("doc_date")} required />
                </label>
              )}
              <p className="consequence">
                <strong>{TYPE_EFFECT[docType] ?? "Read for promises"}</strong>
                {replacing ? ` · Replaces ${replacing.name}, version ${replacing.version}` : " · Added as a new document"}
              </p>
              {hint && hint !== docType && (
                <div className="type-warning">
                  <Notice kind="error">
                    The file name “{file.name}” looks like a {typeLabel(hint)}, but you chose {typeLabel(docType)}. Check before saving.
                  </Notice>
                </div>
              )}
            </div>
          )}
        </li>
        <li>
          <div className="pair">
            <label>
              Note (optional)
              <input value={form.note} onChange={set("note")} maxLength={2000} />
            </label>
            <label>
              Signed off by
              <input value={form.signed_off_by} onChange={set("signed_off_by")} required />
            </label>
          </div>
        </li>
        <li>
          <button type="submit" className="primary" disabled={busy || !file || !docType}>
            {busy ? "Checking…" : "Save & check"}
          </button>
          <span className="hint"> Attaching is not proof: the check closes a finding only when the evidence meets what it needs.</span>
        </li>
        </>
        )}
      </ol>
      {!file && <p className="hint steps-next">Then: confirm the document type → sign off → Save &amp; check.</p>}
      {error && <Notice kind="error">{error}</Notice>}
    </form>
  );
}

function DecisionStatus({ issue }) {
  const d = issue.decision;
  return (
    <>
      {d.must_fix && (
        <p className="flag">
          <span className="tag tag-bad">Must fix before signing</span> {d.must_fix.by}: {d.must_fix.reason}
          {issue.state === "Resolved" ? " · Finding now resolved: a named person must review and clear this flag." : ""}
        </p>
      )}
      {d.status === "okay" && (
        <p>
          <span className="tag tag-ok">Okay to proceed</span> {d.by}: {d.reason}{" "}
          <span className="hint">The finding stays open.</span>
        </p>
      )}
      {d.status === "reconfirm" && (
        <p>
          <span className="tag tag-warn">Needs re-confirmation</span> Okay to proceed by {d.by}: {d.reason}{" "}
          <span className="hint">({(d.reasons ?? []).join("; ")})</span>
        </p>
      )}
      {d.status === "none" && !d.must_fix && issue.state !== "Resolved" && <p className="muted">Awaiting decision</p>}
    </>
  );
}

function DecisionForm({ deal, issue, canDecide, onChanged }) {
  const [form, setForm] = useState({ kind: "must_fix", by: "", reason: "" });
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const flag = issue.decision.must_fix;
  const [clear, setClear] = useState({ by: "", reason: "" });

  const save = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.recordDecision(deal, { ...form, issue_id: issue.id });
      setForm({ ...form, reason: "" });
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  const doClear = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.clearFlag(deal, { flag_id: flag.flag_id, ...clear });
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <details className="decide">
      <summary>{flag ? "Review and clear the must-fix flag" : "Record a decision on this finding"}</summary>
      {flag ? (
        <form onSubmit={doClear} className="pair">
          <label>
            Cleared by
            <input value={clear.by} onChange={(e) => setClear({ ...clear, by: e.target.value })} required />
          </label>
          <label>
            Reason
            <input value={clear.reason} onChange={(e) => setClear({ ...clear, reason: e.target.value })} required />
          </label>
          <button type="submit">Clear flag</button>
        </form>
      ) : (
        <form onSubmit={save} className="stack">
          <fieldset>
            <legend>Decision</legend>
            <label className="check">
              <input type="radio" name={`k${issue.id}`} value="okay_to_proceed" checked={form.kind === "okay_to_proceed"} onChange={set("kind")}
                disabled={!canDecide} /> Okay to proceed
              {!canDecide && <span className="hint"> (rerun the review first)</span>}
            </label>
            <label className="check">
              <input type="radio" name={`k${issue.id}`} value="must_fix" checked={form.kind === "must_fix"} onChange={set("kind")} /> Must fix before signing
            </label>
          </fieldset>
          <div className="pair">
            <label>
              Your name
              <input value={form.by} onChange={set("by")} required />
            </label>
            <label>
              Reason
              <input value={form.reason} onChange={set("reason")} required />
            </label>
          </div>
          <div>
            <button type="submit">Save decision</button>
            <span className="hint"> A decision never changes the finding or the unresolved count.</span>
          </div>
        </form>
      )}
      {error && <Notice kind="error">{error}</Notice>}
    </details>
  );
}

function Accountable({ deal, issue, canDecide, onChanged }) {
  const acc = issue.accountable ?? { status: "none" };
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ person: acc.person ?? "", set_by: "" });
  const [error, setError] = useState(null);
  const save = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      await api.setAccountable(deal, { issue_id: issue.id, ...form, confirm: acc.status === "confirm" && form.person === acc.person });
      setOpen(false);
      onChanged();
    } catch (err) {
      setError(err.message);
    }
  };
  return (
    <div>
      <dt>Accountable person</dt>
      <dd>
        {acc.status === "current" && acc.person}
        {acc.status === "confirm" && (
          <>
            {acc.person} <span className="tag tag-warn">Confirm owner still applies</span>
          </>
        )}
        {acc.status === "none" && (issue.state === "Resolved" ? "—" : <span className="tag tag-warn">Unassigned</span>)}{" "}
        {issue.state !== "Resolved" && !open && (
          <button type="button" className="link" onClick={() => setOpen(true)} disabled={!canDecide} title={canDecide ? "" : "Rerun the review first"}>
            {acc.status === "none" ? "Assign" : acc.status === "confirm" ? "Confirm or change" : "Change"}
          </button>
        )}
        {open && (
          <form onSubmit={save} className="pair inline-form">
            <input aria-label="Accountable person" placeholder="Accountable person" value={form.person} onChange={(e) => setForm({ ...form, person: e.target.value })} required />
            <input aria-label="Your name" placeholder="Your name" value={form.set_by} onChange={(e) => setForm({ ...form, set_by: e.target.value })} required />
            <button type="submit">Save</button>
          </form>
        )}
        {error && <Notice kind="error">{error}</Notice>}
      </dd>
    </div>
  );
}

function FindingBlock({ deal, issue, documents, docTypes, canDecide, result, onResult, onChanged, onOpenDoc }) {
  const resolved = issue.state === "Resolved";
  const mine = result && result.issue_id === issue.id ? result : null;
  const saveOwner = async (owner) => {
    await api.updateIssue(deal, { issue_id: issue.id, owner });
    onChanged();
  };
  return (
    <article className={`finding ${resolved ? "finding-done" : ""}`} id={`finding-${issue.id}`} tabIndex={-1}>
      <header className="finding-head">
        <h3>{issue.finding}</h3>
        <Status value={issue.state} />
      </header>
      {mine && (
        <div className="result" role="status">
          <p><strong>{checkLine(mine)}</strong></p>
          {alsoLine(mine, issue.finding) && <p>{alsoLine(mine, issue.finding)}</p>}
          {mine.new.length > 0 && <p>New finding raised: {mine.new.join("; ")}.</p>}
        </div>
      )}
      {resolved && issue.resolved_by && (
        <p className="resolved-by">
          {issue.resolved_by.text}
          {issue.resolved_by.documents.map((d) => (
            <button key={d.source_version_id} type="button" className="link open-doc" onClick={() => onOpenDoc(d.source_version_id)}>
              Open {d.label}
            </button>
          ))}
        </p>
      )}
      {!resolved && <p className="why">{issue.reason}</p>}
      {!resolved && issue.raised_by === "model_v2" && issue.unmet && issue.unmet.length > 0 && (
        <p className="verified"><span>Checked against the documents and catalogue:</span> {issue.unmet.join(" ")}</p>
      )}
      {resolved && issue.raised_by === "model_v2" && issue.reason && <p className="why">{issue.reason}</p>}
      <dl className="facts">
        {!resolved && (
          <div>
            <dt>What would close it</dt>
            <dd>{issue.next_step}</dd>
          </div>
        )}
        <div>
          <dt>Responsible team</dt>
          <dd>
            <select value={issue.owner} onChange={(e) => saveOwner(e.target.value)} aria-label="Responsible team">
              {OWNERS.map((o) => (
                <option key={o}>{o}</option>
              ))}
            </select>
          </dd>
        </div>
        <Accountable deal={deal} issue={issue} canDecide={canDecide} onChanged={onChanged} />
        <div>
          <dt>Business impact</dt>
          <dd>{issue.impact}</dd>
        </div>
      </dl>
      <DecisionStatus issue={issue} />
      {!resolved && <AttachEvidence deal={deal} issue={issue} documents={documents} docTypes={docTypes} onResult={onResult} />}
      {(!resolved || issue.decision.must_fix) && <DecisionForm deal={deal} issue={issue} canDecide={canDecide} onChanged={onChanged} />}
    </article>
  );
}

function CommitmentDetail({ deal, c, reg, documents, docTypes, result, onResult, onBack, onChanged, onOpenDoc }) {
  const ordered = [...c.issues.filter((i) => i.state !== "Resolved"), ...c.issues.filter((i) => i.state === "Resolved")];
  useEffect(() => scrollNearTop("commitment-detail"), [c.id]);
  return (
    <section className="panel detail" id="commitment-detail" tabIndex={-1}>
      <button type="button" className="link back" onClick={onBack}>← Back to overview</button>
      {result && result.commitment_id === c.id && (
        <div className="banner banner-result" role="status">
          {checkLine(result)}
        </div>
      )}
      <header className="detail-head">
        <h2>{c.name}</h2>
        <Status value={c.status} />
      </header>
      <div className="sides">
        <div className="side">
          <span className="side-label">Told</span>
          <span className="side-value">{c.told}</span>
          <span className="hint">{c.language} · {c.authorisation}</span>
        </div>
        <div className="side">
          <span className="side-label">Contract</span>
          <span className="side-value">{c.contract}</span>
          <span className="hint">{c.presence}</span>
        </div>
      </div>
      <details className="trail">
        <summary>Promise trail · {plural(c.statements.length, "source")}</summary>
        {c.progression && <p className="progression">{c.progression}</p>}
        <ol className="timeline">
          {c.statements.map((s, n) => (
            <li key={n}>
              <span className="when">{fmtDate(s.date)}</span>
              <blockquote>“{s.quote}”</blockquote>
              <cite>
                {s.source_name}, version {s.version}
                {s.page ? `, page ${s.page}` : ""}
                {s.where ? `, ${s.where}` : ""} · {s.language}
              </cite>
            </li>
          ))}
          {c.statements.length === 0 && <li className="hint">No statement in the current documents.</li>}
        </ol>
        <p className="why">{c.authorisation_evidence}</p>
        <p className="why">{c.presence_detail}</p>
      </details>
      {c.check_note && <p className="hint">{c.check_note}</p>}
      {ordered.length === 0 && <Notice>No findings on this commitment.</Notice>}
      {ordered.map((i) => (
        <FindingBlock key={i.id} deal={deal} issue={i} documents={documents} docTypes={docTypes} canDecide={reg.can_decide}
          result={result} onResult={onResult} onChanged={onChanged} onOpenDoc={onOpenDoc} />
      ))}
    </section>
  );
}

function DocViewer({ deal, versionId, onClose }) {
  const [doc, setDoc] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    api.fetchDocumentText(deal, versionId).then(setDoc, (err) => setError(err.message));
  }, [deal, versionId]);
  return (
    <div className="viewer-backdrop" onClick={onClose}>
      <div className="viewer" role="dialog" aria-modal="true" aria-label={doc?.name ?? "Document"} onClick={(e) => e.stopPropagation()}>
        <div className="viewer-head">
          <h3>{doc?.name ?? "Loading…"}</h3>
          <button type="button" onClick={onClose}>Close</button>
        </div>
        {error && <Notice kind="error">{error}</Notice>}
        {doc && <pre className="doc-text">{doc.text}</pre>}
      </div>
    </div>
  );
}

function Workspace({ deal, onDealsChanged }) {
  const [state, setState] = useState({ loading: true });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [view, setView] = useState(null); // null = overview, else a commitment id
  const [result, setResult] = useState(null); // the last Save & check result, until the next action elsewhere
  const [viewing, setViewing] = useState(null);

  const load = useCallback(async () => {
    try {
      const [docs, reg] = await Promise.all([api.fetchDocuments(deal), api.fetchRegister(deal)]);
      setState({ loading: false, docs, reg });
      onDealsChanged();
    } catch (err) {
      setState({ loading: false, error: err.message });
    }
  }, [deal, onDealsChanged]);

  useEffect(() => {
    setState({ loading: true });
    setMessage(null);
    setView(null);
    load();
  }, [load]);

  const review = async () => {
    setBusy(true);
    setMessage(null);
    setResult(null);
    try {
      const { review: r } = await api.reviewDeal(deal);
      setMessage({ kind: "info", text: `Review complete. ${r.model_calls ? `${r.model_calls} document(s) read by the model.` : "No new documents to read."}` });
      await load();
    } catch (err) {
      setMessage({ kind: "error", text: err.message });
    } finally {
      setBusy(false);
    }
  };

  if (state.loading) return <Notice>Loading the deal…</Notice>;
  if (state.error) return <Notice kind="error">{state.error}</Notice>;
  const { docs, reg } = state;
  const current = view != null ? reg.commitments.find((c) => c.id === view) : null;
  const open = (id) => {
    setResult(null);
    setView(id);
  };
  return (
    <div className="workspace">
      {message && <Notice kind={message.kind}>{message.text}</Notice>}
      {reg.commitments.length === 0 ? (
        <>
          <section className="panel deal-head">
            <h2 className="deal-title">{reg.name}</h2>
            <p className="hint">No review yet. Add documents, then choose Review deal.</p>
            <button type="button" className="primary" onClick={review} disabled={busy || docs.documents.length === 0}>
              {busy ? "Reviewing…" : "Review deal"}
            </button>
          </section>
          <Documents deal={deal} data={docs} onChanged={load} startOpen />
        </>
      ) : current ? (
        <CommitmentDetail deal={deal} c={current} reg={reg} documents={docs.documents} docTypes={docs.doc_types} result={result}
          onResult={(r) => { setResult(r); load(); }} onBack={() => { setResult(null); setView(null); }}
          onChanged={() => { setResult(null); load(); }} onOpenDoc={setViewing} />
      ) : (
        <Overview deal={deal} reg={reg} docs={docs} onOpen={open} onChanged={load} busy={busy} onReview={review} />
      )}
      {viewing != null && <DocViewer deal={deal} versionId={viewing} onClose={() => setViewing(null)} />}
    </div>
  );
}

export default function App() {
  const [deals, setDeals] = useState(null);
  const [current, setCurrent] = useState(null);
  const [error, setError] = useState(null);

  const loadDeals = useCallback(() => {
    api.fetchDeals().then(
      (r) => {
        setDeals(r.deals);
        setCurrent((c) => c ?? r.deals[0]?.deal ?? null);
      },
      (err) => setError(err.message),
    );
  }, []);
  useEffect(loadDeals, [loadDeals]);

  return (
    <main>
      <header className="top">
        <p className="eyebrow">Promise to Delivery</p>
        <h1>Hand over the deal as it was promised.</h1>
      </header>
      {error && <Notice kind="error">{error}</Notice>}
      {deals && (
        <div className="layout">
          <DealList deals={deals} current={current} onPick={setCurrent} onCreated={(d) => { setCurrent(d); loadDeals(); }} />
          {current ? <Workspace key={current} deal={current} onDealsChanged={loadDeals} /> : <Notice>Create a deal to begin.</Notice>}
        </div>
      )}
    </main>
  );
}
