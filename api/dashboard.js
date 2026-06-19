// /api/dashboard — Vercel serverless function
// Proxies the live metrics dashboard from VPS (port 8889).
// Cached for 30 seconds to keep the VPS load low and the page snappy.

const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
const CACHE_TTL_MS = 30 * 1000;

let _cache = { data: null, fetchedAt: 0 };

export default async function handler(req, res) {
  if (req.method === 'OPTIONS') {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    return res.status(200).end();
  }
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const now = Date.now();
  if (_cache.data && (now - _cache.fetchedAt) < CACHE_TTL_MS) {
    res.setHeader('X-Cache', 'HIT');
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(200).json(_cache.data);
  }

  try {
    const r = await fetch(`${VPS}/api/dashboard`, {
      method: 'GET',
      headers: { 'X-Forwarded-Source': 'vercel-dashboard' },
      signal: AbortSignal.timeout(15000),
    });
    const data = await r.json();
    _cache = { data, fetchedAt: now };
    res.setHeader('X-Cache', 'MISS');
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(r.ok ? 200 : 502).json(data);
  } catch (e) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    return res.status(502).json({
      success: false,
      message: `VPS unreachable: ${e.message}`,
      hint: 'Check GK_VPS_API_URL env var and that the VPS :8889 listener is up',
    });
  }
}
