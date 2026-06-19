#!/usr/bin/env python3
"""
Garden Keeper — Reddit Draft Validator
Runs Reddit's content rules against every draft and prints a
pass/fail report. Also checks our internal "value-first" rules
(no links in body weeks 1-3, soft-promo only weeks 4+).

Reddit hard rules checked:
  - Title: 1-300 chars
  - Body:  1-40,000 chars
  - Body does not start with a link (auto-removed on most subs)
  - No more than 1 URL in the body
  - Body has actual content (not just title repeated)

Our content rules:
  - Weeks 1-3 (days 1-21): no URLs in body. Post should end with a
    conversational question (engagement signal).
  - Week 4 (days 22-30): at most 1 URL in body, no overt "buy now"
    phrasing, must still end with a question or open invitation.
  - No spammy words: "free", "limited time", "act now", "discount"
  - No all-caps words > 4 chars

Exit 0 = all clean, 1 = failures found.
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = SCRIPT_DIR.parent / "content" / "reddit"
SCHEDULE_PATH = CONTENT_DIR / "schedule.json"

REDDIT_TITLE_MIN = 1
REDDIT_TITLE_MAX = 300
REDDIT_BODY_MIN = 1
REDDIT_BODY_MAX = 40_000

SPAMMY_WORDS = [
    r"\bfree\b(?!.*?(?:cheat sheet|template|guide|download|version))",  # "free" only OK if in context
    r"\blimited time\b",
    r"\bact now\b",
    r"\bdiscount\b",
    r"\bbuy now\b",
    r"\bsign up today\b",
    r"\bexclusive offer\b",
    r"\bclick here\b",
]
ALLCAPS_RE = re.compile(r"\b[A-Z]{5,}\b")
URL_RE = re.compile(r"https?://[^\s\)]+|www\.[^\s\)]+|redd\.it/[^\s\)]+")


def parse_draft(path: Path):
    text = path.read_text()
    if not text.startswith("Title:"):
        return None, None
    parts = text.split("\n\n", 1)
    title = parts[0].replace("Title: ", "").strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def check_hard_rules(title, body):
    issues = []
    if len(title) < REDDIT_TITLE_MIN or len(title) > REDDIT_TITLE_MAX:
        issues.append(f"Title length {len(title)} (must be {REDDIT_TITLE_MIN}-{REDDIT_TITLE_MAX})")
    if len(body) < REDDIT_BODY_MIN:
        issues.append(f"Body too short: {len(body)} chars")
    if len(body) > REDDIT_BODY_MAX:
        issues.append(f"Body too long: {len(body)} chars (max {REDDIT_BODY_MAX})")
    if body.startswith(("http://", "https://", "www.", "**http")):
        issues.append("Body starts with a URL — Reddit auto-removes these")
    urls = URL_RE.findall(body)
    if len(urls) > 1:
        issues.append(f"Body has {len(urls)} URLs — most subs cap at 1")
    if not body or body.lower() == title.lower():
        issues.append("Body is empty or just repeats the title")
    return issues


def check_internal_rules(day_num, title, body, post_type):
    issues = []
    urls = URL_RE.findall(body)
    body_word_count = len(body.split())

    # Week 1-3 (days 1-21): value-first, no URLs
    if day_num <= 21:
        if urls:
            issues.append(f"Week 1-3 post has {len(urls)} URL(s) — value-first only")
        # Soft check for hard-sell phrasing
        sell_phrases = ["I built", "I'm selling", "I made a", "I designed", "I created a"]
        for phrase in sell_phrases:
            if phrase.lower() in body.lower() and day_num <= 14:
                # Week 1-2 is pure value, weeks 3 may use first-person
                if day_num <= 7:
                    issues.append(f"Week 1 should not have self-promo language: '{phrase}'")
        # Engagement: should end with a question or invitation
        last_para = body.strip().split("\n\n")[-1].strip()
        if not (last_para.endswith("?") or last_para.lower().startswith(("anyone", "what", "how", "share", "thoughts"))):
            issues.append("Last paragraph doesn't end with a question or open invitation")

    # Week 4 (days 22-30): at most 1 URL, no hard sell
    elif day_num >= 22:
        if len(urls) > 1:
            issues.append(f"Week 4 post has {len(urls)} URLs — max 1 for soft-promo")
        # Check for spammy words
        for pat in SPAMMY_WORDS:
            if re.search(pat, body, re.IGNORECASE):
                issues.append(f"Spammy phrase detected: {pat}")
        # No all-caps words > 4 chars
        caps = ALLCAPS_RE.findall(body)
        if caps:
            issues.append(f"All-caps words: {caps}")
        # Engagement same as above
        last_para = body.strip().split("\n\n")[-1].strip()
        if not (last_para.endswith("?") or last_para.lower().startswith(("anyone", "what", "how", "share", "thoughts", "comment"))):
            issues.append("Last paragraph doesn't end with a question or open invitation")

    # All weeks: body should be 100-500 words (sweet spot for Reddit)
    if body_word_count < 100:
        issues.append(f"Body too short: {body_word_count} words (target 150-350)")
    if body_word_count > 500:
        issues.append(f"Body too long: {body_word_count} words (target 150-350)")

    return issues


def main():
    schedule = json.loads(SCHEDULE_PATH.read_text())
    posts = schedule["posts"]

    total = 0
    passed = 0
    failed = 0
    warnings = 0

    print("=" * 70)
    print(f"Reddit Draft Validator — {len(posts)} posts to check")
    print("=" * 70)

    for post in posts:
        day = post["day"]
        path = CONTENT_DIR / post["title_file"]
        if not path.exists():
            print(f"  ❌ day-{day:02d} ({post['title_file']}): FILE MISSING")
            failed += 1
            total += 1
            continue

        title, body = parse_draft(path)
        if not title or not body:
            print(f"  ❌ day-{day:02d}: parse failed (no Title/body)")
            failed += 1
            total += 1
            continue

        hard_issues = check_hard_rules(title, body)
        internal_issues = check_internal_rules(day, title, body, post["type"])
        all_issues = hard_issues + internal_issues

        total += 1
        if all_issues:
            print(f"  ⚠️  day-{day:02d} r/{post['subreddit']} ({post['type']}): {len(all_issues)} issue(s)")
            for iss in all_issues:
                print(f"      - {iss}")
            warnings += len(all_issues)
            failed += 1
        else:
            print(f"  ✅ day-{day:02d} r/{post['subreddit']:14s} {post['type']:18s} {len(title):3d}c title / {len(body.split()):3d}w body")
            passed += 1

    print()
    print("=" * 70)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Warnings: {warnings}")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
