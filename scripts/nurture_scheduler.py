#!/usr/bin/env python3
"""
Garden Keeper — Nurture scheduler
Runs every 30 minutes via cron. For each email in the day-2 → day-14 sequence,
find subscribers at the right sequence_day who have waited long enough since
their last send, then send the email via Gmail SMTP and advance their day.

Sends are idempotent: a subscriber who just received day-2 won't get day-4
until at least `min_hours_since_last` have passed and they've been bumped to
sequence_day=2.

Backfill is a separate one-time SQL operation (see scripts/backfill_nurture.py
or run manually), so this file stays focused on the per-run loop.
"""

import os
import sys
import sqlite3
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Make sibling scripts importable when run via cron with a different cwd.
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from emails import day2, day4, day7, day10, day14  # noqa: E402

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"
LOG_PATH = "/root/the-garden-keeper/logs/nurture.log"
ENV_PATH = "/root/.hermes/.env"

# Gmail SMTP — same path as auto_reply.py
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
FROM_ADDR = os.environ.get("GMAIL_USER", "durz0bl1nt1079@gmail.com")
SITE_URL = "https://garden-keeper-v4.vercel.app"

# Order matters: scheduler picks the first module whose target_sequence_day
# matches the subscriber's current state. New emails go at the end.
SEQUENCE = [day2, day4, day7, day10, day14]

# How many hours of slop before an email is considered "overdue". This lets
# the 30-minute cron catch up on missed runs without spamming anyone.
OVERDUE_GRACE_HOURS = 2


def load_env():
    """Load GMAIL_USER / GMAIL_APP_PASSWORD from the Hermes env file."""
    if not os.path.exists(ENV_PATH):
        return
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def setup_logging():
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH),
            logging.StreamHandler(),
        ],
    )
    return logging.getLogger("nurture")


def find_due_subscribers(log, target_day: int, min_hours: int):
    """Return list of (id, email, hours_since_last) for subs at target_day."""
    cutoff = datetime.utcnow() - timedelta(hours=min_hours - OVERDUE_GRACE_HOURS)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, email,
               CAST((julianday('now') - julianday(last_sent_at)) * 24 AS REAL) AS hours_since
        FROM subscribers
        WHERE status = 'active'
          AND sequence_day = ?
          AND last_sent_at IS NOT NULL
          AND last_sent_at <= ?
        ORDER BY last_sent_at ASC
        """,
        (target_day, cutoff_str),
    )
    rows = c.fetchall()
    conn.close()
    return rows


def send_email(log, to_email: str, subject: str, html_body: str) -> dict:
    """Send a single HTML email via Gmail SMTP. Returns {ok, error?, kb?}."""
    app_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not app_pass:
        return {"ok": False, "error": "GMAIL_APP_PASSWORD not set"}

    msg = MIMEMultipart("alternative")
    msg["From"] = f"The Garden Keeper <{FROM_ADDR}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(FROM_ADDR, app_pass)
            smtp.sendmail(FROM_ADDR, [to_email], msg.as_string())
        return {"ok": True, "kb": round(len(msg.as_string()) / 1024, 1)}
    except smtplib.SMTPAuthenticationError as e:
        return {"ok": False, "error": f"SMTP auth failed: {e.smtp_code}"}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def advance_subscriber(sub_id: int, new_day: int, subject: str):
    """Bump sequence_day to new_day, stamp last_sent_at, log to emails_sent."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE subscribers
        SET sequence_day = ?, last_sent_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (new_day, sub_id),
    )
    c.execute(
        "INSERT INTO emails_sent (subscriber_id, email_subject, sent_at) VALUES (?, ?, ?)",
        (sub_id, subject, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def run_once(log) -> dict:
    """One scheduler pass. Returns a small summary dict for logging."""
    summary = {"checked": 0, "sent": 0, "failed": 0, "skipped_no_match": 0}
    log.info("=== nurture scheduler run ===")
    for module in SEQUENCE:
        due = find_due_subscribers(log, module.target_sequence_day, module.min_hours_since_last)
        if not due:
            summary["skipped_no_match"] += 1
            continue
        log.info(
            "day %s → %d candidate(s) (need ≥%dh since last send)",
            module.target_sequence_day,
            len(due),
            module.min_hours_since_last,
        )
        for sub_id, email, hours_since in due:
            summary["checked"] += 1
            html = module.render_html(email)
            result = send_email(log, email, module.subject, html)
            if result["ok"]:
                advance_subscriber(sub_id, module.target_sequence_day, module.subject)
                log.info(
                    "  ✓ sent day=%s to sub_id=%s email=%s (waited %.1fh, %s KB)",
                    module.target_sequence_day, sub_id, email, hours_since, result["kb"],
                )
                summary["sent"] += 1
            else:
                log.warning(
                    "  ✗ FAILED day=%s sub_id=%s email=%s: %s — leaving state for retry",
                    module.target_sequence_day, sub_id, email, result["error"],
                )
                summary["failed"] += 1
    log.info("=== run complete: %s ===", summary)
    return summary


def main():
    load_env()
    log = setup_logging()
    if not os.environ.get("GMAIL_APP_PASSWORD"):
        log.error("GMAIL_APP_PASSWORD missing — cannot send. Aborting.")
        sys.exit(2)
    run_once(log)


if __name__ == "__main__":
    main()
