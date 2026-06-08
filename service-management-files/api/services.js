import { validateToken, getAuthToken, renderApiCall, SERVICES, isConfigured } from './_utils.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate auth
  const token = getAuthToken(req);
  if (!validateToken(token)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Check configuration
  if (!isConfigured()) {
    return res.status(503).json({
      error: 'Render API not configured',
      configured: false,
      services: Object.entries(SERVICES).map(([key, svc]) => ({
        key,
        name: svc.name,
        type: svc.type,
        configured: !!svc.id
      }))
    });
  }

  // Fetch status for each service
  const results = [];

  for (const [key, service] of Object.entries(SERVICES)) {
    if (!service.id) {
      results.push({
        key,
        name: service.name,
        type: service.type,
        configured: false,
        status: 'not_configured'
      });
      continue;
    }

    try {
      const endpoint = service.type === 'postgres'
        ? `/postgres/${service.id}`
        : `/services/${service.id}`;

      const data = await renderApiCall(endpoint);

      results.push({
        key,
        name: service.name,
        type: service.type,
        configured: true,
        suspended: data.suspended || false,
        status: data.suspended ? 'suspended' : 'running',
        raw: data
      });
    } catch (error) {
      results.push({
        key,
        name: service.name,
        type: service.type,
        configured: true,
        status: 'error',
        error: error.message
      });
    }
  }

  return res.status(200).json({
    configured: true,
    services: results,
    timestamp: new Date().toISOString()
  });
}
