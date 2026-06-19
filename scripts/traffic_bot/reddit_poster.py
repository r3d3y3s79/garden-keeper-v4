#!/usr/bin/env python3
"""
Garden Keeper Reddit Traffic Bot
Posts value-first content to targeted subreddits and drives traffic to lead magnet.
Requires Reddit API credentials and a Reddit account.
"""
import os
import sys
import json
import random
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

# Optional: praw for actual posting
try:
    import praw
except ImportError:
    praw = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Load content templates
CONTENT = [
    {
        "title": "I built a free Plant Care Cheat Sheet after killing 5 houseplants",
        "body": """After losing my succulent collection to overwatering, I compiled everything I learned into a one-page cheat sheet.

It covers:
• When to water (not on a schedule)
• Light requirements for 20+ common plants
• Signs of over vs underwatering
• Seasonal care adjustments

Grab it free here:
https://garden-keeper-v4.vercel.app/lead-magnet/

Hope it helps someone avoid my mistakes! 🌿""",
        "subreddits": ["houseplants", "plantclinic", "IndoorGarden"],
        "schedule": ["tuesday"]
    },
    {
        "title": "The 60-second plant diagnosis guide",
        "body": """Yellow leaves? Brown tips? Drooping? Here's my quick diagnostic:

**Yellow lower leaves** → Overwatering. Check roots.
**Yellow new growth** → Needs fertilizer.
**Brown crispy tips** → Low humidity or fluoride in water.
**Drooping** → Check soil. Wet = overwatered. Dry = underwatered.
**Leggy growth** → Needs more light.
**No growth for months** → Root bound or dormant.

I turned this into a printable flowchart + cheat sheet:
https://garden-keeper-v4.vercel.app/lead-magnet/

What's the weirdest plant problem you've diagnosed?""",
        "subreddits": ["plantclinic", "houseplants"],
        "schedule": ["monday", "thursday"]
    },
    {
        "title": "Propagation success rate jumped from 30% to 90% after I started logging",
        "body": """I was failing at water propagation. Cuttings would rot or never root.

Then I started keeping a simple log:
• Cutting date
• Plant type
• Water change dates
• Root appearance dates
• Success/failure

Patterns emerged immediately:
• Pothos: roots in 7 days, 100% success
• Succulents: rot if water touches leaves, 40% success
• Spider plants: roots in 3 days, 95% success

I built a free propagation log template based on what worked:
https://garden-keeper-v4.vercel.app/lead-magnet/

What's your propagation success rate?""",
        "subreddits": ["propagation", "houseplants"],
        "schedule": ["wednesday"]
    },
    {
        "title": "From 3 plants to 47: My 2-year indoor jungle journey",
        "body": """2 years ago I had 3 plants. Now I have 47 and counting.

What changed?
1. Started tracking watering dates, growth, problems
2. Learned propagation — turned 1 pothos into 12
3. Understood seasons — spring = propagate, winter = dormancy
4. Got the right light — grow lights for winter
5. Built a system — journals, reminders, seasonal prep

I'm launching a plant journal system that covers all of this:
https://garden-keeper-v4.vercel.app/

Anyone else document their plant journey?""",
        "subreddits": ["houseplants", "IndoorGarden"],
        "schedule": ["sunday"]
    },
    {
        "title": "Stop buying plant apps. Use this instead.",
        "body": """I paid $10/month for a plant app. Then realized I was paying for notifications I ignored.

Now I use a simple physical journal. One-time purchase. No battery, no subscription.

I track:
• Watering dates
• Fertilizer schedule
• Growth measurements
• Seasonal reminders

5 months in, I prefer it to any app. Writing it down makes me actually pay attention.

I designed the journal I wish existed:
https://garden-keeper-v4.vercel.app/

Anyone else gone analog with plant care?""",
        "subreddits": ["houseplants", "IndoorGarden", "gardening"],
        "schedule": ["saturday"]
    }
]

class RedditTrafficBot:
    def __init__(self):
        self.reddit = None
        self.client_id = os.environ.get('REDDIT_CLIENT_ID')
        self.client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
        self.username = os.environ.get('REDDIT_USERNAME')
        self.password = os.environ.get('REDDIT_PASSWORD')
        self.user_agent = 'Garden Keeper Traffic Bot v1.0 by /u/' + (self.username or 'unknown')

    def connect(self):
        if not praw:
            logger.error("praw not installed. Run: pip install praw")
            return False
        if not all([self.client_id, self.client_secret, self.username, self.password]):
            logger.error("Reddit credentials missing. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
            return False
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                username=self.username,
                password=self.password,
                user_agent=self.user_agent
            )
            me = self.reddit.user.me()
            logger.info(f"Connected as /u/{me.name}")
            return True
        except Exception as e:
            logger.error(f"Reddit connection failed: {e}")
            return False

    def select_content(self):
        today = datetime.now(timezone.utc).strftime('%A').lower()
        candidates = [c for c in CONTENT if today in c.get('schedule', [])]
        if not candidates:
            # Fallback: pick any post
            candidates = CONTENT
        post = random.choice(candidates)
        return post

    def post(self, dry_run=True):
        post = self.select_content()
        subreddit = random.choice(post['subreddits'])
        logger.info(f"Selected post: {post['title']} for r/{subreddit}")

        if dry_run:
            logger.info("DRY RUN — not posting. Use --live to post for real.")
            return {"dry_run": True, "title": post['title'], "subreddit": subreddit, "body": post['body']}

        if not self.connect():
            return {"error": "not connected"}

        try:
            submission = self.reddit.subreddit(subreddit).submit(
                title=post['title'],
                selftext=post['body'],
                flair_id=None
            )
            logger.info(f"Posted: https://reddit.com{submission.permalink}")
            self.log_post(submission.id, subreddit, post['title'])
            return {"success": True, "url": f"https://reddit.com{submission.permalink}", "id": submission.id}
        except Exception as e:
            logger.error(f"Post failed: {e}")
            return {"error": str(e)}

    def log_post(self, post_id, subreddit, title):
        db_path = Path('/root/the-garden-keeper/data/traffic_log.db')
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS reddit_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT,
            subreddit TEXT,
            title TEXT,
            posted_at TEXT,
            url TEXT
        )''')
        c.execute('INSERT INTO reddit_posts (post_id, subreddit, title, posted_at, url) VALUES (?,?,?,?,?)',
                  (post_id, subreddit, title, datetime.now(timezone.utc).isoformat(), f"https://reddit.com/r/{subreddit}/comments/{post_id}"))
        conn.commit()
        conn.close()

    def stats(self):
        db_path = Path('/root/the-garden-keeper/data/traffic_log.db')
        if not db_path.exists():
            return {"total_posts": 0}
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        total = c.execute('SELECT COUNT(*) FROM reddit_posts').fetchone()[0]
        recent = c.execute('SELECT * FROM reddit_posts ORDER BY posted_at DESC LIMIT 10').fetchall()
        conn.close()
        return {"total_posts": total, "recent": recent}

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Actually post to Reddit')
    parser.add_argument('--stats', action='store_true', help='Show posting stats')
    parser.add_argument('--install', action='store_true', help='Install praw')
    args = parser.parse_args()

    if args.install:
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'praw'])
        print('praw installed')
        sys.exit(0)

    bot = RedditTrafficBot()
    if args.stats:
        print(json.dumps(bot.stats(), indent=2))
    else:
        result = bot.post(dry_run=not args.live)
        print(json.dumps(result, indent=2))
