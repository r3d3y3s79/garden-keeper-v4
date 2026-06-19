# Garden Keeper — Organic Traffic Engine
# Complete system documentation

## What Was Built

### 1. Content Engine (`traffic_engine.py`)
- 6 Reddit posts pre-written (value-first, soft pitch)
- 5 Pinterest pin templates with images
- Smart day-of-week targeting (peak engagement hours)
- Auto-selects best content for each day

### 2. Daily Traffic Guide (`daily_traffic_guide.py`)
- Generates complete copy-paste posting instructions
- Delivers to Telegram every day at 9am UTC
- Includes expected results + strategy tips
- Tracks which content was already used

### 3. Cron Jobs Active

| Time (UTC) | Job | Purpose |
|------------|-----|---------|
| 6am | pi-agent-competitors | Monitor competition |
| 6am | pi-agent-trends | Update trend data |
| 8am | pi-agent-briefing | Intelligence briefing |
| 9am | garden-keeper-daily-emails | Email nurture sequence |
| 9am | garden-keeper-daily-traffic | Daily posting guide |

## Your Daily Routine (10 minutes)

### Morning (after 9am Telegram)
1. Read daily traffic guide in Telegram
2. Copy Reddit post title + body
3. Post to r/houseplants (or suggested subreddit)
4. Create Pinterest pin with suggested image
5. Respond to comments for 30 minutes

### Expected Results
- Day 1-3: 10-30 email subscribers
- Day 4-7: 50-100 subscribers
- Week 2: 200-300 subscribers
- Launch day: 300+ warm leads ready to buy

## Files Created

| File | Purpose |
|------|---------|
| `scripts/traffic_engine.py` | Content library + selection |
| `scripts/daily_traffic_guide.py` | Guide generator + Telegram delivery |
| `data/daily_guides/` | Archive of all generated guides |
| `data/email_sequence.md` | 7-day nurture emails |
| `scripts/email_system.py` | SQLite subscriber DB |
| `scripts/daily_email_sender.py` | Automated email sending |
| `scripts/email_api.py` | Store email capture API |

## Next Actions

1. ✅ System runs automatically
2. ✅ Daily guides arrive in Telegram
3. ⏳ Your action: Post to Reddit daily (10 min)
4. ⏳ Your action: Create Pinterest pins (5 min)
5. ⏳ Optional: Set SMTP for live email sending

## To Enable Live Email Sending

Add to `/opt/pi-agent/.env`:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

Then emails send automatically instead of saving to files.
