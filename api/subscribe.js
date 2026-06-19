// /api/subscribe — Vercel serverless function
// Proxies subscription requests to the VPS email API on port 8889.
// This avoids the need for a persistent cloudflared tunnel — the Vercel
// function reaches the VPS by its public IP, which is stable.
//
// The VPS does all the real work: add to subscribers DB, send auto-reply
// email with the PDF, kick off the nurture sequence.
//
// Env vars (set in Vercel project settings, NOT committed):
//   GK_VPS_API_URL — e.g. http://72.61.141.125:8889

export default async function handler(req, res) {
  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ success: false, message: 'Method not allowed' });
  }

  // CORS for the actual response
  res.setHeader('Access-Control-Allow-Origin', '*');

  const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
  const { email, source, interest } = req.body || {};

  if (!email || !email.includes('@')) {
    return res.status(400).json({ success: false, message: 'Invalid email' });
  }

  try {
    const upstream = await fetch(`${VPS}/api/subscribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: String(email).trim().toLowerCase(),
        source: source || 'lead-magnet-html',
        interest: interest || 'plant-care-cheat-sheet',
      }),
      // Vercel serverless: 10s default; bump to 25s for slow email send
    });
    const data = await upstream.json();
    return res.status(upstream.status).json(data);
  } catch (err) {
    return res.status(502).json({
      success: false,
      message: 'Upstream subscription service unavailable',
      detail: String(err && err.message || err),
    });
  }
}
