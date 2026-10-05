// Client for the local API. Errors show the server's plain message, never internals.
async function handle(response) {
  if (response.ok) return response.json();
  let detail = `The request failed (status ${response.status}).`;
  try {
    const body = await response.json();
    if (body && typeof body.detail === "string") detail = body.detail;
  } catch {
    /* keep the generic message */
  }
  throw new Error(detail);
}

const getJson = (path) => fetch(path, { headers: { Accept: "application/json" } }).then(handle);

// Writes carry a custom header: the server refuses writes without it, which blocks cross-site posts.
const postJson = (path, body) =>
  fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json", "X-Requested-With": "deal-workspace" },
    body: JSON.stringify(body ?? {}),
  }).then(handle);

const d = (deal) => `/api/deals/${encodeURIComponent(deal)}`;

export const fetchDeals = () => getJson("/api/workspace/deals");
export const createDeal = (name) => postJson("/api/user-deals", { name });
export const fetchDocuments = (deal) => getJson(`${d(deal)}/documents`);
export const addDocument = (deal, body) => postJson(`${d(deal)}/documents`, body);
export const setIncluded = (deal, source_key, included) => postJson(`${d(deal)}/documents/include`, { source_key, included });
export const fetchRegister = (deal) => getJson(`${d(deal)}/register`);
export const reviewDeal = (deal, fix_id) => postJson(`${d(deal)}/review`, fix_id ? { fix_id } : {});
export const recordFix = (deal, body) => postJson(`${d(deal)}/fixes`, body);
export const updateIssue = (deal, body) => postJson(`${d(deal)}/issues`, body);

export const saveHandoff = (deal, body) => postJson(`${d(deal)}/handoffs`, body);
export const fetchHandoffs = (deal) => getJson(`${d(deal)}/handoffs`);
export const fetchHandoff = (deal, version) => getJson(`${d(deal)}/handoffs/view?version=${encodeURIComponent(version)}`);
export const handoffCsvUrl = (deal, version) => `${d(deal)}/handoffs/export.csv?version=${encodeURIComponent(version)}`;
export const handoffSummaryUrl = (deal, version) => `${d(deal)}/handoffs/summary?version=${encodeURIComponent(version)}`;
