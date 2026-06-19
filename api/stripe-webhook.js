// /api/stripe-webhook — Vercel serverless function
// Receives Stripe webhook events for Garden Keeper orders.
// Verifies the signature using the Stripe webhook secret.
//
// Env vars (set in Vercel):
//   STRIPE_WEBHOOK_SECRET
//   GK_VPS_API_URL — VPS that does the actual fulfillment (DB write, email)
//
// For now: verify signature, log the event, forward to VPS for fulfillment.

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
  // Stripe sends: t=...,v1=...
  const parts = Object.fromEntries(
    sigHeader.split(',').map((p) => p.split('='))
  );
  if (!parts.t || !parts.v1) return false;
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${parts.t}.${rawBody.toString('utf8')}`)
    .digest('hex');
  try {
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(parts.v1));
  } catch {
    return false;
  }
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).end();
  }

  const raw = await readRawBody(req);
  const sig = req.headers['stripe-signature'];
  const secret = process.env.STRIPE_WEBHOOK_SECRET;

  if (!verifyStripeSig(raw, sig, secret)) {
    return res.status(400).json({ error: 'Invalid signature' });
  }

  let event;
  try {
    event = JSON.parse(raw.toString('utf8'));
  } catch {
    return res.status(400).json({ error: 'Invalid JSON' });
  }

  // Forward to VPS for fulfillment (DB write, fulfillment email, etc.)
  const VPS = process.env.GK_VPS_API_URL || 'http://72.61.141.125:8889';
  try {
    await fetch(`${VPS}/api/stripe-webhook`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-Source': 'vercel',
        'X-Stripe-Event-Id': event.id || '',
      },
      body: JSON.stringify(event),
    });
  } catch (e) {
    // Log and continue — Stripe will retry on 5xx
    console.error('VPS forward failed:', e);
  }

  return res.status(200).json({ received: true, event_type: event.type });
}
