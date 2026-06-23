#!/usr/bin/env python3
"""
Garden Keeper — Reddit DNS Bypass

The VPS resolver (127.0.0.53 via systemd-resolved) returns
poisoned A records for reddit.com (Kominfo Trust+ lame-lamanlabuh.aduankonten.id).
This module monkey-patches urllib3's connection pool to resolve reddit.com
through Cloudflare DoH (1.1.1.1) and connect via direct IP, while keeping the
Host header / SNI set to the correct reddit domain so TLS cert validation
works.

Usage:
    import reddit_dns_bypass
    reddit_dns_bypass.install()

After install(), all `requests`/`urllib3` calls to reddit domains
will work via direct-IP routing.
"""
import socket
import urllib3
import urllib3.util.connection
import urllib3.util.url
from urllib.parse import urlparse

# Real Reddit IPs (Fastly) — resolved via Cloudflare DoH
_REDDIT_IPS = {
    "reddit.com":       ["151.101.1.140", "151.101.65.140", "151.101.129.140", "151.101.193.140"],
    "www.reddit.com":   ["151.101.1.140", "151.101.65.140", "151.101.129.140", "151.101.193.140"],
    "oauth.reddit.com": ["151.101.1.140", "151.101.65.140", "151.101.129.140", "151.101.193.140"],
    "old.reddit.com":   ["151.101.1.140", "151.101.65.140", "151.101.129.140", "151.101.193.140"],
    "api.reddit.com":   ["151.101.1.140", "151.101.65.140", "151.101.129.140", "151.101.193.140"],
}

def _reddit_allowed_addr_family():
    # Keep current default (we want IPv4 here to avoid IPv6 happy-eyeballs falling back to poison)
    return socket.AF_INET

def _patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host in _REDDIT_IPS:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in _REDDIT_IPS[host]]
    # Fall back to real resolver for everything else
    return socket._original_getaddrinfo(host, port, family, type, proto, flags)

def install():
    """Monkey-patch DNS resolution to bypass poisoned reddit.com records."""
    if hasattr(socket, "_original_getaddrinfo"):
        # Already installed
        return
    socket._original_getaddrinfo = socket.getaddrinfo
    socket.getaddrinfo = _patched_getaddrinfo
    # Also patch urllib3 in case it cached its own resolver
    urllib3.util.connection.allowed_gai_family = _reddit_allowed_addr_family

if __name__ == "__main__":
    install()
    # Sanity check
    import requests
    r = requests.get("https://oauth.reddit.com/api/v1/me", timeout=10,
                     headers={"User-Agent": "Mozilla/5.0 dns-bypass-test"})
    print(f"Status: {r.status_code}")
    print(f"Body[:200]: {r.text[:200]}")
