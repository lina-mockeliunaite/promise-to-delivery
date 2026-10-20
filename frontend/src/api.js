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
// One call: refuses before writing if the model is needed and unavailable; stores the version and runs the check; sets the version aside if the check fails after storing.
export const addDocumentAndCheck = (deal, body) => postJson(`${d(deal)}/documents/add-and-check`, body);
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

// Layout redesign (9 Oct): fix inside the finding, per-finding decisions, the deal note, the accountable person.
export const checkFinding = (deal, body) => postJson(`${d(deal)}/findings/check`, body);
export const recordDecision = (deal, body) => postJson(`${d(deal)}/decisions`, body);
export const clearFlag = (deal, body) => postJson(`${d(deal)}/decisions/clear`, body);
export const saveNote = (deal, body) => postJson(`${d(deal)}/note`, body);
export const setAccountable = (deal, body) => postJson(`${d(deal)}/accountable`, body);
// Handover (16 Oct): seen marks, both notes, document links, handover complete. None of these changes a finding.
export const markSeen = (deal, body) => postJson(`${d(deal)}/seen`, body);
export const saveHandoverNote = (deal, body) => postJson(`${d(deal)}/handover/notes`, body);
export const setDocumentLink = (deal, body) => postJson(`${d(deal)}/documents/link`, body);
export const resolveByNote = (deal, body) => postJson(`${d(deal)}/resolve-note`, body);
export const completeHandover = (deal, body) => postJson(`${d(deal)}/handover/complete`, body);
export const fetchHandover = (deal) => getJson(`${d(deal)}/handover`);
// Product catalogue (16 Oct): the published catalogue plus capabilities added in the app.
// 20 Oct: one catalogue per vendor. { deal } opens the catalogue that deal is checked against, { vendor } a vendor's directly.
export const fetchCatalogue = ({ deal, vendor } = {}) => {
  const q = deal ? `?deal=${encodeURIComponent(deal)}` : vendor ? `?vendor=${encodeURIComponent(vendor)}` : "";
  return getJson(`/api/catalogue${q}`);
};
export const addCapability = (body) => postJson("/api/catalogue/capabilities", body);
export const fetchDocumentText = (deal, versionId) => getJson(`${d(deal)}/documents/text?version=${encodeURIComponent(versionId)}`);
