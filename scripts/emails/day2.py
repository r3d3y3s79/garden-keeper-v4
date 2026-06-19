"""
Day 2 — "My 5 houseplants that almost died (and what I learned)"
Sent ~24h after day-1. Story-driven, low-pressure, gives value.
"""
from ._base import shell

subject = "The 5 houseplants I nearly killed"

# Subscriber is currently at sequence_day=1 (just received day-1).
# Wait at least 23h since last_sent_at before sending day 2.
target_sequence_day = 1
min_hours_since_last = 23


def render_html(subscriber_email: str) -> str:
    body = """
<p>Quick story before the tips.</p>

<p>Two summers ago I nearly killed five plants in a row. A fiddle leaf fig, a calathea, a peace lily, a pilea, and a basil I'd put on the windowsill.</p>

<p>What they had in common wasn't bad luck. It was me, doing the same four things on repeat:</p>

<ul style="margin:8px 0 16px 20px;padding:0;line-height:1.7;">
  <li>Watering on the same day every week, regardless of weather</li>
  <li>Trusting the moisture meter more than the actual soil</li>
  <li>Leaving them in the same spot year-round</li>
  <li>Repotting "later" until the roots were circling the pot</li>
</ul>

<p>The fiddle leaf dropped eight leaves in a fortnight. The calathea went crispy at the edges despite me misting it twice a day. The peace lily sat in a soggy pot for so long the roots started to smell.</p>

<p>What I learned: <strong>most plant problems are rhythm problems.</strong> Watering, light, feeding — they all need to flex with the season, the room, and the plant's actual stage of growth.</p>

<p>Once I started treating the schedule as a suggestion and the plant as the source of truth, everything got easier. The fiddle leaf has put out three new leaves this month. The calathea is, against all odds, still alive.</p>

<p>One thing I do now that I wish I'd started sooner: I write down what I did to each plant on the day I did it. Two lines. "Watered. Soil still damp at 3cm." That's it.</p>

<p>More on that coming later in the week.</p>

<p style="margin-top:24px;">Talk tomorrow,<br>Joe</p>
"""
    return shell(subject, body, subscriber_email)
