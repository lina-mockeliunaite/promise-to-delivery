import { useEffect, useState } from "react";
import { fetchDeals, fetchLatestResults, fetchSources } from "./api.js";

const humanise = (value) => {
  if (!value) return "—";
  const text = String(value).replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
};

const titleCase = (value) => String(value).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

// The API's "status" is eligibility by document type, not whether the latest run read the document.
const ELIGIBILITY = {
  extracted: "Read for promises",
  reference_only: "Reference only",
  unclassified: "Unclassified",
};

const RUN_STATUS = {
  complete: { label: "Complete", problem: false },
  skipped_reference_only: { label: "Skipped (reference only)", problem: false },
};

function runStatus(status) {
  if (!status) return { label: "Not in latest run", problem: false };
  return RUN_STATUS[status] ?? { label: humanise(status), problem: true };
}

function formatRunTime(timestamp) {
  const date = new Date(timestamp);
  if (!timestamp || Number.isNaN(date.getTime())) return null;
  return date.toISOString().replace("T", " ").slice(0, 16) + " UTC";
}

// One request, three visible states. Failure in one section does not hide the other.
function useRequest(load, key) {
  const [state, setState] = useState({ status: "loading", data: null });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!key) return undefined;
    let cancelled = false;
    setState({ status: "loading", data: null });
    load(key).then(
      (data) => !cancelled && setState({ status: "ready", data }),
      (error) => !cancelled && setState({ status: "error", data: null, message: error.message }),
    );
    return () => {
      cancelled = true;
    };
  }, [load, key, attempt]);
  return [state, () => setAttempt((n) => n + 1)];
}

function Loading({ what }) {
  return (
    <p className="notice" role="status">
      Loading {what}…
    </p>
  );
}

function ErrorNotice({ what, message, onRetry }) {
  return (
    <div className="notice notice-error" role="alert">
      <p>
        <strong>Could not load {what}.</strong> {message}
      </p>
      <button type="button" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

function Empty({ children }) {
  return <p className="notice">{children}</p>;
}

function SourcesTable({ sources, documents }) {
  const byId = new Map((documents ?? []).map((d) => [d.source_id, d.status]));
  const haveRun = byId.size > 0;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>File</th>
            <th>Type</th>
            <th>Date</th>
            <th>Eligibility</th>
            <th>Latest run</th>
          </tr>
        </thead>
        <tbody>
          {sources.map((s) => {
            const run = haveRun ? runStatus(byId.get(s.source_id)) : { label: "No run loaded", problem: false };
            return (
              <tr key={s.source_id}>
                <td className="nowrap">{s.source_id}</td>
                <td>{s.file}</td>
                <td>{humanise(s.doc_type)}</td>
                <td className="nowrap">{s.date ?? "—"}</td>
                <td>{ELIGIBILITY[s.status] ?? humanise(s.status)}</td>
                <td>
                  <span className={run.problem ? "status status-problem" : "status"}>
                    {run.problem ? "! " : ""}
                    {run.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StatementsTable({ statements }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Source</th>
            <th>Quote</th>
            <th>Language</th>
            <th>Speaker</th>
          </tr>
        </thead>
        <tbody>
          {statements.map((s) => (
            <tr key={s.statement_id ?? `${s.source_id}-${s.quote}`}>
              <td className="nowrap">{s.source_id}</td>
              <td className="quote">{s.quote}</td>
              <td className="nowrap">{humanise(s.language)}</td>
              <td>{s.speaker ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function App() {
  const [deals, retryDeals] = useRequest(fetchDeals, "deals");
  const deal = deals.data?.deals?.[0] ?? null;
  const [sources, retrySources] = useRequest(fetchSources, deal);
  const [results, retryResults] = useRequest(fetchLatestResults, deal);

  const resultsValid = results.status === "ready" && results.data.intermediate === true;
  const runTime = resultsValid ? formatRunTime(results.data.run?.timestamp_utc) : null;

  return (
    <main>
      <header>
        <p className="eyebrow">Deal workspace</p>
        <h1>{deal ? titleCase(deal) : "Deal"}</h1>
        <p className="muted">Read-only view of the permitted source documents and the latest saved extraction.</p>
      </header>

      {deals.status === "loading" && <Loading what="deals" />}
      {deals.status === "error" && <ErrorNotice what="deals" message={deals.message} onRetry={retryDeals} />}
      {deals.status === "ready" && !deal && <Empty>No deals are available to show.</Empty>}

      {deal && (
        <>
          <section aria-labelledby="sources-heading">
            <h2 id="sources-heading">Sources</h2>
            {sources.status === "loading" && <Loading what="sources" />}
            {sources.status === "error" && (
              <ErrorNotice what="sources" message={sources.message} onRetry={retrySources} />
            )}
            {sources.status === "ready" &&
              (sources.data.sources.length === 0 ? (
                <Empty>This deal has no source documents listed.</Empty>
              ) : (
                <SourcesTable sources={sources.data.sources} documents={resultsValid ? results.data.documents : null} />
              ))}
          </section>

          <section aria-labelledby="statements-heading">
            <h2 id="statements-heading">Extracted statements</h2>
            <p className="banner" role="note">
              Intermediate output: extracted statements, not reviewed findings.
            </p>
            {results.status === "loading" && <Loading what="results" />}
            {results.status === "error" && (
              <ErrorNotice what="results" message={results.message} onRetry={retryResults} />
            )}
            {results.status === "ready" && !resultsValid && (
              <div className="notice notice-error" role="alert">
                <p>
                  <strong>Results not shown.</strong> The response was not marked as intermediate output.
                </p>
              </div>
            )}
            {resultsValid && (
              <>
                <p className="muted">
                  {results.data.run
                    ? `Latest saved run${runTime ? `: ${runTime}` : ""} · ${results.data.statements.length} statements from ${results.data.documents.length} documents`
                    : "No saved run for this deal."}
                </p>
                {results.data.run === null ? (
                  <Empty>No saved extraction results for this deal yet.</Empty>
                ) : results.data.statements.length === 0 ? (
                  <Empty>The latest saved run found no statements.</Empty>
                ) : (
                  <StatementsTable statements={results.data.statements} />
                )}
              </>
            )}
          </section>
        </>
      )}
    </main>
  );
}
