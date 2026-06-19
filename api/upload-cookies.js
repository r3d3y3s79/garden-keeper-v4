// /api/upload-cookies — Vercel serverless function
// Receives a cookies.txt file via HTTPS, writes it to the VPS, and
// triggers a Telegram notification + agent-reach configuration.
//
// Flow:
//   1. Frontend POSTs JSON: { service, filename, content }
//   2. Function validates the file looks like Netscape cookies.txt
//   3. Forwards to VPS via a write-only endpoint on port 8889
//      (/api/upload-cookies) which writes the file and reports
//      back the saved path.
//   4. Notifies Joe via Telegram with the saved path.
//   5. Returns 200 + path to the frontend.

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

  res.setHeader('Access-Control-Allow-Origin', '*');

  const { service, filename, content } = req.body || {};
  if (!service || !filename || !content) {
    return res.status(400).json({ success: false, message: 'service, filename, content required' });
  }

  // Validate: must look like Netscape cookies.txt format
  // Either: a # Netscape HTTP Cookie File header
  // Or: a tab-separated line starting with a domain
  if (content.length < 50) {
    return res.status(400).json({ success: false, message: 'File too small to be a real cookies.txt' });
  }
  const firstLine = content.split('\n')[0].trim();
  const looksLikeCookies = 
    firstLine.startsWith('# Netscape') ||
    firstLine.startsWith('# This file') ||
    /^#\s*HttpOnly/.test(firstLine) ||
    /^[\w.-]+\s+(TRUE|FALSE)\s+\//.test(firstLine);
  if (!looksLikeCookies) {
    return res.status(400).json({ 
      success: false, 
      message: 'File does not look like Netscape cookies.txt format. First line: ' + firstLine.substring(0, 80),
    });
  }

  // Map service → filename
  const serviceMap = {
    youtube: 'youtube.com_cookies.txt',
    twitter: 'twitter.com_cookies.txt',
    reddit: 'reddit.com_cookies.txt',
    xiaohongshu: 'xiaohongshu.com_cookies.txt',
    other: filename,
  };
  const targetName = serviceMap[service] || filename;
  
  // Sanitize filename (alphanumerics, dots, underscores, hyphens only)
  const safeName = targetName.replace(/[^a-zA-Z0-9._-]/g, '_');

  // Forward to VPS — but we need a VPS endpoint that accepts uploads
  // Use the existing email API on port 8889 as a proxy. We'll add a 
  // /api/upload-cookies endpoint on the VPS side.
  // For now: return a friendly error if VPS endpoint isn't up yet.
  const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
  try {
    const upstream = await fetch(`${VPS}/api/upload-cookies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: safeName,
        service,
        content,
      }),
    });
    const data = await upstream.json();
    if (!data.success) {
      return res.status(upstream.status).json(data);
    }
    return res.status(200).json({
      success: true,
      path: data.path,
      filename: safeName,
      service,
      message: `Cookies saved. Next agent run will configure ${service} automatically.`,
    });
  } catch (err) {
    return res.status(502).json({
      success: false,
      message: 'VPS upload endpoint not reachable: ' + (err && err.message || err),
      hint: 'Run the VPS-side upload handler script: bash /root/.hermes/scripts/install-cookies-handler.sh',
    });
  }
}
