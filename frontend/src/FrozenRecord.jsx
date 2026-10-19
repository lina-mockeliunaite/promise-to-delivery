// Frozen handover record (16 Oct; reordered 19 Oct). What Delivery inherited,
// read from the snapshot saved when the handover was completed. Nothing here can change, and nothing is recomputed:
// it shows the record as it stood, plus the record's SHA-256 fingerprint so anyone can check it was not edited.
import { useEffect, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import {
  STATUS_CHIP, cleanReason, countsLine, extractedAs, findingDetail, firstPromised, contractText, mismatchLine, plainName, recordedBy, sentence, verdictLine,
} from "./dealpage.js";
import { NAME, TAGLINE } from "./brand.js";
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

// One row per commitment, the same list and wording as the live deal page, read-only. Collapsed it is the title, what did
// not line up, where it was first promised and its status at handover; open shows the detail.
function FrozenRow({ status, title, original, mismatch, first, expanded, onToggle, children }) {
  const st = STATUS_CHIP[status];
  return (
    <li className={`dp-prow is-${status} ${expanded ? "is-open" : ""}`}>
      <div className="dp-prow-head" onClick={onToggle} role="button" tabIndex={0} aria-expanded={expanded}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onToggle())}>
        <span className={`dp-chevron fr-noprint ${expanded ? "is-open" : ""}`} aria-hidden="true">›</span>
        <span className="dp-prow-main">
          <span className="dp-prow-title">{title}</span>
          {mismatch && <span className="dp-prow-line">{mismatch}</span>}
          {first && <span className="dp-prow-first">{first}</span>}
        </span>
        <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
          {status === "open" ? <span className="dp-dot" /> : <Check />}
          {st.label}
        </span>
      </div>
      {expanded && (
        <div className="dp-prow-body">
          {children}
          {original && <span className="dp-fact-src">Extracted as: {original}</span>}
        </div>
      )}
    </li>
  );
}

