#!/usr/bin/env python3
"""
Stripe Sandbox Product & Price Setup for The Garden Keeper
"""
import os
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_...")

PRODUCTS = [
    {
        "name": "Single Journal",
        "description": "One beautifully designed Garden Keeper journal for your plant-tracking needs.",
        "metadata": {"tier": "single", "sku": "GK-JRN-001"},
        "prices": [{"unit_amount": 699, "currency": "usd", "lookup_key": "gk_single_journal"}],
    },
    {
        "name": "Bundle (3 Journals)",
        "description": "Triple pack of Garden Keeper journals — perfect for gifting or multi-season tracking.",
        "metadata": {"tier": "bundle", "sku": "GK-JRN-BUNDLE3"},
        "prices": [{"unit_amount": 1199, "currency": "usd", "lookup_key": "gk_bundle_3"}],
    },
    {
        "name": "Complete Set (5 Journals)",
        "description": "The full Garden Keeper collection — five themed journals at our best value.",
        "metadata": {"tier": "complete", "sku": "GK-JRN-SET5"},
        "prices": [{"unit_amount": 1799, "currency": "usd", "lookup_key": "gk_complete_set_5"}],
    },
    {
        "name": "VIP Subscription",
        "description": "Monthly VIP access: exclusive content, plant-care guides, community perks & early releases.",
        "metadata": {"tier": "vip", "sku": "GK-SUB-VIP"},
        "prices": [
            {
                "unit_amount": 499,
                "currency": "usd",
                "recurring": {"interval": "month"},
                "lookup_key": "gk_vip_monthly",
            }
        ],
    },
]


def create_products_and_prices(dry_run=True):
    created = []
    for prod in PRODUCTS:
        if dry_run:
            print("[DRY RUN] Would create product: " + prod["name"])
            for price in prod["prices"]:
                print("  [DRY RUN]   price: {:.2f} {}".format(price["unit_amount"] / 100, price["currency"].upper()))
            created.append({"product": prod["name"], "status": "dry_run"})
            continue

        product_obj = stripe.Product.create(
            name=prod["name"],
            description=prod["description"],
            metadata=prod["metadata"],
        )
        print("Created product: " + product_obj.id + " — " + product_obj.name)

        for price in prod["prices"]:
            kwargs = {
                "unit_amount": price["unit_amount"],
                "currency": price["currency"],
                "product": product_obj.id,
                "lookup_key": price["lookup_key"],
            }
            if "recurring" in price:
                kwargs["recurring"] = price["recurring"]

            price_obj = stripe.Price.create(**kwargs)
            print("  Created price: " + price_obj.id + " — {:.2f} {}".format(price["unit_amount"] / 100, price["currency"].upper()))
            if "recurring" in price:
                print("    Recurring: " + price["recurring"]["interval"])

        created.append({"product_id": product_obj.id, "name": prod["name"]})

    return created


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Stripe sandbox products for The Garden Keeper")
    parser.add_argument("--live", action="store_true", help="Run against live Stripe (not sandbox)")
    args = parser.parse_args()

    results = create_products_and_prices(dry_run=not args.live)
    print("\nTotal items processed: " + str(len(results)))
