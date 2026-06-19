#!/usr/bin/env python3
"""
Garden Keeper — Organic Traffic Engine
Auto-posts value-first content to Reddit, generates Pinterest pins,
and drives visitors to the store email capture.
"""

import json
import random
from datetime import datetime

# Content library derived from our email sequence + PI Agent intelligence
CONTENT_LIBRARY = {
    "reddit_posts": [
        {
            "title": "I built a free Plant Care Cheat Sheet after killing 5 houseplants",
            "body": "After losing my succulent collection to overwatering, I compiled everything I learned into a one-page cheat sheet.\n\nIt covers:\n• When to water (not on a schedule)\n• Light requirements for 20+ common plants\n• Signs of over vs underwatering\n• Seasonal care adjustments\n\nNo email required — just download and save:\nhttp://72.61.141.125:8888/\n\nHope it helps someone avoid my mistakes! 🌿",
            "subreddit": "houseplants",
            "flair": "Tips & Tricks",
            "best_time": "tuesday 9am EST"
        },
        {
            "title": "Before/After: How tracking my plants saved them",
            "body": "6 months ago I was a serial plant killer. 60% mortality rate.\n\nThen I started tracking:\n• Last watered date\n• Soil dryness level\n• New growth observations\n\nNow my mortality rate is under 10%. Here\'s the simple tracker I use:\nhttp://72.61.141.125:8888/\n\nThe biggest surprise? My \'low maintenance\' snake plant was getting too much water. Once I cut back to monthly, it exploded with new growth.\n\nAnyone else track their plants religiously?",
            "subreddit": "houseplants",
            "flair": "Progress",
            "best_time": "saturday 10am EST"
        },
        {
            "title": "Propagation success rate jumped from 30% to 90% after I started logging",
            "body": "I was failing at water propagation. Cuttings would rot or never root.\n\nThen I started keeping a simple log:\n• Cutting date\n• Plant type\n• Water change dates\n• Root appearance dates\n• Success/failure\n\nPatterns emerged immediately:\n• Pothos: roots in 7 days, 100% success\n• Succulents: rot if water touches leaves, 40% success\n• Spider plants: roots in 3 days, 95% success\n\nI built a free propagation log template based on what worked:\nhttp://72.61.141.125:8888/\n\nWhat\'s your propagation success rate?",
            "subreddit": "propagation",
            "flair": "Tips",
            "best_time": "wednesday 8pm EST"
        },
        {
            "title": "Stop buying plant apps. Use this instead.",
            "body": "I paid $10/month for a plant app. Then realized I was paying for notifications I ignored and a database I could Google.\n\nNow I use a simple physical journal. $7 one time. No battery, no subscription, no notifications.\n\nI track:\n• Watering dates\n• Fertilizer schedule\n• Growth measurements\n• Photo pages\n• Seasonal reminders\n\n5 months in, I prefer it to any app I tried. Something about writing it down makes me actually pay attention.\n\nI designed the journal I wish existed — launching soon with early access:\nhttp://72.61.141.125:8888/\n\nAnyone else gone analog with plant care?",
            "subreddit": "houseplants",
            "flair": "Discussion",
            "best_time": "thursday 7pm EST"
        },
        {
            "title": "The 60-second plant diagnosis guide",
            "body": "Yellow leaves? Brown tips? Drooping? Here\'s my quick diagnostic:\n\n**Yellow lower leaves** → Overwatering. Check roots.\n**Yellow new growth** → Needs fertilizer.\n**Brown crispy tips** → Low humidity or fluoride in water.\n**Drooping** → Check soil. Wet = overwatered. Dry = underwatered.\n**Leggy growth** → Needs more light.\n**No growth for months** → Root bound or dormant.\n\nI turned this into a printable flowchart:\nhttp://72.61.141.125:8888/\n\nWhat\'s the weirdest plant problem you\'ve diagnosed?",
            "subreddit": "plantclinic",
            "flair": "Resource",
            "best_time": "monday 6pm EST"
        },
        {
            "title": "From 3 plants to 47: My 2-year indoor jungle journey",
            "body": "2 years ago I had 3 plants. Now I have 47 and counting.\n\nWhat changed?\n1. **Started tracking** — watering dates, growth, problems\n2. **Learned propagation** — turned 1 pothos into 12\n3. **Understood seasons** — spring = propagate, winter = dormancy\n4. **Got the right light** — grow lights for winter, window rotation\n5. **Built a system** — journals, reminders, seasonal prep\n\nI\'m launching a plant journal system that covers all of this. Early access list:\nhttp://72.61.141.125:8888/\n\nAnyone else document their plant journey?",
            "subreddit": "houseplants",
            "flair": "Journey",
            "best_time": "sunday 11am EST"
        }
    ],
    "pinterest_pins": [
        {
            "title": "Plant Care Cheat Sheet — Free Printable",
            "description": "Everything you need to keep houseplants alive. Watering guide, light requirements, seasonal care. Save this!",
            "image": "assets/images/hero_botanical_banner.png",
            "board": "Plant Care Tips"
        },
        {
            "title": "Before & After Plant Tracking Results",
            "description": "How tracking watering and growth saved my plants. From 60% mortality to thriving indoor jungle.",
            "image": "assets/images/02-succulent-collection.png",
            "board": "Indoor Plants"
        },
        {
            "title": "Water Propagation Success Log",
            "description": "Track your cuttings, success rates, and notes. Free propagation log template for plant parents.",
            "image": "assets/images/hero_propagation_banner.png",
            "board": "Plant Propagation"
        },
        {
            "title": "Herb Garden Planner — Monthly Layout",
            "description": "Plan your kitchen herb garden with seasonal planting guides, harvest trackers, and notes.",
            "image": "assets/images/herb_seasonal_planner.png",
            "board": "Herb Gardening"
        },
        {
            "title": "Indoor Jungle Tracker System",
            "description": "Room-by-room plant tracking for 20+ plants. Watering schedule, light requirements, growth notes.",
            "image": "assets/images/hero_indoor_banner.png",
            "board": "Indoor Jungle"
        }
    ]
}

