#!/bin/bash
# Daily Reddit post drip — runs the next pending day from schedule.json
# Respects Reddit's 9-min rate limit by posting at most 1 per day
# Logs to /root/the-garden-keeper/logs/reddit-drip.log
LOG=/root/the-garden-keeper/logs/reddit-drip.log
mkdir -p "$(dirname "$LOG")"
echo "=== Reddit drip $(date -u) ===" >> "$LOG"
cd /root/the-garden-keeper && /usr/bin/python3 scripts/reddit_cookie_poster.py --next >> "$LOG" 2>&1
echo "" >> "$LOG"
