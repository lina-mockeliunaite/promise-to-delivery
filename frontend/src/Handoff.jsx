import { useCallback, useEffect, useState } from "react";
import * as api from "./api.js";
import { fmtDate } from "./format.js";

const DECISIONS = [
  { value: "ready", label: "Ready for handoff", hint: "Only when no issue is open." },
  { value: "proceed", label: "Proceed with open items", hint: "Confirm the owner of each open issue." },
  { value: "not_ready", label: "Not ready", hint: "" },
];

function Notice({ kind = "info", children }) {
  return (
    <div className={`notice notice-${kind}`} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

const ownerText = (item) => `${item.owner} (${item.owner_basis})`;

function SaveForm({ deal, reg, onSaved }) {
  const open = reg.commitments.flatMap((c) => c.issues.filter((i) => i.state !== "Resolved").map((i) => ({ ...i, commitment: c.name })));
  const fresh = reg.freshness;
  const [form, setForm] = useState({ decision: "not_ready", reviewer: "", note: "" });
  const [confirmed, setConfirmed] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const toggle = (id) => setConfirmed(confirmed.includes(id) ? confirmed.filter((x) => x !== id) : [...confirmed, id]);

  const blocked =
    fresh.state === "Not reviewed"
      ? "Run the review before saving the handoff"
      : fresh.state === "Review out of date"
        ? "Rerun the review before saving the handoff"
        : null;
  const readyBlocked = form.decision === "ready" && open.length > 0;
  const proceedBlocked = form.decision === "proceed" && open.some((i) => !confirmed.includes(i.id));

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { version } = await api.saveHandoff(deal, {
        decision: form.decision,
        reviewer: form.reviewer,
        note: form.note,
        confirmed_issue_ids: confirmed,
        review_id: fresh.review_id,
      });
      setConfirmed([]);
      setForm({ ...form, note: "" });
      onSaved(version);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="grid-form">
      <h4>Save a handoff</h4>
      {blocked && <Notice kind="error">{blocked}.</Notice>}
      <fieldset>
        <legend>Reviewer decision</legend>
        {DECISIONS.map((d) => (
          <label key={d.value} className="check">
            <input type="radio" name="decision" value={d.value} checked={form.decision === d.value} onChange={set("decision")} /> {d.label}
            {d.hint && <span className="hint"> {d.hint}</span>}
          </label>
        ))}
      </fieldset>
      {form.decision === "proceed" && open.length > 0 && (
        <fieldset>
          <legend>Confirm the owner of each open issue</legend>
          {open.map((i) => (
            <label key={i.id} className="check">
              <input type="checkbox" checked={confirmed.includes(i.id)} onChange={() => toggle(i.id)} />
              <span>
                {i.commitment}: {i.label} — owner <strong>{i.owner}</strong>
              </span>
            </label>
          ))}
        </fieldset>
      )}
      {readyBlocked && <Notice>Ready for handoff isn't possible while {open.length} issue(s) are open.</Notice>}
      <label>
        Reviewer
        <input value={form.reviewer} onChange={set("reviewer")} required />
      </label>
      <label className="wide">
        Note
        <textarea value={form.note} onChange={set("note")} rows={2} />
      </label>
      <button type="submit" className="primary" disabled={busy || !!blocked || readyBlocked || proceedBlocked || !form.reviewer.trim()}>
        {busy ? "Saving…" : "Save handoff"}
      </button>
      <p className="hint wide">Saving never changes an issue. Each save is a new version; earlier versions stay as they were.</p>
      {error && <Notice kind="error">{error}</Notice>}
    </form>
  );
}

function View({ deal, version, data }) {
  const h = data.handoff;
  const openItems = h.issues.filter((i) => i.open);
  return (
    <div className="handoff-view">
      <header className="handoff-head">
        <h3>
          {h.deal}: {h.decision.label}
        </h3>
        <p>
          Version {version} · reviewed by {h.decision.reviewer} on {fmtDate(h.decision.date)} · review date {fmtDate(h.review_date)} · review {h.freshness.toLowerCase()} when saved
        </p>
        <p className="hint">{h.scope_note}</p>
        {h.decision.note && <p>{h.decision.note}</p>}
        {data.changed_since_saved && <Notice kind="info">The deal has changed since this version was saved. Review again and save a new version to bring it up to date.</Notice>}
        <p>
          <a href={api.handoffCsvUrl(deal, version)}>Download CSV</a> ·{" "}
          <a href={api.handoffSummaryUrl(deal, version)} target="_blank" rel="noreferrer">
            Open readable summary
          </a>{" "}
          <span className="hint">(print it and choose Save as PDF)</span>
        </p>
      </header>

      <h4>Open items ({openItems.length})</h4>
      {openItems.length === 0 && <p className="hint">No open items.</p>}
      <ul className="issues">
        {openItems.map((i, n) => (
          <li key={n} className="issue">
            <div className="issue-head">
              <strong>{i.commitment}</strong> <span className="status s-action">{i.attention}</span> <span className="tag">{i.state}</span>
            </div>
            {i.why && <p className="why">{i.why}</p>}
            <p>Owner: {ownerText(i)}</p>
            {i.next_step && <p className="next">Next: {i.next_step}</p>}
            {i.note && <p>Note: {i.note}</p>}
            {i.evidence.map((e, k) => (
              <div key={k}>
                <blockquote>“{e.quote}”</blockquote>
                <cite>
                  {e.source}, version {e.version}
                  {e.page ? `, page ${e.page}` : ""}
                </cite>
              </div>
            ))}
          </li>
        ))}
      </ul>

      <h4>All commitments</h4>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Promise</th>
              <th>Status</th>
              <th>In the contract</th>
            </tr>
          </thead>
          <tbody>
            {h.commitments.map((c, n) => (
              <tr key={n}>
                <td>{c.promise}</td>
                <td>{c.status}</td>
                <td>{c.contract}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {h.commitments.some((c) => c.check_note) && <p className="hint">{h.commitments.find((c) => c.check_note).check_note}</p>}

      <h4>Approved exceptions</h4>
      {h.exceptions.length === 0 && <p className="hint">None.</p>}
      {h.exceptions.map((x, n) => (
        <p key={n}>
          <strong>{x.commitment}</strong>
          <br />
          <span className="why">{x.evidence}</span>
        </p>
      ))}

      <h4>Fix and decision history</h4>
      {h.history.length === 0 && <p className="hint">No fixes recorded.</p>}
      {h.history.map((f, n) => (
        <p key={n}>
          <strong>{f.route}</strong> · {f.owner} · {fmtDate(f.date)} · signed off by {f.approved_by}
          <br />
          {f.rationale}
          <br />
          <span className="why">
            Addresses: {f.addresses.join("; ") || "none"}. Evidence: {f.evidence.map((e) => `${e.source}, version ${e.version} (${e.where})`).join("; ") || "none"}
          </span>
        </p>
      ))}

      <h4>Reviewed sources</h4>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Document</th>
              <th>Version</th>
              <th>Date</th>
              <th>Used</th>
            </tr>
          </thead>
          <tbody>
            {h.sources.map((s, n) => (
              <tr key={n}>
                <td>{s.document}</td>
                <td>{s.version}</td>
                <td className="nowrap">{fmtDate(s.date)}</td>
                <td>{s.included ? "Included" : "Excluded"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Handoff({ deal, reg }) {
  const [versions, setVersions] = useState([]);
  const [picked, setPicked] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const loadList = useCallback(
    async (select) => {
      try {
        const { versions: list } = await api.fetchHandoffs(deal);
        setVersions(list);
        setPicked(select ?? list[0]?.version ?? null);
      } catch (err) {
        setError(err.message);
      }
    },
    [deal],
  );
  // Reload when the review changes, so "changed since saved" stays honest.
  useEffect(() => {
    loadList();
  }, [loadList, reg.freshness.state, reg.freshness.review_id]);
  useEffect(() => {
    if (picked == null) return setData(null);
    api.fetchHandoff(deal, picked).then(setData, (err) => setError(err.message));
  }, [deal, picked, versions]);

  return (
    <section className="panel">
      <h2>Handoff</h2>
      <p className="hint">For Delivery, Customer Success and Support: what was promised, what is still open, and who owns it.</p>
      {error && <Notice kind="error">{error}</Notice>}
      <SaveForm deal={deal} reg={reg} onSaved={(v) => loadList(v)} />
      {versions.length > 0 && (
        <>
          <label className="version-pick">
            Saved version
            <select value={picked ?? ""} onChange={(e) => setPicked(Number(e.target.value))}>
              {versions.map((v) => (
                <option key={v.version} value={v.version}>
                  Version {v.version} · {v.decision} · {v.reviewer}, {fmtDate(v.date)}
                  {v.changed_since_saved ? " · deal has changed since" : ""}
                </option>
              ))}
            </select>
          </label>
          {data && <View deal={deal} version={picked} data={data} />}
        </>
      )}
      {versions.length === 0 && <Notice>No handoff saved yet.</Notice>}
    </section>
  );
}
