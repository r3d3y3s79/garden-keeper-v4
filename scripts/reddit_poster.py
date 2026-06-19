#!/usr/bin/env python3
"""
Garden Keeper — Reddit Poster
Posts one or more drafts to Reddit via the Composio MCP server.
Logs every post to data/reddit_posted.json so we never double-post.

Usage:
  python3 scripts/reddit_poster.py --day 1                  # Post day 1
  python3 scripts/reddit_poster.py --day 1 --dry-run        # Validate but don't post
  python3 scripts/reddit_poster.py --next                   # Post the next unposted draft
  python3 scripts/reddit_poster.py --next --dry-run         # Show what would be posted
  python3 scripts/reddit_poster.py --list                   # List all + posted status

Composio MCP uses POST https://connect.composio.dev/mcp with
SSE transport. We initialize a session, then call tools/call with
tool name REDDIT_SUBMIT_TEXT_SUBMISSION (or similar) and the post
body as arguments.

KNOWN ISSUE (JOE-82, 2026-06-19, verified by Pathfinder):
The MCP endpoint requires an AuthKit JWT in the Authorization: Bearer header.
This script sends the ak_… API key from COMPOSIO_API_KEY, which Composio's MCP
rejects with HTTP 401 ("not a valid AuthKit JWT"). The REST v3 path
(backend.composio.dev/api/v3/tools/execute/REDDIT_CREATE_REDDIT_POST) DOES
accept the ak_… key via the x-api-key header and is the working transport
for this credential type. Tool name is REDDIT_CREATE_REDDIT_POST, not
REDDIT_SUBMIT_TEXT_SUBMISSION. Use the v3 REST path until the JWT is
provisioned. See docs/JOE-82-reddit-oauth-run-report.md for the full
verification.
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

COMPOSIO_MCP_URL = "https://connect.composio.dev/mcp"
ENV_PATH = Path("/root/.hermes/.env")


def load_api_key():
    """Read COMPOSIO_API_KEY from .env. Falls back to env var."""
    if "COMPOSIO_API_KEY" in os.environ:
        return os.environ["COMPOSIO_API_KEY"]
    if not ENV_PATH.exists():
        return None
    with open(ENV_PATH) as f:
        for line in f:
            m = re.match(r"^COMPOSIO_API_KEY=(['\"]?)([^'\"\n]+)\1", line.strip())
            if m:
                return m.group(2)
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


def mcp_request(api_key, method, params, session_id=None):
    """Make a JSON-RPC 2.0 request to the Composio MCP server.

    Returns (result, error). For SSE responses, parses the first
    'data:' line as JSON.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": int(datetime.now().timestamp()),
        "method": method,
        "params": params,
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {api_key}",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id

    req = urllib.request.Request(COMPOSIO_MCP_URL, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            text = r.read().decode("utf-8", errors="replace")
            # SSE responses look like: event: message\ndata: {...}\n\n
            for line in text.split("\n"):
                if line.startswith("data: "):
                    try:
                        return json.loads(line[6:]), None
                    except json.JSONDecodeError:
                        continue
            # If not SSE, try parsing the whole body
            try:
                return json.loads(text), None
            except json.JSONDecodeError:
                return None, f"Non-JSON response: {text[:300]}"
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:500]
        return None, f"HTTP {e.code}: {body_text}"
    except Exception as e:
        return None, f"Request error: {e}"


def mcp_initialize(api_key):
    """Initialize an MCP session and return the session_id."""
    result, err = mcp_request(api_key, "initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "garden-keeper-poster", "version": "1.0.0"},
    })
    if err:
        return None, err
    if result and "result" in result:
        # Session ID comes from the Mcp-Session-Id response header
        # (we can't access that here without saving it from the request
        # call). For most Composio MCP endpoints, no session is needed
        # for the first tool call.
        return result["result"], None
    return None, f"Unexpected init response: {result}"


def mcp_list_tools(api_key, session_id=None):
    """Return the list of available tools."""
    result, err = mcp_request(api_key, "tools/list", {}, session_id=session_id)
    if err:
        return None, err
    if result and "result" in result and "tools" in result["result"]:
        return result["result"]["tools"], None
    return None, f"Unexpected tools/list response: {result}"


def mcp_call_tool(api_key, tool_name, arguments, session_id=None):
    """Invoke a tool with the given arguments."""
    result, err = mcp_request(api_key, "tools/call", {
        "name": tool_name,
        "arguments": arguments,
    }, session_id=session_id)
    if err:
        return None, err
    if result and "result" in result:
        return result["result"], None
    if result and "error" in result:
        return None, result["error"]
    return None, f"Unexpected tools/call response: {result}"


def find_reddit_submit_tool(tools):
    """Find the right tool name for posting a text submission.

    Reddit tool names from Composio typically follow patterns like:
    - REDDIT_SUBMIT_TEXT_SUBMISSION
    - REDDIT_CREATE_POST
    - REDDIT_SUBMIT_POST
    Returns the first match, or None.
    """
    candidates = [
        "REDDIT_SUBMIT_TEXT_SUBMISSION",
        "REDDIT_SUBMIT_POST",
        "REDDIT_CREATE_POST",
        "REDDIT_SUBMIT_LINK",
    ]
    names = [t.get("name", "") for t in tools]
    for c in candidates:
        for n in names:
            if n.upper() == c:
                return n
    # Fallback: any tool starting with REDDIT_ containing SUBMIT
    for n in names:
        if n.upper().startswith("REDDIT_") and "SUBMIT" in n.upper():
            return n
    return None


