#!/usr/bin/env python3
"""
Garden Keeper — GARDEN10 broadcast.
Sends an honest "10% off with code GARDEN10" email.
Uses a unique subject so it doesn't collide with the prior "20% off" emails.

Reads GMAIL_USER + GMAIL_APP_PASSWORD from /root/.hermes/.env
Logs to subscribers.db `emails_sent` table.
"""
import os
import sys
import smtplib
import sqlite3
import logging
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"
LOG_PATH = "/root/the-garden-keeper/logs/broadcast_garden10.log"

_env_path = "/root/.hermes/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

FROM_ADDR = os.environ.get("GMAIL_USER", "durz0bl1nt1079@gmail.com")
FROM_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SITE_URL = "https://garden-keeper-v4.vercel.app"

Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger("broadcast_garden10")

SUBJECT = "🌿 GARDEN10 — 10% off your first Garden Keeper journal"

HTML_BODY = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>GARDEN10 — 10% off</title></head>
<body style="margin:0;padding:0;background:#f6f9f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2d20;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(31,45,32,0.08);">
<tr><td style="background:linear-gradient(135deg,#2f6b3a,#74a76a);padding:32px;color:#fff;">
  <div style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;opacity:0.85;">The Garden Keeper</div>
  <h1 style="margin:8px 0 0;font-size:28px;font-weight:600;line-height:1.3;">Use code <span style="background:#fff;color:#2f6b3a;padding:2px 10px;border-radius:6px;">GARDEN10</span><br>for 10% off your first journal.</h1>
</td></tr>
<tr><td style="padding:32px;font-size:16px;line-height:1.6;">
  <p>Hey,</p>
  <p>Quick one — the Garden Keeper launch is live. Five watercolor plant journals, all priced at $6.99 (or grab the <b>Complete Set</b> for $17.99).</p>
  <p>As a first-time buyer, drop in <b>GARDEN10</b> at checkout for 10% off anything in the shop. Works on all 5 SKUs and the Complete Set.</p>

  <h2 style="margin:24px 0 8px;font-size:20px;color:#2f6b3a;">The lineup</h2>
  <ul style="line-height:1.8;padding-left:20px;">
    <li><b>Essential Tracker</b> — succulent & single-plant log ($6.99)</li>
    <li><b>Bloom Record</b> — vegetable garden + harvest log ($6.99)</li>
    <li><b>Seasonal Trio</b> — 3 seasonal covers, 90-day reset ($11.99)</li>
    <li><b>Complete Set</b> — all 5 journals, best value ($17.99)</li>
    <li><b>VIP Subscription</b> — monthly journal + cheat sheets ($4.99/mo)</li>
  </ul>

  <p style="margin:24px 0;text-align:center;">
    <a href="https://garden-keeper-v4.vercel.app/#products" style="display:inline-block;background:#2f6b3a;color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:15px;">Shop with GARDEN10 →</a>
  </p>

  <p style="margin-top:24px;font-size:14px;color:#6a7a6b;">Code works at checkout. One per customer. No expiry set yet.</p>
  <p style="font-size:14px;color:#6a7a6b;">P.S. — Not buying yet? Grab the free <a href="https://garden-keeper-v4.vercel.app/#lead-magnet" style="color:#2f6b3a;">Plant Care Cheat Sheet</a>.</p>
</td></tr>
<tr><td style="background:#f6f9f4;padding:20px 32px;text-align:center;font-size:12px;color:#6a7a6b;">
  Sent from The Garden Keeper, an independent project by Joe.<br>
  <a href="{unsub}" style="color:#6a7a6b;">Unsubscribe</a>
</td></tr>
</table></td></tr></table>
</body></html>"""


def render_html(email: str) -> str:
    unsub = f"{SITE_URL}/unsubscribe?email={email}"
    return HTML_BODY.replace("{unsub}", unsub)


def send_one(to_email: str, dry_run: bool = False) -> dict:
    if not FROM_PASS:
        return {"ok": False, "error": "GMAIL_APP_PASSWORD not set"}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"The Garden Keeper <{FROM_ADDR}>"
    msg["To"] = to_email
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(render_html(to_email), "html"))

    if dry_run:
        log.info(f"[DRY-RUN] would send to {to_email}")
        return {"ok": True, "dry_run": True}

    # Log to DB first
    con = sqlite3.connect(DB_PATH)
    c = con.cursor()
    # Find or create subscriber
    c.execute("SELECT id FROM subscribers WHERE email = ?", (to_email,))
    row = c.fetchone()
    if row:
        sub_id = row[0]
    else:
        c.execute("INSERT INTO subscribers (email, source, interest) VALUES (?, ?, ?)",
                  (to_email, "broadcast_garden10", "first-order-discount"))
        sub_id = c.lastrowid
        con.commit()
    c.execute("INSERT INTO emails_sent (subscriber_id, email_subject) VALUES (?, ?)",
              (sub_id, SUBJECT))
    con.commit()
    con.close()

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.starttls()
            s.login(FROM_ADDR, FROM_PASS)
            s.sendmail(FROM_ADDR, [to_email], msg.as_string())
        log.info(f"SENT to {to_email} (subscriber_id={sub_id})")
        return {"ok": True, "subscriber_id": sub_id, "sent_at": datetime.utcnow().isoformat()}
    except Exception as e:
        log.error(f"FAILED to {to_email}: {e}")
        return {"ok": False, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="comma-separated recipient list")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not FROM_PASS:
        print("FATAL: GMAIL_APP_PASSWORD not set in /root/.hermes/.env")
        sys.exit(1)

    recipients = [r.strip() for r in args.to.split(",") if r.strip()]
    results = []
    for r in recipients:
        results.append({"to": r, **send_one(r, dry_run=args.dry_run)})

    ok = sum(1 for r in results if r.get("ok"))
    print(f"=== SUMMARY: {ok}/{len(results)} sent ===")
    for r in results:
        print(f"  {r['to']:>40}  ok={r.get('ok')}  err={r.get('error','')}")
    sys.exit(0 if ok == len(results) else 2)


if __name__ == "__main__":
    main()