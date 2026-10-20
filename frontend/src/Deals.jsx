// Home screen: deals in handover (16 Oct; design from Google Stitch, screen 1, adapted to real data).
// Visibility only. Every number comes from /api/workspace/deals; there are no invented metrics, statuses or actions.
import Logo from "./Logo.jsx";
import { useMemo, useState } from "react";
import * as api from "./api.js";
import { FILTERS, SORTS, counts, initials, lastVendor, page, relativeTime, rememberVendor, vendorsOf, visibleDeals } from "./deals.js";
import { commitmentsNeedText, dealsText, plainName } from "./dealpage.js";
import CatalogueModal from "./CatalogueModal.jsx";
import { DESCRIPTION, FICTIONAL, TAGLINE } from "./brand.js";
import "./Deals.css";

const Icon = ({ d, size = 16 }) => (
  <svg className="dl-icon" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" fill="none"
       stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
);
const ICONS = {
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
  arrow: "M5 12h14M13 6l6 6-6 6",
  lock: "M7 11V7a5 5 0 0 1 10 0v4M5 11h14v10H5z",
  check: "M5 12l5 5L20 7",
  plus: "M12 5v14M5 12h14",
  box: "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  info: "M12 16v-4M12 8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z",
};

function StagePill({ deal }) {
  if (deal.handover_complete) {
    return (
      <span className="dl-pill dl-pill-frozen">
        <Icon d={ICONS.lock} size={12} /> Handover complete
      </span>
    );
  }
  return (
    <span className={`dl-pill ${deal.stage === "signed" ? "dl-pill-signed" : ""}`}>
      <span className="dl-dot" /> {deal.stage_label}
    </span>
  );
}

function GapPill({ deal }) {
  const noted = deal.addressed_by_note ?? 0;
  if (deal.open_gaps === 0) {
    return (
      <span className="dl-gap dl-gap-none">
        <Icon d={ICONS.check} size={12} /> {commitmentsNeedText(0, noted)}
      </span>
    );
  }
  if (deal.handover_complete) {
    return <span className="dl-gap dl-gap-frozen">{deal.open_gaps} {deal.open_gaps === 1 ? "commitment" : "commitments"} at handover{noted > 0 && <span className="dl-gap-sub">{noted} addressed by note</span>}</span>;
  }
  return (
    <span className="dl-gap">
      <span className="dl-dot" /> {commitmentsNeedText(deal.open_gaps)}
      {noted > 0 && <span className="dl-gap-sub">{noted} addressed by note</span>}
    </span>
  );
}

function NewDeal({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const create = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const { deal } = await api.createDeal(name);
      setName("");
      setOpen(false);
      onCreated(deal);
    } catch (err) {
      setError(err.message);
    }
  };
  if (!open) {
    return (
      <button type="button" className="dl-btn dl-btn-primary" onClick={() => setOpen(true)}>
        <Icon d={ICONS.plus} /> New deal
      </button>
    );
  }
  return (
    <form className="dl-new" onSubmit={create}>
      <input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Customer and deal name"
             aria-label="New deal name" />
      <button type="submit" className="dl-btn dl-btn-primary" disabled={!name.trim()}>Create</button>
      <button type="button" className="dl-btn" onClick={() => setOpen(false)}>Cancel</button>
      {error && <span className="dl-error" role="alert">{error}</span>}
    </form>
  );
}

