// Frozen handover record (16 Oct; reordered 19 Oct). What Delivery inherited,
// read from the snapshot saved when the handover was completed. Nothing here can change, and nothing is recomputed:
// it shows the record as it stood, plus the record's SHA-256 fingerprint so anyone can check it was not edited.
import { BrandBlock } from "./Logo.jsx";
import { useEffect, useMemo, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import {
  STATUS_CHIP, attentionText, coverageLine, frozenView, hashFor, plainName, readHash, recordedBy, short, verdictLine,
} from "./dealpage.js";
import { Drawer, CommitmentView, DocumentView, MismatchSentence, TitleLine, Icon, ICON } from "./Drawer.jsx";
import BriefCard from "./BriefCard.jsx";
import { appendixEntries, hasStoredText, shortHash } from "./docHash.js";
import { IdentityLine, useScrolledPast } from "./Identity.jsx";
import { FICTIONAL } from "./brand.js";
import "./DealPage.css";

const Lock = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2"
       strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}><path d="M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z" /></svg>
);

const shortDate = (iso) => fmtDate(iso).replace(/ \d{4}$/, "");
const Check = () => (
  <svg width={12} height={12} viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.5"
       strokeLinecap="round" strokeLinejoin="round" style={{ flex: "none" }}><path d="M20 6 9 17l-5-5" /></svg>
);

// One row per commitment, the same list and wording as the live deal page, read-only. Click opens the drawer (no actions).
// In print every commitment is written out inline instead, since the drawer is not printed.
function FrozenRow({ v, active, onOpen }) {
  const st = STATUS_CHIP[v.status];
  return (
    <li className={`dp-prow is-${v.status} ${active ? "is-active" : ""}`}>
      <div className="dp-prow-head" onClick={onOpen} role="button" tabIndex={0} aria-haspopup="dialog" aria-expanded={active}
           onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), onOpen())}>
        <span className="dp-prow-main">
          <TitleLine title={v.title} labels={v.status !== "closed" ? v.badges : []} />
          {v.status !== "closed" && <MismatchSentence parts={v.mismatch} />}
          {v.first && <span className="dp-prow-first">{v.first}</span>}
          {v.status === "closed" && v.closedLines.map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
          {v.status === "closed" && v.signedLines.map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
          {v.status !== "closed" && v.reopenedLines.map((l) => <span key={l} className="dp-prow-note">{l}</span>)}
        </span>
        <span className={`dp-chip dp-chip-${st.tone}`} title={st.title}>
          <span className={`dp-dot ${v.status === "noted" ? "dp-dot-grey" : v.status === "closed" ? "dp-dot-green" : ""}`} />
          {st.label}
        </span>
        <span className="dp-chevron fr-noprint" aria-hidden="true"><Icon d={ICON.chevron} size={16} /></span>
      </div>
      <PrintDetail v={v} />
    </li>
  );
}

// The commitment written out for print: the plain mismatch line, what the customer was told, the contract, what was found.
function PrintDetail({ v }) {
  return (
    <div className="fr-print">
      {v.plain && <p>{v.plain}</p>}
      {v.extracted && <p className="dp-muted-line">Extracted as: {v.extracted}</p>}
      <p><strong>Customer was told:</strong>{" "}
        {v.told.length ? v.told.map((t) => `“${t.quote}” (${t.label}${t.date ? `, ${short(t.date)}` : ""})`).join(" ") : v.toldFallback}</p>
      <p><strong>Contract says:</strong>{v.contract.text ? ` ${v.contract.text}` : ""}{v.contract.quote ? ` “${v.contract.quote.quote}” (${v.contract.quote.label})` : ""}
        {v.contract.now ? ` Contract wording containing “${v.contract.now.target}”: “${v.contract.now.quote}” (${v.contract.now.label}), a lookup in the current documents.` : ""}</p>
      {v.found.map((f) => <p key={f.label}><strong>{f.label}</strong>{f.fact ? ` ${f.fact}` : ""}</p>)}
      {v.closed.map((c) => <p key={c.label}><strong>{c.gap.headline}</strong>{c.gap.notes.length ? ` ${c.gap.notes.map((n) => `${n}.`).join(" ")}` : ""}</p>)}
      {v.closed.length > 0 && v.signedLines?.length > 0 && <p>{v.signedLines.join(" ")}</p>}
      {v.reopenedLines?.length > 0 && <p><strong>Signed paperwork:</strong> {v.reopenedLines.join(" ")}</p>}
      {v.ai.length > 0 && <p><em>AI-written summary · quotes checked against the supplied documents:</em> {v.ai.join(" ")}</p>}
      {v.notes.map((n) => <p key={`${n.by}|${n.text}`}><strong>{recordedBy(n.by, n.at, fmtDate)}:</strong> “{n.text}”</p>)}
    </div>
  );
}

