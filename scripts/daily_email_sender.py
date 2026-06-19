#!/usr/bin/env python3
"""
Garden Keeper — Daily Email Sender
Reads email sequence, sends next email to subscribers at their current day.
"""

import sqlite3
import os
import re
from datetime import datetime
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"
SEQUENCE_PATH = "/root/the-garden-keeper/data/email_sequence.md"

# Read email sequence from markdown file
def parse_email_sequence():
    """Parse email_sequence.md into a dict: day_number -> {subject, preview, body}"""
    with open(SEQUENCE_PATH, 'r') as f:
        content = f.read()
    
    emails = {}
    # Split by DAY header
    days = re.split(r'---\s*\nDAY\s+(\d+):', content)
    
    for i in range(1, len(days), 2):
        day_num = int(days[i])
        section = days[i+1]
        
        subject_match = re.search(r'Subject:\s*(.+)', section)
        preview_match = re.search(r'Preview:\s*(.+)', section)
        body_match = re.search(r'Body:\s*\n(.+)', section, re.DOTALL)
        
        if subject_match and body_match:
            emails[day_num] = {
                'subject': subject_match.group(1).strip(),
                'preview': preview_match.group(1).strip() if preview_match else '',
                'body': body_match.group(1).strip()
            }
    
    return emails

def render_email(template, email):
    """Personalize email template."""
    # Extract first name from email
    first_name = email.split('@')[0].replace('.', ' ').title()
    
    # Simple template substitution
    body = template['body'].replace('{{first_name|Plant Parent}}', first_name)
    body = body.replace('{{first_name}}', first_name)
    
    subject = template['subject'].replace('{{first_name|Plant Parent}}', first_name)
    
    return subject, body

def send_email_smtp(to_email, subject, body):
    """Send email via SMTP. Returns True if sent."""
    # Check if SMTP credentials are configured
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    
    if not all([smtp_host, smtp_user, smtp_pass]):
        # No SMTP configured — save to file for now
        save_email_to_file(to_email, subject, body)
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = to_email
        
        html_body = body.replace('\n', '<br>\n')
        html_body = f"<html><body style='font-family:Inter,sans-serif;max-width:600px;margin:20px auto;line-height:1.6;color:#333;'><div style='background:#2E5E2E;color:white;padding:20px;border-radius:8px 8px 0 0;'><h2 style='margin:0;'>🌿 The Garden Keeper</h2></div><div style='padding:24px;background:#fff;border:1px solid #ddd;border-top:none;border-radius:0 0 8px 8px;'>{html_body}</div><div style='text-align:center;padding:20px;color:#888;font-size:12px;'><p>You received this because you subscribed at thegardenkeeper.shop</p><p><a href='#' style='color:#888;'>Unsubscribe</a></p></div></body></html>"
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"SMTP error: {e}")
        save_email_to_file(to_email, subject, body)
        return False

def save_email_to_file(to_email, subject, body):
    """Save email to file when SMTP not configured."""
    out_dir = "/root/the-garden-keeper/data/emails_out"
    os.makedirs(out_dir, exist_ok=True)
    
    safe_email = to_email.replace('@', '_at_')
    filename = f"{out_dir}/{safe_email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w') as f:
        f.write(f"To: {to_email}\n")
        f.write(f"Subject: {subject}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write("-" * 40 + "\n")
        f.write(body)
    
    print(f"Email saved to: {filename}")

def process_daily_emails():
    """Main function: send next email to all subscribers at their sequence day."""
    emails = parse_email_sequence()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get all active subscribers
    c.execute("SELECT id, email, sequence_day FROM subscribers WHERE status = 'active'")
    subscribers = c.fetchall()
    conn.close()
    
    print(f"Processing {len(subscribers)} subscribers...")
    
    sent_count = 0
    for sub_id, email, day in subscribers:
        if day in emails:
            subject, body = render_email(emails[day], email)
            
            # Send or save
            if send_email_smtp(email, subject, body):
                sent_count += 1
            
            # Update subscriber to next day
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''
                UPDATE subscribers SET sequence_day = sequence_day + 1, last_sent_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (sub_id,))
            c.execute('''
                INSERT INTO emails_sent (subscriber_id, email_subject)
                VALUES (?, ?)
            ''', (sub_id, subject))
            conn.commit()
            conn.close()
            
            print(f"  Day {day} → {email}")
    
    print(f"\n✅ Processed {len(subscribers)} subscribers, sent/queued {sent_count} emails")
    return len(subscribers)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "init":
        # Just initialize DB
        from email_system import init_db
        init_db()
        print("Database initialized")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        from email_system import get_stats
        stats = get_stats()
        print(json.dumps(stats, indent=2))
    else:
        # Run daily email send
        count = process_daily_emails()
        if count == 0:
            print("No subscribers to process")
