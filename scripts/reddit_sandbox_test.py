#!/usr/bin/env python3
"""
Reddit Sandbox End-to-End Test — Garden Keeper
================================================
Per JOE-82 deliverable 3: "Test post 1 post to a sandbox subreddit to verify
pipeline works end-to-end".

This script attempts a REAL post to r/test (Reddit's official sandbox subreddit)
via the Composio MCP server. It captures every step and the actual response,
so we have verifiable evidence the pipeline reaches Reddit (or, if blocked by
missing OAuth, exactly which auth gate stops it).

Outcomes (one of these will be true):
  A) Post succeeds  -> we print the live reddit.com URL and the post id.
  B) Composio says "Reddit not connected" / "auth required" -> the script path
     is proven end-to-end; only the human OAuth step is missing. We log the
     exact error message.
  C) Composio says something else (rate limit, etc.) -> we log verbatim.

In all three cases we write data/reddit_sandbox_test.json with the full
result. We never fabricate success.

Usage:
  python3 scripts/reddit_sandbox_test.py
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
LOG_PATH = DATA_DIR / "reddit_sandbox_test.json"
ENV_PATH = Path("/root/.hermes/.env")
COMPOSIO_MCP_URL = "https://connect.composio.dev/mcp"

SANDBOX_SUBREDDIT = "test"
SANDBOX_TITLE = "[Garden Keeper Pipeline Test] Sandbox post — please ignore"
SANDBOX_BODY = (
    "This is an automated end-to-end pipeline test by the Garden Keeper auto-poster. "
    "Posted to r/test as a sandbox verification per JOE-82 deliverable 3. "
    "If you can read this on reddit.com, the Composio MCP path is wired correctly. "
    "Test ran at " + datetime.now().isoformat(timespec="seconds") + "."
)


def load_api_key():
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


def mcp_request(api_key, method, params, session_id=None, return_headers=False):
    payload = {
        "jsonrpc": "2.0",
        "id": int(datetime.now().timestamp() * 1000),
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

    req = urllib.request.Request(
        COMPOSIO_MCP_URL, data=body, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            text = r.read().decode("utf-8", errors="replace")
            resp_headers = dict(r.headers)
            for line in text.split("\n"):
                if line.startswith("data: "):
                    try:
                        out = json.loads(line[6:])
                        return (out, None, resp_headers) if return_headers else (out, None)
                    except json.JSONDecodeError:
                        continue
            try:
                parsed = json.loads(text)
                return (parsed, None, resp_headers) if return_headers else (parsed, None)
            except json.JSONDecodeError:
                err = f"Non-JSON response: {text[:300]}"
                return (None, err, resp_headers) if return_headers else (None, err)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:500]
        err = f"HTTP {e.code}: {body_text}"
        return (None, err, {}) if return_headers else (None, err)
    except Exception as e:
        err = f"Request error: {e}"
        return (None, err, {}) if return_headers else (None, err)


def find_submit_tool(tools):
    names = [t.get("name", "") for t in tools]
    # Composio Reddit tool name variants
    preferred = [
        "REDDIT_SUBMIT_TEXT_SUBMISSION",
        "REDDIT_SUBMIT_POST",
        "REDDIT_CREATE_POST",
    ]
    for p in preferred:
        for n in names:
            if n.upper() == p:
                return n
    for n in names:
        if n.upper().startswith("REDDIT_") and "SUBMIT" in n.upper():
            return n
    return None


def main():
    result = {
        "test_run_at": datetime.now().isoformat(timespec="seconds"),
        "sandbox_subreddit": SANDBOX_SUBREDDIT,
        "composio_url": COMPOSIO_MCP_URL,
        "steps": [],
    }

    api_key = load_api_key()
    if not api_key:
        result["outcome"] = "BLOCKED_NO_API_KEY"
        result["error"] = "COMPOSIO_API_KEY not found in /root/.hermes/.env"
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOG_PATH.write_text(json.dumps(result, indent=2))
        print(f"❌ {result['error']}")
        return 1
    result["api_key_loaded"] = True
    result["api_key_prefix"] = api_key[:8] + "..."  # don't leak full key
    print(f"✅ COMPOSIO_API_KEY loaded (prefix {result['api_key_prefix']})")

    # Step 1: Initialize MCP session
    print("\n[1/3] Initializing MCP session...")
    init_resp, init_err, init_headers = mcp_request(
        api_key, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "garden-keeper-sandbox-test", "version": "1.0.0"},
        },
        return_headers=True,
    )
    session_id = init_headers.get("Mcp-Session-Id") or init_headers.get("mcp-session-id")
    result["steps"].append({
        "step": "initialize",
        "session_id_returned": bool(session_id),
        "session_id_prefix": (session_id[:8] + "...") if session_id else None,
        "response": init_resp,
        "error": init_err,
    })
    if init_err:
        result["outcome"] = "BLOCKED_AT_INIT"
        result["error"] = init_err
        LOG_PATH.write_text(json.dumps(result, indent=2))
        print(f"❌ MCP init failed: {init_err}")
        return 1
    print(f"✅ Session initialized (session_id: {result['steps'][-1]['session_id_prefix']})")

    # Step 2: List tools (verify Reddit is wired)
    print("\n[2/3] Listing tools...")
    tools_resp, tools_err = mcp_request(api_key, "tools/list", {}, session_id=session_id)
    if tools_err:
        result["outcome"] = "BLOCKED_AT_TOOLS_LIST"
        result["error"] = tools_err
        LOG_PATH.write_text(json.dumps(result, indent=2))
        print(f"❌ tools/list failed: {tools_err}")
        return 1
    tools = tools_resp.get("result", {}).get("tools", []) if tools_resp else []
    reddit_tools = [t.get("name") for t in tools if "REDDIT" in (t.get("name", "")).upper()]
    submit_tool = find_submit_tool(tools)
    result["steps"].append({
        "step": "tools/list",
        "total_tools": len(tools),
        "reddit_tools": reddit_tools,
        "submit_tool": submit_tool,
    })
    print(f"✅ Found {len(tools)} tools. Reddit-related: {len(reddit_tools)}")
    for t in reddit_tools:
        print(f"    - {t}")
    if not submit_tool:
        result["outcome"] = "BLOCKED_NO_SUBMIT_TOOL"
        result["error"] = f"REDDIT_SUBMIT_TEXT_SUBMISSION not in tools list (got {len(tools)} tools)"
        LOG_PATH.write_text(json.dumps(result, indent=2))
        print(f"❌ {result['error']}")
        return 1

    # Step 3: Try to post to r/test
    print(f"\n[3/3] Calling {submit_tool} → r/{SANDBOX_SUBREDDIT}...")
    call_resp, call_err = mcp_request(
        api_key, "tools/call", {
            "name": submit_tool,
            "arguments": {
                "subreddit": SANDBOX_SUBREDDIT,
                "title": SANDBOX_TITLE,
                "body": SANDBOX_BODY,
            },
        },
        session_id=session_id,
    )
    result["steps"].append({
        "step": "tools/call",
        "tool": submit_tool,
        "arguments": {
            "subreddit": SANDBOX_SUBREDDIT,
            "title": SANDBOX_TITLE,
            "body_length": len(SANDBOX_BODY),
        },
        "response": call_resp,
        "error": call_err,
    })
    if call_err:
        result["outcome"] = "BLOCKED_AT_TOOLS_CALL"
        result["error"] = call_err
        print(f"❌ Tool call failed: {call_err[:200]}")
    elif call_resp and "error" in call_resp:
        result["outcome"] = "REDDIT_AUTH_REQUIRED"
        result["error"] = call_resp["error"]
        print(f"⚠️  Composio returned error (likely missing Reddit OAuth):")
        print(f"    {json.dumps(call_resp['error'], indent=2)[:400]}")
    elif call_resp and "result" in call_resp:
        result["outcome"] = "POSTED_SUCCESSFULLY"
        result["result"] = call_resp["result"]
        print(f"✅ Post returned successfully:")
        print(f"    {json.dumps(call_resp['result'], indent=2)[:400]}")
    else:
        result["outcome"] = "UNKNOWN_RESPONSE"
        result["response"] = call_resp
        print(f"⚠️  Unexpected response shape: {json.dumps(call_resp)[:300]}")

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(result, indent=2))
    print(f"\n📄 Full result written to: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
