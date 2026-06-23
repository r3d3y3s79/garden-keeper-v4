#!/usr/bin/env python3
"""
Garden Keeper — Email Lead Capture & Nurture System
SQLite-backed, runs on VPS, zero external dependencies.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs

DB_PATH = "/root/the-garden-keeper/data/subscribers.db"

# Connection helper used everywhere — WAL mode + 30s busy_timeout
# prevents "database is locked" errors when concurrent writers hit the
# DB at the same time. WAL also lets readers proceed during writes.
def _connect(timeout=30):
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
    except Exception:
        pass
    return conn

def init_db():
    """Create SQLite database with subscriber table."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = _connect()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            source TEXT DEFAULT 'store',
            interest TEXT DEFAULT 'general',
            subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sent_at TIMESTAMP,
            sequence_day INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active',
            opens INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS emails_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscriber_id INTEGER,
            email_subject TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            opened_at TIMESTAMP,
            clicked_at TIMESTAMP,
            FOREIGN KEY (subscriber_id) REFERENCES subscribers(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_subscriber(email, source='store', interest='general'):
    """Add a new subscriber to the database."""
    conn = None
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute('''
            INSERT INTO subscribers (email, source, interest)
            VALUES (?, ?, ?)
        ''', (email, source, interest))
        conn.commit()
        return {"success": True, "message": "Subscribed!"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Already subscribed."}
    finally:
        if conn is not None:
            try: conn.close()
            except Exception: pass

def get_stats():
    """Get subscriber statistics."""
    conn = _connect()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM subscribers WHERE status = 'active'")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM subscribers WHERE DATE(subscribed_at) = DATE('now')")
    today = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM subscribers WHERE sequence_day > 0")
    nurtured = c.fetchone()[0]

    conn.close()
    return {
        "total_active": total,
        "new_today": today,
        "in_nurture": nurtured,
        "timestamp": datetime.now().isoformat()
    }

def get_subscribers_for_day(day_number):
    """Get subscribers who should receive day N of sequence."""
    conn = _connect()
    c = conn.cursor()
    c.execute('''
        SELECT id, email, sequence_day FROM subscribers
        WHERE status = 'active' AND sequence_day = ?
    ''', (day_number,))
    subscribers = c.fetchall()
    conn.close()
    return subscribers

def increment_sequence_day(subscriber_id):
    """Move subscriber to next day in sequence."""
    conn = None
    try:
        conn = _connect()
        c = conn.cursor()
        c.execute('''
            UPDATE subscribers
            SET sequence_day = sequence_day + 1, last_sent_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (subscriber_id,))
        conn.commit()
    finally:
        if conn is not None:
            try: conn.close()
            except Exception: pass

if __name__ == "__main__":
    init_db()
    print("✅ Email system database initialized")
    print(f"   Database: {DB_PATH}")
    stats = get_stats()
    print(f"   Active subscribers: {stats['total_active']}")
