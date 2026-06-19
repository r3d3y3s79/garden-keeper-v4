#!/usr/bin/env python3
"""
Reddit App Registration Helper — V2
Generates a static HTML page that walks the user through creating a
Reddit app for Composio integration, with all field values pre-filled
and copy buttons for each.

Critical correctness note: the redirect URI is
https://backend.composio.dev/api/v1/auth-apps/add — this is set by
Composio's own API as the default, and Reddit's "app creation" form
will accept ANY valid URI here. The actual validation happens at
OAuth time, when the URI must match what's registered in Composio's
auth config. Setting it to Composio's URL on the Reddit side means
the round-trip works without re-editing the Reddit app later.
"""

import json
import os
import re
import sys
import webbrowser
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT = SCRIPT_DIR / "reddit-register-helper.html"

REDIRECT_URI = "https://backend.composio.dev/api/v1/auth-apps/add"
APP_NAME = "Garden Keeper Auto-Poster v2"
DESCRIPTION = "Garden Keeper automated poster via Composio"
ABOUT_URL = "https://garden-keeper-v4.vercel.app"
SCRIPT_TYPE = "script"
SCOPES = "identity,read,vote,submit,flair,edit"

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reddit App Registration Helper — Garden Keeper</title>
  <style>
    :root {{
      --bg: #1a1a1b;
      --card: #272729;
      --border: #343536;
      --text: #d7dadc;
      --muted: #818384;
      --accent: #ff4500;
      --green: #46d160;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 1.5rem;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.55;
    }}
    .wrap {{ max-width: 720px; margin: 0 auto; }}
    h1 {{ color: var(--accent); font-size: 1.5rem; margin: 0 0 0.5rem; }}
    .lede {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
    .step {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem 1rem;
      margin-bottom: 1rem;
    }}
    .step h2 {{
      margin: 0 0 0.5rem;
      font-size: 1.05rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .step h2 .num {{
      background: var(--accent);
      color: white;
      width: 1.5rem;
      height: 1.5rem;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 0.85rem;
      font-weight: 700;
    }}
    .step p {{ margin: 0 0 0.75rem; font-size: 0.92rem; }}
    .field {{
      background: #0e0e0f;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 0.5rem 0.75rem;
      font-family: ui-monospace, "SF Mono", Menlo, monospace;
      font-size: 0.85rem;
      color: #e8e8e8;
      word-break: break-all;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .field .value {{ flex: 1; min-width: 0; }}
    .field button {{
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 4px;
      padding: 0.35rem 0.7rem;
      font-size: 0.78rem;
      font-weight: 600;
      cursor: pointer;
      flex-shrink: 0;
    }}
    .field button:hover {{ background: #ff5a1f; }}
    .field button.copied {{ background: var(--green); }}
    a.button {{
      display: inline-block;
      background: var(--accent);
      color: white;
      text-decoration: none;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.9rem;
      margin-top: 0.5rem;
    }}
    a.button:hover {{ background: #ff5a1f; }}
    .warning {{
      background: #3a1a1a;
      border: 1px solid var(--accent);
      border-radius: 4px;
      padding: 0.75rem;
      margin: 1rem 0;
      font-size: 0.88rem;
    }}
    .success {{
      background: #1a3a1a;
      border: 1px solid var(--green);
      border-radius: 4px;
      padding: 0.75rem;
      margin: 1rem 0;
      font-size: 0.88rem;
    }}
    code {{
      background: #0e0e0f;
      border: 1px solid var(--border);
      border-radius: 3px;
      padding: 0.1rem 0.3rem;
      font-size: 0.85em;
    }}
    .snippet {{
      background: #0e0e0f;
      border: 1px solid var(--green);
      border-radius: 6px;
      padding: 0.75rem;
      font-family: ui-monospace, "SF Mono", Menlo, monospace;
      font-size: 0.82rem;
      color: #d7dadc;
      word-break: break-all;
      user-select: all;
    }}
    .meta {{ color: var(--muted); font-size: 0.85rem; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>🌿 Reddit App Registration Helper</h1>
    <p class="lede">5 minutes. Do this on a <strong>desktop browser</strong> (mobile has OAuth redirect issues with Reddit + Composio).</p>

    <div class="step">
      <h2><span class="num">1</span> Open Reddit app creation</h2>
      <p>Click below. You must be logged in to your Reddit account <code>r3d3y3s79</code>.</p>
      <a class="button" href="https://www.reddit.com/prefs/apps/" target="_blank" rel="noopener">Open reddit.com/prefs/apps →</a>
      <p class="meta" style="margin-top: 0.75rem">Scroll to the bottom. Click <strong>"are you a developer? create an app..."</strong> or <strong>"create another app"</strong>.</p>
    </div>

    <div class="step">
      <h2><span class="num">2</span> Fill in the form</h2>
      <p>Use these exact values. Click any copy button to copy a value, then paste into the form.</p>

      <p class="meta" style="margin: 0.5rem 0 0.25rem"><strong>name</strong></p>
      <div class="field"><span class="value">{APP_NAME}</span><button onclick="copy(this, '{APP_NAME}')">Copy</button></div>

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>App type</strong></p>
      <div class="field"><span class="value">⚪ {SCRIPT_TYPE} (radio button — choose this one)</span></div>
      <p class="meta" style="margin: 0.5rem 0 0.25rem">Why <code>script</code>: Reddit's "script" type is for personal automation. It only has access to your account (which is what we want). <code>web app</code> requires you to host your own OAuth flow — overkill here.</p>

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>description</strong></p>
      <div class="field"><span class="value">{DESCRIPTION}</span><button onclick="copy(this, '{DESCRIPTION}')">Copy</button></div>

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>about url</strong></p>
      <div class="field"><span class="value">{ABOUT_URL}</span><button onclick="copy(this, '{ABOUT_URL}')">Copy</button></div>

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>redirect uri</strong> (this is the critical one — exactly as shown)</p>
      <div class="field"><span class="value">{REDIRECT_URI}</span><button onclick="copy(this, '{REDIRECT_URI}')">Copy</button></div>

      <p class="meta" style="margin: 0.5rem 0">⚠️ Reddit will accept ANY valid URL here at app-creation time. The real validation happens later, when Reddit OAuth checks this URL against what's registered in Composio. Set it to Composio's URL so the round-trip works.</p>
    </div>

    <div class="step">
      <h2><span class="num">3</span> Solve the captcha and submit</h2>
      <p>Reddit uses reCAPTCHA. Solve it (check the "I'm not a robot" box) and click <strong>create app</strong>.</p>
      <div class="warning">
        ⚠️ If you get an error like <code>405 Method Not Allowed</code> or <code>something went wrong</code>, the issue is the captcha. Refresh the page, wait 30 seconds, and try again. Don't use a VPN — Reddit's reCAPTCHA is sensitive to IP changes.
      </div>
    </div>

    <div class="step">
      <h2><span class="num">4</span> Get your credentials</h2>
      <p>After successful creation, Reddit shows your new app. You'll see two values:</p>
      <p class="meta" style="margin: 0.5rem 0"><strong>client_id</strong> = the string under the app icon/name (e.g. <code>d3XyZ_AbCdEf123</code>)</p>
      <p class="meta"><strong>client_secret</strong> = the longer "secret" string below it (e.g. <code>AbCdEf123_-XyZ_456longstring</code>)</p>
      <p>Type or paste them into the boxes below.</p>

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>client_id</strong></p>
      <input type="text" id="client_id" placeholder="paste client_id here" style="width:100%;padding:0.5rem;background:#0e0e0f;border:1px solid var(--border);color:#d7dadc;border-radius:4px;font-family:ui-monospace,monospace;font-size:0.85rem">

      <p class="meta" style="margin: 1rem 0 0.25rem"><strong>client_secret</strong></p>
      <input type="text" id="client_secret" placeholder="paste client_secret here" style="width:100%;padding:0.5rem;background:#0e0e0f;border:1px solid var(--border);color:#d7dadc;border-radius:4px;font-family:ui-monospace,monospace;font-size:0.85rem">
    </div>

    <div class="step">
      <h2><span class="num">5</span> Generate the snippet and send it back</h2>
      <p>Click the button. The snippet is what you paste back to me in Telegram.</p>
      <button onclick="generate()" style="background:var(--green);color:#0e0e0f;border:none;padding:0.6rem 1.2rem;border-radius:4px;font-weight:700;font-size:0.95rem;cursor:pointer;margin-top:0.5rem">Generate credentials snippet</button>

      <div id="snippet-container" style="display:none;margin-top:1rem">
        <p class="meta">Copy this entire line and send it back to me in Telegram:</p>
        <div class="snippet" id="snippet"></div>
        <button onclick="copySnippet()" style="background:var(--accent);color:white;border:none;padding:0.4rem 0.8rem;border-radius:4px;font-weight:600;font-size:0.85rem;cursor:pointer;margin-top:0.5rem">Copy snippet</button>
      </div>
    </div>

    <div class="step">
      <h2>What happens next</h2>
      <p>Once you send the snippet, I'll:</p>
      <ol style="margin: 0; padding-left: 1.25rem; font-size: 0.9rem">
        <li>Create the auth config in Composio with your client_id/secret</li>
        <li>Trigger the connected-account creation — this gives you a Reddit consent URL</li>
        <li>You open that URL in a desktop browser (laptop, not phone)</li>
        <li>Reddit consent screen → click Allow</li>
        <li>I verify the connection, post day-01 to r/houseplants, and show you the live URL</li>
      </ol>
    </div>
  </div>

  <script>
    function copy(btn, text) {{
      navigator.clipboard.writeText(text).then(() => {{
        const orig = btn.textContent;
        btn.textContent = 'Copied';
        btn.classList.add('copied');
        setTimeout(() => {{
          btn.textContent = orig;
          btn.classList.remove('copied');
        }}, 1500);
      }});
    }}

    function generate() {{
      const cid = document.getElementById('client_id').value.trim();
      const csec = document.getElementById('client_secret').value.trim();
      if (!cid || !csec) {{
        alert('Please paste both client_id and client_secret first.');
        return;
      }}
      const snippet = `REDDIT_CREDS={{"client_id":"${{cid}}","client_secret":"${{csec}}","scopes":"{SCOPES}"}}`;
      document.getElementById('snippet').textContent = snippet;
      document.getElementById('snippet-container').style.display = 'block';
    }}

    function copySnippet() {{
      const text = document.getElementById('snippet').textContent;
      navigator.clipboard.writeText(text).then(() => {{
        alert('Snippet copied! Paste it into your Telegram chat with Hermes.');
      }});
    }}
  </script>
</body>
</html>
"""

OUTPUT.write_text(HTML)
size = OUTPUT.stat().st_size
print(f"Helper page written to: {OUTPUT}")
print(f"File size: {size} bytes")

# Also open in default browser for immediate use
try:
    webbrowser.open(f"file://{OUTPUT}")
    print("Opened in default browser.")
except Exception as e:
    print(f"Could not open browser automatically: {e}")