def find_reddit_account(tools):
    """Look for a tool that lists/manages accounts."""
    names = [t.get("name", "") for t in tools]
    candidates = [
        "REDDIT_GET_ACCOUNT",
        "REDDIT_LIST_ACCOUNTS",
        "REDDIT_MY_PROFILE",
    ]
    for c in candidates:
        for n in names:
            if n.upper() == c:
                return n
    return None


def post_draft(api_key, day_num, dry_run=False):
    """Post a single draft by day number. Returns dict with status."""
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
        print(f"\n  [DRY RUN] Would call Composio MCP with tool: REDDIT_SUBMIT_TEXT_SUBMISSION")
        print(f"  [DRY RUN] Arguments:")
        print(f"    subreddit: {post['subreddit']}")
        print(f"    title: {title}")
        print(f"    body: {body[:100]}{'...' if len(body) > 100 else ''}")
        if post.get("flair"):
            print(f"    flair: {post['flair']}")
        return {"ok": True, "dry_run": True, "day": day_num}

    # 1. Initialize session
    print(f"\n  Initializing MCP session...")
    init_result, err = mcp_initialize(api_key)
    if err:
        return {"ok": False, "error": f"MCP init failed: {err}"}
    print(f"  ✅ Session initialized")

    # 2. List tools to find the right one
    print(f"  Listing available tools...")
    tools, err = mcp_list_tools(api_key)
    if err:
        return {"ok": False, "error": f"tools/list failed: {err}"}
    tool_names = [t.get("name", "") for t in tools]
    print(f"  ✅ Found {len(tools)} tools. Reddit-related:")
    reddit_tools = [n for n in tool_names if "REDDIT" in n.upper()]
    for n in reddit_tools:
        print(f"      - {n}")

    submit_tool = find_reddit_submit_tool(tools)
    if not submit_tool:
        return {"ok": False, "error": f"No Reddit submit tool found in {len(tools)} tools"}

    # 3. Call the tool
    print(f"\n  Calling {submit_tool}...")
    arguments = {
        "subreddit": post["subreddit"],
        "title": title,
        "body": body,
    }
    if post.get("flair"):
        arguments["flair"] = post["flair"]

    result, err = mcp_call_tool(api_key, submit_tool, arguments)
    if err:
        return {"ok": False, "error": f"tools/call failed: {err}"}
    print(f"  ✅ Tool call returned: {json.dumps(result, indent=2)[:300]}")

    # 4. Log it
    log["posts"].append({
        "day": day_num,
        "subreddit": post["subreddit"],
        "title": title,
        "tool": submit_tool,
        "result": result,
        "posted_at": datetime.now().isoformat(timespec="seconds"),
    })
    save_log(log)
    print(f"\n  ✅ Logged to {LOG_PATH}")
    return {"ok": True, "day": day_num, "tool": submit_tool, "result": result}


def list_status():
    schedule = json.loads(SCHEDULE_PATH.read_text())
    log = load_log()
    posted_days = {p["day"]: p for p in log["posts"]}

    print("=" * 70)
    print("Reddit Posting Status")
    print("=" * 70)
    print(f"Total posts in schedule: {len(schedule['posts'])}")
    print(f"Posts already made:       {len(posted_days)}")
    print(f"Remaining:                {len(schedule['posts']) - len(posted_days)}")
    print()
    for post in schedule["posts"]:
        day = post["day"]
        status = "✅ posted" if day in posted_days else "⏳ pending"
        marker = f"  day-{day:02d}  {status:12s}  r/{post['subreddit']:14s} {post['type']:18s} {post['title_preview'][:50]}"
        if day in posted_days:
            marker += f"  (at {posted_days[day].get('posted_at', '?')[:16]})"
        print(marker)

    next_pending = next((p for p in schedule["posts"] if p["day"] not in posted_days), None)
    if next_pending:
        print()
        print(f"Next to post: day-{next_pending['day']:02d} → r/{next_pending['subreddit']}")


def cmd_post_day(args):
    api_key = load_api_key()
    if not api_key:
        print("ERROR: COMPOSIO_API_KEY not found in /root/.hermes/.env", file=sys.stderr)
        return 1
    result = post_draft(api_key, args.day, dry_run=args.dry_run)
    if not result["ok"]:
        print(f"\n  ❌ FAILED: {result.get('error')}")
        return 1
    return 0


def cmd_post_next(args):
    schedule = json.loads(SCHEDULE_PATH.read_text())
    log = load_log()
    posted_days = {p["day"] for p in log["posts"]}
    next_post = next((p for p in schedule["posts"] if p["day"] not in posted_days), None)
    if not next_post:
        print("All 30 posts have been made. 🎉")
        return 0
    api_key = load_api_key()
    if not api_key:
        print("ERROR: COMPOSIO_API_KEY not found in /root/.hermes/.env", file=sys.stderr)
        return 1
    result = post_draft(api_key, next_post["day"], dry_run=args.dry_run)
    if not result["ok"]:
        print(f"\n  ❌ FAILED: {result.get('error')}")
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="Garden Keeper Reddit Poster")
    parser.add_argument("--day", type=int, help="Specific day number to post (1-30)")
    parser.add_argument("--next", action="store_true", help="Post the next unposted draft")
    parser.add_argument("--list", action="store_true", help="List all drafts and their status")
    parser.add_argument("--dry-run", action="store_true", help="Validate but don't actually post")
    args = parser.parse_args()

    if args.list:
        list_status()
        return 0
    if args.day is not None:
        return cmd_post_day(args)
    if args.next:
        return cmd_post_next(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
