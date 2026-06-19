"""
Day 7 — "The watering trick that doubled my success rate"
Single insight, builds authority.
"""
from ._base import shell

subject = "The one watering trick that changed everything"

target_sequence_day = 4
min_hours_since_last = 71  # ~3 days after day-4


def render_html(subscriber_email: str) -> str:
    body = """
<p>I've tried every watering gadget on the market. Moisture meters. Self-watering globes. App-controlled drippers. Most of them sit in a drawer now.</p>

<p>The one trick I still use, every single time, costs nothing and works better than all of them:</p>

<p style="font-size:18px;line-height:1.5;color:#2f6b3a;"><strong>The chopstick test.</strong></p>

<p>Push a plain wooden chopstick (or a bamboo skewer) into the soil, about 4cm down. Pull it out. Look at it.</p>

<ul style="margin:8px 0 16px 20px;padding:0;line-height:1.7;">
  <li><strong>Comes out clean and dry:</strong> water now.</li>
  <li><strong>Comes out dark and damp with soil stuck to it:</strong> leave it another two or three days.</li>
  <li><strong>Comes out somewhere in between:</strong> check again tomorrow.</li>
</ul>

<p>That's the whole trick. No batteries. No app. No guesswork.</p>

<p>Why it works: the top of the soil dries out well before the root zone does. Watering based on what the surface looks like means you either water too early (and the roots sit in damp) or too late (and the plant wilts between waterings). The chopstick tells you what's happening where the roots actually are.</p>

<p>I started doing this in 2023. My plant survival rate went from about 60% to over 90% in a single season. The only plants I've lost since are the ones I skipped the test on because I was in a hurry.</p>

<p>Try it on your saddest plant this week. I think you'll be surprised.</p>

<p style="margin-top:24px;">— Joe</p>
"""
    return shell(subject, body, subscriber_email)
