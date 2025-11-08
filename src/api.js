import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
});

// const token = process.env.REACT_APP_JWT_TOKEN;
//const token = process.env.REACT_APP_JWT_TOKEN || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzZWV0aGEiLCJ1c2VyX2lkIjoxLCJleHAiOjE3NTMyNjg0MDN9.PcS3-Zdg54v6IZIvCNTqCEI-E4v0YdkvmTDu-l7S1xk"
//console.log("TOKEN as in api.js is:", token);

// Interceptor to auto-logout on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response &&
      error.response.status === 401
    ) {
      // Remove token and reload page
      localStorage.removeItem("jwt_token");
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

// --- Helper to set Authorization header ---
export const authHeader = (token) => ({
  headers: { Authorization: `Bearer ${token}` },
});

// --- 1. Add RSS or API Source ---
export async function addSource(payload, token) {
  // payload: { name, url, type, provider, query }
  const res = await api.post("/sources/", payload, authHeader(token));
  return res.data;
}

// --- 2. Upload PDF (creates file & source) ---
export async function uploadFile(file, token) {
  const formData = new FormData();
  formData.append("uploaded_file", file);
  const res = await api.post("/files/", formData, {
    ...authHeader(token),
    "Content-Type": "multipart/form-data"
  });
  return res.data;
}

// --- 3. List all sources (any type) ---
export async function getSources(token) {
  const res = await api.get("/sources/", authHeader(token));
  return res.data;
}

// --- 4. Toggle source (activate/deactivate) ---
export async function toggleSource(id, token) {
  const res = await api.patch(`/sources/${id}/activate`, {}, authHeader(token));
  return res.data;
}

// --- 5. Delete source ---
export async function deleteSource(id, token) {
  const res = await api.delete(`/sources/${id}`, authHeader(token));
  return res.data;
}

// --- 6. List files ---
export async function getFiles(token) {
  const res = await api.get("/files/", authHeader(token));
  return res.data;
}

// --- 7. Sync all sources (one click) ---
export async function syncSources(token, { limit = 10, from_date = "" } = {}) {
  // POST body: { limit: 10, from_date: "2025-07-21" }
  const res = await api.post(
    "/sync/",
    { limit, from_date },         // JSON body!
    authHeader(token)
  );
  return res.data;
}

// Get articles with params (filters/search)
export async function getArticles(token, params = {}) {
   // params example: { category: 'AI Adoption in Finance', status: 'final', search: 'openai' }
  //const query = new URLSearchParams(params).toString();
  //const res = await api.get(`/articles/${query ? "?" + query : ""}`, {
  //  headers: { Authorization: `Bearer ${token}` }
  //});
  const res = await api.get("/articles/", {
    ...authHeader(token),
    params,  // Axios will convert this to a query string for you!
  });
  return res.data;
}

// Update status
export async function updateArticleStatus(articleId, status, token) {
  const res = await api.patch(`/articles/${articleId}/status?status=${status}`, {}, authHeader(token));
  return res.data;
}

// Update note
export async function updateArticleNote(articleId, note, token) {
  const res = await api.patch(`/articles/${articleId}/note?note=${encodeURIComponent(note)}`, {}, authHeader(token));
  return res.data;
}

export async function registerUser(username, password) {
  const res = await api.post("/auth/register", { username, password });
  return res.data;
}

export async function loginUser(username, password) {
  const res = await api.post("/auth/login", { username, password });
  return res.data; // { access_token, token_type }
}


export async function getDeepInsights(token, articleId) {
  const res = await api.post(
    `/articles/${articleId}/deep_insights`,
    {},
    authHeader(token)
  );
  return res.data;
}

export async function fetchPaidSearchResults(token, query, providers  ) {
  const res = await api.post(
    "/paid_search/",
    { query, providers, limit: 10, offset: 0 },
    authHeader(token)
  );
  // Axios responses always have res.status and res.data, no res.ok or res.json()
  if (res.status < 200 || res.status >= 300) {
    // If the backend returns error JSON in res.data, access it here
    throw new Error(res.data?.detail || "Failed to fetch paid search results");
  }

  // Axios automatically parses JSON response, so no await res.json()
  return res.data;
}

export async function savePaidArticles(token, articles) {
  const res = await api.post("/paid_search/save", { articles }, authHeader(token));
  return res.data;
}

export async function getSavedPaidArticles(token, query = "") {
  const res = await api.get("/paid_search/saved", {
    ...authHeader(token),
    params: query ? { query } : {}
  });
  return res.data;
}

export async function fetchDashboardMetrics(token) {
  const res = await api.get("/dashboard/metrics", {
    headers: { Authorization: `Bearer ${token}` }
  });
  return res.data;
}

export async function updatePaidArticle(token, articleId, payload) {
  // payload: { status, category }
  const res = await api.patch(`/paid_search/paid_articles/${articleId}`, payload, authHeader(token));
  return res.data;
}

// For regular articles
export async function fetchArticleFullText(url, summary = "") {
  const res = await fetch('/articles/fulltext', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, summary }),
  });
  if (!res.ok) throw new Error("Failed to fetch article full text");
  return await res.json();
}

// For paid articles
export async function fetchPaidArticleFullText(url, summary = "") {
  const res = await fetch('/paid_search/fulltext', {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, summary }),
  });
  if (!res.ok) throw new Error("Failed to fetch paid article full text");
  return await res.json();
}

// Patch PPTX with source URLs and download
export async function patchPPTXLinks(presentation_id, sourceUrlArray) {
  // Use FormData because backend expects it (not JSON)
  const formData = new FormData();
  formData.append("presentation_id", presentation_id);
  formData.append("source_urls", JSON.stringify(sourceUrlArray));

  // responseType: 'blob' is critical for downloading binary files!
  const res = await api.post(
    "/slidesgpt/add-links",
    formData,
    { responseType: "blob" }
  );
  return res.data; // The blob!
}

export async function buildDeckPpt(token, payload, opts = {}) {
  const url = `/deck/build-ppt${opts.returnUrl ? "?return_url=1" : ""}`;
  const res = await api.post(url, payload, {
    ...(opts.returnUrl ? {} : { responseType: "blob" }), // Blob for local download
    ...authHeader(token),
  });
  return res.data; // If blob → binary, if opts.returnUrl → JSON { file_url, viewer_url }
}

export default api;