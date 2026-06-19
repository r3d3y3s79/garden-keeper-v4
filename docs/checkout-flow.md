# Checkout Flow — The Garden Keeper (Stripe Sandbox)

## Architecture
```
Customer -> Checkout Page (checkout-frontend/index.html)
         -> POST /api/create-checkout-session
         -> Stripe Checkout Session (hosted)
         -> Stripe Payment Page
         -> Redirect /success or /cancel
         -> Webhook fulfillment (optional, future)
```

## Step-by-Step Flow

1. **Pricing Display**
   - Customer visits checkout page.
   - Four tiers rendered: Single (**$6.99**), Bundle (**$11.99**), Complete Set (**$17.99**), VIP (**$4.99/mo**).

2. **Session Creation**
   - Frontend sends price_lookup key to backend.
   - Backend resolves Price ID via Stripe API (Price.list(lookup_keys=[...])).
   - Backend creates checkout.session with mode = payment (one-time) or subscription (VIP).

3. **Stripe Hosted Checkout**
   - Customer is redirected to Stripe Checkout URL.
   - Stripe handles: card input, 3D Secure, tax (if configured), receipt email.

4. **Post-Payment**
   - success_url: Redirects to store success page with session_id query param.
   - cancel_url: Redirects back to checkout page.

5. **Fulfillment (Future)**
   - Webhook endpoint listens for checkout.session.completed.
   - For digital products: trigger email with PDF download link.
   - For VIP: provision community access.

## Security Notes
- Never expose secret keys in frontend.
- Verify webhook signatures in production.
- Use Stripe test mode (sandbox) for all development.

## Environment Variables
| Variable | Purpose |
|----------|---------|
| STRIPE_SECRET_KEY | Backend API authentication (test key) |
| STRIPE_WEBHOOK_SECRET | Verify webhook events (future) |
| FRONTEND_URL | Allowed CORS origin |
