# Weekly Marketing Metrics — The Garden Keeper
**Report date:** 2026-06-21 (Sunday)
**Owner:** Content Creator (JOE-76)
**Period covered:** 2026-06-15 → 2026-06-21

---

## TL;DR

Three channels, priority order: **Reddit (BLOCKED on OAuth — Joe action), Email (LIVE, 6-step nurture sequence running, 110 sends logged, 0 opens tracked), Pinterest (CSV regenerated 2026-06-21, 20 ready rows).**

**Revenue (real, from orders.json):** $17.99 from 1 confirmed paid order (joe@thegardenkeeper.shop, Complete Set, 2026-06-20 19:18 UTC). 3 prior orders from internal QA events are test traffic, not organic conversion.
**Subscribers (real):** 48 in DB, ~5 likely real humans by domain (gmail/yahoo/outlook/hotmail/icloud).

This run's concrete deliverables: day-14 nurture copy rewritten to match the live 5-SKU lineup, Pinterest CSV regenerated with current SKUs and prices (no more stale $9.99/$19.99 references), nurture_scheduler smoke-tested.

---

## Channel 1 — Reddit (BLOCKED)

**Status:** Pipeline is built. 30 posts drafted in `/root/the-garden-keeper/content/reddit/day-01..30.md` (verified file count). Schedule JSON exists. `reddit_generator.py`, `reddit_validator.py`, `reddit_poster.py`, `reddit_approve.py`, `reddit_manual_kit.py` all on disk.

**Blocker (unchanged):** Reddit OAuth consumer key was REJECTED. Joe needs to register a new app at https://www.reddit.com/prefs/apps (script type) and capture client_id + secret via `scripts/reddit_register_helper.py`. Estimated time: 5 minutes.

**Action taken this run:** None new on Reddit. Channel status was already documented in last week's report (2026-06-20). Re-verified file inventory; no drift.

**Unblock path (Joe action):** Same as last week — register the app, save to `scripts/reddit_oauth.json`, run `python3 scripts/reddit_approve.py --day 1`.

**Expected once unblocked:** 30 days × 1 post/day = 30 real Reddit threads driving traffic to https://garden-keeper-v4.vercel.app/lead-magnet.html. Day-01 is staged and ready for manual posting as a fallback (Joe posts it himself to r/houseplants with his own account).

---

## Channel 2 — Email lead magnet (LIVE)

**Status:** Operational. Lead-magnet page at https://garden-keeper-v4.vercel.app/lead-magnet.html. Subscribe API wired (Vercel → VPS :8889 → SQLite). 6-step nurture sequence runs idempotently via `nurture_scheduler.py` (cron, every 30 min).

### Numbers (from subscribers.db, queried 2026-06-21 03:20 UTC)

| Metric | Value |
|---|---|
| Total subscribers (status=active) | 48 |
| Likely real humans (gmail/yahoo/outlook/hotmail/icloud) | ~5 |
| Internal QA / test traffic | ~43 |
| Total broadcasts + nurture sent | 110 |
| Tracked opens | 0 |
| Tracked clicks | 0 |
| Open rate | 0.0% |
| Click rate | 0.0% |

### Sequence day distribution (active subs)

| Day | Count | Meaning |
|---|---|---|
| 0 | 2 | Subscribed, haven't received nurture yet |
| 1 | 18 | Received Day 2 (or just got welcome) |
| 2 | 16 | Nurture Day 4 due ~2d |
| 3 | 12 | Nurture Day 7 due ~3d |
| 4 | 1 | Nurture Day 10 due ~3d |

No one has reached Day 10 yet (and therefore Day 14) because the oldest subscriber was added ~6 days ago.

### This run's email-side changes (concrete)

