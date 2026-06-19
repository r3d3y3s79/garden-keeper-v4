#!/usr/bin/env python3
"""
Garden Keeper — Reddit Draft Generator
Auto-generates the missing day-XX.md drafts in the same voice as the
existing 20. Each draft is value-first, conversational, 150-350 words,
no overt promo in weeks 1-3, light promo only in week 4.

Reads the schedule.json to know which (subreddit, type, flair) each
new draft must target. Output: ../content/reddit/day-XX.md files
matching the format of the existing ones (Title: ...\n\n<body>).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Path resolution — works whether called from / or /root/the-garden-keeper
SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = SCRIPT_DIR.parent / "content" / "reddit"
SCHEDULE_PATH = CONTENT_DIR / "schedule.json"


def load_schedule():
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


def parse_existing_draft(path: Path):
    """Parse an existing draft into (title, body)."""
    text = path.read_text()
    if not text.startswith("Title:"):
        return None, None
    parts = text.split("\n\n", 1)
    title = parts[0].replace("Title: ", "").strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def voice_signature_examples():
    """Return 3 example bodies from existing drafts so the generator
    can match tone, length, sentence structure, and emoji usage."""
    examples = []
    for n in [1, 7, 15]:
        path = CONTENT_DIR / f"day-{n:02d}.md"
        if path.exists():
            t, b = parse_existing_draft(path)
            if t and b:
                examples.append((t, b))
    return examples


# All drafts that need to be generated. Day 21 was missing from the
# original content folder, days 22-30 were referenced in schedule.json
# but never written. All hand-authored to match the existing voice:
# casual, first-person, value-first, ends with a question, uses bold
# sparingly, no markdown headers.
MISSING_DRAFTS = {
    21: {
        "subreddit": "houseplants",
        "type": "troubleshooting",
        "flair": "Help",
        "title": "Why your plant is 'leggy' (and the cheap fix that actually works)",
        "body": (
            "Leggy = stretching toward the light. Long, thin stems with big gaps between leaves. It's not a death sentence, but it means the plant isn't getting enough light to grow compact.\n\n"
            "**Why it happens:**\n"
            "- The light source is too far away (most \"bright indirect light\" is dimmer than people think)\n"
            "- The plant only gets light from one direction (it grows toward the window)\n"
            "- It's winter and daylight hours dropped (most leggy growth happens Feb-March)\n\n"
            "**The fix that actually works:**\n"
            "1. Move the plant closer to the window (within 2-3 feet for most species)\n"
            "2. Rotate it 90° every week so growth stays even\n"
            "3. If natural light isn't enough, add a $20-40 LED grow light on a timer for 4-6 hours/day\n"
            "4. Prune the leggy growth back to a node — new growth will come in bushier\n\n"
            "**What doesn't work:**\n"
            "- \"Just put it in a sunnier spot\" without checking the actual light levels\n"
            "- Moving it outside suddenly (sunburn on adapted leaves is real)\n"
            "- Fertilizing (the plant isn't hungry, it's reaching)\n\n"
            "After 2-3 months of proper light, you'll see shorter stem segments and bigger leaves. The plant is responding to better conditions.\n\n"
            "Anyone else have a leggy plant they rehabbed? How long did it take to look normal again?"
        ),
    },
    22: {
        "subreddit": "IndoorGarden",
        "type": "product-anchored",
        "flair": "Resource",
        "title": "I made a printable plant care cheat sheet — free for the community",
        "body": (
            "After answering the same five questions about my plants in every plant group I'm in, I sat down and made a one-page cheat sheet I wish had existed when I started.\n\n"
            "It's not an app. It's not a subscription. It's a single PDF that fits on a fridge.\n\n"
            "What's on it:\n"
            "- The 6 most common houseplants and what they actually need (light, water, humidity, soil)\n"
            "- A watering decision tree (chopstick test + finger test + pot weight)\n"
            "- The 4 yellow-leaf patterns and what each one means\n"
            "- A 12-month fertilizer schedule you can actually follow\n"
            "- A simple log section to track your own plants\n\n"
            "I built it because the plant-care internet is full of advice that contradicts itself. This is the version I distilled from killing 30+ plants and learning what actually works.\n\n"
            "Drop a comment with \"cheat sheet\" and I'll DM you the link. No email signup, no mailing list, no \"join my free workshop.\" Just the file.\n\n"
            "If people find it useful I'll do a v2 with more species."
        ),
    },
    23: {
        "subreddit": "plantclinic",
        "type": "value",
        "flair": "Tip",
        "title": "When to repot (and the 3 signs that say 'not yet')",
        "body": (
            "Most \"repot your plant\" advice is wrong about half the time. Plants get repotted when they don't need it and stressed out for weeks.\n\n"
            "Here's how I tell when it's actually time:\n\n"
            "**Repot if:**\n"
            "- Roots are growing out of the drainage holes\n"
            "- Water runs straight through the pot without being absorbed\n"
            "- The plant is physically top-heavy and tips over\n"
            "- It's been in the same soil 2+ years and growth has stalled\n\n"
            "**Don't repot if:**\n"
            "- It's winter (most plants are dormant — wait until spring)\n"
            "- The plant is currently flowering (repotting drops buds)\n"
            "- It just got over a pest or disease (it's already stressed)\n"
            "- You just brought it home (give it 2-4 weeks to acclimate first)\n\n"
            "When you do repot, go up only 1-2 inches in pot diameter. Going from a 6\" to a 10\" pot is the most common repotting mistake — too much wet soil around small roots = root rot.\n\n"
            "Anyone else have a \"I repotted it and it got worse\" story?"
        ),
    },
    24: {
        "subreddit": "houseplants",
        "type": "case-study",
        "flair": "Story",
        "title": "I gave my partner a plant journal for Christmas. 6 months later, they're hooked.",
        "body": (
            "My partner had killed 3 succulents in a row and declared themselves a \"plant murderer.\" Last Christmas I gave them a cheap notebook and said \"just write down when you water it.\"\n\n"
            "I expected it to last 2 weeks. It's now 6 months in and they have 11 living plants.\n\n"
            "What changed:\n\n"
            "**The first month:** They wrote \"watered monstera 12/26\" and nothing else. I had to remind them to use it. The succulents stayed alive purely because they were being watered monthly instead of weekly.\n\n"
            "**Month 2:** They started noting new growth. \"Monstera has a new leaf unfurling 1/14.\" This was a breakthrough — they were observing instead of just maintaining.\n\n"
            "**Month 3:** They added a notes column. \"Why are the leaves yellow on the bottom?\" — then Google, then fix. The journal turned into a learning tool.\n\n"
            "**Month 4-6:** They started propagating. Cuttings from friends' plants. Trades at the local plant swap. The collection grew because they felt competent, not because they were buying more.\n\n"
            "The whole thing cost me $8 (notebook) and they now have a hobby they love. I'm not going to pretend I designed this — I just read somewhere that writing things down builds the habit, and the habit built the confidence.\n\n"
            "Has anyone else turned a \"black thumb\" partner into a plant person?"
        ),
    },
    25: {
        "subreddit": "gardening",
        "type": "troubleshooting",
        "flair": "Help",
        "title": "Tomato hornworm vs. tobacco hornworm: a gardener's field guide",
        "body": (
            "If you've ever walked out to your tomato plants and seen a 4-inch green caterpillar with a horn on its butt, you have a Manduca situation. The question is which one.\n\n"
            "They look almost identical. Both eat tomatoes, both have that weird tail horn, both turn into beautiful hawk moths. But the difference matters because of how they lay eggs and how to interrupt their cycle.\n\n"
            "**Tomato hornworm (Manduca quinquemaculata):**\n"
            "- V-shaped white stripes on the side, no diagonal lines\n"
            "- Horn is dark blue/black, sometimes curved\n"
            "- 8 white eggs laid singly on upper leaves\n"
            "- 1 generation per year in the north, 2 in the south\n\n"
            "**Tobacco hornworm (Manduca sexta):**\n"
            "- Diagonal white stripes on the side, no V shapes\n"
            "- Horn is red/orange (this is the easier tell)\n"
            "- Eggs laid on both upper and lower leaves\n"
            "- More common in the southeast US\n\n"
            "**The good news:** Braconid wasps parasitize both. If you see a hornworm covered in white rice-looking cocoons, LEAVE IT. The wasps are hatching and will handle the rest of the generation.\n\n"
            "**Manual control:** Hand-pick at dawn or dusk (they're easier to spot then), drop in soapy water. Check the undersides of leaves for eggs.\n\n"
            "**Prevention:** Till the soil in fall to kill pupae. Plant basil, marigold, or dill nearby as trap crops.\n\n"
            "Anyone else do a weekly hornworm hunt? It's honestly one of the most satisfying garden chores."
        ),
    },
    26: {
        "subreddit": "IndoorGarden",
        "type": "value",
        "flair": "Discussion",
        "title": "Grow lights: the math I did before I bought mine (and the answer surprised me)",
        "body": (
            "I almost bought a $200 full-spectrum grow light setup. Then I did the math.\n\n"
            "Here's what I actually needed to figure out:\n\n"
            "**PPFD (photosynthetic photon flux density):** the measurement that actually matters. Plants need 100-300 PPFD for low-light species, 300-600 for medium, 600+ for fruiting/flowering.\n\n"
            "**Footprint:** how big an area the light covers at the right intensity. Cheap lights claim 4x4 ft coverage but only deliver usable light to a 1x1 ft area.\n\n"
            "**Watts per square foot:** the real budget metric. Low-light plants need ~20W/sqft, high-light need 30-40W/sqft. Calculate your coverage area FIRST, then size the light to that.\n\n"
            "**What I learned:**\n"
            "- My \"bright window\" is closer to 50 PPFD on a good day. Most houseplants survive but don't grow.\n"
            "- A single $40 LED panel from a reputable brand delivered 200 PPFD across a 2x2 ft area. That's enough for 90% of my collection.\n"
            "- The $200 setup would've been overkill. I'd have been paying for features (dimmable, daisy-chain, app control) I don't need.\n\n"
            "**The shortcut formula:**\n"
            "1. Measure your space\n"
            "2. Pick plants rated for that PPFD range\n"
            "3. Buy the cheapest light that hits those numbers in your footprint\n"
            "4. Skip the smart features\n\n"
            "Anyone else do the math first, or are you all just going by vibes and reviews?"
        ),
    },
    27: {
        "subreddit": "plantclinic",
        "type": "case-study",
        "flair": "Story",
        "title": "How I saved my monstera from a thrips infestation (with photos, day by day)",
        "body": (
            "Found thrips on my monstera on a Tuesday. By the following Tuesday, I'd spent $80, lost 4 leaves, and learned more than I ever wanted to about the order Thysanoptera.\n\n"
            "**Day 1 (Tuesday):** Spotted black specks on the leaves and silver streaks on the new growth. Confirmed thrips with my phone camera and a Google search. Panicked.\n\n"
            "**Day 2:** Quarantined the plant in the bathroom. Wiped every leaf (top AND bottom) with 70% isopropyl alcohol and a microfiber cloth. Tedious but effective. The adults are slow and the alcohol kills on contact.\n\n"
            "**Day 3:** Bought Bonide systemic granules ($15) and Captain Jack's deadbug brew ($20). Dosed the soil with the systemic, sprayed the leaves with the Bt.\n\n"
            "**Day 4-7:** Daily leaf inspections. Found 2-3 adults per day, wiped and sprayed. New damage slowed dramatically. The systemic takes 7-14 days to fully work its way through the plant tissue.\n\n"
            "**Day 8-10:** Started seeing the larvae (tiny yellow specks that don't move much). The Bt was killing them before they could pupate. Population visibly down.\n\n"
            "**Day 11-14:** Zero new damage. Two new leaves unfurled with no silver streaks. I declared victory and moved the plant back to its normal spot.\n\n"
            "**What I'd do differently:**\n"
            "- Start the systemic on Day 1, not Day 3. Earlier intervention = less damage.\n"
            "- Treat ALL nearby plants preventatively. Thrips are fliers and they spread.\n"
            "- Don't trust a single negative inspection. Quarantine for 3 full weeks after the last sighting.\n\n"
            "Lost 4 leaves, kept the plant. The new growth that's come in since is bigger than any of the leaves I lost.\n\n"
            "Anyone else win a thrips war? What was your timeline?"
        ),
    },
    28: {
        "subreddit": "houseplants",
        "type": "product-anchored",
        "flair": "Resource",
        "title": "I built a 5-year plant journal. Sharing the free version with this sub.",
        "body": (
            "I've been plant journaling for 5 years. Different notebooks, different formats, lots of trial and error. Last month I finally compiled everything that actually worked into a single printable journal I wish had existed on day 1.\n\n"
            "It's designed for someone with 5-50 plants who wants to keep them alive without becoming a slave to a spreadsheet.\n\n"
            "**What's in it:**\n\n"
            "**Per-plant pages** — 30 of them. Each gets a full page with watering log, fertilizer schedule, growth tracking, photo placement, and a notes section for problems/observations. One page per plant per year lasts most people.\n\n"
            "**Monthly check-in pages** — 12 of them. Quick walkthrough checklist + room for noting seasonal changes, pest sightings, watering schedule adjustments.\n\n"
            "**Problem diagnosis flowchart** — the one-page version of the cheat sheet I posted a few months back. Yellow leaves? Brown tips? Drooping? Follow the arrows.\n\n"
            "**Seasonal care calendar** — when to fertilize, when to repot, when to expect dormancy, when to expect growth spurts. For tropicals AND outdoor garden plants.\n\n"
            "**Propagation log** — 20 entries for tracking cuttings, with success/failure columns so you start to see patterns.\n\n"
            "I'm sharing the print-at-home version for free. If you're a chronic plant killer like I was, this is the system that took me from 60% mortality to under 10%.\n\n"
            "Comment \"journal\" and I'll DM you the link. No email signup. Just a file."
        ),
    },
    29: {
        "subreddit": "IndoorGarden",
        "type": "question",
        "flair": "Question",
        "title": "What's one habit that made you a better plant parent?",
        "body": (
            "Curious what single change made the biggest difference for people here. I'll start:\n\n"
            "**My one habit:** The Sunday sweep.\n\n"
            "Every Sunday morning, I walk through every plant in the house with a watering can. I don't water all of them — just the ones that need it (chopstick test). While I'm at it, I rotate any leaning plants, wipe dust off big leaves, and glance at the undersides for pests.\n\n"
            "Takes 20-30 minutes for ~30 plants. Nothing fancy.\n\n"
            "What it fixed:\n"
            "- I stopped watering on a schedule (overwatering dropped to almost zero)\n"
            "- I catch pest problems early (caught 2 thrips infestations in week 1 instead of month 3)\n"
            "- I notice growth I'm proud of (turns out plants being alive is rewarding when you slow down enough to see it)\n\n"
            "The plants that died in my collection were always the ones I forgot to check for a few weeks. The Sunday sweep prevents forgetting.\n\n"
            "What's your one habit? Could be a daily thing, a monthly thing, a one-time setup that changed everything. Just curious what works for other people here."
        ),
    },
    30: {
        "subreddit": "gardening",
        "type": "case-study",
        "flair": "Story",
        "title": "Three seasons, one garden journal: what the data actually taught me",
        "body": (
            "I started a garden journal because I kept buying the same seeds twice. Three seasons later, I have data I never expected to collect.\n\n"
            "**Spring (Year 1):** Tracked planting dates, germination rates, first true leaves. Learned: my soil temperature matters more than the calendar. Two weeks \"late\" in warm soil beat one week \"on time\" in cold soil, every time.\n\n"
            "**Summer (Year 1):** Added a daily observation line. \"Tomato hornworm on Brandywine 7/14.\" \"First harvest 7/28.\" The data showed me that my squash bugs showed up within 3 days of consistent 80°F+ nights — not a calendar date.\n\n"
            "**Fall (Year 1):** Tracked what I actually ate vs. what I grew. Discovered I grew 4x more zucchini than I could use and 1/3 of the green beans I wanted. The journal turned into a planning tool.\n\n"
            "**Spring (Year 2):** Cross-referenced Year 1 data. Planted 1 zucchini instead of 4. Doubled green beans. Added a row of stuff my family actually eats (kale, snap peas, cherry tomatoes).\n\n"
            "**Summer (Year 2):** Tracked pest pressure by location. The data showed me my north bed had 80% fewer hornworms than the south bed. Moved tomatoes to the north side. Zero hornworm damage all year.\n\n"
            "**Fall (Year 2):** Started a seed inventory. I now know exactly what I have, when it expires, and what I need to buy. No more duplicate purchases.\n\n"
            "**Spring (Year 3):** The journal isn't a project anymore. It's a tool I use the way I use a recipe book. The data compounds — Year 3 was the easiest gardening year I've ever had, and the harvest was the biggest.\n\n"
            "If you're on the fence about starting one, start small. One page, one row per planting, one column for observations. That's it. The data will tell you what else to track.\n\n"
            "Anyone else have a multi-year journal story?"
        ),
    },
}


def write_drafts(drafts_to_write=None):
    """Write missing drafts. If drafts_to_write is None, write all MISSING_DRAFTS."""
    if drafts_to_write is None:
        drafts_to_write = list(MISSING_DRAFTS.keys())

    written = []
    for day_num in drafts_to_write:
        if day_num not in MISSING_DRAFTS:
            print(f"  Skip: day-{day_num:02d} not in MISSING_DRAFTS")
            continue
        d = MISSING_DRAFTS[day_num]
        out_path = CONTENT_DIR / f"day-{day_num:02d}.md"
        if out_path.exists():
            print(f"  Skip: {out_path.name} already exists")
            continue
        content = f"Title: {d['title']}\n\n{d['body']}\n"
        out_path.write_text(content)
        size = len(content)
        words = len(d["body"].split())
        print(f"  Wrote: {out_path.name} ({size} chars, {words} body words, type={d['type']}, sub={d['subreddit']})")
        written.append(out_path)

    return written


def update_schedule_with_new_files(written):
    """No-op for now — schedule.json already references day-22 through day-30."""
    pass


def main():
    print("=" * 60)
    print(f"Garden Keeper — Reddit Draft Generator")
    print(f"Run at: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 60)

    schedule = load_schedule()
    expected_days = [p["day"] for p in schedule["posts"]]
    print(f"Schedule expects {len(expected_days)} posts (day 1-30)")

    existing = sorted([p.stem for p in CONTENT_DIR.glob("day-*.md")])
    print(f"Existing drafts: {len(existing)} ({existing[0]} ... {existing[-1]})")

    missing_nums = []
    for d in expected_days:
        if f"day-{d:02d}" not in existing:
            missing_nums.append(d)
    print(f"Missing drafts: {len(missing_nums)} (day {missing_nums})")

    if not missing_nums:
        print("\nNo missing drafts. Nothing to write.")
        return 0

    print(f"\nWriting {len(missing_nums)} drafts to {CONTENT_DIR}...")
    written = write_drafts(missing_nums)
    print(f"\nDone. Wrote {len(written)} new files.")

    # Voice-conformance check
    print("\nVoice conformance check (vs existing drafts):")
    existing_lens = []
    for p in CONTENT_DIR.glob("day-*.md"):
        t, b = parse_existing_draft(p)
        if b:
            existing_lens.append(len(b.split()))
    if existing_lens:
        avg = sum(existing_lens) / len(existing_lens)
        print(f"  Existing drafts avg body length: {avg:.0f} words (range {min(existing_lens)}-{max(existing_lens)})")
        new_lens = [len(MISSING_DRAFTS[d]["body"].split()) for d in missing_nums if d in MISSING_DRAFTS]
        if new_lens:
            print(f"  New drafts avg body length: {sum(new_lens)/len(new_lens):.0f} words (range {min(new_lens)}-{max(new_lens)})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
