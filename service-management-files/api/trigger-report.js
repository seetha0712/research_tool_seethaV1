// Manual trigger for daily report (for testing)
// Requires admin authentication

import { validateToken, getAuthToken } from './_utils.js';
import handler from './cron/daily-report.js';

export default async function triggerHandler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Validate admin token
  const token = getAuthToken(req);
  if (!validateToken(token)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  // Add cron secret header to satisfy the handler
  req.headers['authorization'] = `Bearer ${process.env.CRON_SECRET}`;

  // Call the actual handler
  return handler(req, res);
}
