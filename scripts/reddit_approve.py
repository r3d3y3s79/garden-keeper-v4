#!/usr/bin/env python3
"""
Garden Keeper — Reddit Approval Gate
Sends a Telegram preview of the next post and waits for
"ship it" / "skip" / "edit X" before posting.

Flow:
  1. Pick the next unposted draft (or --day N)
  2. Render a preview (title, body, target subreddit)
  3. Send to Telegram
  4. Wait for a reply:
       - "ship it"        → run reddit_poster.py
       - "skip"           → mark skipped, move to next
       - "edit TITLE..."  → update draft, repost preview, wait again
       - anything else    → "didn't catch that, ship/skip/edit"
  5. Log decision

Replies are received via the inbound-approval.json file. The cron
job that calls this script is expected to:
  - Read Telegram replies
  - Append to /tmp/reddit-approval-replies.json
  - Call this script in --wait mode

For interactive use, this script writes the pending approval to
/tmp/reddit-pending-approval.json and exits; the user (you) sends
"ship" or "skip" and the next cron tick picks it up.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = SCRIPT_DIR.parent / "content" / "reddit"
SCHEDULE_PATH = CONTENT_DIR / "schedule.json"
DATA_DIR = SCRIPT_DIR.parent / "data"
LOG_PATH = DATA_DIR / "reddit_posted.json"
DECISIONS_LOG = DATA_DIR / "reddit_decisions.json"
PENDING_PATH = Path("/tmp/reddit-pending-approval.json")
REPLIES_PATH = Path("/tmp/reddit-approval-replies.json")

ENV_PATH = Path("/root/.hermes/.env")
TELEGRAM_CHAT_ID = "6482991006"  # Joe's Telegram chat


def load_env_value(key):
    if key in os.environ:
        return os.environ[key]
    if not ENV_PATH.exists():
        return None
    with open(ENV_PATH) as f:
        for line in f:
            m = re.match(rf"^{key}=(['\"]?)([^'\"\n]+)\1", line.strip())
            if m:
                return m.group(2)
    return None


def parse_draft(path):
    text = path.read_text()
    if not text.startswith("Title:"):
        return None, None
    parts = text.split("\n\n", 1)
    title = parts[0].replace("Title: ", "").strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def send_telegram(text):
    """Send a message to Joe's Telegram. Returns True on success."""
    token = load_env_value("TELEGRAM_BOT_TOKEN")
    if not token:
        print("WARNING: TELEGRAM_BOT_TOKEN not set, can't send preview", file=sys.stderr)
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read())
            return d.get("ok", False)
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)
        return False


def render_preview(day, post, title, body):
    """Render the approval message. Telegram-safe HTML."""
    body_preview = body[:1200] + ("..." if len(body) > 1200 else "")
    # Escape HTML special chars
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        f"🌿 <b>Reddit Draft — Day {day} of 30</b>\n\n"
        f"<b>Subreddit:</b> r/{esc(post['subreddit'])}\n"
        f"<b>Type:</b> {esc(post['type'])}\n"
        f"<b>Flair:</b> {esc(post.get('flair', 'none'))}\n\n"
        f"<b>Title:</b>\n{esc(title)}\n\n"
        f"<b>Body:</b>\n{esc(body_preview)}\n\n"
        f"<code>ship it</code> → post now\n"
        f"<code>skip</code> → move to next\n"
        f"<code>edit TITLE:new title</code> → change title and re-preview\n"
        f"<code>edit BODY:new body line</code> → add a line to body"
    )


def post_to_reddit(day, dry_run=False):
    """Call reddit_poster.py as a subprocess."""
    cmd = [sys.executable, str(SCRIPT_DIR / "reddit_poster.py"), "--day", str(day)]
    if dry_run:
        cmd.append("--dry-run")
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def record_decision(day, decision, extra=None):
    log = load_json(DECISIONS_LOG, {"decisions": []})
    log["decisions"].append({
        "day": day,
        "decision": decision,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "extra": extra or {},
    })
    save_json(DECISIONS_LOG, log)