export default function Deals({ deals, onOpen, onCreated }) {
  const [filter, setFilter] = useState("handover");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("updated");
  const [pageNo, setPageNo] = useState(1);
  const [catalogue, setCatalogue] = useState(false);

  const vendors = useMemo(() => vendorsOf(deals), [deals]);
  const open = (d) => { if (d.vendor) rememberVendor(d.vendor); onOpen(d.deal); }; // the catalogue switch opens on the vendor of the deal opened last
  const n = useMemo(() => counts(deals), [deals]);
  const rows = useMemo(() => visibleDeals(deals, { filter, query, sort }), [deals, filter, query, sort]);
  const shown = page(rows, pageNo);
  const sortLabel = SORTS.find((s) => s.key === sort)?.label.toLowerCase();

  return (
    <div className="dl">
      <header className="dl-brand"><Logo /><span>{TAGLINE}</span></header>
      <section className="dl-head">
        <div>
          <span className="dl-eyebrow">Before signing and at handover</span>
          <div className="dl-title-row">
            <h1>Deal reviews</h1>
            <span className="dl-count">{dealsText(n.handover)}</span>
          </div>
          <p className="dl-sub">{DESCRIPTION}</p>
        </div>
        <div className="dl-actions">
          <button type="button" className="dl-btn" onClick={() => setCatalogue(true)}><Icon d={ICONS.box} size={16} /> Product catalogue</button>
          <NewDeal onCreated={onCreated} />
        </div>
      </section>
      {catalogue && <CatalogueModal vendors={vendors} vendor={lastVendor(vendors)} onClose={() => setCatalogue(false)} onChanged={onCreated ? () => onCreated(null) : undefined} />}

      <section className="dl-bar-row">
        <div className="dl-tabs" role="tablist" aria-label="Filter deals">
          {FILTERS.filter((f) => f.key !== "earlier" || n.earlier > 0).map((f) => (
            <button key={f.key} type="button" role="tab" aria-selected={filter === f.key}
                    className={`dl-tab ${filter === f.key ? "is-active" : ""}`}
                    onClick={() => { setFilter(f.key); setPageNo(1); }}>
              {f.label}
              <span className={`dl-tab-n ${f.key === "open" ? "tone-amber" : ""}`}>{dealsText(n[f.key])}</span>
            </button>
          ))}
        </div>
        <div className="dl-tools">
          <label className="dl-search">
            <Icon d={ICONS.search} />
            <input value={query} onChange={(e) => { setQuery(e.target.value); setPageNo(1); }}
                   placeholder="Search by deal, owner or stage" aria-label="Search deals" />
          </label>
          <label className="dl-sort">
            <span>Sort:</span>
            <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort deals">
              {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </label>
        </div>
      </section>

      <section className="dl-table-card">
        <div className="dl-scroll">
          <table className="dl-table">
            <thead>
              <tr>
                <th scope="col">Deal</th>
                <th scope="col">Commitments needing attention</th>
                <th scope="col">Deal owner</th>
                <th scope="col">Last updated</th>
                <th scope="col" className="dl-right"><span className="dl-sr">Action</span></th>
              </tr>
            </thead>
            <tbody>
              {shown.rows.map((d) => (
                <tr key={d.deal} className={d.handover_complete ? "is-frozen" : ""} onClick={() => open(d)}>
                  <td>
                    <span className="dl-deal-cell">
                      <span className="dl-tile" aria-hidden="true">{initials(d.name)}</span>
                      <span className="dl-deal-text">
                        <span className="dl-deal-name">{d.name}{d.kind === "user" && <span className="dl-tag">Uploaded</span>}</span>
                        {d.scope && <span className="dl-scope-line">{d.scope}</span>}
                        <StagePill deal={d} />
                      </span>
                    </span>
                  </td>
                  <td><GapPill deal={d} /></td>
                  <td>
                    {d.owner ? (
                      <span className="dl-owner">
                        <span className="dl-avatar" aria-hidden="true">{initials(d.owner)}</span>
                        {plainName(d.owner)}
                      </span>
                    ) : (
                      <span className="dl-muted">Not set</span>
                    )}
                  </td>
                  <td>
                    <span className="dl-mono" title={d.last_updated ?? ""}>{relativeTime(d.last_updated)}</span>
                  </td>
                  <td className="dl-right">
                    <button type="button" className={`dl-open ${d.handover_complete ? "is-muted" : ""}`}
                            onClick={(e) => { e.stopPropagation(); open(d); }}>
                      {d.handover_complete ? "Open record" : "Open deal"} <Icon d={ICONS.arrow} size={14} />
                    </button>
                  </td>
                </tr>
              ))}
              {shown.rows.length === 0 && (
                <tr className="dl-empty">
                  <td colSpan={5}>{query ? "No deals match that search." : "No deals here yet."}</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <footer className="dl-foot">
          <span>
            Showing <strong>{shown.rows.length}</strong> of <strong>{dealsText(rows.length)}</strong> · Sorted by {sortLabel}
          </span>
          <span className="dl-scope"><Icon d={ICONS.info} size={14} /> Lists commitments where the customer's expectation, the contract and what we can sell don't line up.</span>
          {shown.pages > 1 && (
            <span className="dl-pager">
              <button type="button" className="dl-btn" disabled={shown.page === 1} onClick={() => setPageNo(shown.page - 1)}>Previous</button>
              <span className="dl-mono">{shown.page} / {shown.pages}</span>
              <button type="button" className="dl-btn" disabled={shown.page === shown.pages} onClick={() => setPageNo(shown.page + 1)}>Next</button>
            </span>
          )}
        </footer>
      </section>
      <footer className="dl-pagefoot">{FICTIONAL}</footer>
    </div>
  );
}
