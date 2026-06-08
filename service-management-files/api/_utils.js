const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;
const RENDER_API_KEY = process.env.RENDER_API_KEY;
const RENDER_API_BASE = 'https://api.render.com/v1';

// Service configuration
export const SERVICES = {
  database: {
    id: process.env.RENDER_SERVICE_ID_DB || '',
    name: 'research-tool-db',
    type: 'postgres'
  },
  app: {
    id: process.env.RENDER_SERVICE_ID_APP || '',
    name: 'research_tool_seethaV1',
    type: 'web_service'
  }
};

export function validateToken(token) {
  if (!token || !ADMIN_PASSWORD) return false;

  try {
    const decoded = Buffer.from(token, 'base64').toString('utf-8');
    const [timestamp, password] = decoded.split(':');
    const tokenAge = Date.now() - parseInt(timestamp, 10);
    const maxAge = 24 * 60 * 60 * 1000; // 24 hours

    return password === ADMIN_PASSWORD && tokenAge < maxAge;
  } catch {
    return false;
  }
}

export function getAuthToken(req) {
  const authHeader = req.headers.authorization || '';
  if (authHeader.startsWith('Bearer ')) {
    return authHeader.slice(7);
  }
  return null;
}

export async function renderApiCall(endpoint, method = 'GET', body = null) {
  const options = {
    method,
    headers: {
      'Authorization': `Bearer ${RENDER_API_KEY}`,
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    }
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${RENDER_API_BASE}${endpoint}`, options);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Render API error: ${response.status} - ${text}`);
  }

  // Some endpoints return empty response
  const text = await response.text();
  return text ? JSON.parse(text) : {};
}

export function isConfigured() {
  return !!(RENDER_API_KEY && (SERVICES.database.id || SERVICES.app.id));
}
