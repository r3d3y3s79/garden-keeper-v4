#!/usr/bin/env python3
"""
Garden Keeper — Reddit Poster (v3 REST path)

Per JOE-82 (2026-06-19), Composio MCP endpoint at connect.composio.dev/mcp
returns HTTP 401 with the ak_… API key. The v3 REST endpoint
backend.composio.dev/api/v3/tools/execute/<TOOL> ACCEPTS the ak_… key
via the x-api-key header. This script uses the v3 REST path.

Usage:
  python3 scripts/reddit_poster_v3.py --day 1
  python3 scripts/reddit_poster_v3.py --day 1 --dry-run
  python3 scripts/reddit_poster_v3.py --next
  python3 scripts/reddit_poster_v3.py --list
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = SCRIPT_DIR.parent / "content" / "reddit"
DATA_DIR = SCRIPT_DIR.parent / "data"
SCHEDULE_PATH = CONTENT_DIR / "schedule.json"
LOG_PATH = DATA_DIR / "reddit_posted.json"

COMPOSIO_V3_URL = "https://backend.composio.dev/api/v3/tools/execute/REDDIT_CREATE_REDDIT_POST"
ENV_PATH = Path("/root/.hermes/.env")


def load_api_key():
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith("COMPOSIO_API_KEY="):
            return line.split("=", 1)[1].strip()
    return None


def parse_draft(path: Path):
    text = path.read_text()
    if not text.startswith("Title:"):
        return None, None
    parts = text.split("\n\n", 1)
    title = parts[0].replace("Title: ", "").strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def load_log():
    if not LOG_PATH.exists():
        return {"posts": []}
    try:
        return json.loads(LOG_PATH.read_text())
    except json.JSONDecodeError:
        return {"posts": []}


def save_log(log):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2))


def v3_post(api_key, subreddit, title, body, flair=None):
    """POST to Composio v3 REST execute endpoint."""
    arguments = {
        "subreddit": subreddit,
        "title": title,
        "body": body,
    }
    if flair:
        arguments["flair"] = flair
    # Try multiple payload shapes — exact schema varies by tool version
    for payload in [
        {"tool_slug": "REDDIT_CREATE_REDDIT_POST", "arguments": arguments},
        {"toolName": "REDDIT_CREATE_REDDIT_POST", "input": arguments},
        {"arguments": arguments},
    ]:
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
        }
        req = urllib.request.Request(COMPOSIO_V3_URL, data=body_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8", errors="replace")
                return True, f"HTTP {r.status}: {text[:800]}", text
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
            # If 422, try next shape
            if e.code == 422:
                continue
            return False, f"HTTP {e.code}: {err_body}", err_body
        except Exception as e:
            return False, f"Request error: {e}", str(e)
    return False, "All payload shapes failed (422)", ""


def list_status():
    schedule = json.loads(SCHEDULE_PATH.read_text())
    log = load_log()
    posted_days = {p["day"] for p in log["posts"]}
    print("=" * 70)
    print("Reddit Posting Status (v3 REST path)")
    print("=" * 70)
    print(f"Total posts in schedule: {len(schedule['posts'])}")
    print(f"Posts already made:       {len(posted_days)}")
    print(f"Remaining:                {len(schedule['posts']) - len(posted_days)}")
    print()
    for p in schedule["posts"]:
        status = "✅ posted" if p["day"] in posted_days else "⏳ pending"
        print(f"  day-{p['day']:02d}  {status:<12} r/{p['subreddit']:<14} {p['type']:<18} {p['title_preview'][:50]}")
    next_pending = next((p for p in schedule["posts"] if p["day"] not in posted_days), None)
    if next_pending:
        print(f"\nNext to post: day-{next_pending['day']:02d} → r/{next_pending['subreddit']}")


def post_draft(api_key, day_num, dry_run=False):
    schedule = json.loads(SCHEDULE_PATH.read_text())
    post = next((p for p in schedule["posts"] if p["day"] == day_num), None)
    if not post:
        return {"ok": False, "error": f"day {day_num} not in schedule"}

    path = CONTENT_DIR / post["title_file"]
    if not path.exists():
        return {"ok": False, "error": f"draft file missing: {path}"}
    title, body = parse_draft(path)
    if not title or not body:
        return {"ok": False, "error": "draft parse failed"}

    log = load_log()
    if any(p["day"] == day_num for p in log["posts"]):
        return {"ok": False, "error": f"day {day_num} already posted (see {LOG_PATH})"}

    print(f"  Day {day_num}: r/{post['subreddit']} | flair: {post.get('flair', 'none')}")
    print(f"  Title ({len(title)} chars): {title[:80]}{'...' if len(title) > 80 else ''}")
    print(f"  Body:  {len(body.split())} words, {len(body)} chars")
    print(f"  Type:  {post['type']}")

    if dry_run:
        print(f"\n  [DRY RUN] Would POST to: {COMPOSIO_V3_URL}")
        print(f"  [DRY RUN] x-api-key: {api_key[:8]}…")
        print(f"  [DRY RUN] subreddit: {post['subreddit']}")
        print(f"  [DRY RUN] title: {title}")
        print(f"  [DRY RUN] body: {body[:100]}...")
        return {"ok": True, "dry_run": True, "day": day_num}

    print(f"\n  Posting via Composio v3 REST...")
    ok, msg, raw = v3_post(api_key, post["subreddit"], title, body, flair=post.get("flair"))
    if ok:
        print(f"  ✅ POSTED: {msg[:200]}")
        log["posts"].append({
            "day": day_num,
            "subreddit": post["subreddit"],
            "title": title,
            "permalink": None,
            "transport": "composio_v3_rest",
            "posted_at": datetime.now().isoformat(),
            "raw_response": raw[:2000],
        })
        save_log(log)
        return {"ok": True, "day": day_num, "response": msg}
    else:
        print(f"  ❌ FAILED: {msg[:300]}")
        return {"ok": False, "error": msg}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", type=int)
    p.add_argument("--next", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.list:
        list_status()
        return

    if not args.day and not args.next:
        p.print_help()
        return

    api_key = load_api_key()
    if not api_key:
        print("❌ COMPOSIO_API_KEY not found in /root/.hermes/.env")
        sys.exit(1)

    day_num = args.day
    if args.next:
        log = load_log()
        posted_days = {p["day"] for p in log["posts"]}
        schedule = json.loads(SCHEDULE_PATH.read_text())
        next_pending = next((p for p in schedule["posts"] if p["day"] not in posted_days), None)
        if not next_pending:
            print("✅ All posts already made.")
            return
        day_num = next_pending["day"]

    result = post_draft(api_key, day_num, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
