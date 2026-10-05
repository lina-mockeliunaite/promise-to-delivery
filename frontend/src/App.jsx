import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import Handoff from "./Handoff.jsx";
import { fmtDate, fmtDateTime, recheckLine } from "./format.js";

const OWNERS = ["Product", "Commercial", "Delivery", "Customer Success", "Support"];
const ROUTES = [
  { value: "align_documents", label: "Align the documents" },
  { value: "allowed_exception", label: "Record an allowed exception" },
  { value: "change_or_withdraw_promise", label: "Change or withdraw the promise" },
];
const STATUS = {
  "Needs action": { icon: "●", cls: "s-action" },
  "Needs evidence": { icon: "◐", cls: "s-evidence" },
  "Not in current documents": { icon: "○", cls: "s-muted" },
  Resolved: { icon: "✓", cls: "s-ok" },
  "No issues raised": { icon: "–", cls: "s-muted" },
};

function Status({ value }) {
  const s = STATUS[value] ?? { icon: "", cls: "s-muted" };
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
    if (!form.file) return setError("Choose a text or Markdown file.");
    setBusy(true);
    try {
      const text = await readFile(form.file);
      const body = form.source_key
        ? { source_key: form.source_key, filename: form.file.name, text }
        : { name: form.file.name, filename: form.file.name, doc_type: form.doc_type, doc_date: form.doc_date, text };
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
                  </td>
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
            File (.md or .txt)
            <input type="file" accept=".md,.txt,text/plain,text/markdown" onChange={set("file")} />
          </label>
          <button type="submit" disabled={busy}>
            {busy ? "Uploading…" : "Upload"}
          </button>
        </form>
        <p className="hint">This build reads text and Markdown. PDF, Word, Excel and PowerPoint follow.</p>
      </details>
      )}
      {error && <Notice kind="error">{error}</Notice>}
    </section>
  );
}

