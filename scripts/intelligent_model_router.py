#!/usr/bin/env python3
"""
Intelligent Model Router (IMR) v1.0
NVIDIA-NIM + Multi-Provider Load Distribution System

Problem: 16 agents hitting same NVIDIA NIM free tier = rate limit exhaustion
Solution: Intelligent task-classified routing with quota tracking

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │  Agent Issues (16 agents × multiple tasks/day)          │
  └──────────────────┬──────────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────────┐
  │  TASK CLASSIFIER                                         │
  │  • Critical (revenue decisions, architecture)           │
  │  • Standard (code, content, analysis)                  │
  │  • Routine (triage, formatting, simple responses)        │
  └──────────────────┬──────────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────────┐
  │  QUOTA-AWARE ROUTER                                      │
  │  Tracks: requests/min, tokens/day, quota remaining     │
  └──────────────────┬──────────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────────┐
  │  PROVIDER POOLS (tiered)                                 │
  │  Tier A: NVIDIA NIM FREE (reserved for critical)       │
  │  Tier B: Anthropic Claude (your paid account)          │
  │  Tier C: Gemini (your paid account)                      │
  │  Tier D: OpenAI (your paid account)                      │
  │  Tier E: Chinese FREE (bulk overflow)                    │
  │  Tier F: Local Ollama (offline fallback)                │
  └──────────────────┬──────────────────────────────────────┘
                     │
  ┌──────────────────▼──────────────────────────────────────┐
  │  FALLBACK CHAIN (automatic)                              │
  │  If Tier A exhausted → Tier B → C → D → E → F           │
  └─────────────────────────────────────────────────────────┘
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple

# ═══════════════════════════════════════════════════════════════════
# PROVIDER DEFINITIONS — Joseph's Actual Accounts
# ═══════════════════════════════════════════════════════════════════

PROVIDERS = {
    # TIER A: NVIDIA NIM FREE — Frontier quality, $0, limited quota
    "nvidia_nim_free": {
        "name": "NVIDIA NIM Free",
        "tier": "A",
        "cost_per_1m": 0.0,
        "models": {
            "ultra": "nvidia/nemotron-3-ultra-550b-a55b:free",   # 550B MoE, 1M ctx
            "super": "nvidia/nemotron-3-super-120b-a12b:free",   # 120B, 1M ctx
            "nano": "nvidia/nemotron-3-nano-30b-a3b:free",        # 30B, 256K ctx
        },
        "rate_limit_rpm": 8,          # OpenRouter free: 8 req/min across all free models
        "rate_limit_rpd": 200,         # Estimated daily free quota
        "priority": 1,                # Highest quality, use sparingly
        "strategy": "Reserve for critical tasks only. Ultra gets 40% of quota, Super 30%, Nano 30%.",
    },
    
    # TIER B: Anthropic Claude — Your PAID account (best reasoning)
    "anthropic": {
        "name": "Anthropic Claude",
        "tier": "B",
        "cost_per_1m": 3.00,          # $3/$15 per 1M (Sonnet)
        "models": {
            "opus": "~anthropic/claude-opus-latest",             # Best reasoning, expensive
            "sonnet": "~anthropic/claude-sonnet-latest",         # Good balance
            "haiku": "~anthropic/claude-haiku-latest",          # Fast, cheap
        },
        "rate_limit_rpm": 4000,       # Very high (paid tier)
        "rate_limit_rpd": 100000,     # Essentially unlimited for our use
        "priority": 2,
        "strategy": "Primary workhorse. Use Sonnet for complex code/reasoning. Opus only for make-or-break decisions.",
    },
    
    # TIER C: Google Gemini — Your PAID account (best context)
    "gemini": {
        "name": "Google Gemini",
        "tier": "C",
        "cost_per_1m": 0.50,          # $0.50 per 1M (Flash)
        "models": {
            "pro": "~google/gemini-pro-latest",                   # Best quality
            "flash": "~google/gemini-flash-latest",             # Fast, cheap
            "3.5": "google/gemini-3.5-flash",                      # Latest
        },
        "rate_limit_rpm": 1000,
        "rate_limit_rpd": 50000,
        "priority": 3,
        "strategy": "Secondary workhorse. Use for long-context tasks (1M tokens). Flash for bulk generation.",
    },
    
    # TIER D: OpenAI — Your PAID account (reliable)
    "openai": {
        "name": "OpenAI",
        "tier": "D",
        "cost_per_1m": 2.50,          # ~$2.50 per 1M (GPT-4 class)
        "models": {
            "latest": "~openai/gpt-latest",                     # Auto-updating
            "mini": "~openai/gpt-mini-latest",                   # Cheapest
        },
        "rate_limit_rpm": 500,
        "rate_limit_rpd": 20000,
        "priority": 4,
        "strategy": "Tertiary fallback. Reliable but expensive. Use only when Anthropic/Gemini unavailable.",
    },
    
    # TIER E: Chinese FREE — Overflow tier, truly free but lower quality
    "chinese_free": {
        "name": "Chinese Models (Free)",
        "tier": "E",
        "cost_per_1m": 0.0,
        "models": {
            "qwen_next": "qwen/qwen3-next-80b-a3b-instruct:free",   # Good general
            "qwen_coder": "qwen/qwen3-coder:free",                   # Code tasks
            "deepseek_flash": "deepseek/deepseek-v4-flash:free",     # Fast reasoning
        },
        "rate_limit_rpm": 8,          # OpenRouter free: shared with NVIDIA
        "rate_limit_rpd": 200,        # Same pool as NVIDIA free
        "priority": 5,
        "strategy": "Overflow only. Use when all paid tiers exhausted. Accept lower quality for $0.",
    },
    
    # TIER F: Ollama Local — Your subscription, runs on VPS
    "ollama": {
        "name": "Ollama Local",
        "tier": "F",
        "cost_per_1m": 0.0,
        "models": {
            "kimi": "ollama-cloud/kimi-k2.6",                        # Via Ollama Cloud API
            "llama": "ollama/llama3.3",                             # Local inference
        },
        "rate_limit_rpm": 9999,        # No rate limit (local/cloud sub)
        "rate_limit_rpd": 999999,
        "priority": 6,
        "strategy": "Offline fallback. Zero latency, zero cost. Use for dev/testing or when all APIs down.",
    },
}

# ═══════════════════════════════════════════════════════════════════
# TASK CLASSIFIER — Determines which tier gets the work
# ═══════════════════════════════════════════════════════════════════

TASK_PATTERNS = {
    # CRITICAL — Tier A (NVIDIA) + fallback to Anthropic Opus
    "critical": {
        "keywords": [
            "strategic decision", "revenue model", "pricing strategy", 
            "architecture review", "security audit", "fundraising", "investor",
            "make-or-break", "irreversible", "high-stakes", "CEO directive"
        ],
        "issue_types": ["strategy", "architecture", "security", "compliance"],
        "budget_pct": 5,              # 5% of total workload
        "primary_tier": "A",
        "fallback_chain": ["B", "C", "D"],
    },
    
    # COMPLEX — Tier B (Anthropic Sonnet) primary
    "complex": {
        "keywords": [
            "refactor", "implement", "debug", "code review", "API design",
            "database schema", "performance optimization", "testing strategy",
            "competitive analysis", "market research", "user journey"
        ],
        "issue_types": ["feature", "bug", "refactor", "research", "design"],
        "budget_pct": 40,             # 40% of workload
        "primary_tier": "B",
        "fallback_chain": ["C", "D", "A"],
    },
    
    # STANDARD — Tier C (Gemini) primary
    "standard": {
        "keywords": [
            "create", "generate", "write", "update", "content", "email",
            "social media", "blog post", "description", "documentation"
        ],
        "issue_types": ["content", "documentation", "marketing", "ui"],
        "budget_pct": 35,             # 35% of workload
        "primary_tier": "C",
        "fallback_chain": ["B", "D", "E"],
    },
    
    # ROUTINE — Tier D/E/F (cheapest)
    "routine": {
        "keywords": [
            "triage", "respond", "format", "lint", "simple", "quick",
            "verify", "check", "monitor", "daily", "routine"
        ],
        "issue_types": ["triage", "chore", "maintenance", "alert"],
        "budget_pct": 20,             # 20% of workload
        "primary_tier": "E",          # Start with Chinese free
        "fallback_chain": ["F", "C", "D"],  # Then Ollama, Gemini, OpenAI
    },
}

# ═══════════════════════════════════════════════════════════════════
# USAGE TRACKING DATABASE
# ═══════════════════════════════════════════════════════════════════

DB_PATH = "/root/the-garden-keeper/data/model_router.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Track provider usage
    c.execute('''
        CREATE TABLE IF NOT EXISTS provider_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            tokens_prompt INTEGER DEFAULT 0,
            tokens_completion INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1,
            error_message TEXT
        )
    ''')
    
    # Track quota state
    c.execute('''
        CREATE TABLE IF NOT EXISTS quota_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL UNIQUE,
            requests_today INTEGER DEFAULT 0,
            requests_this_hour INTEGER DEFAULT 0,
            tokens_today INTEGER DEFAULT 0,
            last_reset_hour TEXT,
            last_reset_day TEXT,
            quota_exhausted INTEGER DEFAULT 0
        )
    ''')
    
    # Initialize quota tracking for all providers
    for provider_id in PROVIDERS:
        c.execute('''
            INSERT OR IGNORE INTO quota_state (provider, last_reset_hour, last_reset_day)
            VALUES (?, ?, ?)
        ''', (provider_id, datetime.now().isoformat(), datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    print(f"✅ Router DB initialized: {DB_PATH}")

# ═══════════════════════════════════════════════════════════════════
# INTELLIGENT ROUTER CLASS
# ═══════════════════════════════════════════════════════════════════

class IntelligentModelRouter:
    """
    Routes agent tasks to optimal models based on:
    - Task complexity classification
    - Provider quota state
    - Cost optimization
    - Quality requirements
    """
    
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
    
    def classify_task(self, title: str, description: str = "", issue_type: str = "") -> str:
        """Classify task as critical/complex/standard/routine"""
        text = f"{title} {description} {issue_type}".lower()
        
        scores = {}
        for task_class, config in TASK_PATTERNS.items():
            score = 0
            # Keyword matching
            for kw in config["keywords"]:
                if kw in text:
                    score += 1
            # Issue type matching
            if issue_type.lower() in [t.lower() for t in config["issue_types"]]:
                score += 3
            scores[task_class] = score
        
        # Return highest scoring class, default to standard
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "standard"
    
    def check_quota(self, provider_id: str) -> Dict:
        """Check remaining quota for a provider"""
        provider = PROVIDERS[provider_id]
        
        c = self.db.cursor()
        c.execute('''
            SELECT * FROM quota_state WHERE provider = ?
        ''', (provider_id,))
        row = c.fetchone()
        
        if not row:
            return {"available": False, "reason": "No quota tracking"}
        
        now = datetime.now()
        last_reset_hour = datetime.fromisoformat(row["last_reset_hour"])
        last_reset_day = datetime.fromisoformat(row["last_reset_day"])
        
        # Reset hourly counters if hour changed
        if now.hour != last_reset_hour.hour:
            c.execute('''
                UPDATE quota_state 
                SET requests_this_hour = 0, last_reset_hour = ?
                WHERE provider = ?
            ''', (now.isoformat(), provider_id))
            self.db.commit()
            row = dict(row)
            row["requests_this_hour"] = 0
        
        # Reset daily counters if day changed
        if now.date() != last_reset_day.date():
            c.execute('''
                UPDATE quota_state 
                SET requests_today = 0, tokens_today = 0, quota_exhausted = 0, last_reset_day = ?
                WHERE provider = ?
            ''', (now.isoformat(), provider_id))
            self.db.commit()
            row = dict(row)
            row["requests_today"] = 0
            row["tokens_today"] = 0
            row["quota_exhausted"] = 0
        
        rpm = provider["rate_limit_rpm"]
        rpd = provider["rate_limit_rpd"]
        
        rpm_remaining = max(0, rpm - row["requests_this_hour"])
        rpd_remaining = max(0, rpd - row["requests_today"])
        
        # For paid providers, assume ~90% available (conservative)
        if provider["cost_per_1m"] > 0:
            rpm_remaining = int(rpm * 0.9)
            rpd_remaining = int(rpd * 0.9)
        
        available = rpm_remaining > 0 and rpd_remaining > 0 and row["quota_exhausted"] == 0
        
        return {
            "available": available,
            "provider": provider_id,
            "rpm_limit": rpm,
            "rpm_used": row["requests_this_hour"],
            "rpm_remaining": rpm_remaining,
            "rpd_limit": rpd,
            "rpd_used": row["requests_today"],
            "rpd_remaining": rpd_remaining,
            "cost_per_1m": provider["cost_per_1m"],
        }
    
    def select_model(self, agent_name: str, task_title: str, task_desc: str = "", issue_type: str = "") -> Dict:
        """
        Main routing logic. Returns optimal model with fallback chain.
        """
        # Step 1: Classify task
        task_class = self.classify_task(task_title, task_desc, issue_type)
        config = TASK_PATTERNS[task_class]
        
        # Step 2: Try primary tier
        primary_tier = config["primary_tier"]
        provider_id = self._tier_to_provider(primary_tier)
        quota = self.check_quota(provider_id)
        
        if quota["available"]:
            return self._build_result(provider_id, task_class, agent_name, quota, is_primary=True)
        
        # Step 3: Walk fallback chain
        for fallback_tier in config["fallback_chain"]:
            provider_id = self._tier_to_provider(fallback_tier)
            quota = self.check_quota(provider_id)
            if quota["available"]:
                return self._build_result(provider_id, task_class, agent_name, quota, is_primary=False, fallback_from=config["primary_tier"])
        
        # Step 4: Last resort — Ollama local (always available)
        return self._build_result("ollama", task_class, agent_name, {"available": True, "rpm_remaining": 9999}, is_primary=False, fallback_from="ALL")
    
    def _tier_to_provider(self, tier: str) -> str:
        """Map tier letter to provider ID"""
        tier_map = {
            "A": "nvidia_nim_free",
            "B": "anthropic", 
            "C": "gemini",
            "D": "openai",
            "E": "chinese_free",
            "F": "ollama",
        }
        return tier_map.get(tier, "ollama")
    
    def _build_result(self, provider_id: str, task_class: str, agent_name: str, quota: Dict, is_primary: bool, fallback_from: str = None) -> Dict:
        """Build the routing result"""
        provider = PROVIDERS[provider_id]
        
        # Select model variant based on task class
        if task_class == "critical":
            model_key = "ultra" if "ultra" in provider["models"] else list(provider["models"].keys())[0]
        elif task_class == "complex":
            model_key = "sonnet" if "sonnet" in provider["models"] else ("super" if "super" in provider["models"] else list(provider["models"].keys())[0])
        elif task_class == "standard":
            model_key = "flash" if "flash" in provider["models"] else ("nano" if "nano" in provider["models"] else list(provider["models"].keys())[0])
        else:
            model_key = list(provider["models"].keys())[0]
        
        model_id = provider["models"][model_key]
        
        return {
            "agent": agent_name,
            "task_class": task_class,
            "provider": provider_id,
            "provider_name": provider["name"],
            "model_key": model_key,
            "model_id": model_id,
            "cost_per_1m": provider["cost_per_1m"],
            "is_primary": is_primary,
            "fallback_from": fallback_from,
            "quota_remaining": {
                "rpm": quota.get("rpm_remaining", 0),
                "rpd": quota.get("rpd_remaining", 0),
            },
            "reasoning": f"{'Primary' if is_primary else 'Fallback'}: {task_class} task → {provider['name']} ({model_key})",
        }
    
    def log_usage(self, provider_id: str, model_id: str, agent_name: str, task_type: str, tokens_in: int = 0, tokens_out: int = 0, cost: float = 0.0, success: bool = True, error: str = None):
        """Log usage to database"""
        c = self.db.cursor()
        c.execute('''
            INSERT INTO provider_usage (provider, model, agent_name, task_type, tokens_prompt, tokens_completion, cost_usd, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (provider_id, model_id, agent_name, task_type, tokens_in, tokens_out, cost, 1 if success else 0, error))
        
        # Update quota state
        c.execute('''
            UPDATE quota_state 
            SET requests_today = requests_today + 1,
                requests_this_hour = requests_this_hour + 1,
                tokens_today = tokens_today + ?
            WHERE provider = ?
        ''', (tokens_in + tokens_out, provider_id))
        
        self.db.commit()
    
    def get_usage_report(self, hours: int = 24) -> Dict:
        """Generate usage report"""
        c = self.db.cursor()
        
        # Total usage by provider
        c.execute('''
            SELECT provider, COUNT(*) as calls, SUM(tokens_prompt + tokens_completion) as tokens,
                   SUM(cost_usd) as cost, AVG(success) as success_rate
            FROM provider_usage
            WHERE timestamp > datetime('now', '-{} hours')
            GROUP BY provider
        '''.format(hours))
        
        by_provider = [dict(row) for row in c.fetchall()]
        
        # Total stats
        c.execute('''
            SELECT COUNT(*) as total_calls, SUM(cost_usd) as total_cost,
                   SUM(tokens_prompt + tokens_completion) as total_tokens
            FROM provider_usage
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours))
        
        totals = dict(c.fetchone())
        
        return {
            "period_hours": hours,
            "by_provider": by_provider,
            "totals": totals,
        }
    
    def close(self):
        self.db.close()

# ═══════════════════════════════════════════════════════════════════
# AGENT-SPECIFIC ROUTING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

AGENT_ROUTING = {
    # Strategic agents — get NVIDIA Ultra for critical, Anthropic for routine
    "CEO":               {"critical_pct": 80, "standard_pct": 20, "routine_fallback": "anthropic"},
    "Insight Engine":    {"critical_pct": 60, "standard_pct": 40, "routine_fallback": "anthropic"},
    "Research Analyst":  {"critical_pct": 40, "standard_pct": 60, "routine_fallback": "gemini"},
    "Revenue Specialist":{"critical_pct": 50, "standard_pct": 50, "routine_fallback": "anthropic"},
    "Growth Operator":   {"critical_pct": 30, "standard_pct": 70, "routine_fallback": "gemini"},
    "Pathfinder":        {"critical_pct": 70, "standard_pct": 30, "routine_fallback": "anthropic"},
    
    # Code agents — Anthropic Sonnet primary, NVIDIA Super for reviews
    "Code Specialist":   {"complex_pct": 80, "routine_pct": 20, "routine_fallback": "gemini"},
    "QA Reviewer":       {"complex_pct": 90, "routine_pct": 10, "routine_fallback": "chinese_free"},
    "Vision Coder":      {"complex_pct": 50, "standard_pct": 50, "routine_fallback": "gemini"},
    "DevOps Engineer":   {"complex_pct": 60, "standard_pct": 40, "routine_fallback": "gemini"},
    
    # Content agents — Gemini primary, Chinese free overflow
    "Content Creator":   {"standard_pct": 70, "routine_pct": 30, "routine_fallback": "chinese_free"},
    "Social Media Manager":{"standard_pct": 80, "routine_pct": 20, "routine_fallback": "chinese_free"},
    "Shopify AI Toolkit Specialist": {"standard_pct": 60, "routine_pct": 40, "routine_fallback": "gemini"},
    
    # Support agents — Cheapest possible, quality less critical
    "Customer Success Agent": {"routine_pct": 90, "standard_pct": 10, "routine_fallback": "ollama"},
    "Quick Responder":   {"routine_pct": 95, "standard_pct": 5, "routine_fallback": "ollama"},
    "Operator PM":       {"routine_pct": 70, "standard_pct": 30, "routine_fallback": "gemini"},
}

# ═══════════════════════════════════════════════════════════════════
# MAIN — Demonstrate the system
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    
    router = IntelligentModelRouter()
    
    # Simulate routing for various tasks
    test_tasks = [
        ("CEO", "Strategic pivot: Enter B2B plant software market", "strategy", "critical"),
        ("Code Specialist", "Refactor Stripe integration for multi-currency", "feature", "complex"),
        ("Content Creator", "Generate 100 plant care tips for email sequence", "content", "standard"),
        ("Quick Responder", "Triage: Customer asking about shipping times", "triage", "routine"),
        ("Research Analyst", "Deep competitor analysis: Bloomscape vs. our offering", "research", "critical"),
        ("Social Media Manager", "Create 7 TikTok scripts for launch week", "marketing", "standard"),
        ("QA Reviewer", "Review PR #42: Authentication middleware", "bug", "complex"),
        ("Customer Success Agent", "Respond to refund request", "support", "routine"),
    ]
    
    print("\n" + "="*80)
    print("INTELLIGENT MODEL ROUTER — DEMONSTRATION")
    print("="*80 + "\n")
    
    for agent, title, issue_type, expected in test_tasks:
        result = router.select_model(agent, title, "", issue_type)
        marker = "✅" if result["is_primary"] else "⚠️ FALLBACK"
        print(f"{marker} {agent:25s} | {result['task_class']:10s} | {result['provider_name']:20s} | {result['model_key']}")
        print(f"    → {result['reasoning']}")
        if result["fallback_from"]:
            print(f"    → Fallback from: {result['fallback_from']} (quota exhausted)")
        print()
    
    # Show quota state
    print("\n" + "="*80)
    print("CURRENT QUOTA STATE")
    print("="*80)
    
    for provider_id in ["nvidia_nim_free", "anthropic", "gemini", "chinese_free", "ollama"]:
        quota = router.check_quota(provider_id)
        status = "✅ AVAILABLE" if quota["available"] else "❌ EXHAUSTED"
        print(f"\n{status} {PROVIDERS[provider_id]['name']}")
        print(f"  RPM: {quota['rpm_used']}/{quota['rpm_limit']} remaining")
        print(f"  RPD: {quota['rpd_used']}/{quota['rpd_limit']} remaining")
        print(f"  Cost: ${quota['cost_per_1m']:.2f}/1M tokens")
    
    router.close()
    
    print("\n" + "="*80)
    print("ROUTER CONFIGURATION SAVED")
    print("="*80)
    print(f"\nDatabase: {DB_PATH}")
    print("\nTo use in production:")
    print("  1. Wrap agent execution with router.select_model() before each call")
    print("  2. Call router.log_usage() after each completion")
    print("  3. Monitor quota via router.get_usage_report()")
    print("  4. Set up cron to reset quotas daily")
