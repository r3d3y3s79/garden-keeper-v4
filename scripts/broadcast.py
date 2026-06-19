#!/usr/bin/env python3
"""
Garden Keeper — One-off broadcast email sender.
Sends a 5-SKU bundle offer to a list of recipients.
Used by Growth Operator to drive manual traffic from a known seed list
(joe's personal network) into the lead-magnet funnel.

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
LOG_PATH = "/root/the-garden-keeper/logs/broadcast.log"

# Load Gmail creds
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
log = logging.getLogger("broadcast")


SUBJECT = "The Garden Keeper — 5 journals, 1 free plant journal cheat sheet, launch pricing"

HTML_BODY = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>The Garden Keeper — 5-SKU Bundle</title></head>
<body style="margin:0;padding:0;background:#f6f9f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2d20;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(31,45,32,0.08);">
<tr><td style="background:linear-gradient(135deg,#2f6b3a,#74a76a);padding:32px;color:#fff;">
  <div style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;opacity:0.85;">The Garden Keeper</div>
  <h1 style="margin:8px 0 0;font-size:28px;font-weight:600;line-height:1.3;">5 journals. 1 mission.<br>Stop killing your plants.</h1>
</td></tr>
<tr><td style="padding:32px;font-size:16px;line-height:1.6;">
  <p>Hey,</p>
  <p>You asked for a system that actually works. Here's the launch lineup — five watercolor journals, each built around the one mistake I kept making (overwatering, propagation failure, lost planting dates, dead seedlings, no harvest records).</p>
  <p>Each journal has the data fields a real plant parent fills in — not blank pages and good intentions.</p>

  <h2 style="margin:28px 0 8px;font-size:20px;color:#2f6b3a;">The 5-SKU launch lineup</h2>
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:8px 0 24px;">
    <tr style="background:#f6f9f4;">
      <td style="padding:12px 16px;font-weight:600;border-bottom:1px solid #e3eae0;">Essential Tracker</td>
      <td style="padding:12px 16px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">succulents, cacti, single plant log</td>
      <td style="padding:12px 16px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$6.99</td>
    </tr>
    <tr>
      <td style="padding:12px 16px;font-weight:600;border-bottom:1px solid #e3eae0;">Bloom Record</td>
      <td style="padding:12px 16px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">vegetable garden + harvest log</td>
      <td style="padding:12px 16px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$6.99</td>
    </tr>
    <tr style="background:#f6f9f4;">
      <td style="padding:12px 16px;font-weight:600;border-bottom:1px solid #e3eae0;">Seasonal Trio</td>
      <td style="padding:12px 16px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">3 seasonal covers — 90-day reset</td>
      <td style="padding:12px 16px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$11.99</td>
    </tr>
    <tr>
      <td style="padding:12px 16px;font-weight:600;border-bottom:1px solid #e3eae0;">Complete Set</td>
      <td style="padding:12px 16px;color:#6a7a6b;border-bottom:1px solid #e3eae0;">all 5 journals — best value</td>
      <td style="padding:12px 16px;font-weight:600;color:#2f6b3a;text-align:right;border-bottom:1px solid #e3eae0;">$17.99</td>
    </tr>
    <tr style="background:#f6f9f4;">
      <td style="padding:12px 16px;font-weight:600;">VIP Subscription</td>
      <td style="padding:12px 16px;color:#6a7a6b;">monthly journal + cheat sheets</td>
      <td style="padding:12px 16px;font-weight:600;color:#2f6b3a;text-align:right;">$4.99/mo</td>
    </tr>
  </table>

  <h2 style="margin:24px 0 8px;font-size:20px;color:#2f6b3a;">Why a journal works</h2>
  <p>The fastest way to keep a plant alive is to remember what you did last time. Watering dates, fertilizer ratios, when you repotted, the soil mix that failed. Most plant parents lose more plants to "I forgot" than to bad luck.</p>
  <p>The Garden Keeper journals fix that. Each page is a small experiment with a date, a result, and a note to future-you.</p>

  <p style="margin:24px 0;text-align:center;">
    <a href="https://garden-keeper-v4.vercel.app/shop" style="display:inline-block;background:#2f6b3a;color:#fff;text-decoration:none;padding:14px 28px;border-radius:8px;font-weight:600;font-size:15px;">Shop the launch lineup →</a>
  </p>

  <p style="margin-top:24px;font-size:14px;color:#6a7a6b;">P.S. — Not ready to buy? Grab the free <a href="https://garden-keeper-v4.vercel.app/lead-magnet.html" style="color:#2f6b3a;">Plant Care Cheat Sheet</a> — 1 page, 20 houseplants, watering frequency at a glance.</p>
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


def ensure_subscriber(email: str, source: str = "broadcast_growth") -> int:
    """Add subscriber if missing, return id."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM subscribers WHERE email = ?", (email,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    c.execute(
        "INSERT INTO subscribers (email, source, interest) VALUES (?, ?, ?)",
        (email, source, "5-sku-bundle"),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def log_send(subscriber_id: int, subject: str) -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO emails_sent (subscriber_id, email_subject) VALUES (?, ?)",
        (subscriber_id, subject),
    )
    conn.commit()
    conn.close()


def send_one(to_email: str, dry_run: bool = False) -> dict:
    if not FROM_PASS:
        return {"ok": False, "error": "GMAIL_APP_PASSWORD not set"}

    sub_id = ensure_subscriber(to_email)

    msg = MIMEMultipart("alternative")
    msg["From"] = f"The Garden Keeper <{FROM_ADDR}>"
    msg["To"] = to_email
    msg["Subject"] = SUBJECT
    msg.attach(MIMEText(render_html(to_email), "html"))

    if dry_run:
        log.info(f"[DRY-RUN] would send to {to_email}, subject={SUBJECT}")
        return {"ok": True, "dry_run": True, "subscriber_id": sub_id}

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
            s.starttls()
            s.login(FROM_ADDR, FROM_PASS)
            s.sendmail(FROM_ADDR, [to_email], msg.as_string())
        log_send(sub_id, SUBJECT)
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
