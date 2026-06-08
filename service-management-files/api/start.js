import { validateToken, getAuthToken, renderApiCall, SERVICES, isConfigured } from './_utils.js';
import { sendNotification } from './_email.js';

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate auth
  const token = getAuthToken(req);
  if (!validateToken(token)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Check configuration
  if (!isConfigured()) {
    return res.status(503).json({ error: 'Render API not configured' });
  }

  const { serviceKey } = req.body || {};

  if (!serviceKey || !SERVICES[serviceKey]) {
    return res.status(400).json({ error: 'Invalid service key. Use "database" or "app"' });
  }

  const service = SERVICES[serviceKey];

  if (!service.id) {
    return res.status(400).json({ error: `Service "${serviceKey}" not configured` });
  }

  try {
    const endpoint = service.type === 'postgres'
      ? `/postgres/${service.id}/resume`
      : `/services/${service.id}/resume`;

    await renderApiCall(endpoint, 'POST');

    // Send email notification (non-blocking)
    sendNotification('start', service.name, true).catch(console.error);

    return res.status(200).json({
      success: true,
      service: serviceKey,
      name: service.name,
      action: 'start',
      message: `Service "${service.name}" is starting...`,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    // Send failure notification (non-blocking)
    sendNotification('start', service.name, false, error.message).catch(console.error);

    return res.status(500).json({
      success: false,
      service: serviceKey,
      name: service.name,
      action: 'start',
      error: error.message
    });
  }
}
