// /api/stripe-webhook — Vercel serverless function
// Receives Stripe webhook events for Garden Keeper orders.
//
// Flow:
//   1. Stripe POSTs signed event to /api/stripe-webhook on Vercel
//   2. We verify the Stripe-Signature using STRIPE_WEBHOOK_SECRET
//   3. We forward the parsed event to the VPS API (port 8889) which
//      persists the order, merges the buyer email into subscribers.db,
//      and kicks off fulfillment emails.
//   4. We return 200 to Stripe. If the VPS forward fails, we return 502
//      so Stripe retries (idempotency on the VPS side prevents dupes).
//
// Env vars (set in Vercel project settings, NEVER committed):
//   STRIPE_WEBHOOK_SECRET     — from Stripe Dashboard > Webhooks > Signing secret
//   GK_VPS_API_URL            — VPS base URL, e.g. http://72.61.141.125:8889
//
// Test in dev with Stripe CLI:
//   stripe listen --forward-to https://garden-keeper-v4.vercel.app/api/stripe-webhook
//   stripe trigger checkout.session.completed

import crypto from 'node:crypto';

export const config = {
  api: { bodyParser: false },
};

function readRawBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

function verifyStripeSig(rawBody, sigHeader, secret) {
  if (!sigHeader || !secret) return false;
  // Stripe sends: t=<unix-ts>,v1=<hmac-sha256-hex>
  const parts = Object.fromEntries(
    sigHeader.split(',').map((p) => p.split('='))
  );
  if (!parts.t || !parts.v1) return false;
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${parts.t}.${rawBody.toString('utf8')}`)
    .digest('hex');
  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected, 'hex'),
      Buffer.from(parts.v1, 'hex')
    );
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  let raw;
  try {
    raw = await readRawBody(req);
  } catch (e) {
    return res.status(400).json({ error: `Body read failed: ${e.message}` });
  }

  const sig = req.headers['stripe-signature'];
  const secret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!secret) {
    console.error('STRIPE_WEBHOOK_SECRET not configured in Vercel env');
    return res.status(500).json({ error: 'Webhook secret not configured' });
  }

  if (!verifyStripeSig(raw, sig, secret)) {
    console.warn('Stripe signature verification failed');
    return res.status(400).json({ error: 'Invalid signature' });
  }

  let event;
  try {
    event = JSON.parse(raw.toString('utf8'));
  } catch (e) {
    return res.status(400).json({ error: `Invalid JSON: ${e.message}` });
  }

  // Forward to VPS for fulfillment (DB write, email merge)
  const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
  let vpsResult = null;
  let vpsError = null;
  try {
    const vpsResp = await fetch(`${VPS}/api/stripe-webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-Source': 'vercel-stripe-webhook',
        'X-Stripe-Event-Id': event.id || '',
      },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(15000),
    });
    vpsResult = await vpsResp.json().catch(() => ({ status: vpsResp.status }));
  } catch (e) {
    vpsError = e.message;
    console.error('VPS forward failed:', e);
  }

  // If VPS failed, return 502 so Stripe retries (VPS is idempotent)
  if (vpsError || (vpsResult && vpsResult.success === false)) {
    return res.status(502).json({
      received: true,
      event_type: event.type,
      vps_ok: false,
      vps_error: vpsError || (vpsResult && vpsResult.message) || 'unknown',
      retry: true,
    });
  }

  return res.status(200).json({
    received: true,
    event_type: event.type,
    event_id: event.id,
    vps_ok: true,
    order_id: vpsResult && vpsResult.order_id,
    buyer_email: vpsResult && vpsResult.buyer_email,
    subscriber_merged: vpsResult && vpsResult.subscriber_merged,
  });
}
