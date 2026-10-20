// Product catalogue pop-up (16 Oct). What Elva can sell, where, with which limits: the authority every check uses.
// Opens from the deal list, the deal page, or a finding (focused on the entry the finding cites). New capabilities can
// be added; existing ones cannot be edited here. An addition changes what every deal is checked against.
import { useEffect, useMemo, useRef, useState } from "react";
import * as api from "./api.js";
import { fmtDate, fmtDateTime } from "./format.js";
import { useName } from "./dealpage.js";
import "./Catalogue.css";

// 20 Oct: green is reserved for "Closed by documents" and amber for commitments, so the catalogue's status and sale-type
// chips are all neutral and told apart by their text.

function AddForm({ data, onAdded, onCancel }) {
  const [name, setName] = useName();
  const [form, setForm] = useState({ name: "", regions: [], other: "", status: "beta", sellable: "requires_named_approval",
    roadmap_date: "", limit_name: "", limit_value: "", integrations: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const toggle = (r) => setForm((f) => ({ ...f, regions: f.regions.includes(r) ? f.regions.filter((x) => x !== r) : [...f.regions, r] }));
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const other = form.other.trim().toUpperCase();
    try {
      const { capability } = await api.addCapability({
        name: form.name, regions: [...form.regions, ...(other ? [other] : [])], status: form.status, sellable: form.sellable,
        roadmap_date: form.status === "generally_available" ? null : form.roadmap_date || null,
        limit_name: form.limit_name.trim() || null, limit_value: form.limit_value === "" ? null : form.limit_value,
        integrations: form.integrations.split(",").map((s) => s.trim()).filter(Boolean), added_by: name,
      });
      onAdded(capability);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="cat-add" onSubmit={submit}>
      <div className="cat-add-warn">
        <strong>Adding a capability changes what every deal is checked against.</strong> Every deal will show "Review out
        of date" until it is checked again. Checking again on unchanged documents costs nothing; a gap involving the new
        capability can only appear when the model next reads the documents. Existing entries can't be edited here.
      </div>
      <div className="cat-grid">
        <label className="cat-wide">Capability name<input value={form.name} onChange={set("name")} placeholder="e.g. Payee name check" maxLength={120} /></label>
        <label>Your name<input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Arjun Rao (Product)" maxLength={120} /></label>
        <div className="cat-wide">
          <span className="cat-label">Regions</span>
          <div className="cat-chips">
            {data.regions.map((r) => (
              <button key={r} type="button" className={`cat-chip ${form.regions.includes(r) ? "is-on" : ""}`} onClick={() => toggle(r)}>{r}</button>
            ))}
            <input className="cat-other" value={form.other} onChange={set("other")} placeholder="Other (e.g. NZ)" maxLength={2} />
          </div>
        </div>
        <label>Status
          <select value={form.status} onChange={set("status")}>{data.statuses.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select>
        </label>
        <label>How it can be sold
          <select value={form.sellable} onChange={set("sellable")}>{data.sellable.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}</select>
        </label>
        {form.status !== "generally_available" && (
          <label>Planned general availability<input type="date" value={form.roadmap_date} onChange={set("roadmap_date")} /></label>
        )}
        <label>Limit (optional)<input value={form.limit_name} onChange={set("limit_name")} placeholder="max_checks_per_day" /></label>
        <label>Limit value<input type="number" min="1" value={form.limit_value} onChange={set("limit_value")} placeholder="400000" /></label>
        <label className="cat-wide">Pre-built integrations (optional, comma-separated)<input value={form.integrations} onChange={set("integrations")} /></label>
      </div>
      <div className="cat-row">
        <button type="submit" className="cat-btn cat-btn-dark" disabled={busy || !form.name.trim() || !name.trim()}>{busy ? "Adding…" : "Add to catalogue"}</button>
        <button type="button" className="cat-btn" onClick={onCancel}>Cancel</button>
        {error && <span className="cat-error" role="alert">{error}</span>}
      </div>
    </form>
  );
}

export default function CatalogueModal({ focus, onClose, onChanged }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [adding, setAdding] = useState(false);
  const [added, setAdded] = useState(null);
  const focusRef = useRef(null);
  const focusId = (focus ?? "").split("/")[0];

  const load = () => api.fetchCatalogue().then(setData, (err) => setError(err.message));
  useEffect(() => { load(); }, []);
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  useEffect(() => { focusRef.current?.scrollIntoView({ block: "center" }); }, [data]);

  const caps = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.capabilities
      .map((c) => ({ ...c, rows: c.rows.filter((r) => region === "all" || r.region === region) }))
      .filter((c) => c.rows.length && (!q || `${c.id} ${c.name} ${c.integrations.join(" ")}`.toLowerCase().includes(q)));
  }, [data, query, region]);

  return (
    <div className="cat-overlay" role="dialog" aria-modal="true" aria-label="Product catalogue" onClick={onClose}>
      <div className="cat-modal" onClick={(e) => e.stopPropagation()}>
        <header className="cat-head">
          <div>
            <span className="cat-eyebrow">What Elva can sell · the authority every check uses</span>
            <h2>Product catalogue</h2>
            {data && (
              <span className="cat-sub">
                Published {fmtDate(data.as_of)} · {data.capabilities.length} capabilities
                {data.additions ? ` · ${data.additions} added in the app` : ""}
              </span>
            )}
          </div>
          <div className="cat-row">
            {!adding && <button type="button" className="cat-btn cat-btn-dark" onClick={() => { setAdding(true); setAdded(null); }}>+ Add a capability</button>}
            <button type="button" className="cat-btn" onClick={onClose} aria-label="Close">Close</button>
          </div>
        </header>

        {error && <p className="cat-error">{error}</p>}
        {data && (
          <>
            {adding && (
              <AddForm data={data} onCancel={() => setAdding(false)}
                       onAdded={(cap) => { setAdding(false); setAdded(cap); load(); onChanged?.(); }} />
            )}
            {added && (
              <div className="cat-added" role="status">
                Added {added.id} {added.name}. Deals now show "Review out of date" until they are checked again.
              </div>
            )}
            <p className="cat-rule">{data.unlisted_rule}</p>
            <div className="cat-tools">
              <input className="cat-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by name, ID or integration" aria-label="Search the catalogue" />
              <div className="cat-chips">
                {["all", ...data.regions].map((r) => (
                  <button key={r} type="button" className={`cat-chip ${region === r ? "is-on" : ""}`} onClick={() => setRegion(r)}>{r === "all" ? "All regions" : r}</button>
                ))}
              </div>
            </div>
            <div className="cat-list">
              {caps.map((c) => (
                <section key={c.id} ref={c.id === focusId ? focusRef : null} className={`cat-cap ${c.id === focusId ? "is-focus" : ""}`}>
                  <div className="cat-cap-head">
                    <span className="cat-id">{c.id}</span>
                    <strong>{c.name}</strong>
                    {c.integrations.length > 0 && <span className="cat-int">Integrates with {c.integrations.join(", ")}</span>}
                    {c.added && <span className="cat-badge">Added by {c.added.by} · {fmtDateTime(c.added.at)}</span>}
                  </div>
                  <table className="cat-table">
                    <tbody>
                      {c.rows.map((r) => (
                        <tr key={r.path} className={r.path === focus ? "is-focus" : ""}>
                          <td className="cat-where">{r.region}{r.variant ? ` · ${r.variant}` : ""}</td>
                          <td><span className={`cat-pill`}>{r.status_label}</span></td>
                          <td><span className={`cat-pill`}>{r.sellable_label}</span></td>
                          <td className="cat-limits">{r.limits.length ? r.limits.join(" · ") : <span className="cat-faint">No limit</span>}</td>
                          <td className="cat-date">{r.roadmap_date ? `GA planned ${fmtDate(r.roadmap_date)}` : ""}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              ))}
              {caps.length === 0 && <p className="cat-faint">Nothing matches.</p>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
