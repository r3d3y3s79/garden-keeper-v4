#!/usr/bin/env python3
"""
Garden Keeper Pinterest Traffic Bot
Uses pinterest-login via browser automation or n8n Pinterest node.
For now, it pings the n8n webhook to register a Pinterest traffic event.
"""
import os, json, requests

def log_event():
    webhook = os.environ.get('GK_N8N_WEBHOOK', 'http://72.61.141.125:5678/webhook/garden-keeper-social')
    try:
        r = requests.post(webhook, json={"source":"cron-pinterest","channel":"pinterest"}, timeout=10)
        print(json.dumps({"status": r.status_code, "body": r.text[:200]}))
    except Exception as e:
        print(json.dumps({"error": str(e)}))

if __name__ == '__main__':
    log_event()
