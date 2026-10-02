// GET-only client for the local API. Error messages are generic on purpose: the status code, nothing else.
async function getJson(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`The request failed (status ${response.status}).`);
  return response.json();
}

export const fetchDeals = () => getJson("/api/deals");
export const fetchSources = (deal) => getJson(`/api/deals/${encodeURIComponent(deal)}/sources`);
export const fetchLatestResults = (deal) => getJson(`/api/deals/${encodeURIComponent(deal)}/results/latest`);
