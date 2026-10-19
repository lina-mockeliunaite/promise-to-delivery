// Frozen handover record (16 Oct; design from Google Stitch, screen 3, adapted to real data). What Delivery inherited,
// read from the snapshot saved when the handover was completed. Nothing here can change, and nothing is recomputed:
// it shows the record as it stood, plus the record's SHA-256 fingerprint so anyone can check it was not edited.
import { useEffect, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import { cleanReason } from "./dealpage.js";
import "./DealPage.css";

const Lock = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}><path d="M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z" /></svg>
);

const shortDate = (iso) => fmtDate(iso).replace(/ \d{4}$/, "");
const toldIn = (pairs) => (pairs ?? []).map(([label, date]) => (date ? `${label} (${shortDate(date)})` : label)).join(" · ");
const Check = () => (
  <svg width={12} height={12} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}><path d="M20 6 9 17l-5-5" /></svg>
);

// One row per promise, the same list as the live deal page (17 Oct): collapsed it is the title and its status at
// handover; open shows the detail. Open in amber, resolved by a note outlined, closed by the documents solid green.
const STATUS = {
  open: { chip: "dp-chip-amber", label: (n) => `Open at handover · ${n} ${n === 1 ? "gap" : "gaps"}` },
  noted: { chip: "dp-chip-note", label: () => "Resolved by note", title: "Settled by a named person without a document. Delivery inherits it on that person's word." },
  closed: { chip: "dp-chip-green", label: () => "Closed by documents", title: "The documents at handover no longer show the gap." },
};

function FrozenRow({ status, title, count, expanded, onToggle, children }) {
  const st = STATUS[status];
  return (
    <li className={`dp-prow is-${status} ${expanded ? "is-open" : ""}`}>
      <div className="dp-prow-head" onClick={onToggle} role="button" tabIndex={0} aria-expanded={expanded}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onToggle())}>
        <span className={`dp-chevron fr-noprint ${expanded ? "is-open" : ""}`} aria-hidden="true">›</span>
        <span className="dp-prow-title">{title}</span>
        <span className={`dp-chip ${st.chip}`} title={st.title}>
          {status === "open" ? <span className="dp-dot" /> : <Check />}
          {st.label(count)}
        </span>
      </div>
      {expanded && <div className="dp-prow-body">{children}</div>}
    </li>
  );
}

