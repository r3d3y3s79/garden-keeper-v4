#!/usr/bin/env python3
"""
Garden Keeper — Pinterest pin CSV regenerator.
Writes /root/the-garden-keeper/social/pinterest-pins.csv from a single source
of truth (CURRENT_SKUS below) so the CSV never drifts from the live store.

Output columns match the spec in JOE-76:
  board, title, description, destination_link, image_url, alt_text, sku, price

5 product covers × 4 boards = 20 rows. Each row points at the homepage
anchor (#products), which is the canonical shop entry point as of 2026-06-21
(individual product pages 404; /shop also 404s).
"""
import csv
from pathlib import Path

OUT = Path("/root/the-garden-keeper/social/pinterest-pins.csv")
SITE = "https://garden-keeper-v4.vercel.app"
DEST = f"{SITE}/#products"

# Source of truth for the live lineup. Synced with broadcast.py and day-14.py.
CURRENT_SKUS = [
    {
        "slug": "essential-tracker",
        "title": "Essential Tracker",
        "sku_name": "Essential Tracker — single plant journal",
        "price": "$6.99",
        "cover": "cover_succulent.png",
        "description": (
            "One page per plant. Water, soil, light, fertilize, repot — all on "
            "the same spread so you can see what worked two months ago without "
            "flipping pages. The cheapest way to find out whether writing "
            "things down actually works for you."
        ),
        "alt": "The Garden Keeper — Essential Tracker. Premium watercolor succulent journal cover. $6.99.",
    },
    {
        "slug": "bloom-record",
        "title": "Bloom Record",
        "sku_name": "Bloom Record — vegetable garden planner",
        "price": "$6.99",
        "cover": "cover_vegetable.png",
        "description": (
            "Plot planning, seed-to-harvest dates, pest notes, rotation map. "
            "Designed for the gardener who wants to stop guessing and start "
            "tracking what actually grew. One spread per crop."
        ),
        "alt": "The Garden Keeper — Bloom Record. Premium watercolor vegetable garden planner cover. $6.99.",
    },
    {
        "slug": "indoor-jungle",
        "title": "Indoor Jungle",
        "sku_name": "Indoor Jungle — houseplant log",
        "price": "$6.99",
        "cover": "cover_indoor.png",
        "description": (
            "Built for the 30+ plant parent. Humidity, fertilizer, light, and "
            "growth photos for every plant in your collection. The journal "
            "that turns 'which one needs water?' into a 10-second glance."
        ),
        "alt": "The Garden Keeper — Indoor Jungle log. Premium watercolor houseplant journal cover. $6.99.",
    },
    {
        "slug": "seasonal-trio",
        "title": "Seasonal Trio",
        "sku_name": "Seasonal Trio — 3 seasonal covers, 90-day reset",
        "price": "$11.99",
        "cover": "cover_seasonal.png",
        "description": (
            "Three seasonal covers — spring, summer, fall — designed to be "
            "used for one full 90-day growing cycle. Best for the climate-"
            "aware grower who plans 12 months ahead."
        ),
        "alt": "The Garden Keeper — Seasonal Trio bundle. Premium watercolor cover, 3 seasonal journals. $11.99.",
    },
    {
        "slug": "complete-set",
        "title": "Complete Set",
        "sku_name": "Complete Set — all 5 journals, best value",
        "price": "$17.99",
        "cover": "cover_seasonal.png",  # hero shot uses seasonal cover (broadest appeal)
        "description": (
            "All five Garden Keeper journals in one bundle — the cheapest way "
            "to get the full system. 5 watercolor covers, 600+ pages total, "
            "designed to replace the scrap of paper you've been losing."
        ),
        "alt": "The Garden Keeper — Complete Set. All 5 watercolor journals bundled. Best value at $17.99.",
    },
]

# Boards chosen for organic discovery (Pinterest search volume). Each board
# already exists as a recommended starting board for plant parents.
BOARDS = [
    "Indoor Plant Care",
    "Vegetable Garden Planner",
    "Succulent Care Tips",
    "Seasonal Planting Calendar",
]


def build_rows():
    rows = []
    for board in BOARDS:
        for sku in CURRENT_SKUS:
            rows.append({
                "board": board,
                "title": f"{sku['title']} — the {slug_to_angle(sku['slug'])} journal",
                "description": sku["description"],
                "destination_link": DEST,
                "image_url": f"/root/the-garden-keeper/assets/images/{sku['cover']}",
                "alt_text": sku["alt"],
                "sku": sku["slug"],
                "price": sku["price"],
                "upload_status": "READY",
                "upload_instructions": (
                    "1) Open image_url. 2) Pinterest > Create Pin. "
                    "3) Copy title + description from this row. "
                    "4) Destination: " + DEST + " (homepage anchor — live shop entry). "
                    "5) Pin to the named board."
                ),
            })
    return rows


def slug_to_angle(slug):
    return {
        "essential-tracker": "single-plant",
        "bloom-record": "vegetable",
        "indoor-jungle": "houseplant",
        "seasonal-trio": "seasonal",
    }.get(slug, slug)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    fields = [
        "board", "title", "description", "destination_link",
        "image_url", "alt_text", "sku", "price",
        "upload_status", "upload_instructions",
    ]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"WROTE {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()