export default function FrozenRecord({ deal, onBack }) {
  const [hv, setHv] = useState(null);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);
  const [record, setRecord] = useState(false);
  const [headRef, headerGone] = useScrolledPast();
  const [documents, setDocuments] = useState([]);
  const [drawer, setDrawer] = useState(null); // { type: "commitment", key } | { type: "doc", docKey, quote, fromKey } | { type: "record-doc", id }
  const [withText, setWithText] = useState(false); // "Include full document text" in print (off by default)
  const [texts, setTexts] = useState({}); // { version id: text as read }, fetched when the box is ticked
  useEffect(() => { api.fetchHandover(deal).then(setHv, (err) => setError(err.message)); }, [deal]);
  const snapDocs = hv?.snapshot?.documents;
  useEffect(() => {
    if (!withText || !snapDocs) return;
    for (const d of snapDocs.filter(hasStoredText)) {
      api.fetchDocumentText(deal, d.source_version_id).then((r) => setTexts((t) => ({ ...t, [d.source_version_id]: r.text })), () => {});
    }
  }, [withText, snapDocs, deal]);
  useEffect(() => { api.fetchDocuments(deal).then((r) => setDocuments(r.documents), () => setDocuments([])); }, [deal]);
  useEffect(() => {
    const { c } = readHash(window.location.hash);
    if (c) setDrawer({ type: "commitment", key: c });
    else window.history.replaceState(null, "", hashFor({ d: deal }));
  }, [deal]);
  const writeHash = (key) => window.history.replaceState(null, "", hashFor({ d: deal, c: key }));
  useEffect(() => {
    const onHash = () => { const { c } = readHash(window.location.hash); setDrawer((cur) => (c ? { type: "commitment", key: c } : cur?.type === "commitment" ? null : cur)); };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

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
  const views = [
    ...open.map((item) => frozenView({ item, status: "open", closedFindings: closedFor(item.promise), documents, titles })),
    ...noted.map((item) => frozenView({ item, status: "noted", closedFindings: closedFor(item.promise), documents, titles })),
    ...closedOnly.map((p) => frozenView({ item: { promise: p, findings: [], ...(s.closed_items ?? []).find((x) => x.promise === p) }, status: "closed", closedFindings: closedFor(p), documents, titles })),
  ];
  const active = drawer ? views.find((v) => v.key === (drawer.key ?? drawer.fromKey)) : null;
  const appendix = withText ? appendixEntries(s.documents, texts) : [];
  const printAll = () => { setRecord(true); setTimeout(() => window.print(), 80); };
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
      <div className="fr-ident" aria-hidden={!headerGone}>
        <IdentityLine name={s.deal} stage={`Stage: ${s.stage}`} goLive={s.brief?.go_live} show={headerGone} />
      </div>
      <div className="dp-topbar">
        <BrandBlock className="dp-brandline" />
        <span className="dp-row fr-noprint">
          <button type="button" className="dp-back" onClick={onBack}>← All deals</button>
          {s.documents.some(hasStoredText) && (
            <label className="fr-withtext">
              <input type="checkbox" checked={withText} onChange={(e) => setWithText(e.target.checked)} /> Include full document text
            </label>
          )}
          <button type="button" className="dp-btn" onClick={printAll} disabled={withText && appendix.some((a) => a.text === null)}>Print or save as PDF</button>
        </span>
      </div>

      <div className="fr-bar">
        <Lock size={14} /> <span>Handover complete · locked on <strong>{fmtDate(hv.completed_at)}</strong> by <strong>{plainName(hv.completed_by)}</strong></span>
      </div>

      <section className="dp-card fr-head" ref={headRef}>
        <span className="fr-eyebrow">Handover record · for Delivery, Customer Success and Support</span>
        <h1>{s.deal}: what Delivery inherits</h1>
        <div className="fr-pills">
          <span className="dp-stage-pill">Stage: {s.stage}</span>
          {s.brief?.go_live && <span className="dp-meta-strong">Target go-live: {fmtDate(s.brief.go_live)}</span>}
          {hv.owner && <span className="dp-meta-strong">Deal owner: {plainName(hv.owner)}</span>}
        </div>
        <p className="dp-faint dp-small fr-checked">Checked {s.documents.length} documents and the product catalogue · {s.scope_note}</p>
        <div className={`fr-verdict ${open.length ? "is-open" : "is-clear"}`}>
          <strong>{verdictLine(counts)}</strong>
          <div className="fr-chips">
            <span className="dp-chip dp-chip-amber"><span className="dp-dot" />{counts.open} needing attention</span>
            <span className="dp-chip dp-chip-note"><span className="dp-dot dp-dot-grey" />{counts.noted} addressed by note</span>
            <span className="dp-chip dp-chip-green"><Check />{counts.closed} closed by documents</span>
          </div>
        </div>
      </section>

      <section className={`dp-card dp-promises ${counts.open ? "is-attention" : "is-clear"}`}>
        <div className="dp-sec-head">
          <div className="dp-sec-title">
            <h2>Commitments at handover</h2>
            <span className={`dp-chip ${counts.open ? "dp-chip-amber" : "dp-chip-grey"}`}>
              <span className={`dp-dot ${counts.open ? "" : "dp-dot-grey"}`} />
              {attentionText(counts.open, counts.noted)}
            </span>
          </div>
        </div>
        {coverageLine(s.check_coverage?.rejected) && <p className="dp-coverage">{coverageLine(s.check_coverage.rejected)}</p>}
        {views.length === 0 && <p className="dp-faint dp-pad">No commitment had a gap on the documents checked.</p>}
        <ul className="dp-plist">
          {views.map((v) => (
            <FrozenRow key={v.key} v={v} active={active?.key === v.key}
                       onOpen={() => { setDrawer({ type: "commitment", key: v.key }); writeHash(v.key); }} />
          ))}
        </ul>
      </section>

      <BriefCard brief={s.brief} />

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
              {s.documents.map((d) => {
                const name = `${d.name}${d.version > 1 ? ` · v${d.version}` : ""}`;
                const stored = hasStoredText(d);
                return (
                  <li key={`${d.name}|${d.version}`}>
                    <div className="dp-doc-row">
                      {stored
                        ? <button type="button" className="dp-doc-name dp-link-btn" onClick={() => setDrawer({ type: "record-doc", id: d.source_version_id })}
                                  aria-haspopup="dialog" title="Opens the exact text read at handover">{name}</button>
                        : d.link
                          ? <a className="dp-doc-name" href={d.link} target="_blank" rel="noopener noreferrer">{name} ↗</a>
                          : <span className="dp-doc-name fr-plain">{name}</span>}
                      <span className="dp-mono">{shortDate(d.version_date || d.date)}</span>
                    </div>
                    {stored && (
                      <div className="dp-doc-row fr-doc-hash">
                        <code className="fr-hash" title={d.sha256}>SHA-256 <span className="fr-h-short">{shortHash(d.sha256)}</span><span className="fr-h-full">{d.sha256}</span></code>
                        {d.link && <a className="fr-noprint" href={d.link} target="_blank" rel="noopener noreferrer">Open in Drive ↗</a>}
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
          {hv.fingerprint && (
            <div>
              <span className="dp-side-title"><Lock /> Record fingerprint</span>
              <code className="fr-hash" title={hv.fingerprint}><span className="fr-h-short">{hv.fingerprint.slice(0, 12)}…{hv.fingerprint.slice(-4)}</span><span className="fr-h-full">{hv.fingerprint}</span></code>
              <span className="dp-faint dp-small">
                SHA-256 of the saved record. If anyone edited the record, this would change. It shows the record is unchanged;
                it is not a signature.
              </span>
              <button type="button" className="dp-link-btn fr-noprint" onClick={copy}>{copied ? "Copied" : "Copy full fingerprint"}</button>
            </div>
          )}
        </div>
      </details>

      <footer className="dp-foot">Lists commitments where the customer's expectation, the contract and what we can sell don't line up. {FICTIONAL}</footer>

      {appendix.length > 0 && (
        <div className="fr-appendix" data-testid="appendix">
          {appendix.map((a) => (
            <section key={a.key} className="fr-appendix-doc">
              <h2>{a.name}{a.version > 1 ? ` · v${a.version}` : ""}</h2>
              <p>Version {a.version} · {fmtDate(a.date)} · SHA-256 <code>{a.sha256}</code></p>
              <pre>{a.text}</pre>
            </section>
          ))}
        </div>
      )}

      {drawer && (
        <Drawer labelledBy="dr-title" flush onClose={() => { setDrawer(null); writeHash(null); }} focusKey={`${drawer.type}:${drawer.key ?? drawer.docKey ?? ""}`}>
          {drawer.type === "commitment" && active && (
            <CommitmentView v={active} titleId="dr-title" readOnly onClose={() => { setDrawer(null); writeHash(null); }}
                            onOpenDoc={(doc, quote) => doc && setDrawer({ type: "doc", docKey: doc.source_key, quote, fromKey: active.key })} />
          )}
          {drawer.type === "record-doc" && s.documents.find((d) => d.source_version_id === drawer.id) && (
            <DocumentView deal={deal} doc={s.documents.find((d) => d.source_version_id === drawer.id)} titleId="dr-title"
                          onClose={() => setDrawer(null)} />
          )}
          {drawer.type === "doc" && documents.find((d) => d.source_key === drawer.docKey) && (
            <DocumentView deal={deal} doc={documents.find((d) => d.source_key === drawer.docKey)} quote={drawer.quote} titleId="dr-title"
                          backLabel="Back to commitment" onBack={() => setDrawer({ type: "commitment", key: drawer.fromKey })}
                          onClose={() => { setDrawer(null); writeHash(null); }} />
          )}
        </Drawer>
      )}
    </div>
  );
}