function FixForm({ deal, commitment, documents, onStart, onDone }) {
  const open = commitment.issues.filter((i) => i.state !== "Resolved");
  const [form, setForm] = useState({
    route: "allowed_exception",
    owner: open[0]?.owner ?? "Product",
    rationale: "",
    approved_by: "",
    issue_ids: open.map((i) => i.id),
    evidence: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggleIssue = (id) =>
    setForm({ ...form, issue_ids: form.issue_ids.includes(id) ? form.issue_ids.filter((x) => x !== id) : [...form.issue_ids, id] });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const evidence = form.evidence ? [{ source_version_id: Number(form.evidence), locator: "whole document" }] : [];
      onStart();
      const { fix_id } = await api.recordFix(deal, { ...form, evidence });
      await api.reviewDeal(deal, fix_id);
      const fresh = await api.fetchRegister(deal);
      const now = fresh.commitments.find((x) => x.id === commitment.id);
      onDone(recheckLine(open, now ? now.issues : []));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  if (open.length === 0) return null;
  return (
    <form onSubmit={submit} className="fix grid-form">
      <h4>Record a fix, then recheck</h4>
      <label>
        Route
        <select value={form.route} onChange={set("route")}>
          {ROUTES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Owner
        <select value={form.owner} onChange={set("owner")}>
          {OWNERS.map((o) => (
            <option key={o}>{o}</option>
          ))}
        </select>
      </label>
      <fieldset>
        <legend>Issues this fix addresses</legend>
        {open.map((i) => (
          <label key={i.id} className="check">
            <input type="checkbox" checked={form.issue_ids.includes(i.id)} onChange={() => toggleIssue(i.id)} /> {i.label}
          </label>
        ))}
      </fieldset>
      <label>
        Evidence (the document version that supports it)
        <select value={form.evidence} onChange={set("evidence")}>
          <option value="">None (only for changing or withdrawing a promise)</option>
          {documents
            .filter((d) => d.included)
            .map((d) => (
              <option key={d.source_version_id} value={d.source_version_id}>
                {d.name}, version {d.version}
              </option>
            ))}
        </select>
      </label>
      <label className="wide">
        Rationale
        <textarea value={form.rationale} onChange={set("rationale")} rows={2} required />
      </label>
      <label>
        Approved by
        <input value={form.approved_by} onChange={set("approved_by")} required />
      </label>
      <button type="submit" disabled={busy || form.issue_ids.length === 0}>
        {busy ? "Rechecking…" : "Record and recheck"}
      </button>
      <p className="hint wide">Recording a fix is not proof. The recheck closes an issue only when the evidence meets its criteria.</p>
      {error && <Notice kind="error">{error}</Notice>}
    </form>
  );
}

function IssueRow({ deal, issue, onChanged, onEdit }) {
  const [note, setNote] = useState(issue.note ?? "");
  const save = async (body) => {
    onEdit();
    await api.updateIssue(deal, { issue_id: issue.id, ...body });
    onChanged();
  };
  return (
    <li className="issue">
      <div className="issue-head">
        <Status value={issue.state} />
        <strong>{issue.label}</strong>
        {issue.absolute_limit && <span className="tag tag-warn">Not offered</span>}
      </div>
      {issue.next_step && <p className="next">Next: {issue.next_step}</p>}
      <p className="why">{issue.reason}</p>
      <div className="issue-edit">
        <label>
          Owner
          <select value={issue.owner} onChange={(e) => save({ owner: e.target.value })}>
            {OWNERS.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </select>
        </label>
        <label className="grow">
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} onBlur={() => note !== (issue.note ?? "") && save({ note })} />
        </label>
      </div>
    </li>
  );
}

function CommitmentCard({ deal, c, documents, onChanged, result, setResult }) {
  const clear = () => setResult(null);
  return (
    <article className="card" id="commitment-card" tabIndex={-1}>
      <header className="card-head">
        <h3>{c.name}</h3>
        <Status value={c.status} />
      </header>
      {result && result.id === c.id && (
        <p className="recheck-line" role="status">
          {result.text}
        </p>
      )}
      <dl className="facts">
        <div>
          <dt>Language</dt>
          <dd>{c.language}</dd>
        </div>
        <div>
          <dt>Authorisation</dt>
          <dd>{c.authorisation}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd>{c.presence}</dd>
        </div>
      </dl>
      <h4>What was said</h4>
      {c.progression && <p className="progression">{c.progression}</p>}
      <ul className="quotes">
        {c.statements.map((s, n) => (
          <li key={n}>
            <blockquote>“{s.quote}”</blockquote>
            <cite>
              {s.source_name}, version {s.version} · {s.language}
            </cite>
          </li>
        ))}
        {c.statements.length === 0 && <li className="hint">No statement in the current documents.</li>}
      </ul>
      <details>
        <summary>Evidence behind the verdicts</summary>
        <p className="why">{c.authorisation_evidence}</p>
        <p className="why">{c.presence_detail}</p>
      </details>
      {c.issues.length > 0 && (
        <>
          <h4>Issues</h4>
          <ul className="issues">
            {c.issues.map((i) => (
              <IssueRow key={i.id} deal={deal} issue={i} onChanged={onChanged} onEdit={clear} />
            ))}
          </ul>
        </>
      )}
      <FixForm
        key={c.id + c.issues.map((i) => i.state).join()}
        deal={deal}
        commitment={c}
        documents={documents}
        onStart={clear}
        onDone={(text) => {
          setResult({ id: c.id, text });
          onChanged();
        }}
      />
    </article>
  );
}

function Register({ deal, reg, documents, onChanged, result, setResult }) {
  const [selected, setSelected] = useState(null);
  const [scrollTick, setScrollTick] = useState(0);
  const current = reg.commitments.find((c) => c.id === selected) ?? null;
  // Every click scrolls, including a second click on the same row after the reader has scrolled away.
  const pick = (id) => {
    setSelected(id);
    setScrollTick((t) => t + 1);
  };
  useEffect(() => {
    if (!scrollTick) return;
    // Put the card's top near the top of the viewport (16px of air). Two frames, so the card has rendered and
    // laid out; an instant jump, so a re-render cannot cancel a smooth scroll half-way.
    let second;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => {
        const card = document.getElementById("commitment-card");
        if (!card) return;
        window.scrollTo({ top: Math.max(0, card.getBoundingClientRect().top + window.scrollY - 16), behavior: "auto" });
        card.focus({ preventScroll: true });
      });
    });
    return () => {
      cancelAnimationFrame(first);
      if (second) cancelAnimationFrame(second);
    };
  }, [scrollTick]);
  return (
    <section className="panel">
      <h2>Commitments</h2>
      <p className="hint">
        {Object.entries(reg.counts)
          .map(([k, v]) => `${v} ${k.toLowerCase()}`)
          .join(" · ")}
      </p>
      <div className="table-wrap">
        <table className="register">
          <thead>
            <tr>
              <th>Commitment</th>
              <th>What needs attention</th>
              <th>Owner</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {reg.commitments.map((c) => (
              <tr key={c.id} className={c.id === selected ? "selected" : ""} onClick={() => pick(c.id)}>
                <td>
                  <button type="button" className="link">
                    {c.name}
                  </button>
                </td>
                <td>{c.attention.length ? c.attention.join("; ") : "—"}</td>
                <td>{c.owners.join(", ") || "—"}</td>
                <td>
                  <Status value={c.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {current && <CommitmentCard deal={deal} c={current} documents={documents} onChanged={onChanged} result={result} setResult={setResult} />}
    </section>
  );
}

function Workspace({ deal, onDealsChanged }) {
  const [state, setState] = useState({ loading: true });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [result, setResult] = useState(null);  // the last recheck's one-line result, until the next action

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
  const fresh = reg.freshness;
  return (
    <div className="workspace">
      <div className={`banner ${fresh.state === "Up to date" ? "" : "banner-warn"}`}>
        <div>
          <h2 className="deal-title">{reg.name}</h2>
          <p>
            <strong>{fresh.state}</strong>
            {fresh.finished_at ? ` · last review ${fmtDateTime(fresh.finished_at)}` : ""}
          </p>
          <p className="hint">{reg.scope_note}</p>
        </div>
        <button type="button" className="primary" onClick={review} disabled={busy || docs.documents.length === 0}>
          {busy ? "Reviewing…" : "Review deal"}
        </button>
      </div>
      {message && <Notice kind={message.kind}>{message.text}</Notice>}
      {reg.commitments.length > 0 ? (
        <Register deal={deal} reg={reg} documents={docs.documents} onChanged={load} result={result} setResult={setResult} />
      ) : (
        <Notice>No review yet. Add documents, then choose Review deal.</Notice>
      )}
      <Documents deal={deal} data={docs} onChanged={() => { setResult(null); load(); }} startOpen={reg.commitments.length === 0 || docs.documents.length === 0} />
      {reg.commitments.length > 0 && <Handoff deal={deal} reg={reg} />}
      <p className="hint footer-note">{reg.resolved_means}</p>
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
        <h1>Catch deal surprises before you sign.</h1>
        <p className="lead">What was promised, what needs resolving, and whether the fixes close the gaps.</p>
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
