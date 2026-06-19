#!/usr/bin/env python3
"""
Garden Keeper — Reddit manual-post kit builder.
Generates a one-click "submit to Reddit" deep link from a day-N draft,
plus an HTML page that wraps the link + the title/body for copy-paste fallback.

The Reddit submit endpoint accepts ?title= and ?text= query params.
It also pre-selects the subreddit and lets the user pick the flair in-UI.

Usage:
    python3 reddit_manual_kit.py --day 1                  # r/houseplants, prints URL + HTML
    python3 reddit_manual_kit.py --day 1 --open           # open the submit URL in default browser
    python3 reddit_manual_kit.py --day 1 --html out.html  # write standalone HTML page
    python3 reddit_manual_kit.py --all                    # print URL for days 1-30

Logs to data/reddit_manual_kit.json so we never re-suggest a day Joe already
says he posted.
"""
import os
import sys
import json
import argparse
import urllib.parse
import webbrowser
from pathlib import Path
from datetime import datetime

ROOT = Path("/root/the-garden-keeper")
DRAFTS = ROOT / "content" / "reddit"
SCHEDULE = ROOT / "content" / "reddit" / "schedule.json"
LOG = ROOT / "data" / "reddit_manual_kit.json"


def load_schedule() -> dict:
    return json.loads(SCHEDULE.read_text())


def load_draft(day: int) -> tuple[str, str]:
    """Return (title, body) from day-XX.md. The first line is 'Title: ...'."""
    p = DRAFTS / f"day-{day:02d}.md"
    if not p.exists():
        return None, None
    text = p.read_text()
    if text.startswith("Title:"):
        nl = text.index("\n")
        title = text[len("Title:"):nl].strip()
        body = text[nl+1:].strip()
        return title, body
    return None, None


def build_submit_url(subreddit: str, title: str, body: str) -> str:
    base = f"https://www.reddit.com/r/{subreddit}/submit"
    qs = urllib.parse.urlencode({"title": title, "text": body})
    return f"{base}?{qs}"


def render_html(day: int, sub: str, title: str, body: str, url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Day {day} — r/{sub}</title>
<style>
  body {{ font: 15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; max-width: 720px; margin: 32px auto; padding: 0 16px; color: #1f2d20; background: #f6f9f4; }}
  h1 {{ color: #2f6b3a; margin-bottom: 4px; }}
  .sub {{ color: #6a7a6b; font-size: 14px; margin-bottom: 24px; }}
  .card {{ background: #fff; border-radius: 14px; padding: 24px 28px; box-shadow: 0 4px 18px rgba(0,0,0,0.06); }}
  a.cta {{ display: inline-block; background: #2f6b3a; color: #fff !important; padding: 14px 22px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 16px 0 24px; }}
  h2 {{ font-size: 17px; margin-top: 24px; }}
  pre {{ background: #f6f9f4; border: 1px solid #e3eae0; border-radius: 8px; padding: 14px; white-space: pre-wrap; word-wrap: break-word; font: 14px/1.5 ui-monospace, 'SF Mono', Menlo, monospace; }}
  .copy {{ cursor: pointer; background: #2f6b3a; color: #fff; border: 0; padding: 6px 12px; border-radius: 6px; font-size: 13px; margin-left: 8px; }}
  .meta {{ color: #6a7a6b; font-size: 13px; margin-top: 8px; }}
</style></head>
<body>
<h1>Day {day} manual post kit</h1>
<div class="sub">Subreddit: <strong>r/{sub}</strong> · Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
<div class="card">
  <p>Reddit OAuth is blocked, so this kit makes the manual post a one-click action. Click the green button below — it opens Reddit's submit page with the title and body pre-filled. You just pick the flair and click Post.</p>
  <a class="cta" href="{url}" target="_blank" rel="noopener">Open r/{sub} submit (pre-filled) →</a>
  <h2>Title <button class="copy" onclick="navigator.clipboard.writeText(document.getElementById('t').textContent)">Copy</button></h2>
  <pre id="t">{title}</pre>
  <h2>Body <button class="copy" onclick="navigator.clipboard.writeText(document.getElementById('b').textContent)">Copy</button></h2>
  <pre id="b">{body}</pre>
  <p class="meta">After you post, paste the resulting reddit.com/r/{sub}/comments/... URL into the project tracker so we can attribute traffic to the manual-post path.</p>
</div>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--html", help="path to write standalone HTML for the day")
    args = ap.parse_args()

    sched = load_schedule()
    posts = {p["day"]: p for p in sched["posts"]}

    if args.all:
        for day in range(1, 31):
            p = posts[day]
            t, b = load_draft(day)
            if not t:
                continue
            url = build_submit_url(p["subreddit"], t, b)
            print(f"day {day:>2}  r/{p['subreddit']:<20}  {url}")
        return

    if not args.day:
        ap.error("--day N or --all required")

    p = posts.get(args.day)
    if not p:
        sys.exit(f"day {args.day} not in schedule.json")

    title, body = load_draft(args.day)
    if not title:
        sys.exit(f"day-{args.day:02d}.md missing or malformed")

    url = build_submit_url(p["subreddit"], title, body)

    print(f"=== Day {args.day}: r/{p['subreddit']} ===")
    print(f"TITLE: {title}")
    print(f"BODY ({len(body)} chars):")
    print(body)
    print()
    print(f"SUBMIT URL ({len(url)} chars):")
    print(url)

    if args.html:
        html = render_html(args.day, p["subreddit"], title, body, url)
        Path(args.html).write_text(html)
        print(f"\nHTML written: {args.html}")

    if args.open:
        webbrowser.open(url)
        print("\n(opened in default browser)")

    # Log it
    log = []
    if LOG.exists():
        log = json.loads(LOG.read_text())
    log.append({
        "day": args.day,
        "subreddit": p["subreddit"],
        "title": title,
        "url": url,
        "generated_at": datetime.utcnow().isoformat(),
    })
    LOG.write_text(json.dumps({"kits": log}, indent=2))


if __name__ == "__main__":
    main()