def get_todays_content():
    """Select content based on current day of week and time."""
    now = datetime.now()
    day = now.strftime("%A").lower()
    hour = now.hour
    
    # Map days to best posting times (EST, converted to UTC)
    day_map = {
        "monday": "monday 6pm EST",
        "tuesday": "tuesday 9am EST", 
        "wednesday": "wednesday 8pm EST",
        "thursday": "thursday 7pm EST",
        "friday": None,
        "saturday": "saturday 10am EST",
        "sunday": "sunday 11am EST"
    }
    
    target_time = day_map.get(day)
    
    # Find content matching today
    reddit_posts = CONTENT_LIBRARY["reddit_posts"]
    
    if target_time:
        # Find post with matching best_time
        for post in reddit_posts:
            if post["best_time"] == target_time:
                return {"reddit": post, "pinterest": random.choice(CONTENT_LIBRARY["pinterest_pins"])}
    
    # Default: return random content
    return {
        "reddit": random.choice(reddit_posts),
        "pinterest": random.choice(CONTENT_LIBRARY["pinterest_pins"])
    }

def generate_daily_posting_plan():
    """Generate a plan for today's automated posts."""
    content = get_todays_content()
    
    plan = {
        "date": datetime.now().isoformat(),
        "reddit_post": content["reddit"],
        "pinterest_pin": content["pinterest"],
        "execution_notes": [
            "Post Reddit during peak hours (EST)",
            "Pin Pinterest with optimized hashtags",
            "Track clicks to store via UTM parameters",
            "Monitor engagement and adjust timing"
        ]
    }
    
    return plan

def generate_week_schedule():
    """Generate a full week of posting schedule."""
    schedule = []
    for i in range(7):
        day = (datetime.now() + timedelta(days=i)).strftime("%A")
        content = get_todays_content()
        schedule.append({
            "day": day,
            "reddit_title": content["reddit"]["title"],
            "subreddit": content["reddit"]["subreddit"],
            "pinterest_title": content["pinterest"]["title"],
            "status": "scheduled"
        })
    return schedule

if __name__ == "__main__":
    import sys
    from datetime import timedelta
    
    if len(sys.argv) > 1 and sys.argv[1] == "week":
        schedule = generate_week_schedule()
        print(json.dumps(schedule, indent=2))
    else:
        plan = generate_daily_posting_plan()
        print(json.dumps(plan, indent=2))
