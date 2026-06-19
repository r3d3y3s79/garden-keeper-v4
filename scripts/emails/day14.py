"""
Day 14 — "Three journals, one routine — meet the system"
Soft product introduction. 90% value, mention journals exist, link to /shop.
"""
from ._base import shell, SITE_URL

subject = "Three journals, one routine"

target_sequence_day = 10
min_hours_since_last = 95  # ~4 days after day-10


def render_html(subscriber_email: str) -> str:
    body = f"""
<p>Two weeks ago you signed up for the cheat sheet. Since then I've sent you what I think are the four most useful things I've learned about keeping plants alive: read the signals, test the soil, flex the schedule, write it down.</p>

<p>If you did even half of those things, your plants are doing better than they were a fortnight ago. That's the goal.</p>

<p>Today I want to show you what happens when you take "write it down" seriously, with a system instead of a scrap of paper.</p>

<p>I designed three journals. Each one does one job, and they work together as a single routine.</p>

<p><strong>1. The Watering Journal.</strong><br>
One page per plant. Track when you watered, what the soil was like, and how the plant looked that week. After a month you'll see your own patterns clearly, and you'll stop watering on autopilot.</p>

<p><strong>2. The Propagation Log.</strong><br>
For when you take a cutting. Date, parent plant, where you cut, root progress, transplant date, survival rate. Over time you'll learn which plants you can multiply easily and which ones fight you.</p>

<p><strong>3. The Seasonal Planner.</strong><br>
A 12-month overview of feeding, repotting, and growth milestones for each of your plants. Designed so you can plan a quiet Sunday in winter instead of doing six emergency repots in spring.</p>

<p>That's the system. Three journals, one routine, no app required.</p>

<p>If you want to see them, they're all live at <a href="{SITE_URL}/shop" style="color:#2f6b3a;">the shop</a>. No pressure — the cheat sheet and these emails will keep you growing whether you buy anything or not.</p>

<p>Thanks for letting me into your inbox for two weeks. It's been good to write to you.</p>

<p style="margin-top:24px;">— Joe<br><span style="color:#6a7a6b;font-size:14px;">Founder, The Garden Keeper</span></p>
"""
    return shell(subject, body, subscriber_email)
