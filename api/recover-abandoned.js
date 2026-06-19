// /api/recover-abandoned — Vercel serverless proxy
// Queries VPS email API (port 8889) for abandoned Stripe checkouts.
// Supports GET (report) and POST with {action: "send"} (trigger recovery emails).

export default async function handler(req, res) {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(200).end();
  }

  res.setHeader('Access-Control-Allow-Origin', '*');

  const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
  const method = req.method === 'POST' ? 'POST' : 'GET';

  let body = {};
  if (method === 'POST') {
    body = req.body && Object.keys(req.body).length ? req.body : { action: 'list' };
  } else {
    body = { action: 'list' };
  }

  try {
    const upstream = await fetch(`${VPS}/api/recover-abandoned`, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: method === 'POST' ? JSON.stringify(body) : undefined,
    });
    const data = await upstream.json();
    return res.status(upstream.status).json(data);
  } catch (err) {
    return res.status(502).json({
      success: false,
      message: 'Upstream recovery service unavailable',
      detail: String(err && err.message || err),
    });
  }
}