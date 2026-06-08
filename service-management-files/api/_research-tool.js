// Research Tool API Client
const RESEARCH_TOOL_URL = process.env.RESEARCH_TOOL_URL || 'https://research-tool-seethav1.onrender.com';
const RESEARCH_TOOL_USER = process.env.RESEARCH_TOOL_USER;
const RESEARCH_TOOL_PASSWORD = process.env.RESEARCH_TOOL_PASSWORD;

let cachedToken = null;
let tokenExpiry = 0;

export async function login() {
  // Return cached token if still valid (with 5 min buffer)
  if (cachedToken && Date.now() < tokenExpiry - 5 * 60 * 1000) {
    return cachedToken;
  }

  const response = await fetch(`${RESEARCH_TOOL_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: RESEARCH_TOOL_USER,
      password: RESEARCH_TOOL_PASSWORD
    })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Login failed: ${response.status} - ${text}`);
  }

  const data = await response.json();
  cachedToken = data.access_token;
  // Assume 24h token validity, cache for 23h
  tokenExpiry = Date.now() + 23 * 60 * 60 * 1000;

  return cachedToken;
}

export async function checkHealth() {
  try {
    const response = await fetch(`${RESEARCH_TOOL_URL}/`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function waitForHealthy(maxWaitMs = 180000, intervalMs = 5000) {
  const startTime = Date.now();

  while (Date.now() - startTime < maxWaitMs) {
    const healthy = await checkHealth();
    if (healthy) {
      console.log('Research Tool is healthy');
      return true;
    }
    console.log('Waiting for Research Tool to become healthy...');
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }

  throw new Error('Research Tool did not become healthy within timeout');
}

export async function syncSources(token, limit = 25, fromDate = '') {
  const response = await fetch(`${RESEARCH_TOOL_URL}/sync/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ limit, from_date: fromDate })
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Sync failed: ${response.status} - ${text}`);
  }

  return response.json();
}

export async function getArticles(token, params = {}) {
  const queryParams = new URLSearchParams();

  if (params.limit) queryParams.set('limit', params.limit.toString());
  if (params.status) queryParams.set('status', params.status);
  if (params.sort_by) queryParams.set('sort_by', params.sort_by);
  if (params.sort_order) queryParams.set('sort_order', params.sort_order);

  const url = `${RESEARCH_TOOL_URL}/articles/${queryParams.toString() ? '?' + queryParams.toString() : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Accept': 'application/json'
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Get articles failed: ${response.status} - ${text}`);
  }

  return response.json();
}

export function isConfigured() {
  return !!(RESEARCH_TOOL_USER && RESEARCH_TOOL_PASSWORD);
}
