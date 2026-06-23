#!/usr/bin/env python3
"""Garden Keeper — Reddit Cookie Poster

Posts Garden Keeper value-first drafts to Reddit using the
browser-session cookies already on disk. Bypasses the OAuth
gate that blocks reddit_poster.py (JOE-82).

Logs every post to data/reddit_posted.json so we never double-post.

Usage:
  python3 scripts/reddit_cookie_poster.py --day 1
  python3 scripts/reddit_cookie_poster.py --day 1 --dry-run
  python3 scripts/reddit_cookie_poster.py --next
  python3 scripts/reddit_cookie_poster.py --list
  python3 scripts/reddit_cookie_poster.py --days 1,2,3

Subreddit names in schedule.json are written like "r/houseplants"
(this script strips the r/ prefix when sending to the API).
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# VPS DNS resolves reddit.com → Kominfo poison page.
# Patch socket.getaddrinfo to return real Fastly IPs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import reddit_dns_bypass  # noqa: F401
    reddit_dns_bypass.install()
except Exception as _e:
    print(f"WARN: reddit_dns_bypass not installed: {_e}", file=sys.stderr)

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = SCRIPT_DIR.parent / "content" / "reddit"
DATA_DIR = SCRIPT_DIR.parent / "data"
SCHEDULE_PATH = CONTENT_DIR / "schedule.json"
LOG_PATH = DATA_DIR / "reddit_posted.json"
OVERRIDES_PATH = DATA_DIR / "reddit_flair_overrides.json"
COOKIES_PATH = "/root/.agent-reach/reddit.com_cookies-20260619-013723.configured.txt"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def parse_netscape(path):
    jar = {}
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            parts = re.split(r"\s+", line, maxsplit=6)
            if len(parts) < 7:
                continue
            domain, _flag, _path, _secure, _expires, name, value = parts
            if "reddit" in domain.lower():
                jar[name] = (value, domain.lstrip("."), "/")
    return jar


def build_session(jar):
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json, text/html;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    })
    for name, (val, dom, path) in jar.items():
        s.cookies.set(name, val, domain=dom, path=path)
    return s


def get_modhash(session):
    r = session.get("https://oauth.reddit.com/api/v1/me", timeout=15)
    if r.status_code == 200:
        try:
            data = r.json()
            if isinstance(data, dict):
                if "modhash" in data:
                    return data["modhash"]
                if "data" in data and isinstance(data["data"], dict) and "modhash" in data["data"]:
                    return data["data"]["modhash"]
        except Exception:
            pass
    r = session.get("https://oauth.reddit.com/", timeout=15)
    if r.status_code == 200:
        m = re.search(r'"modhash":\s*"([^"]+)"', r.text)
        if m:
            return m.group(1)
    return None


def submit_post(session, subreddit, title, body, flair=None, flair_id=None):
    """Submit one self-text post. Returns dict."""
    modhash = get_modhash(session)
    if not modhash:
        return {"ok": False, "error": "could not fetch modhash — cookies expired?"}

    payload = {
        "sr": subreddit,
        "title": title,
        "text": body,
        "kind": "self",
        "resubmit": "true",
        "iden": "",
        "srst": "",
        "uh": modhash,
        "api_type": "json",
    }
    if flair_id:
        payload["flair_id"] = flair_id
    elif flair:
        payload["flair"] = flair

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": f"https://oauth.reddit.com/r/{subreddit}/submit",
        "Origin": "https://oauth.reddit.com",
        "X-Modhash": modhash,
    }
    r = session.post(
        "https://oauth.reddit.com/api/submit",
        data=payload,
        headers=headers,
        timeout=30,
    )
    if r.status_code in (200, 201):
        try:
            j = r.json()
        except Exception:
            return {"ok": False, "error": f"non-JSON response: {r.text[:300]}"}
        pd = j.get("json", {})
        errs = pd.get("errors", [])
        data = pd.get("data", {})
        if errs:
            return {"ok": False, "error": f"reddit errors: {errs}", "body": pd}
        return {"ok": True, "url": data.get("url"), "id": data.get("id"), "name": data.get("name")}
    return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:300]}"}


def parse_draft(path):
    text = path.read_text()
    if not text.startswith("Title:"):
        return None, None
    parts = text.split("\n\n", 1)
    title = parts[0].replace("Title: ", "").strip()
    body = parts[1].strip() if len(parts) > 1 else ""
    return title, body


def load_log():
    if not LOG_PATH.exists():
        return {"posts": [], "comments": []}
    try:
        return json.loads(LOG_PATH.read_text())
    except json.JSONDecodeError:
        return {"posts": [], "comments": []}


def save_log(log):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def post_day(session, day_num, dry_run=False):
    schedule = json.loads(SCHEDULE_PATH.read_text())
    entry = next((p for p in schedule["posts"] if p["day"] == day_num), None)
    if not entry:
        return {"ok": False, "error": f"day {day_num} not in schedule"}

    # Apply overrides if present (verified sub + flair_id from reddit_flair_overrides.json)
    overrides = {}
    if OVERRIDES_PATH.exists():
        overrides = json.loads(OVERRIDES_PATH.read_text())
    sub_override = overrides.get("subreddit_overrides", {}).get(str(day_num))
    flair_overrides = overrides.get("flair_ids", {})

    if sub_override:
        sub = sub_override["subreddit"]
        flair_label = sub_override.get("flair")
    else:
        sub = entry["subreddit"].lstrip("r/")
        flair_label = entry.get("flair")

    flair_id = None
    if flair_label and sub in flair_overrides and flair_overrides[sub]:
        flair_id = flair_overrides[sub].get(flair_label)

    path = CONTENT_DIR / entry["title_file"]
    if not path.exists():
        return {"ok": False, "error": f"draft file missing: {path}"}
    title, body = parse_draft(path)
    if not title or not body:
        return {"ok": False, "error": "draft parse failed"}

    log = load_log()
    if any(p.get("day") == day_num and p.get("title") == title for p in log["posts"]):
        return {"ok": False, "error": f"day {day_num} already posted"}

    flair_display = f"{flair_label} (id={flair_id[:18] + '…' if flair_id else 'auto'})"
    print(f"\n=== Day {day_num} → r/{sub} | flair={flair_display}")
    print(f"  Title ({len(title)} chars): {title[:80]}")
    print(f"  Body:  {len(body.split())} words, {len(body)} chars")

    if dry_run:
        return {"ok": True, "dry_run": True, "sub": sub, "flair_id": flair_id}

    res = submit_post(session, sub, title, body, flair=flair_label, flair_id=flair_id)
    if res["ok"]:
        log["posts"].append({
            "day": day_num,
            "subreddit": sub,
            "title": title,
            "flair": flair_label,
            "flair_id": flair_id,
            "url": res["url"],
            "id": res["id"],
            "name": res["name"],
            "posted_at": datetime.now().isoformat(timespec="seconds"),
            "method": "cookie_auth_oauth.reddit.com",
        })
        save_log(log)
        print(f"  ✅ POSTED: {res['url']}")
    else:
        print(f"  ❌ FAILED: {res['error']}")
    return res


def cmd_list(_):
    schedule = json.loads(SCHEDULE_PATH.read_text())
    log = load_log()
    posted_titles = {p["title"] for p in log.get("posts", [])}
    print("=" * 78)
    print("Garden Keeper Reddit Posting Status (cookie auth)")
    print("=" * 78)
    print(f"Total drafts: {len(schedule['posts'])} | Posted: {len(posted_titles)} | Remaining: {len(schedule['posts']) - len(posted_titles)}")
    for p in schedule["posts"]:
        day = p["day"]
        path = CONTENT_DIR / p["title_file"]
        title, _ = parse_draft(path) if path.exists() else (None, None)
        is_posted = title in posted_titles if title else False
        status = "✅ posted" if is_posted else "⏳ pending"
        marker = f"  day-{day:02d}  {status:12s}  r/{p['subreddit']:14s} {p['type']:18s} {p['title_preview'][:48]}"
        if is_posted:
            entry = next((x for x in log["posts"] if x["title"] == title), None)
            if entry:
                marker += f"  ({entry.get('posted_at', '?')[:16]})"
        print(marker)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", type=int, help="specific day number (1-30)")
    ap.add_argument("--days", help="comma-separated days, e.g. 1,2,3")
    ap.add_argument("--next", action="store_true", help="post next unposted draft")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    jar = parse_netscape(COOKIES_PATH)
    if "reddit_session" not in jar and "token_v2" not in jar:
        print("ERROR: cookies missing reddit_session/token_v2", file=sys.stderr)
        sys.exit(3)
    sess = build_session(jar)

    if args.list:
        cmd_list(args)
        return 0

    if args.days:
        days = [int(d) for d in args.days.split(",")]
        ok = True
        for d in days:
            r = post_day(sess, d, dry_run=args.dry_run)
            if not r["ok"]:
                ok = False
                print(f"  ⚠️  Day {d} failed: {r['error']}")
        return 0 if ok else 1

    if args.next:
        schedule = json.loads(SCHEDULE_PATH.read_text())
        log = load_log()
        posted_titles = {p["title"] for p in log.get("posts", [])}
        next_post = None
        for p in schedule["posts"]:
            path = CONTENT_DIR / p["title_file"]
            if not path.exists():
                continue
            title, _ = parse_draft(path)
            if title and title not in posted_titles:
                next_post = p
                break
        if not next_post:
            print("All drafts posted. 🎉")
            return 0
        r = post_day(sess, next_post["day"], dry_run=args.dry_run)
        return 0 if r["ok"] else 1

    if args.day is not None:
        r = post_day(sess, args.day, dry_run=args.dry_run)
        return 0 if r["ok"] else 1

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
