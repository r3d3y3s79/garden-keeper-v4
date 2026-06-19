#!/usr/bin/env python3
"""
Garden Keeper — Auto-reply email sender.
Sends the Plant Care Cheat Sheet PDF as an attachment the moment someone
subscribes via the lead magnet form. Uses Gmail SMTP with app password.
"""

import smtplib
import os
import sys
import sqlite3
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from datetime import datetime

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"
# Load Gmail credentials from Hermes env (systemd may not inject them)
_env_path = "/root/.hermes/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
PDF_PATHS = [
    Path("/root/.hermes/skills/ecommerce/ecommerce-stripe-vercel-store/templates/lead-magnet-page/plant-care-cheat-sheet.pdf"),
    Path("/root/the-garden-keeper/lead-magnet/plant-care-cheat-sheet.pdf"),
    Path("/root/the-garden-keeper/public/plant-care-cheat-sheet.pdf"),
]
FROM_ADDR = os.environ.get("GMAIL_USER", "durz0bl1nt1079@gmail.com")
FROM_PASS = os.environ.get("GMAIL_APP_PASSWORD", "")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SITE_URL = "https://garden-keeper-v4.vercel.app"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("/root/the-garden-keeper/logs/auto_reply.log"), logging.StreamHandler()],
)
log = logging.getLogger("auto-reply")


def find_pdf() -> Path | None:
    for p in PDF_PATHS:
        if p.exists() and p.stat().st_size > 1000:
            return p
    # Fallback: try the live URL and download once
    return None


def render_html(subscriber_email: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Your Plant Care Cheat Sheet</title></head>
<body style="margin:0;padding:0;background:#f6f9f4;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2d20;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px;">
<table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 6px 24px rgba(31,45,32,0.08);">
<tr><td style="background:linear-gradient(135deg,#2f6b3a,#74a76a);padding:28px 32px;color:#fff;">
  <div style="font-size:13px;letter-spacing:0.18em;text-transform:uppercase;opacity:0.85;">The Garden Keeper</div>
  <h1 style="margin:8px 0 0;font-size:24px;font-weight:600;">Your cheat sheet is on the way 🌿</h1>
</td></tr>
<tr><td style="padding:28px 32px;font-size:16px;line-height:1.6;">
  <p>Thanks for subscribing. Attached is the <strong>Plant Care Cheat Sheet</strong> — print it, stick it on the fridge, save a plant.</p>
  <p>Inside you'll get:</p>
  <ul>
    <li>Watering frequency for the 20 most common houseplants</li>
    <li>Light requirements at a glance</li>
    <li>Common warning signs + what they really mean</li>
    <li>A 4-season feeding schedule</li>
  </ul>
  <p>Over the next week I'll send a few short emails with the exact routine I use to keep 40+ plants alive in an apartment with no balcony. Reply any time — I read everything.</p>
  <p style="margin:24px 0 8px;">— Joe<br><span style="color:#6a7a6b;font-size:14px;">Founder, The Garden Keeper</span></p>
</td></tr>
<tr><td style="background:#f6f9f4;padding:20px 32px;text-align:center;">
  <a href="{SITE_URL}/shop" style="display:inline-block;background:#2f6b3a;color:#fff;text-decoration:none;padding:12px 22px;border-radius:8px;font-weight:600;font-size:14px;">Shop The Garden Keeper →</a>
  <div style="font-size:12px;color:#6a7a6b;margin-top:14px;">
    You're getting this because you signed up at thegardenkeeper.example.<br>
    <a href="{SITE_URL}/unsubscribe?email={subscriber_email}" style="color:#6a7a6b;">Unsubscribe</a>
  </div>
</td></tr>
</table></td></tr></table>
</body></html>"""


def send_auto_reply(to_email: str) -> dict:
    if not FROM_PASS:
        return {"ok": False, "error": "GMAIL_APP_PASSWORD not set in env"}

    pdf_path = find_pdf()
    if not pdf_path:
        return {"ok": False, "error": "PDF not found locally — would need to download"}

    msg = MIMEMultipart("mixed")
    msg["From"] = f"The Garden Keeper <{FROM_ADDR}>"
    msg["To"] = to_email
    msg["Subject"] = "🌿 Your Plant Care Cheat Sheet (attached)"

    html_part = MIMEText(render_html(to_email), "html")
    msg.attach(html_part)

    try:
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        part = MIMEBase("application", "octet-stream")
        part.set_payload(pdf_data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="plant-care-cheat-sheet.pdf"',
        )
        msg.attach(part)
    except Exception as e:
        return {"ok": False, "error": f"PDF attach failed: {e}"}

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(FROM_ADDR, FROM_PASS)
            smtp.sendmail(FROM_ADDR, [to_email], msg.as_string())
        return {"ok": True, "pdf_size_kb": round(len(pdf_data) / 1024, 1)}
    except smtplib.SMTPAuthenticationError as e:
        return {"ok": False, "error": f"SMTP auth failed: {e.smtp_code} {e.smtp_error.decode(errors='replace')}"}
    except Exception as e:
        return {"ok": False, "error": f"SMTP send failed: {type(e).__name__}: {e}"}


def record_send(subscriber_id: int, subject: str, ok: bool):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO emails_sent (subscriber_id, email_subject, sent_at) VALUES (?, ?, ?)",
            (subscriber_id, subject, datetime.utcnow().isoformat()),
        )
        if ok:
            c.execute(
                "UPDATE subscribers SET last_sent_at = CURRENT_TIMESTAMP, sequence_day = 1 WHERE id = ?",
                (subscriber_id,),
            )
        conn.commit()
        conn.close()
    except Exception as e:
        log.warning("Failed to record send for sub_id=%s: %s", subscriber_id, e)


def process_pending():
    """Find subscribers who haven't had day-1 email yet."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, email FROM subscribers WHERE status='active' AND sequence_day = 0 ORDER BY subscribed_at ASC"
    )
    pending = c.fetchall()
    conn.close()
    return pending


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Manual test: send to LEAF_RECIPIENT or to address arg
        recipient = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("LEAD_RECIPIENT", FROM_ADDR)
        log.info("Test send to %s", recipient)
        result = send_auto_reply(recipient)
        print(result)
        sys.exit(0 if result["ok"] else 1)

    pending = process_pending()
    if not pending:
        print("No pending subscribers.")
        sys.exit(0)
    log.info("Found %d pending subscriber(s)", len(pending))
    for sub_id, email in pending:
        log.info("Sending auto-reply to sub_id=%s email=%s", sub_id, email)
        result = send_auto_reply(email)
        record_send(sub_id, "Plant Care Cheat Sheet", result["ok"])
        log.info("Result: %s", result)
