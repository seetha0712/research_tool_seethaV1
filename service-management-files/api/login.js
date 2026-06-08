const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD;

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body || {};

  if (!ADMIN_PASSWORD) {
    return res.status(500).json({ error: 'ADMIN_PASSWORD not configured on server' });
  }

  if (password === ADMIN_PASSWORD) {
    // Generate a simple session token (valid for 24 hours)
    const token = Buffer.from(`${Date.now()}:${ADMIN_PASSWORD}`).toString('base64');
    return res.status(200).json({
      success: true,
      token,
      message: 'Login successful'
    });
  }

  return res.status(401).json({ error: 'Invalid password' });
}
