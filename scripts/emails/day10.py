"""
Day 10 — "Why I started writing in a journal (and the plant I lost that made me do it)"
Founder story, emotional pull.
"""
from ._base import shell

subject = "The plant I lost that started this whole thing"

target_sequence_day = 7
min_hours_since_last = 71  # ~3 days after day-7


def render_html(subscriber_email: str) -> str:
    body = """
<p>I lost a fiddle leaf fig in 2022 and I still think about it.</p>

<p>Not because it was expensive — it wasn't — but because I couldn't tell you what happened. I'd watered it on Tuesday, like always. I'd moved it a metre closer to the window in autumn. I'd wiped the leaves, fed it once a month, done all the things I thought I was supposed to do.</p>

<p>Then one Tuesday it dropped a leaf. Then another. Then eleven in a week.</p>

<p>By the time I tipped it out of the pot to look at the roots, the root ball was a soggy brown brick. The plant was gone. I threw it out and went for a walk, and on the walk I realised: I had no record of what I'd done. I'd watered "regularly" but I couldn't tell you when, or how much, or whether the soil had been dry that day or wet. I just had a feeling.</p>

<p>That weekend I bought a cheap notebook and wrote down the date, what I did to each plant, and what the plant looked like. Two lines per plant. That's it.</p>

<p>Three months in, I could see patterns I'd never noticed. The calathea hated the spot by the heater in winter. The monstera loved the bathroom after showers. The snake plant sulked when I repotted it but exploded with new growth two months later.</p>

<p>I stopped guessing. The plants got healthier. I got less anxious. And the notebook filled up, plant by plant.</p>

<p>That notebook is why The Garden Keeper exists. Not as a brand idea, but because I wanted one that was actually designed to record what the plant is doing, not just what I'm planning to do to it.</p>

<p>More on that soon. But first: a question. Have you ever kept a plant journal, even a rough one? Reply and tell me. I read every response.</p>

<p style="margin-top:24px;">— Joe</p>
"""
    return shell(subject, body, subscriber_email)
