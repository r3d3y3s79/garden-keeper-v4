"""
Day 4 — "How to read a plant's signals (leaf color, droop, stretch)"
Practical cheat sheet. Builds on day 2's story.
"""
from ._base import shell

subject = "What your plant is trying to tell you"

target_sequence_day = 2
min_hours_since_last = 47  # ~2 days after day-2


def render_html(subscriber_email: str) -> str:
    body = """
<p>Plants can't talk. But they can show you exactly what's wrong, if you know where to look.</p>

<p>Here's the cheat sheet I wish someone had handed me in year one.</p>

<p><strong>Yellow leaves, mostly lower/older ones:</strong><br>
Usually overwatering, or a nitrogen shortfall. Stick a finger 3cm into the soil. If it's damp, hold off on water for a week. If it's bone dry and the rest of the plant looks pale, feed it.</p>

<p><strong>Yellow leaves, all over, including new growth:</strong><br>
Often a light problem. Too little light and the plant can't photosynthesise properly. Move it closer to a window, or add a grow light on a timer.</p>

<p><strong>Brown, crispy leaf tips:</strong><br>
Low humidity, or fluoride/chlorine in tap water. Try filtered water and group plants together so they humidify each other.</p>

<p><strong>Drooping, but soil is moist:</strong><br>
Root rot, almost always. Tip it out of the pot. If the roots are brown and squishy, cut them back, repot in fresh dry mix, and don't water for a week.</p>

<p><strong>Drooping, soil is dry:</strong><br>
It's thirsty. Water deeply, let it drain, and check again in an hour. Most plants bounce back fast from underwatering.</p>

<p><strong>Long, leggy stems with small leaves and big gaps between nodes:</strong><br>
Not enough light. The plant is stretching. Move it closer to a window, or rotate it so all sides get equal exposure.</p>

<p><strong>Brown soft spots on leaves:</strong><br>
Fungal infection, usually from water sitting on the leaf overnight. Water at the base, not over the top, and improve airflow around the plant.</p>

<p>Save this email. Next time something looks off, start at the top of the list and work down.</p>

<p style="margin-top:24px;">— Joe</p>
"""
    return shell(subject, body, subscriber_email)
