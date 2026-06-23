from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_...")

app = FastAPI(title="The Garden Keeper Stripe API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "mode": "sandbox"}

@app.post("/create-checkout-session")
def create_checkout_session(body: dict):
    import traceback
    price_lookup = body.get("price_lookup")
    customer_email = body.get("customer_email")
    if not price_lookup:
        raise HTTPException(status_code=400, detail="price_lookup required")
    print(f"[checkout] lookup={price_lookup} email={customer_email} key_prefix={stripe.api_key[:14]}", flush=True)
    try:
        prices = stripe.Price.list(lookup_keys=[price_lookup], limit=1)
        print(f"[checkout] prices={len(prices.data)}", flush=True)
        if not prices.data:
            return {"session_id": "mock_" + price_lookup, "url": "/success?mock=1", "mock": True}
        price_id = prices.data[0].id
        mode = "subscription" if getattr(prices.data[0], "recurring", None) else "payment"
        sess = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode=mode,
            success_url="https://thegardenkeeper.shop/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://thegardenkeeper.shop/cancel",
            customer_email=customer_email,
            allow_promotion_codes=True,
        )
        print(f"[checkout] session={sess.id}", flush=True)
        return {"session_id": sess.id, "url": sess.url}
    except Exception as e:
        print(f"[checkout] ERROR: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/prices")
def list_prices():
    return {
        "single_journal": {"name": "Single Journal", "amount": 699, "currency": "usd", "lookup_key": "gk_single_journal"},
        "bundle_3": {"name": "Bundle (3 Journals)", "amount": 1199, "currency": "usd", "lookup_key": "gk_bundle_3"},
        "complete_set_5": {"name": "Complete Set (5 Journals)", "amount": 1799, "currency": "usd", "lookup_key": "gk_complete_set_5"},
        "vip_monthly": {"name": "VIP Subscription", "amount": 499, "currency": "usd", "lookup_key": "gk_vip_monthly", "recurring": "month"},
    }
