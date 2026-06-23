"""
Day 14 — "The launch lineup — five journals, one routine"
Soft product introduction. 90% value, mention journals exist, link to homepage.
Synced 2026-06-21 with the live store lineup at garden-keeper-v4.vercel.app.
"""
from ._base import shell, SITE_URL

subject = "The launch lineup — five journals, one routine"

target_sequence_day = 10
min_hours_since_last = 95  # ~4 days after day-10


def render_html(subscriber_email: str) -> str:
    # Anchor #products on the homepage is the live shop entry point as of 2026-06-21.
    # /shop returns 404 — homepage anchor is the canonical link.
    shop_url = f"{SITE_URL}/#products"
    body = f"""
<p>Two weeks ago you signed up for the cheat sheet. Since then I've sent you what I think are the four most useful things I've learned about keeping plants alive: read the signals, test the soil, flex the schedule, write it down.</p>

<p>If you did even half of those things, your plants are doing better than they were a fortnight ago. That's the goal.</p>

<p>Today I want to show you what happens when you take "write it down" seriously, with a system instead of a scrap of paper.</p>

<p>I designed five journals. Each one does one job, and they work together as a single routine. Here's the launch lineup, with the prices as of today:</p>

<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:16px 0;">
  <tr style="background:#f6f9f4;">
    <td style="padding:10px 14px;font-weight:600;border-bottom:1px solid #e3eae0;">Essential Tracker</td>
    <td style="padding:10px 14px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">succulents, cacti, single-plant log</td>
    <td style="padding:10px 14px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$6.99</td>
  </tr>
  <tr>
    <td style="padding:10px 14px;font-weight:600;border-bottom:1px solid #e3eae0;">Bloom Record</td>
    <td style="padding:10px 14px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">vegetable garden + harvest log</td>
    <td style="padding:10px 14px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$6.99</td>
  </tr>
  <tr style="background:#f6f9f4;">
    <td style="padding:10px 14px;font-weight:600;border-bottom:1px solid #e3eae0;">Seasonal Trio</td>
    <td style="padding:10px 14px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">3 seasonal covers — 90-day reset</td>
    <td style="padding:10px 14px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$11.99</td>
  </tr>
  <tr>
    <td style="padding:10px 14px;font-weight:600;border-bottom:1px solid #e3eae0;">Complete Set</td>
    <td style="padding:10px 14px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">all 5 journals — best value</td>
    <td style="padding:10px 14px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$17.99</td>
  </tr>
  <tr style="background:#f6f9f4;">
    <td style="padding:10px 14px;font-weight:600;">VIP Subscription</td>
    <td style="padding:10px 14px;color:#6a7a6b;">monthly journal + cheat sheets</td>
    <td style="padding:10px 14px;font-weight:600;color:#2f6b3a;text-align:right;">$4.99/mo</td>
  </tr>
</table>

<p>Pick the one that matches your situation. If you don't know yet, the <strong>Essential Tracker</strong> at $6.99 is the cheapest way to find out whether writing things down works for you. If it clicks, the <strong>Complete Set</strong> at $17.99 is the deal.</p>

<p>You can see all five covers, read what's inside each one, and check out at <a href="{shop_url}" style="color:#2f6b3a;">the shop</a>. No pressure — the cheat sheet and these emails will keep you growing whether you buy anything or not.</p>

<p>Thanks for letting me into your inbox for two weeks. It's been good to write to you.</p>

<p style="margin-top:24px;">Talk soon,<br>Joe<br><span style="color:#6a7a6b;font-size:14px;">Founder, The Garden Keeper</span></p>
"""
    return shell(subject, body, subscriber_email)