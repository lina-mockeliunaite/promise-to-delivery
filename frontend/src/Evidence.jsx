// Evidence-first comparison (17 Oct, after the UI review). The customer's exact words beside the contract's, then one
// plain line per gap. Every quote and fact here was checked by code; the AI's sentence sits behind its own label.
import { short } from "./dealpage.js";

const STATUS = {
  open: { chip: "dp-chip-amber", text: "Open" },
  closed: { chip: "dp-chip-green", text: "Closed by documents" },
  noted: { chip: "dp-chip-note", text: "Resolved by note" },
};

function Quote({ q }) {
  return (
    <blockquote className="ev-quote">
      <span>“{q.quote}”</span>
      <cite>{q.source}{q.date ? ` · ${short(q.date)}` : ""}</cite>
    </blockquote>
  );
}

export default function Evidence({ quotes = [], told, contract, gaps, onCatalogue }) {
  const [first, ...more] = quotes;
  return (
    <div className="ev">
      <div className="ev-cols">
        <div className="ev-col">
          <span className="ev-label">What the customer was told</span>
          {first ? <Quote q={first} /> : <p className="ev-plain">{told}</p>}
          {more.length > 0 && (
            <details className="ev-more">
              <summary>Also said in {more.length} more {more.length === 1 ? "place" : "places"}</summary>
              {more.map((q) => <Quote key={q.quote} q={q} />)}
            </details>
          )}
        </div>
        <div className="ev-col">
          <span className="ev-label">What the contract says</span>
          {contract.quote ? (
            <Quote q={{ quote: contract.quote, source: contract.source }} />
          ) : contract.missing ? (
            <>
              <p className="ev-plain ev-none">No matching wording found in the draft contract or SOW.</p>
              <span className="ev-searched">Searched for: {contract.missing.map((m) => `“${m}”`).join(" · ")}</span>
            </>
          ) : (
            <p className="ev-plain">{contract.text}</p>
          )}
        </div>
      </div>
      <ul className="ev-gaps">
        {gaps.map((g) => (
          <li key={g.key} className={`ev-gap is-${g.status}`}>
            <div className="ev-gap-head">
              <strong>{g.label}</strong>
              <span className={`dp-chip ${STATUS[g.status].chip}`}>{STATUS[g.status].text}</span>
            </div>
            {g.line && <span className="ev-line">{g.line}</span>}
            {g.extra && <span className="ev-extra">{g.extra}</span>}
            {(g.catalogue || g.ai) && (
              <div className="ev-meta">
                {g.catalogue && onCatalogue && (
                  <button type="button" className="cat-open" onClick={() => onCatalogue(g.catalogue)} title="Open the product catalogue at this entry">
                    Catalogue: {g.catalogue.split("/").slice(0, 2).join(" · ")}{g.catalogue.split("/").length > 2 ? ` · ${g.catalogue.split("/").slice(2).join(" ").replace(/_/g, " ")}` : ""}
                  </button>
                )}
                {g.ai && (
                  <details className="ev-ai">
                    <summary>AI explanation · source quotes checked</summary>
                    <p>{g.ai}</p>
                  </details>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
