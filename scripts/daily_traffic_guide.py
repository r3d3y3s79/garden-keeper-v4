#!/usr/bin/env python3
"""
Garden Keeper Daily Traffic Guide Generator
Generates ready-to-post content for Reddit/Pinterest,
delivers to Telegram as a daily action item.
"""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, '/root/the-garden-keeper/scripts')
from traffic_engine import generate_daily_posting_plan, CONTENT_LIBRARY

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('HERMES_SESSION_CHAT_ID', '6482991006')

def generate_posting_guide():
    """Generate complete daily posting instructions."""
    plan = generate_daily_posting_plan()
    reddit = plan["reddit_post"]
    pinterest = plan["pinterest_pin"]
    
    guide = f"""
🌿 DAILY TRAFFIC GUIDE — {datetime.now().strftime('%A, %B %d')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 REDDIT POST (High Priority)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Subreddit: r/{reddit['subreddit']}
Flair: {reddit['flair']}
Best Time: {reddit['best_time']}

Title:
{reddit['title']}

Body:
{reddit['body']}

⚡ ACTION: Copy above → post to Reddit → wait 30 min → respond to first 5 comments → add "Edit: Wow this blew up! Link to free cheat sheet in comments" → paste store link

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 PINTEREST PIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Board: {pinterest['board']}

Title: {pinterest['title']}

Description:
{pinterest['description']}

Image: {pinterest['image']}

Hashtags: #PlantParent #HousePlants #PlantCare #IndoorPlants #PlantTips #GreenThumb #PlantJourney

⚡ ACTION: Create pin → upload image → add title + description + hashtags → link to store → save to board

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 TODAY'S STRATEGY TIPS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Post during peak hours for maximum visibility
2. Respond to ALL comments in first hour (algorithm boost)
3. If post hits 50+ upvotes, pin a comment with store link
4. Cross-post to related subreddits after 24 hours
5. Save high-performing posts for future reposting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 EXPECTED RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Reddit: 500-3,000 views → 20-100 clicks → 5-15 email subscribers
• Pinterest: 100-500 impressions → 5-20 clicks → 1-3 subscribers
• Combined daily potential: 6-18 new email subscribers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Your store link: http://72.61.141.125:8888/
📧 Subscribers so far: check http://72.61.141.125:8889/api/stats
⏰ Next guide: Tomorrow at 9am UTC
"""
    return guide.strip()

def send_to_telegram(message):
    """Send guide to Joseph's Telegram."""
    import urllib.request
    import urllib.parse
    
    if not TELEGRAM_TOKEN:
        # Try to load from env file
        try:
            with open('/opt/pi-agent/.env') as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        token = line.split('=', 1)[1].strip().strip('"')
                    if line.startswith('TELEGRAM_CHAT_ID='):
                        chat_id = line.split('=', 1)[1].strip().strip('"')
        except:
            print("No Telegram credentials found")
            return False
    else:
        token = TELEGRAM_TOKEN
        chat_id = TELEGRAM_CHAT_ID
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        response = urllib.request.urlopen(req, timeout=30)
        return json.loads(response.read().decode())
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def main():
    guide = generate_posting_guide()
    
    # Save to file
    today = datetime.now().strftime('%Y%m%d')
    out_dir = '/root/the-garden-keeper/data/daily_guides'
    os.makedirs(out_dir, exist_ok=True)
    
    filepath = f"{out_dir}/guide_{today}.txt"
    with open(filepath, 'w') as f:
        f.write(guide)
    
    print(f"✅ Daily guide saved: {filepath}")
    print(f"   Length: {len(guide)} characters")
    
    # Send to Telegram
    result = send_to_telegram(guide)
    if result and result.get('ok'):
        print("✅ Sent to Telegram")
    else:
        print("⚠️  Telegram send failed (saved to file)")
    
    return filepath

if __name__ == "__main__":
    main()