export default function FrozenRecord({ deal, onBack }) {
  const [hv, setHv] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [record, setRecord] = useState(false);
  const [expanded, setExpanded] = useState(() => new Set());
  const toggle = (k) => setExpanded((prev) => { const n = new Set(prev); n.has(k) ? n.delete(k) : n.add(k); return n; });
  useEffect(() => { api.fetchHandover(deal).then(setHv, (err) => setError(err.message)); }, [deal]);

  if (error) return <div className="dp"><p className="dp-error">{error}</p></div>;
  if (!hv) return <div className="dp"><p className="dp-faint">Loading…</p></div>;
  const s = hv.snapshot;
  const open = s.open_items ?? [];
  const noted = s.resolved_by_note ?? [];
  const resolved = s.resolved ?? [];
  // Owner-confirmed plain titles, matched by the promise name saved in the snapshot and read now; a promise without one
  // keeps its original name. The saved record itself is never changed.
  const titles = hv.display_names ?? {};
  const titled = (promise) => ({ title: titles[promise] || promise, original: titles[promise] && titles[promise] !== promise ? promise : "" });
  // Findings closed by the documents, grouped by promise. A promise still needing attention or addressed by note keeps its
  // own row and shows these inside; a promise whose every gap closed gets a row of its own.
  const closedFor = (promise) => resolved.filter((r) => r.promise === promise);
  const elsewhere = new Set([...open.map((x) => x.promise), ...noted.map((x) => x.promise)]);
  const closedOnly = [...new Set(resolved.map((r) => r.promise))].filter((p) => !elsewhere.has(p));
  const keys = [...open.map((x) => x.promise), ...noted.map((x) => x.promise), ...closedOnly];
  const allOpen = keys.length > 0 && expanded.size === keys.length;
  const printAll = () => { setExpanded(new Set(keys)); setRecord(true); setTimeout(() => window.print(), 80); };
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
  const counts = { open: open.length, noted: noted.length, closed: closedOnly.length };

  return (
    <div className="dp fr">
      <div className="dp-topbar fr-noprint">
        <button type="button" className="dp-back" onClick={onBack}>← All deals</button>
        <button type="button" className="dp-btn" onClick={printAll}>Print or save as PDF</button>
      </div>

      <div className="fr-bar">
        <Lock size={13} /> <span>Handover complete · locked on <strong>{fmtDate(hv.completed_at)}</strong> by <strong>{plainName(hv.completed_by)}</strong></span>
      </div>

      <section className="fr-head">
        <span className="fr-eyebrow">{NAME} · {TAGLINE}</span>
        <h1>{s.deal}: what Delivery inherits</h1>
        <div className="dp-meta">
          <span className="dp-chip dp-chip-grey">Stage at handover: {s.stage}</span>
          {s.brief?.go_live && <span className="dp-meta-strong">Go-live {fmtDate(s.brief.go_live)}</span>}
          <span className="dp-faint">Checked {s.documents.length} documents and the product catalogue · {s.scope_note}</span>
        </div>
      </section>

      {s.brief && (
        <section className="dp-card">
          <div className="dp-sec-head">
            <h2 className="dp-upper">What we're delivering</h2>
            <span className="dp-faint">Confirmed by <strong className="dp-ink">{plainName(s.brief.confirmed_by)}</strong>{s.brief.basis ? ` from ${s.brief.basis}` : ""}</span>
          </div>
          <p className="dp-brief">{s.brief.summary}</p>
          {s.brief.deliverables?.length > 0 && (
            <div className="dp-deliverables">
              {s.brief.deliverables.map((d) => <span key={d}><span className="dp-dot dp-brand-bg" />{d}</span>)}
            </div>
          )}
          {s.brief.needs_reconfirmation && <div className="dp-warn">{s.brief.reconfirm_note}</div>}
        </section>
      )}

      <section className={`fr-verdict ${open.length ? "is-open" : "is-clear"}`}>
        <strong>{verdictLine(counts)}</strong>
      </section>

      <section className="dp-card dp-promises">
        <div className="dp-sec-head">
          <div className="dp-row">
            <h2>Commitments at handover</h2>
            {keys.length > 0 && (
              <button type="button" className="dp-link-btn dp-brand fr-noprint"
                      onClick={() => setExpanded(allOpen ? new Set() : new Set(keys))}>{allOpen ? "Collapse all" : "Expand all"}</button>
            )}
          </div>
          <span className="dp-counts">{countsLine(counts)}</span>
        </div>
        {keys.length === 0 && <p className="dp-faint">No commitment had a gap on the documents checked.</p>}
        <ul className="dp-plist">
          {open.map((it) => {
            const seen = [...new Map(it.findings.flatMap((f) => f.seen ?? []).map((x) => [x.by, x])).values()];
            const t = titled(it.promise);
            return (
              <FrozenRow key={it.promise} status="open" title={t.title} original={t.original}
                         mismatch={mismatchLine(it.findings, it.contract)}
                         first={firstPromised((it.told_in ?? []).map(([label, date]) => ({ doc_type_label: label, date })))}
                         expanded={expanded.has(it.promise)} onToggle={() => toggle(it.promise)}>
                <div className="dp-three">
                  <div className="dp-fact">
                    <span className="dp-fact-label">Customer was told</span>
                    <p>{it.told}</p>
                    {it.told_in?.length > 0 && <span className="dp-fact-src">{toldIn(it.told_in)}</span>}
                  </div>
                  <div className="dp-fact">
                    <span className="dp-fact-label">Contract says</span>
                    <p>{contractText(it.contract)}</p>
                    {it.contract_detail && <span className="dp-fact-src">{it.contract_detail}</span>}
                  </div>
                  <div className="dp-fact dp-fact-found">
                    <span className="dp-fact-label">What we found</span>
                    {it.findings.map((f) => <p key={f.finding} className="dp-finding"><strong>{sentence(findingDetail(f, it.contract))}</strong> {cleanReason(f.why)}</p>)}
                    <span className="dp-fact-src">AI-written summary · the quotes behind it are checked against the documents</span>
                  </div>
                </div>
                {alreadyClosed(it.promise)}
                {[...new Map(it.findings.filter((f) => f.note).map((f) => [`${f.note.by}|${f.note.reason}`, f.note])).values()].map((n) => (
                  <div key={`${n.by}|${n.reason}`} className={`dp-decision ${n.current ? "" : "is-stale"}`}>
                    <span className="dp-kicker">{n.current ? "Note at handover · still needs attention" : "Note at handover · not re-confirmed after the documents changed"}</span>
                    <span>“{n.reason}”</span>
                    <span className="dp-faint dp-small">{recordedBy(n.by, n.at, fmtDate)}</span>
                  </div>
                ))}
                <footer className="dp-gap-foot">
                  <span className="dp-row">
                    <span className="dp-faint">Seen by:</span>
                    {seen.length ? seen.map((x) => <span key={x.by} className="fr-seen">✓ {plainName(x.by)}</span>) : <span className="dp-faint">nobody before handover</span>}
                  </span>
                  <span className="dp-faint dp-row"><Lock size={12} /> Locked</span>
                </footer>
              </FrozenRow>
            );
          })}
          {noted.map((x) => {
            const n = x.findings.find((f) => f.resolved_by_note)?.resolved_by_note;
            const t = titled(x.promise);
            return (
              <FrozenRow key={x.promise} status="noted" title={t.title} original={t.original}
                         mismatch={mismatchLine(x.findings, x.contract)}
                         first={firstPromised((x.quotes ?? []).map((q) => ({ doc_type_label: q.source, date: q.date })))}
                         expanded={expanded.has(x.promise)} onToggle={() => toggle(x.promise)}>
                <div className="dp-three fr-two">
                  <div className="dp-fact"><span className="dp-fact-label">Customer was told</span><p>{x.told}</p></div>
                  <div className="dp-fact"><span className="dp-fact-label">Contract says</span><p>{contractText(x.contract)}</p></div>
                </div>
                {alreadyClosed(x.promise)}
                {n && (
                  <div className="dp-decision is-done is-note">
                    <span className="dp-kicker">Addressed by note · not in the documents · Delivery inherits it on this person's word</span>
                    <span>“{n.reason}”</span>
                    <span className="dp-faint dp-small">{recordedBy(n.by, n.at, fmtDate)}</span>
                  </div>
                )}
              </FrozenRow>
            );
          })}
          {closedOnly.map((p) => {
            const t = titled(p);
            return (
              <FrozenRow key={p} status="closed" title={t.title} original={t.original} expanded={expanded.has(p)} onToggle={() => toggle(p)}>
                {alreadyClosed(p)}
              </FrozenRow>
            );
          })}
        </ul>
      </section>

      <section className="dp-card">
        <div className="dp-sec-head"><h2>Handover notes</h2><span className="dp-chip dp-chip-grey"><Lock size={11} /> Locked</span></div>
        <div className="dp-notes">
          {["sales", "delivery"].map((role) => {
            const note = s.notes?.[role];
            return (
              <div key={role} className="dp-note">
                <div className="dp-note-head">
                  <div>
                    <span className="dp-note-who">{plainName(note?.by) || (role === "sales" ? "Sales" : "Delivery")}</span>
                    <span className="dp-note-role">{note?.label ?? (role === "sales" ? "Deal owner's handoff note" : "Delivery acceptance note")}</span>
                  </div>
                  <Lock />
                </div>
                <p className={`dp-note-text ${note ? "" : "is-empty"}`}>{note ? `“${note.note}”` : "No note."}</p>
                <div className="dp-note-foot"><span>{note ? recordedBy(note.by, note.at, fmtDateTime) : ""}</span></div>
              </div>
            );
          })}
        </div>
      </section>

      <details className="dp-card fr-record" open={record} onToggle={(e) => setRecord(e.currentTarget.open)}>
        <summary>Record details · {s.documents.length} documents at handover and the record fingerprint</summary>
        <div className="fr-record-body">
          <div>
            <span className="dp-side-title">Documents at handover</span>
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
            <div>
              <span className="dp-side-title"><Lock /> Record fingerprint</span>
              <code className="fr-hash" title={hv.fingerprint}>{hv.fingerprint.slice(0, 12)}…{hv.fingerprint.slice(-4)}</code>
              <span className="dp-faint dp-small">
                SHA-256 of the saved record. If anyone edited the record, this would change. It shows the record is unchanged;
                it is not a signature.
              </span>
              <button type="button" className="dp-link-btn fr-noprint" onClick={copy}>{copied ? "Copied" : "Copy full fingerprint"}</button>
            </div>
          )}
        </div>
      </details>

      <footer className="dp-foot"><strong>{NAME}</strong> · {TAGLINE}<br />All companies, people and deals are fictional.</footer>
    </div>
  );
}