def get_next_unposted_day(target_day=None):
    schedule = json.loads(SCHEDULE_PATH.read_text())
    log = load_json(LOG_PATH, {"posts": []})
    skipped = {d["day"] for d in load_json(DECISIONS_LOG, {"decisions": []}).get("decisions", []) if d.get("decision") == "skip"}
    posted = {p["day"] for p in log["posts"]}
    if target_day is not None:
        if target_day in posted:
            return None
        if target_day in skipped:
            return None
        return target_day
    for p in schedule["posts"]:
        if p["day"] not in posted and p["day"] not in skipped:
            return p["day"]
    return None


def cmd_preview(args):
    day = get_next_unposted_day(args.day)
    if day is None:
        print("No unposted drafts remain.")
        return 1
    schedule = json.loads(SCHEDULE_PATH.read_text())
    post = next(p for p in schedule["posts"] if p["day"] == day)
    path = CONTENT_DIR / post["title_file"]
    title, body = parse_draft(path)
    if not title or not body:
        print(f"ERROR: failed to parse {path}", file=sys.stderr)
        return 1

    preview = render_preview(day, post, title, body)
    if not args.dry_run and not args.no_send:
        send_telegram(preview)
    print(preview)

    pending = {
        "day": day,
        "post": post,
        "title": title,
        "body": body,
        "previewed_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_json(PENDING_PATH, pending)
    print(f"\n(Pending approval saved to {PENDING_PATH})")
    return 0


def cmd_check_reply(args):
    """Check replies file for a decision on the pending draft."""
    if not PENDING_PATH.exists():
        print("No pending approval.")
        return 1
    pending = load_json(PENDING_PATH, None)
    if not pending:
        return 1

    replies = load_json(REPLIES_PATH, [])
    if not replies:
        print("No replies yet.")
        return 0

    # Find the most recent reply
    latest = replies[-1]
    text = latest.get("text", "").strip()
    print(f"Latest reply: {text!r}")

    day = pending["day"]
    if re.match(r"^ship\s*it?$", text, re.IGNORECASE):
        print(f"\n→ Ship it. Posting day {day}...")
        ok = post_to_reddit(day, dry_run=False)
        record_decision(day, "ship")
        if ok:
            send_telegram(f"✅ Day {day} posted to r/{pending['post']['subreddit']}.")
        else:
            send_telegram(f"❌ Day {day} post failed. Check /root/the-garden-keeper/data/reddit_posted.json")
        PENDING_PATH.unlink()
        return 0 if ok else 1

    if re.match(r"^skip$", text, re.IGNORECASE):
        print(f"\n→ Skip. Marking day {day} as skipped.")
        record_decision(day, "skip")
        send_telegram(f"⏭️ Day {day} skipped. Will move to the next draft.")
        PENDING_PATH.unlink()
        return 0

    if text.lower().startswith("edit title:"):
        new_title = text[11:].strip()
        path = CONTENT_DIR / pending["post"]["title_file"]
        body = pending["body"]
        path.write_text(f"Title: {new_title}\n\n{body}\n")
        record_decision(day, "edit_title", {"new_title": new_title})
        print(f"  Title updated. Re-rendering preview...")
        return cmd_preview(argparse.Namespace(day=day, dry_run=False, no_send=False))

    if text.lower().startswith("edit body:"):
        new_line = text[10:].strip()
        path = CONTENT_DIR / pending["post"]["title_file"]
        title = pending["title"]
        body = pending["body"] + "\n\n" + new_line
        path.write_text(f"Title: {title}\n\n{body}\n")
        record_decision(day, "edit_body", {"added": new_line})
        print(f"  Body updated. Re-rendering preview...")
        return cmd_preview(argparse.Namespace(day=day, dry_run=False, no_send=False))

    print(f"\nUnrecognized reply. Send 'ship it', 'skip', or 'edit TITLE:...' / 'edit BODY:...'")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Garden Keeper Reddit Approval Gate")
    sub = parser.add_subparsers(dest="cmd")

    p_prev = sub.add_parser("preview", help="Generate and send preview for the next draft")
    p_prev.add_argument("--day", type=int, help="Specific day to preview")
    p_prev.add_argument("--dry-run", action="store_true", help="Don't send to Telegram")
    p_prev.add_argument("--no-send", action="store_true", help="Don't send to Telegram")
    p_prev.set_defaults(func=cmd_preview)

    p_check = sub.add_parser("check", help="Check replies file for a decision")
    p_check.set_defaults(func=cmd_check_reply)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