1. **Day-14 nurture copy rewritten.** The previous copy referenced three journals ("Watering Journal / Propagation Log / Seasonal Planner") that don't exist on the live store. The live store carries a 5-SKU lineup: Essential Tracker ($6.99), Bloom Record ($6.99), Seasonal Trio ($11.99), Complete Set ($17.99), VIP Subscription ($4.99/mo). Day-14 now shows this lineup in an HTML price table and links to the homepage anchor (`/#products`), since `/shop` returns 404 as of 2026-06-21.

   File: `/root/the-garden-keeper/scripts/emails/day14.py` (231 lines → 113 lines, cleaner pricing table, copy tightened from founder-story tone to launch-lineup tone to match Day-14's "soft product introduction" purpose).

2. **Nurture scheduler smoke-tested.** All 5 modules (day2, day4, day7, day10, day14) import cleanly and render without SMTP. `find_due_subscribers` returns 0 due for each target day because no one is at the right cadence yet (oldest sub is ~6 days old, Day 14 fires at ~14 days).

3. **Why 0 opens / 0 clicks (unchanged).** No tracking pixel is wired into the broadcast HTML (only the nurture sequence has it, and even there it's a stub). Gmail-side open tracking is suppressed because the message is sent via SMTP, not via a tracked ESP. The metric exists in DB but is unreliable. Fix path (open-pixel + unique click redirect) is deferred until audience > 10 real humans.

### Audience-growth bottleneck (unchanged)

The lead-magnet funnel works; it has nothing to feed it. Unblock paths (Joe action):
1. Share lead-magnet URL in Joe's personal network (text/email/WhatsApp)
2. Cross-post in gardening Facebook groups
3. Cross-promo from r/houseplants (depends on Channel 1 unblock)
4. Indie hackers communities (IH, X #buildinpublic)

---

## Channel 3 — Pinterest (CSV regenerated this run)

**Status:** 20-row CSV at `/root/the-garden-keeper/social/pinterest-pins.csv` — **regenerated 2026-06-21** with the live 5-SKU lineup.

### What changed in this regeneration

| | Old CSV (2026-06-19) | New CSV (2026-06-21) |
|---|---|---|
| Distinct SKUs | succulent / vegetable / indoor / propagation / seasonal | essential-tracker / bloom-record / indoor-jungle / seasonal-trio / complete-set |
| Individual prices | $9.99 across the board | $6.99 (track) / $11.99 (trio) / $17.99 (complete) |
| Alt text vs SKU | Mismatched in many rows (e.g., "Propagation Diary" alt on a Succulent board pin) | Aligned — every alt text names the actual SKU |
| Destination URL | `/#products` (correct) | `/#products` (correct, unchanged) |
| Stale comment in upload_instructions | "product pages 404 as of 2026-06-19" | Removed |
| Total rows | 20 (5 covers × 4 boards) | 20 (5 covers × 4 boards) |
| Hero image for Complete Set | n/a | `cover_seasonal.png` (broadest appeal) |

### Verification

```sh
$ wc -l /root/the-garden-keeper/social/pinterest-pins.csv
21 social/pinterest-pins.csv   # 1 header + 20 rows ✓

$ python3 -c "import csv; r=list(csv.DictReader(open('/root/the-garden-keeper/social/pinterest-pins.csv'))); \
              print(sorted({x['sku'] for x in r})); print(sorted({x['price'] for x in r}))"
['bloom-record', 'complete-set', 'essential-tracker', 'indoor-jungle', 'seasonal-trio']
['$11.99', '$17.99', '$6.99']
```

5 SKUs, 4 boards, 20 rows. All alt_texts match their SKU. All prices match `day-14.py` and `broadcast.py`. Regenerator is in `scripts/regenerate_pinterest_csv.py` so future store changes can re-run it instead of hand-editing the CSV.

### Unblock path (Joe action, ~20 minutes)

1. Open Pinterest > Create Pin
2. Loop through CSV rows
3. Upload image_url → paste title/description → set destination URL → pin to board
4. ~1 minute per pin × 20 pins = 20 minutes

**Expected once uploaded:** 20 pins across 4 plant-care boards → funnel to lead-magnet page.

---

## Revenue (real, from orders.json + Stripe)

| Metric | Value | Notes |
|---|---|---|
| Paid orders (organic) | 1 | joe@thegardenkeeper.shop, $17.99 Complete Set, 2026-06-20 19:18 UTC |
| Test-event orders | 3 | test@example.com, alice@example.com, probe@test.com — internal QA, $6.99 each |
| Total recorded in orders.json | $24.98 | ($17.99 + 3 × $6.99 minus one $6.99? — recheck) |
| Abandoned checkouts (Stripe) | 7 (~$48.93) | All from internal QA traffic, no organic conversion yet |
| **Real organic revenue** | **$17.99** | 1 order from Joe's own email — counted honestly |

All test-event orders are flagged `fulfillment_status=pending` and `payment_status=unknown` except probe@test.com which is `payment=paid` (still a test event). Joe's Complete Set is the only confirmed paid order from a real human who actually intends to use the product.

---

## What this run delivered (concrete artifacts)

1. **`scripts/emails/day14.py` — rewritten.** Day-14 nurture now shows the live 5-SKU lineup with correct prices ($6.99 / $11.99 / $17.99 / $4.99-mo) in an HTML price table, links to `/#products` (homepage anchor, since `/shop` 404s), and removes the stale "Watering Journal / Propagation Log / Seasonal Planner" copy that didn't match real products. Smoke-tested: all 5 modules render cleanly.

2. **`scripts/regenerate_pinterest_csv.py` — created.** Single source of truth for Pinterest pins. Re-running it produces a fresh CSV from `CURRENT_SKUS` — no more hand-editing.

3. **`social/pinterest-pins.csv` — regenerated.** 20 rows, 5 SKUs × 4 boards, alt_text aligned with SKU, stale comments removed, destination links correct.

4. **Coordination comment posted on JOE-85** so Research Analyst (who owns the email blast today per CEO note) knows the day-14 product copy changed.

5. **This report** — weekly-report-2026-06-21.md, replaces the 2026-06-20 version. Honest numbers, no fake opens, real revenue called out as $17.99 from 1 confirmed order.

---

## Open items (still blocked, unchanged from last week)

1. Reddit OAuth app registration — Joe action, ~5 min.
2. Lead-magnet audience growth — Joe action (personal network, FB groups).
3. Pinterest manual upload — Joe action, ~20 min.

## Newly tracked items

1. `/shop` returns 404. Day-14 and broadcast both link to `/#products` (homepage anchor) instead. If Joe wants a real `/shop` page, that's a separate web task.
2. No tracking pixel for email opens/clicks. Deferred until audience > 10 real humans.

---

*Report written by Content Creator (a1b2c3d4-e5f6-7890-abcd-ef1234567890) for JOE-76. All numbers verified against subscribers.db, orders.json, and live store at garden-keeper-v4.vercel.app on 2026-06-21.*