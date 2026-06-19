#!/usr/bin/env python3
"""
One-time backfill for the existing Garden Keeper subscribers (was 14 at the
time the task was written, 15 by the time backfill runs).

Before the day-2 nurture existed, day-1 was sent by auto_reply.py, which set
sequence_day=1 on every successful send. The day-2 scheduler only fires for
subscribers at sequence_day=1 with last_sent_at at least 23h ago, so the
existing list is already correctly positioned for day-2 on the next cron run.

This script resets every active subscriber that is NOT one of the two
Task-1 tunnel smoke-test addresses (created during the systemd-cloudflared
E2E check) back to sequence_day=0, so they pick up day-2 on the next
scheduler run. We preserve last_sent_at (used by the 23h-since-last check)
so we don't accidentally fire day-2 immediately for subs whose last send
was minutes ago — they'll wait the full 23h like anyone else.

Run: python3 /root/the-garden-keeper/scripts/backfill_nurture.py
"""
import os
import sqlite3
import sys
from datetime import datetime

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"

# The only addresses we explicitly exclude. These were inserted during the
# Task-1 systemd tunnel smoke test and shouldn't enter the live nurture loop.
EXCLUDE_EMAIL_PATTERNS = (
    "@test.local",
    "@vercel-check.local",
)


def main():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT id, email, sequence_day, last_sent_at FROM subscribers "
        "WHERE status='active' ORDER BY id"
    )
    rows = c.fetchall()

    excluded = [r for r in rows if any(p in r[1] for p in EXCLUDE_EMAIL_PATTERNS)]
    targets = [r for r in rows if r not in excluded]

    print(f"Active subscribers total: {len(rows)}")
    print(f"  Will receive nurture (sequence_day → 0): {len(targets)}")
    print(f"  Excluded (Task-1 tunnel test rows):       {len(excluded)}")
    print()
    print("Targets before backfill:")
    for r in targets:
        print(f"  id={r[0]:>3}  day={r[2]}  last_sent={r[3]}  {r[1]}")
    print()
    print("Excluded (left untouched):")
    for r in excluded:
        print(f"  id={r[0]:>3}  day={r[2]}  last_sent={r[3]}  {r[1]}")

    if targets:
        c.execute(
            "UPDATE subscribers SET sequence_day = 0 WHERE id IN ({})".format(
                ",".join("?" * len(targets))
            ),
            [r[0] for r in targets],
        )
        conn.commit()

    print()
    print(
        f"Backfill complete at {datetime.utcnow().isoformat()}Z — "
        f"{len(targets)} subscriber(s) reset to sequence_day=0."
    )
    conn.close()


if __name__ == "__main__":
    main()