export default function FrozenRecord({ deal, onBack }) {
  const [hv, setHv] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set());
  const toggle = (k) => setExpanded((prev) => { const n = new Set(prev); n.has(k) ? n.delete(k) : n.add(k); return n; });
  useEffect(() => { api.fetchHandover(deal).then(setHv, (err) => setError(err.message)); }, [deal]);

  if (error) return <div className="dp"><p className="dp-error">{error}</p></div>;
  if (!hv) return <div className="dp"><p className="dp-faint">Loading…</p></div>;
  const s = hv.snapshot;
  const open = s.open_items ?? [];
  const noted = s.resolved_by_note ?? [];
  const resolved = s.resolved ?? [];
  // Findings closed by the documents, grouped by promise. A promise still open or resolved by a note keeps its own row
  // and shows these inside; a promise whose every gap closed gets a row of its own.
  const closedFor = (promise) => resolved.filter((r) => r.promise === promise);
  const elsewhere = new Set([...open.map((x) => x.promise), ...noted.map((x) => x.promise)]);
  const closedOnly = [...new Set(resolved.map((r) => r.promise))].filter((p) => !elsewhere.has(p));
  const keys = [...open.map((x) => x.promise), ...noted.map((x) => x.promise), ...closedOnly];
  const allOpen = keys.length > 0 && expanded.size === keys.length;
  const printAll = () => { setExpanded(new Set(keys)); setTimeout(() => window.print(), 80); };
  const alreadyClosed = (promise) => closedFor(promise).length > 0 && (
    <div className="dp-decision is-done">
      <span className="dp-kicker">Closed by the documents before handover</span>
      {closedFor(promise).map((r) => <span key={r.finding}><strong>{r.finding}.</strong> {r.resolved_by}</span>)}
    </div>
  );
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(hv.fingerprint);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="dp fr">
      <div className="dp-topbar fr-noprint">
        <button type="button" className="dp-back" onClick={onBack}>← All deals</button>
        <button type="button" className="dp-btn" onClick={printAll}>Print or save as PDF</button>
      </div>

      <div className="fr-bar">
        <span className="fr-tag"><Lock size={12} /> Frozen record</span>
        <span>Handover complete · frozen on <strong>{fmtDateTime(hv.completed_at)}</strong> by <strong>{hv.completed_by}</strong> · this record does not change</span>
      </div>

      <section className="fr-head">
        <span className="fr-eyebrow">Handover record · for Delivery, Customer Success and Support</span>
        <h1>{s.deal} — what Delivery inherits</h1>
        <div className="dp-meta">
          <span className="dp-chip dp-chip-grey">Stage at handover: {s.stage}</span>
          {s.brief?.go_live && <span className="dp-meta-strong">Go-live {fmtDate(s.brief.go_live)}</span>}
          <span className="dp-faint">Fictional deal · {s.scope_note}</span>
        </div>
      </section>

      <section className={`fr-verdict ${open.length ? "is-open" : "is-clear"}`}>
        <strong>
          {open.length
            ? `Handed over with ${open.length} ${open.length === 1 ? "promise" : "promises"} still open. Delivery inherits ${open.length === 1 ? "this gap" : "these gaps"}.`
            : "Handed over with no open gaps on the documents checked."}
        </strong>
        <div className="fr-scope">
          <span>Checked: <strong>{s.documents.length} documents</strong> and the product catalogue</span>
          <span>Scope: promises with gaps, not every commitment</span>
        </div>
      </section>

      <div className="dp-grid">
        <main className="dp-main">
          <section className="dp-card dp-promises">
            <div className="dp-sec-head">
              <div className="dp-row">
                <h2>Promises at handover</h2>
                {open.length > 0 && <span className="dp-chip dp-chip-amber"><span className="dp-dot" />{open.length} open</span>}
                {noted.length + closedOnly.length > 0 && <span className="dp-chip dp-chip-green"><Check />{noted.length + closedOnly.length} resolved</span>}
                {keys.length > 0 && (
                  <button type="button" className="dp-link-btn dp-brand fr-noprint"
                          onClick={() => setExpanded(allOpen ? new Set() : new Set(keys))}>{allOpen ? "Collapse all" : "Expand all"}</button>
                )}
              </div>
              <span className="dp-faint dp-small">As they stood when the handover was completed.</span>
            </div>
            {keys.length === 0 && <p className="dp-faint">No promise had a gap on the documents checked.</p>}
            <ul className="dp-plist">
              {open.map((it) => {
                const seen = [...new Map(it.findings.flatMap((f) => f.seen ?? []).map((x) => [x.by, x])).values()];
                return (
                  <FrozenRow key={it.promise} status="open" title={it.promise} count={it.findings.length}
                             expanded={expanded.has(it.promise)} onToggle={() => toggle(it.promise)}>
                    <span className="dp-kicker">{it.findings.map((f) => f.finding).join(" · ")}</span>
                    <div className="dp-three">
                      <div className="dp-fact">
                        <span className="dp-fact-label">Customer was told</span>
                        <p>{it.told}</p>
                        {it.told_in?.length > 0 && <span className="dp-fact-src">{toldIn(it.told_in)}</span>}
                      </div>
                      <div className="dp-fact">
                        <span className="dp-fact-label">Contract says</span>
                        <p>{it.contract}</p>
                        {it.contract_detail && <span className="dp-fact-src">{it.contract_detail}</span>}
                      </div>
                      <div className="dp-fact dp-fact-found">
                        <span className="dp-fact-label">What we found</span>
                        {it.findings.map((f) => <p key={f.finding} className="dp-finding"><strong>{f.finding}.</strong> {cleanReason(f.why)}</p>)}
                        <span className="dp-fact-src">AI-written summary · the quotes behind it are checked against the documents</span>
                      </div>
                    </div>
                    {alreadyClosed(it.promise)}
                    {[...new Map(it.findings.filter((f) => f.note).map((f) => [`${f.note.by}|${f.note.reason}`, f.note])).values()].map((n) => (
                      <div key={`${n.by}|${n.reason}`} className={`dp-decision ${n.current ? "" : "is-stale"}`}>
                        <span className="dp-kicker">{n.current ? "Note at handover · gap still open" : "Note at handover · not re-confirmed after the documents changed"}</span>
                        <span><strong>{n.by}:</strong> {n.reason}</span>
                      </div>
                    ))}
                    <footer className="dp-gap-foot">
                      <span className="dp-row">
                        <span className="dp-faint">Seen by:</span>
                        {seen.length ? seen.map((x) => <span key={x.by} className="fr-seen">✓ {x.by}</span>) : <span className="dp-faint">nobody before handover</span>}
                      </span>
                      <span className="dp-faint dp-row"><Lock size={12} /> Frozen</span>
                    </footer>
                  </FrozenRow>
                );
              })}
              {noted.map((x) => {
                const n = x.findings.find((f) => f.resolved_by_note)?.resolved_by_note;
                return (
                  <FrozenRow key={x.promise} status="noted" title={x.promise}
                             expanded={expanded.has(x.promise)} onToggle={() => toggle(x.promise)}>
                    <span className="dp-kicker">{x.findings.map((f) => f.finding).join(" · ")}</span>
                    <div className="dp-three fr-two">
                      <div className="dp-fact"><span className="dp-fact-label">Customer was told</span><p>{x.told}</p></div>
                      <div className="dp-fact"><span className="dp-fact-label">Contract says</span><p>{x.contract}</p></div>
                    </div>
                    {alreadyClosed(x.promise)}
                    {n && (
                      <div className="dp-decision is-done is-note">
                        <span className="dp-kicker">Resolved by a note · not in the documents · Delivery inherits it on this person's word</span>
                        <span><strong>{n.by}</strong> · {fmtDateTime(n.at)}: “{n.reason}”</span>
                      </div>
                    )}
                  </FrozenRow>
                );
              })}
              {closedOnly.map((p) => (
                <FrozenRow key={p} status="closed" title={p} expanded={expanded.has(p)} onToggle={() => toggle(p)}>
                  {alreadyClosed(p)}
                </FrozenRow>
              ))}
            </ul>
          </section>

          <section className="dp-card">
            <div className="dp-sec-head"><h2>Handover notes</h2><span className="dp-chip dp-chip-grey"><Lock size={11} /> Frozen</span></div>
            <div className="dp-notes">
              {["sales", "delivery"].map((role) => {
                const note = s.notes?.[role];
                return (
                  <div key={role} className="dp-note">
                    <div className="dp-note-head">
                      <div>
                        <span className="dp-note-who">{note?.by ?? (role === "sales" ? "Sales" : "Delivery")}</span>
                        <span className="dp-note-role">{note?.label ?? (role === "sales" ? "Deal owner's handoff note" : "Delivery acceptance note")}</span>
                      </div>
                      <Lock />
                    </div>
                    <p className={`dp-note-text ${note ? "" : "is-empty"}`}>{note ? `“${note.note}”` : "No note."}</p>
                    <div className="dp-note-foot"><span>{note ? fmtDateTime(note.at) : ""}</span></div>
                  </div>
                );
              })}
            </div>
          </section>
        </main>

        <aside className="dp-aside">
          {s.brief && (
            <div className="dp-card dp-side">
              <span className="dp-side-title">The deal in brief</span>
              <p className="dp-brief fr-small">{s.brief.summary}</p>
              {s.brief.deliverables?.length > 0 && (
                <ul className="fr-deliv">{s.brief.deliverables.map((d) => <li key={d}>{d}</li>)}</ul>
              )}
              <span className="dp-faint dp-small">Confirmed by {s.brief.confirmed_by}{s.brief.basis ? ` from ${s.brief.basis}` : ""}</span>
              {s.brief.needs_reconfirmation && <div className="dp-warn">{s.brief.reconfirm_note}</div>}
            </div>
          )}

          <div className="dp-card dp-side">
            <div className="dp-side-head"><span className="dp-side-title">Documents at handover</span><span className="dp-count">{s.documents.length}</span></div>
            <ul className="dp-docs">
              {s.documents.map((d) => (
                <li key={`${d.name}|${d.version}`}>
                  <div className="dp-doc-row">
                    {d.link
                      ? <a className="dp-doc-name" href={d.link} target="_blank" rel="noopener noreferrer">{d.name}{d.version > 1 ? ` · v${d.version}` : ""} ↗</a>
                      : <span className="dp-doc-name fr-plain">{d.name}{d.version > 1 ? ` · v${d.version}` : ""}</span>}
                    <span className="dp-mono">{shortDate(d.date)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {hv.fingerprint && (
            <div className="dp-card dp-side">
              <span className="dp-side-title"><Lock /> Record fingerprint</span>
              <code className="fr-hash" title={hv.fingerprint}>{hv.fingerprint.slice(0, 12)}…{hv.fingerprint.slice(-4)}</code>
              <span className="dp-faint dp-small">
                SHA-256 of the saved record. If anyone edited the record, this would change. It shows the record is unchanged;
                it is not a signature.
              </span>
              <button type="button" className="dp-link-btn fr-noprint" onClick={copy}>{copied ? "Copied" : "Copy full fingerprint"}</button>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
