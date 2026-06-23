#!/usr/bin/env python3
"""
Simple HTTP API for email capture from The Garden Keeper store.
Serves on port 8889 (separate from store on 8888).
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sys
import os

# Load Gmail credentials from Hermes env (systemd unit may not inject them)
_env_path = "/root/.hermes/.env"
if os.path.exists(_env_path):
    with open(_env_path) as _ef:
        for _line in _ef:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# Add scripts path
sys.path.insert(0, '/root/the-garden-keeper/scripts')
from email_system import add_subscriber, init_db
from auto_reply import send_auto_reply, record_send

class EmailHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logs to save tokens
        pass
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/stripe-webhook':
            self._handle_stripe_webhook()
        elif self.path == '/api/subscribe':
            import sqlite3 as _sq
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(post_data)
                email = data.get('email', '').strip().lower()
                source = data.get('source', 'store')
                interest = data.get('interest', 'general')
                
                if not email or '@' not in email:
                    self._send_json(400, {"success": False, "message": "Invalid email"})
                    return
                
                result = add_subscriber(email, source, interest)
                # Fire auto-reply with PDF attachment on every new subscription
                if result['success']:
                    try:
                        ar = send_auto_reply(email)
                        if ar['ok']:
                            # Mark day-1 as sent
                            _c = None
                            try:
                                _c = _sq.connect('/root/the-garden-keeper/data/subscribers.db', timeout=30)
                                _c.execute("PRAGMA journal_mode=WAL")
                                _c.execute("PRAGMA busy_timeout=30000")
                                _c.execute("UPDATE subscribers SET last_sent_at=CURRENT_TIMESTAMP, sequence_day=1 WHERE email=?", (email,))
                                _c.commit()
                            finally:
                                if _c is not None:
                                    try: _c.close()
                                    except Exception: pass
                        result['auto_reply'] = ar
                    except Exception as ar_err:
                        result['auto_reply'] = {'ok': False, 'error': str(ar_err)}
                self._send_json(200 if result['success'] else 409, result)
                
            except Exception as e:
                self._send_json(500, {"success": False, "message": str(e)})
        elif self.path == '/api/upload-cookies':
            self._handle_upload_cookies()
        elif self.path == '/api/recover-abandoned':
            self._handle_recover_abandoned()
        else:
            self._send_json(404, {"success": False, "message": "Not found"})

    def do_GET(self):
        if self.path == '/api/stats':
            from email_system import get_stats
            stats = get_stats()
            self._send_json(200, stats)
        elif self.path == '/api/upload-cookies':
            self._handle_upload_cookies()
        elif self.path == '/api/dashboard':
            self._handle_dashboard()
        elif self.path == '/api/recover-abandoned':
            # GET returns the abandoned report (same as POST action=list)
            self._handle_recover_abandoned()
        elif self.path == '/health':
            self._send_json(200, {"status": "ok", "service": "garden-keeper-email-api", "port": 8889})
        else:
            self._send_json(404, {"success": False, "message": "Not found"})

    def _handle_recover_abandoned(self):
        """Query Stripe for unpaid checkout sessions and emit a recovery report.

        POST body (all optional):
          action: "list"  -> return abandoned sessions grouped by recoverability
          action: "send" -> email recovery to known addresses, log unknown ones

        GET returns the same report as action=list.

        Returns JSON: { success, abandoned[], recoverable_count,
                        unrecoverable_count, total_value_cents, ... }
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length).decode('utf-8') if content_length else '{}'
            try:
                body = json.loads(raw) if raw else {}
            except Exception:
                body = {}

            action = (body.get('action') or 'list').strip().lower()

            # Pull the Stripe live key from env
            stripe_key = (
                os.environ.get('STRIPE_LIVE_SECRET_KEY') or
                os.environ.get('STRIPE_SECRET_KEY') or
                ''
            ).strip()
            if not stripe_key:
                self._send_json(500, {"success": False, "message": "No Stripe key configured"})
                return

            # Pull all checkout sessions (paginated, up to 100 per page)
            import urllib.request as _ur, urllib.error as _ue, base64 as _b64
            from datetime import datetime as _dt2
            auth = 'Basic ' + _b64.b64encode(f'{stripe_key}:'.encode()).decode()
            sessions = []
            starting_after = None
            for _ in range(10):
                url = 'https://api.stripe.com/v1/checkout/sessions?limit=100'
                if starting_after:
                    url += f'&starting_after={starting_after}'
                req = _ur.Request(url, headers={'Authorization': auth})
                try:
                    with _ur.urlopen(req, timeout=20) as r:
                        page = json.loads(r.read())
                except _ue.HTTPError as e:
                    self._send_json(502, {"success": False, "message": f"Stripe error {e.code}: {e.read().decode()[:200]}"})
                    return
                data = page.get('data', [])
                sessions.extend(data)
                if not page.get('has_more') or not data:
                    break
                starting_after = data[-1]['id']

            abandoned = []
            for s in sessions:
                if s.get('payment_status') != 'unpaid':
                    continue
                abandoned.append({
                    'session_id': s.get('id'),
                    'amount_cents': s.get('amount_total', 0),
                    'currency': s.get('currency', 'usd'),
                    'created': s.get('created'),
                    'expires_at': s.get('expires_at'),
                    'status': s.get('status'),
                    'payment_link': s.get('payment_link'),
                    'email': (
                        s.get('customer_email') or
                        (s.get('customer_details') or {}).get('email')
                    ),
                    'customer': s.get('customer'),
                    'metadata': s.get('metadata') or {},
                })

            total_cents = sum(a['amount_cents'] for a in abandoned)
            with_email = [a for a in abandoned if a['email']]
            without_email = [a for a in abandoned if not a['email']]

            result = {
                'success': True,
                'action': action,
                'generated_at': _dt2.now().isoformat(timespec='seconds'),
                'abandoned_count': len(abandoned),
                'recoverable_count': len(with_email),
                'unrecoverable_count': len(without_email),
                'total_value_cents': total_cents,
                'total_value_usd': round(total_cents / 100.0, 2),
                'abandoned': abandoned,
            }

            if action == 'send':
                emailed, errors = [], []
                for a in with_email:
                    try:
                        from auto_reply import send_recovery_email
                        r = send_recovery_email(a['email'], a['session_id'], a['amount_cents'])
                        emailed.append({'email': a['email'], 'session_id': a['session_id'], 'result': r})
                    except Exception as e:
                        errors.append({'email': a['email'], 'error': str(e)})
                result['emails_sent'] = len(emailed)
                result['emailed'] = emailed
                result['errors'] = errors
                result['missing_emails'] = [
                    {'session_id': a['session_id'], 'amount_cents': a['amount_cents'],
                     'created': a['created'], 'payment_link': a['payment_link']}
                    for a in without_email
                ]

            self._send_json(200, result)
        except Exception as e:
            import traceback
            self._send_json(500, {"success": False, "message": f"Recover error: {e}",
                                   "trace": traceback.format_exc()[:500]})

    def _handle_stripe_webhook(self):
        """Receive a Stripe webhook event from the Vercel proxy.
        Persists paid orders to /root/the-garden-keeper/data/orders.json
        and merges the buyer email into the subscribers DB.

        Event types handled:
          - checkout.session.completed
          - payment_intent.succeeded
        Anything else is acknowledged with 200 (so Stripe doesn't retry).
        """
        import sqlite3 as _sq
        from datetime import datetime as _dt
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw = self.rfile.read(content_length).decode('utf-8') if content_length else ''
            if not raw:
                self._send_json(400, {"success": False, "message": "Empty body"})
                return
            try:
                event = json.loads(raw)
            except Exception as e:
                self._send_json(400, {"success": False, "message": f"Invalid JSON: {e}"})
                return

            event_id = event.get('id') or f"evt_{int(_dt.now().timestamp() * 1000)}"
            event_type = event.get('type', 'unknown')

            ORDERS_PATH = '/root/the-garden-keeper/data/orders.json'
            os.makedirs(os.path.dirname(ORDERS_PATH), exist_ok=True)

            # Load or init orders file
            try:
                with open(ORDERS_PATH, 'r') as _f:
                    orders_data = json.loads(_f.read() or '{}')
            except (FileNotFoundError, json.JSONDecodeError):
                orders_data = {"orders": [], "total_revenue_cents": 0, "updated_at": None}

            order_entry = None
            buyer_email = None

            if event_type == 'checkout.session.completed':
                obj = event.get('data', {}).get('object', {}) or {}
                buyer_email = (obj.get('customer_email') or obj.get('customer_details', {}).get('email') or '').strip().lower() or None
                amount_total = obj.get('amount_total')
                currency = obj.get('currency', 'usd')
                session_id = obj.get('id', '')
                payment_status = obj.get('payment_status', 'unknown')
                metadata = obj.get('metadata') or {}
                line_items = obj.get('line_items') or {}  # may be empty without expand

                order_entry = {
                    "order_id": session_id,
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "email": buyer_email,
                    "amount_cents": amount_total,
                    "currency": currency,
                    "payment_status": payment_status,
                    "product_lookup": metadata.get('price_lookup') or metadata.get('product') or 'unknown',
                    "fulfillment_status": "pending",
                    "received_at": _dt.now().isoformat(timespec='seconds'),
                }
            elif event_type == 'payment_intent.succeeded':
                obj = event.get('data', {}).get('object', {}) or {}
                buyer_email = None  # PI doesn't carry email by default; session event will have it
                amount_total = obj.get('amount_received')
                currency = obj.get('currency', 'usd')
                pi_id = obj.get('id', '')
                order_entry = {
                    "order_id": pi_id,
                    "stripe_event_id": event_id,
                    "event_type": event_type,
                    "email": None,
                    "amount_cents": amount_total,
                    "currency": currency,
                    "payment_status": "succeeded",
                    "product_lookup": "unknown",
                    "fulfillment_status": "pending",
                    "received_at": _dt.now().isoformat(timespec='seconds'),
                }
            else:
                # Acknowledge unknown events without storing anything
                self._send_json(200, {"received": True, "event_type": event_type, "action": "ignored"})
                return

            if order_entry is None:
                self._send_json(200, {"received": True, "action": "no_order_extracted"})
                return

            # Idempotency: don't double-write the same order
            existing_ids = {o.get('stripe_event_id') for o in orders_data.get('orders', [])}
            if order_entry['stripe_event_id'] in existing_ids:
                self._send_json(200, {"received": True, "action": "duplicate_skipped", "order_id": order_entry['order_id']})
                return

            orders_data.setdefault('orders', []).append(order_entry)
            orders_data['total_revenue_cents'] = sum(
                (o.get('amount_cents') or 0) for o in orders_data['orders']
                if o.get('payment_status') in ('paid', 'succeeded', 'complete')
            )
            orders_data['updated_at'] = _dt.now().isoformat(timespec='seconds')
            with open(ORDERS_PATH, 'w') as _f:
                json.dump(orders_data, _f, indent=2)

            # Merge buyer email into subscribers DB
            merged = False
            if buyer_email and '@' in buyer_email:
                _c = None
                try:
                    _c = _sq.connect('/root/the-garden-keeper/data/subscribers.db', timeout=30)
                    _c.execute("PRAGMA journal_mode=WAL")
                    _c.execute("PRAGMA busy_timeout=30000")
                    _c.execute('''
                        INSERT OR IGNORE INTO subscribers (email, source, interest, status)
                        VALUES (?, 'stripe_paid', 'paying_customer', 'active')
                    ''', (buyer_email,))
                    # If they already existed, bump interest to paying_customer
                    _c.execute('''
                        UPDATE subscribers
                        SET interest = 'paying_customer', source = COALESCE(NULLIF(source, ''), 'stripe_paid')
                        WHERE email = ? AND interest != 'paying_customer'
                    ''', (buyer_email,))
                    _c.commit()
                    # Confirm merge
                    row = _c.execute('SELECT id, interest, source FROM subscribers WHERE email = ?', (buyer_email,)).fetchone()
                    if row:
                        merged = True
                        order_entry['subscriber_id'] = row[0]
                        # Save back the updated entry
                        orders_data['orders'][-1] = order_entry
                        with open(ORDERS_PATH, 'w') as _f:
                            json.dump(orders_data, _f, indent=2)
                except Exception as db_err:
                    order_entry['subscriber_merge_error'] = str(db_err)
                finally:
                    if _c is not None:
                        try: _c.close()
                        except Exception: pass

            self._send_json(200, {
                "received": True,
                "event_type": event_type,
                "order_id": order_entry['order_id'],
                "amount_cents": order_entry['amount_cents'],
                "currency": order_entry['currency'],
                "buyer_email": buyer_email,
                "subscriber_merged": merged,
                "orders_path": ORDERS_PATH,
                "total_orders": len(orders_data['orders']),
                "total_revenue_cents": orders_data['total_revenue_cents'],
            })
        except Exception as e:
            import traceback
            self._send_json(500, {"success": False, "message": f"Webhook error: {e}", "trace": traceback.format_exc()[:500]})

    def _handle_dashboard(self):
        """Live metrics dashboard data — revenue, list size, conversion rate,
        recent orders. CEO's eyes for the $1K Weekend."""
        import sqlite3 as _sq
        from datetime import datetime as _dt, timedelta as _td
        try:
            ORDERS_PATH = '/root/the-garden-keeper/data/orders.json'
            try:
                with open(ORDERS_PATH, 'r') as _f:
                    orders_data = json.loads(_f.read() or '{}')
            except (FileNotFoundError, json.JSONDecodeError):
                orders_data = {"orders": [], "total_revenue_cents": 0, "updated_at": None}

            orders = orders_data.get('orders', []) or []
            revenue_cents = orders_data.get('total_revenue_cents', 0) or 0

            # Subscriber stats
            _db = None
            try:
                _db = _sq.connect('/root/the-garden-keeper/data/subscribers.db', timeout=30)
                _db.execute("PRAGMA journal_mode=WAL")
                _db.execute("PRAGMA busy_timeout=30000")
                db = _db
                sub_count = db.execute('SELECT COUNT(*) FROM subscribers WHERE status = "active"').fetchone()[0]
                # Last 7d signups
                week_ago = (_dt.now() - _td(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                recent_signups = db.execute(
                    'SELECT COUNT(*) FROM subscribers WHERE subscribed_at >= ?', (week_ago,)
                ).fetchone()[0]
                # Top sources
                sources = db.execute(
                    'SELECT source, COUNT(*) c FROM subscribers GROUP BY source ORDER BY c DESC LIMIT 5'
                ).fetchall()
            finally:
                if _db is not None:
                    try: _db.close()
                    except Exception: pass

            paid_count = sum(1 for o in orders if o.get('payment_status') in ('paid', 'succeeded', 'complete'))
            conversion_rate = (paid_count / sub_count * 100.0) if sub_count > 0 else 0.0

            dashboard = {
                "generated_at": _dt.now().isoformat(timespec='seconds'),
                "revenue": {
                    "total_cents": revenue_cents,
                    "total_usd": round(revenue_cents / 100.0, 2),
                    "orders_count": len(orders),
                    "paid_orders_count": paid_count,
                },
                "subscribers": {
                    "active_total": sub_count,
                    "new_last_7d": recent_signups,
                    "top_sources": [{"source": s[0], "count": s[1]} for s in sources],
                },
                "conversion": {
                    "rate_pct": round(conversion_rate, 2),
                    "paid": paid_count,
                    "subscribers": sub_count,
                },
                "recent_orders": orders[-10:],  # last 10
                "kpi_targets": {
                    "weekend_target_usd": 1000,
                    "progress_pct": round((revenue_cents / 100000) * 100, 2),
                    "remaining_usd": max(0, round(1000 - (revenue_cents / 100.0), 2)),
                },
            }
            self._send_json(200, dashboard)
        except Exception as e:
            import traceback
            self._send_json(500, {"success": False, "message": f"Dashboard error: {e}", "trace": traceback.format_exc()[:500]})

    def _handle_upload_cookies(self):
        """Receive a cookies.txt file from the Vercel proxy and save
        it to /root/.agent-reach/ for the agent-reach tool to pick up.
        Also notifies Joe via Telegram."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            filename = data.get('filename', '').strip()
            service = data.get('service', '').strip()
            content = data.get('content', '')

            if not filename or not content:
                self._send_json(400, {"success": False, "message": "filename and content required"})
                return

            # Security: validate filename, no path traversal
            safe_name = ''.join(c for c in filename if c.isalnum() or c in '._-')
            if not safe_name or safe_name != filename:
                self._send_json(400, {"success": False, "message": "Invalid filename (only a-z 0-9 . _ - allowed)"})
                return

            # Security: size limit
            if len(content) > 1_000_000:  # 1MB hard cap
                self._send_json(400, {"success": False, "message": "File too large (>1MB)"})
                return

            # Save to /root/.agent-reach/ with timestamp suffix to avoid collisions
            target_dir = "/root/.agent-reach"
            os.makedirs(target_dir, exist_ok=True)
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            base, ext = os.path.splitext(safe_name)
            final_name = f"{base}-{ts}{ext}"
            final_path = os.path.join(target_dir, final_name)
            with open(final_path, 'w') as f:
                f.write(content)
            os.chmod(final_path, 0o600)  # owner read/write only — these are credentials

            # Send Telegram notification (best-effort)
            try:
                sys.path.insert(0, '/root/.hermes/scripts')
                from telegram_sender import send_message
                msg = (
                    f"🍪 **Cookies uploaded**\n\n"
                    f"**Service:** `{service}`\n"
                    f"**File:** `{safe_name}`\n"
                    f"**Saved to:** `{final_path}`\n"
                    f"**Size:** {len(content):,} bytes\n\n"
                    f"Next agent run will run `agent-reach configure {service}-cookies` automatically."
                )
                send_message(msg)
            except Exception as tlg_err:
                # Don't fail the upload on Telegram error
                pass

            self._send_json(200, {
                "success": True,
                "path": final_path,
                "filename": final_name,
                "size": len(content),
            })
        except Exception as e:
            self._send_json(500, {"success": False, "message": f"Upload handler error: {e}"})

    def _send_json(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

def run_server(port=8889):
    init_db()
    server = HTTPServer(('0.0.0.0', port), EmailHandler)
    print(f"Email API running on port {port}")
    print(f"POST /api/subscribe to capture emails")
    print(f"GET /api/stats for subscriber count")
    server.serve_forever()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8889
    run_server(port)
