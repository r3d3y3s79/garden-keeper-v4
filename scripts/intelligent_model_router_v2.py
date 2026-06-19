#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
INTELLIGENT MODEL ROUTER v2.0 — JOSEPH'S EXACT PRIORITY HIERARCHY
═══════════════════════════════════════════════════════════════════════════════

Priority Order (as explicitly requested):
  1. NVIDIA NIM FREE        — Frontier models, $0, limited quota
  2. OLLAMA (Subscription)  — Your paid account, unlimited, zero latency
  3. CHINESE MODELS (Free)  — Top Chinese models, $0, decent quality
  4. ANTHROPIC (Paid)       — Claude, your paid account, best reasoning
  5. GEMINI (Paid)          — Google, your paid account, best context
  6. OPENAI (Paid)          — OpenAI, your paid account, reliable fallback

Philosophy:
  • Burn FREE tiers first (NVIDIA, Chinese)
  • Burn your subscription next (Ollama — already paid, use it)
  • Burn paid API credits LAST (Anthropic, Gemini, OpenAI — conserve these)
  • Reserve capacity, never exhaust a single provider
  • Automatic failover with graceful degradation

═══════════════════════════════════════════════════════════════════════════════
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# PROVIDER DEFINITIONS — JOSEPH'S EXACT PRIORITY HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════════

PROVIDERS = {
    # ═══════════════════════════════════════════════════════════════════════
    # TIER A: NVIDIA NIM FREE — Frontier quality, $0, LIMITED QUOTA (Reserve!)
    # ═══════════════════════════════════════════════════════════════════════
    "nvidia_nim_free": {
        "name": "NVIDIA NIM Free",
        "tier": "A",
        "priority_rank": 1,
        "cost_per_1m": 0.0,
        "models": {
            "ultra": "nvidia/nemotron-3-ultra-550b-a55b:free",    # 550B MoE, 1M ctx, frontier
            "super": "nvidia/nemotron-3-super-120b-a12b:free",    # 120B, 1M ctx, excellent
            "nano": "nvidia/nemotron-3-nano-30b-a3b:free",         # 30B, 256K ctx, fast
        },
        "rate_limit_rpm": 8,           # OpenRouter free: 8 req/min ALL free models
        "rate_limit_rpd": 200,          # Estimated daily free quota
        "provider_id": "openrouter",
        "strategy": "RESERVE for critical tasks only. Ultra gets 40%, Super 30%, Nano 30%. NEVER use for routine.",
        "strengths": ["reasoning", "coding", "1M_context", "frontier_quality"],
        "weaknesses": ["rate_limited", "shared_pool", "can_exhaust"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIER B: OLLAMA — Your subscription, UNLIMITED, already paid for
    # ═══════════════════════════════════════════════════════════════════════
    "ollama": {
        "name": "Ollama (Your Subscription)",
        "tier": "B",
        "priority_rank": 2,
        "cost_per_1m": 0.0,             # Already paid via subscription
        "models": {
            "kimi_k2_6": "ollama-cloud/kimi-k2.6",                 # Via Ollama Cloud API
            "kimi_k2_5": "ollama-cloud/kimi-k2.5",                 # Fallback
            "llama3_3": "ollama/llama3.3",                         # Local inference option
            "nemotron_70b": "ollama/nemotron-70b",                # If available
        },
        "rate_limit_rpm": 9999,          # Subscription = essentially unlimited
        "rate_limit_rpd": 999999,
        "provider_id": "ollama",          # Direct Ollama Cloud API
        "strategy": "PRIMARY workhorse. You've already paid for this subscription — use it! Zero marginal cost, zero latency. Use for complex AND standard tasks.",
        "strengths": ["unlimited", "zero_marginal_cost", "fast", "subscription_paid"],
        "weaknesses": ["model_availability_varies", "requires_ollama_cloud_api_key"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIER C: CHINESE MODELS (Free) — Top tier, $0, shared quota with NVIDIA
    # ═══════════════════════════════════════════════════════════════════════
    "chinese_free": {
        "name": "Chinese Models (Free)",
        "tier": "C",
        "priority_rank": 3,
        "cost_per_1m": 0.0,
        "models": {
            "qwen3_next": "qwen/qwen3-next-80b-a3b-instruct:free",     # 80B, excellent general
            "qwen3_coder": "qwen/qwen3-coder:free",                     # Coding specialist
            "deepseek_v4_flash": "deepseek/deepseek-v4-flash:free",     # Fast reasoning
            "qwen3_5_flash": "qwen/qwen3.5-flash-02-23:free",           # Latest flash
        },
        "rate_limit_rpm": 8,           # SHARED pool with NVIDIA free
        "rate_limit_rpd": 200,          # Same shared quota
        "provider_id": "openrouter",
        "strategy": "SECONDARY workhorse. Use for standard tasks. NOTE: Shares quota with NVIDIA — if NVIDIA used heavily, Chinese also throttled. Track combined usage.",
        "strengths": ["free", "good_quality", "coding_specialists", "large_context"],
        "weaknesses": ["shares_pool_with_nvidia", "rate_limited", "variable_quality"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIER D: ANTHROPIC (Paid) — Your Claude account, CONSERVE THIS
    # ═══════════════════════════════════════════════════════════════════════
    "anthropic": {
        "name": "Anthropic Claude (Your Paid Account)",
        "tier": "D",
        "priority_rank": 4,
        "cost_per_1m": 3.00,            # Sonnet: $3/$15 per 1M
        "models": {
            "opus": "~anthropic/claude-opus-latest",                  # Best reasoning, EXPENSIVE
            "sonnet": "~anthropic/claude-sonnet-latest",              # Best balance, primary
            "haiku": "~anthropic/claude-haiku-latest",                # Fast, cheap
        },
        "rate_limit_rpm": 4000,          # Very high (paid tier)
        "rate_limit_rpd": 100000,
        "provider_id": "openrouter",
        "strategy": "FALLBACK — use only when NVIDIA+Ollama+Chinese exhausted or for tasks requiring Claude's unique reasoning. CONSERVE credits. Sonnet for complex, Haiku for quick tasks.",
        "strengths": ["best_reasoning", "excellent_coding", "huge_context", "reliable"],
        "weaknesses": ["expensive", "costs_real_money"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIER E: GEMINI (Paid) — Your Google account, CONSERVE THIS
    # ═══════════════════════════════════════════════════════════════════════
    "gemini": {
        "name": "Google Gemini (Your Paid Account)",
        "tier": "E",
        "priority_rank": 5,
        "cost_per_1m": 0.50,            # Flash: $0.50 per 1M
        "models": {
            "pro": "~google/gemini-pro-latest",                       # Best quality
            "flash": "~google/gemini-flash-latest",                   # Fast, cheap
            "flash_3_5": "google/gemini-3.5-flash",                    # Latest
        },
        "rate_limit_rpm": 1000,
        "rate_limit_rpd": 50000,
        "provider_id": "openrouter",
        "strategy": "FALLBACK — use when Anthropic credits low or for 1M context tasks. CONSERVE. Flash for bulk, Pro rarely.",
        "strengths": ["1M_context", "cheap", "multimodal", "reliable"],
        "weaknesses": ["costs_money", "not_as_good_as_claude_for_coding"],
    },
    
    # ═══════════════════════════════════════════════════════════════════════
    # TIER F: OPENAI (Paid) — Your OpenAI account, LAST RESORT
    # ═══════════════════════════════════════════════════════════════════════
    "openai": {
        "name": "OpenAI (Your Paid Account)",
        "tier": "F",
        "priority_rank": 6,
        "cost_per_1m": 2.50,            # GPT-4 class
        "models": {
            "latest": "~openai/gpt-latest",                          # Auto-updating
            "mini": "~openai/gpt-mini-latest",                        # Cheapest
        },
        "rate_limit_rpm": 500,
        "rate_limit_rpd": 20000,
        "provider_id": "openrouter",
        "strategy": "LAST RESORT. Most expensive, use only when all others unavailable. Mini for simple tasks if you must use OpenAI.",
        "strengths": ["reliable", "broad_capabilities"],
        "weaknesses": ["expensive", "not_better_than_claude", "costs_real_money"],
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# TASK CLASSIFICATION — Determines routing tier
# ═══════════════════════════════════════════════════════════════════════════════

TASK_PATTERNS = {
    # CRITICAL: Reserve NVIDIA Ultra (Tier A), fallback to Ollama (Tier B)
    "critical": {
        "keywords": [
            "strategic decision", "revenue model", "pricing strategy", "pivot",
            "architecture review", "security audit", "fundraising", "investor",
            "make-or-break", "irreversible", "high-stakes", "CEO directive",
            "company direction", "competitive moat", "defensibility"
        ],
        "issue_types": ["strategy", "architecture", "security", "compliance", "pivot"],
        "budget_pct": 5,
        "primary_tier": "A",              # NVIDIA NIM FREE
        "fallback_chain": ["B", "D"],      # Ollama → Anthropic (skip Chinese for critical)
        "rationale": "Critical tasks get frontier models. NVIDIA first (free), Ollama second (your sub), Anthropic last (conserve).",
    },
    
    # COMPLEX: Ollama primary (Tier B), Chinese fallback (Tier C), Anthropic reserve (Tier D)
    "complex": {
        "keywords": [
            "refactor", "implement", "debug", "code review", "API design",
            "database schema", "performance optimization", "testing strategy",
            "competitive analysis", "market research", "user journey",
            "build", "create system", "integrate", "deploy pipeline"
        ],
        "issue_types": ["feature", "bug", "refactor", "research", "design", "integration"],
        "budget_pct": 40,
        "primary_tier": "B",              # OLLAMA (your subscription!)
        "fallback_chain": ["C", "D", "A"], # Chinese → Anthropic → NVIDIA
        "rationale": "Complex tasks go to Ollama (unlimited, already paid). Chinese free as overflow. Anthropic only if Ollama+Chinese down.",
    },
    
    # STANDARD: Chinese primary (Tier C), Ollama fallback (Tier B), Gemini reserve (Tier E)
    "standard": {
        "keywords": [
            "create", "generate", "write", "update", "content", "email",
            "social media", "blog post", "description", "documentation",
            "configure", "setup", "template", "draft"
        ],
        "issue_types": ["content", "documentation", "marketing", "ui", "config"],
        "budget_pct": 35,
        "primary_tier": "C",              # CHINESE FREE
        "fallback_chain": ["B", "E", "D"], # Ollama → Gemini → Anthropic
        "rationale": "Standard tasks go to Chinese free (good enough, $0). Ollama fallback (unlimited). Paid APIs only if free exhausted.",
    },
    
    # ROUTINE: Ollama primary (Tier B) — fastest, unlimited
    # OR Chinese (Tier C) if Ollama busy
    "routine": {
        "keywords": [
            "triage", "respond", "format", "lint", "simple", "quick",
            "verify", "check", "monitor", "daily", "routine",
            "acknowledge", "confirm", "status update"
        ],
        "issue_types": ["triage", "chore", "maintenance", "alert", "status"],
        "budget_pct": 20,
        "primary_tier": "B",              # OLLAMA (fastest, unlimited)
        "fallback_chain": ["C", "F"],      # Chinese → Local Ollama
        "rationale": "Routine tasks to Ollama (zero latency, unlimited). Chinese if Ollama model unavailable. Never burn paid credits on routine.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT-SPECIFIC ROUTING — Fine-tuned per agent role
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_ROUTING = {
    # ═══════════════════════════════════════════════════════════════════
    # STRATEGIC AGENTS — NVIDIA for critical, Ollama for everything else
    # ═══════════════════════════════════════════════════════════════════
    "CEO": {
        "critical_pct": 80,      # 80% of CEO tasks → NVIDIA Ultra
        "complex_pct": 15,       # 15% → Ollama
        "standard_pct": 5,       # 5% → Chinese
        "reserve_nvidia": True,  # Always reserve NVIDIA capacity for CEO
        "rationale": "CEO makes strategic decisions. NVIDIA for pivots/revenue. Ollama for everything else.",
    },
    "Insight Engine": {
        "critical_pct": 60,      # Deep analysis → NVIDIA
        "complex_pct": 30,       # Research synthesis → Ollama
        "standard_pct": 10,      # Reports → Chinese
        "reserve_nvidia": True,
        "rationale": "Insight Engine does deep thinking. NVIDIA for breakthrough analysis. Ollama for ongoing intel.",
    },
    "Research Analyst": {
        "critical_pct": 40,      # Competitive intel → NVIDIA
        "complex_pct": 50,       # Market research → Ollama
        "standard_pct": 10,      # Data summaries → Chinese
        "reserve_nvidia": False,
        "rationale": "Research is ongoing. Ollama handles bulk research. NVIDIA for game-changing discoveries.",
    },
    "Revenue Specialist": {
        "critical_pct": 50,      # Pricing strategy → NVIDIA
        "complex_pct": 40,       # Monetization experiments → Ollama
        "standard_pct": 10,      # Reports → Chinese
        "reserve_nvidia": True,
        "rationale": "Revenue decisions are critical. NVIDIA for pricing. Ollama for funnel optimization.",
    },
    "Growth Operator": {
        "critical_pct": 30,      # Growth strategy → NVIDIA
        "complex_pct": 50,       # Experiments → Ollama
        "standard_pct": 20,      # Content → Chinese
        "reserve_nvidia": False,
        "rationale": "Growth is iterative. Ollama for experiments. NVIDIA for strategic shifts.",
    },
    "Pathfinder": {
        "critical_pct": 70,      # Creative breakthroughs → NVIDIA
        "complex_pct": 25,       # Problem solving → Ollama
        "standard_pct": 5,       # Rarely standard
        "reserve_nvidia": True,
        "rationale": "Pathfinder finds unconventional solutions. NVIDIA for creative leaps. Ollama for iteration.",
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # CODE AGENTS — Ollama primary, Chinese secondary, Anthropic reserve
    # ═══════════════════════════════════════════════════════════════════
    "Code Specialist": {
        "complex_pct": 80,       # Architecture → Ollama
        "standard_pct": 15,      # Boilerplate → Chinese
        "critical_pct": 5,       # Security → NVIDIA
        "reserve_nvidia": False,
        "rationale": "Code Specialist builds systems. Ollama (unlimited) for bulk coding. Chinese for quick scripts.",
    },
    "QA Reviewer": {
        "complex_pct": 70,       # Code review → Ollama
        "standard_pct": 25,      # Linting → Chinese
        "critical_pct": 5,       # Security audit → NVIDIA
        "reserve_nvidia": False,
        "rationale": "QA is high-volume. Ollama for reviews. Chinese for automated checks. NVIDIA for security gates.",
    },
    "Vision Coder": {
        "complex_pct": 50,       # UI architecture → Ollama
        "standard_pct": 45,      # HTML/CSS → Chinese
        "critical_pct": 5,       # Accessibility audit → NVIDIA
        "reserve_nvidia": False,
        "rationale": "Vision Coder is high-volume UI work. Ollama/Chinese handle 95%. NVIDIA for critical UX.",
    },
    "DevOps Engineer": {
        "complex_pct": 60,       # Infrastructure → Ollama
        "standard_pct": 35,      # Config → Chinese
        "critical_pct": 5,       # Security → NVIDIA
        "reserve_nvidia": False,
        "rationale": "DevOps is config-heavy. Ollama for Terraform/K8s. Chinese for simple configs.",
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # CONTENT AGENTS — Chinese primary, Ollama fallback
    # ═══════════════════════════════════════════════════════════════════
    "Content Creator": {
        "standard_pct": 60,      # Content → Chinese
        "complex_pct": 30,       # Strategy → Ollama
        "critical_pct": 10,      # Brand voice → NVIDIA
        "reserve_nvidia": False,
        "rationale": "Content Creator is high-volume. Chinese (free) for bulk. Ollama for tone refinement.",
    },
    "Social Media Manager": {
        "standard_pct": 80,      # Posts → Chinese
        "complex_pct": 15,       # Campaign strategy → Ollama
        "critical_pct": 5,       # Crisis response → NVIDIA
        "reserve_nvidia": False,
        "rationale": "Social media is volume game. Chinese for daily posts. Ollama for viral strategy.",
    },
    "Shopify AI Toolkit Specialist": {
        "standard_pct": 60,      # Liquid code → Chinese
        "complex_pct": 35,       # Store architecture → Ollama
        "critical_pct": 5,       # Checkout security → NVIDIA
        "reserve_nvidia": False,
        "rationale": "Shopify work is routine. Chinese for Liquid templates. Ollama for custom features.",
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # SUPPORT AGENTS — Ollama primary (fastest), Chinese fallback
    # ═══════════════════════════════════════════════════════════════════
    "Customer Success Agent": {
        "routine_pct": 80,       # Support tickets → Ollama
        "standard_pct": 15,      # Escalation docs → Chinese
        "complex_pct": 5,        # Retention strategy → Ollama
        "reserve_nvidia": False,
        "rationale": "Support needs speed. Ollama (zero latency) for instant responses. Chinese for documentation.",
    },
    "Quick Responder": {
        "routine_pct": 95,       # Triage → Ollama (always)
        "standard_pct": 5,       # Rarely standard
        "reserve_nvidia": False,
        "rationale": "Quick Responder needs 2min SLA. Ollama local = instant. Never wait for API.",
    },
    "Operator PM": {
        "routine_pct": 70,       # Coordination → Ollama
        "standard_pct": 25,      # Backlog → Chinese
        "complex_pct": 5,        # Strategy → Ollama
        "reserve_nvidia": False,
        "rationale": "PM work is coordination. Ollama for daily standups. Chinese for documentation.",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# QUOTA BUDGET ALLOCATION — How we distribute the scarce resources
# ═══════════════════════════════════════════════════════════════════════════════

QUOTA_BUDGETS = {
    "nvidia_nim_free": {
        "daily_requests": 50,         # Conservative out of ~200 estimated
        "hourly_requests": 6,          # Out of 8 RPM
        "ultra_allocation": 20,       # 40% for critical
        "super_allocation": 15,        # 30% for complex
        "nano_allocation": 15,         # 30% for fast critical
        "emergency_reserve": 5,        # Always keep 5 in reserve
        "alert_threshold": 10,         # Alert when < 10 remaining
    },
    "chinese_free": {
        "daily_requests": 100,        # Shared pool, but use Chinese AFTER NVIDIA
        "hourly_requests": 6,          # Same 8 RPM pool
        "qwen_allocation": 50,         # 50% Qwen3
        "deepseek_allocation": 30,       # 30% DeepSeek
        "qwen_coder_allocation": 20,     # 20% Qwen Coder
        "alert_threshold": 20,         # Alert when < 20 remaining
    },
    "ollama": {
        "daily_requests": 999999,      # UNLIMITED (subscription)
        "hourly_requests": 999999,
        "alert_threshold": 0,         # Never alerts
        "note": "Subscription already paid — use liberally",
    },
    "anthropic": {
        "monthly_budget_usd": 25.00,   # Soft cap
        "daily_budget_usd": 1.00,      # ~$30/month
        "alert_threshold_usd": 20.00,  # Alert when month > $20
        "strategy": "Only use when NVIDIA+Ollama+Chinese exhausted",
    },
    "gemini": {
        "monthly_budget_usd": 15.00,
        "daily_budget_usd": 0.50,
        "alert_threshold_usd": 12.00,
        "strategy": "Fallback for long-context tasks",
    },
    "openai": {
        "monthly_budget_usd": 10.00,
        "daily_budget_usd": 0.30,
        "alert_threshold_usd": 8.00,
        "strategy": "Last resort only",
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE SETUP
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = "/root/the-garden-keeper/data/model_router_v2.db"

def init_db():
    """Initialize the router database with quota tracking"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Provider usage log
    c.execute('''
        CREATE TABLE IF NOT EXISTS provider_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            task_type TEXT NOT NULL,
            task_class TEXT NOT NULL,
            tokens_prompt INTEGER DEFAULT 0,
            tokens_completion INTEGER DEFAULT 0,
            cost_usd REAL DEFAULT 0.0,
            was_fallback INTEGER DEFAULT 0,
            fallback_from TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            success INTEGER DEFAULT 1,
            error_message TEXT,
            latency_ms INTEGER
        )
    ''')
    
    # Quota state (resets hourly/daily)
    c.execute('''
        CREATE TABLE IF NOT EXISTS quota_state (
            provider TEXT PRIMARY KEY,
            requests_today INTEGER DEFAULT 0,
            requests_this_hour INTEGER DEFAULT 0,
            tokens_today INTEGER DEFAULT 0,
            cost_today REAL DEFAULT 0.0,
            cost_this_month REAL DEFAULT 0.0,
            last_reset_hour TEXT,
            last_reset_day TEXT,
            last_reset_month TEXT,
            quota_exhausted INTEGER DEFAULT 0
        )
    ''')
    
    # Agent routing history
    c.execute('''
        CREATE TABLE IF NOT EXISTS agent_routing_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            issue_title TEXT,
            task_class TEXT,
            selected_provider TEXT,
            selected_model TEXT,
            was_fallback INTEGER,
            fallback_from TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Initialize quota tracking
    now = datetime.now().isoformat()
    for provider_id in PROVIDERS:
        c.execute('''
            INSERT OR IGNORE INTO quota_state 
            (provider, last_reset_hour, last_reset_day, last_reset_month)
            VALUES (?, ?, ?, ?)
        ''', (provider_id, now, now, now))
    
    conn.commit()
    conn.close()
    print(f"✅ Router v2 DB initialized: {DB_PATH}")

# ═══════════════════════════════════════════════════════════════════════════════
# INTELLIGENT ROUTER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class IntelligentModelRouterV2:
    """
    Routes agent tasks based on Joseph's exact priority hierarchy:
    NVIDIA → Ollama → Chinese → Anthropic → Gemini → OpenAI
    """
    
    def __init__(self):
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
    
    # ─────────────────────────────────────────────────────────────────────
    # TASK CLASSIFICATION
    # ─────────────────────────────────────────────────────────────────────
    
    def classify_task(self, title: str, description: str = "", issue_type: str = "") -> str:
        """Classify task as critical/complex/standard/routine"""
        text = f"{title} {description} {issue_type}".lower()
        
        scores = {}
        for task_class, config in TASK_PATTERNS.items():
            score = 0
            for kw in config["keywords"]:
                if kw in text:
                    score += 2
            if issue_type.lower() in [t.lower() for t in config["issue_types"]]:
                score += 5
            scores[task_class] = score
        
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "standard"
    
    # ─────────────────────────────────────────────────────────────────────
    # QUOTA MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────
    
    def _reset_quotas_if_needed(self):
        """Reset hourly/daily/monthly quotas when time periods change"""
        c = self.db.cursor()
        now = datetime.now()
        
        c.execute("SELECT * FROM quota_state")
        rows = c.fetchall()
        
        for row in rows:
            provider = row["provider"]
            last_hour = datetime.fromisoformat(row["last_reset_hour"]) if row["last_reset_hour"] else now
            last_day = datetime.fromisoformat(row["last_reset_day"]) if row["last_reset_day"] else now
            last_month = datetime.fromisoformat(row["last_reset_month"]) if row["last_reset_month"] else now
            
            updates = {}
            
            # Reset hourly
            if now.hour != last_hour.hour:
                updates["requests_this_hour"] = 0
                updates["last_reset_hour"] = now.isoformat()
            
            # Reset daily
            if now.date() != last_day.date():
                updates["requests_today"] = 0
                updates["tokens_today"] = 0
                updates["cost_today"] = 0.0
                updates["last_reset_day"] = now.isoformat()
                updates["quota_exhausted"] = 0
            
            # Reset monthly
            if now.month != last_month.month:
                updates["cost_this_month"] = 0.0
                updates["last_reset_month"] = now.isoformat()
            
            if updates:
                set_clause = ", ".join([f"{k} = ?" for k in updates])
                values = list(updates.values()) + [provider]
                c.execute(f"UPDATE quota_state SET {set_clause} WHERE provider = ?", values)
        
        self.db.commit()
    
    def check_quota(self, provider_id: str) -> Dict:
        """Check remaining quota for a provider"""
        self._reset_quotas_if_needed()
        
        provider = PROVIDERS[provider_id]
        budget = QUOTA_BUDGETS.get(provider_id, {})
        
        c = self.db.cursor()
        c.execute("SELECT * FROM quota_state WHERE provider = ?", (provider_id,))
        row = c.fetchone()
        
        if not row:
            return {"available": False, "reason": "No quota tracking"}
        
        # Paid providers: check monthly budget
        if provider["cost_per_1m"] > 0:
            monthly_budget = budget.get("monthly_budget_usd", 999999)
            current_cost = row["cost_this_month"] or 0.0
            
            if current_cost >= monthly_budget:
                return {
                    "available": False,
                    "provider": provider_id,
                    "reason": f"Monthly budget exhausted (${current_cost:.2f} / ${monthly_budget:.2f})",
                    "rpm_remaining": 0,
                    "rpd_remaining": 0,
                }
            
            # Assume 90% available for paid tiers (conservative)
            rpm = provider["rate_limit_rpm"]
            rpd = provider["rate_limit_rpd"]
            
            return {
                "available": True,
                "provider": provider_id,
                "rpm_limit": rpm,
                "rpm_used": row["requests_this_hour"] or 0,
                "rpm_remaining": int(rpm * 0.9),
                "rpd_limit": rpd,
                "rpd_used": row["requests_today"] or 0,
                "rpd_remaining": int(rpd * 0.9),
                "cost_per_1m": provider["cost_per_1m"],
                "monthly_cost": current_cost,
                "monthly_budget": monthly_budget,
            }
        
        # Free providers: check request limits
        rpm = provider["rate_limit_rpm"]
        rpd = provider["rate_limit_rpd"]
        
        rpm_used = row["requests_this_hour"] or 0
        rpd_used = row["requests_today"] or 0
        
        rpm_remaining = max(0, rpm - rpm_used)
        rpd_remaining = max(0, rpd - rpd_used)
        
        # Special handling: NVIDIA and Chinese share the same OpenRouter free pool!
        if provider_id in ["nvidia_nim_free", "chinese_free"]:
            # Check combined usage
            c.execute("""
                SELECT SUM(requests_this_hour) as combined_hourly,
                       SUM(requests_today) as combined_daily
                FROM quota_state
                WHERE provider IN ('nvidia_nim_free', 'chinese_free')
            """)
            combined = c.fetchone()
            combined_hourly = combined["combined_hourly"] or 0
            combined_daily = combined["combined_daily"] or 0
            
            # Shared pool: 8 RPM total, ~200 RPD total
            shared_rpm_remaining = max(0, 8 - combined_hourly)
            shared_rpd_remaining = max(0, 200 - combined_daily)
            
            available = shared_rpm_remaining > 0 and shared_rpd_remaining > 0 and row["quota_exhausted"] == 0
            
            return {
                "available": available,
                "provider": provider_id,
                "rpm_limit": rpm,
                "rpm_used": rpm_used,
                "rpm_remaining": shared_rpm_remaining,  # Shared pool!
                "rpd_limit": rpd,
                "rpd_used": rpd_used,
                "rpd_remaining": shared_rpd_remaining,   # Shared pool!
                "cost_per_1m": 0.0,
                "shared_pool_note": "Shares quota with NVIDIA free",
            }
        
        available = rpm_remaining > 0 and rpd_remaining > 0 and row["quota_exhausted"] == 0
        
        return {
            "available": available,
            "provider": provider_id,
            "rpm_limit": rpm,
            "rpm_used": rpm_used,
            "rpm_remaining": rpm_remaining,
            "rpd_limit": rpd,
            "rpd_used": rpd_used,
            "rpd_remaining": rpd_remaining,
            "cost_per_1m": provider["cost_per_1m"],
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # CORE ROUTING LOGIC
    # ─────────────────────────────────────────────────────────────────────
    
    def select_model(self, agent_name: str, issue_title: str, issue_desc: str = "", 
                     issue_type: str = "", force_class: str = None) -> Dict:
        """
        Main routing logic. Returns optimal model with full metadata.
        
        Priority: NVIDIA → Ollama → Chinese → Anthropic → Gemini → OpenAI
        """
        # Step 1: Classify task
        task_class = force_class or self.classify_task(issue_title, issue_desc, issue_type)
        config = TASK_PATTERNS[task_class]
        
        # Step 2: Get agent-specific overrides
        agent_config = AGENT_ROUTING.get(agent_name, {})
        
        # Step 3: Try primary tier
        primary_tier = config["primary_tier"]
        provider_id = self._tier_to_provider(primary_tier)
        quota = self.check_quota(provider_id)
        
        if quota["available"]:
            return self._build_result(provider_id, task_class, agent_name, quota, 
                                       is_primary=True, fallback_from=None)
        
        # Step 4: Walk fallback chain
        for fallback_tier in config["fallback_chain"]:
            provider_id = self._tier_to_provider(fallback_tier)
            quota = self.check_quota(provider_id)
            if quota["available"]:
                return self._build_result(provider_id, task_class, agent_name, quota,
                                           is_primary=False, fallback_from=config["primary_tier"])
        
        # Step 5: Last resort — try every provider
        for provider_id in ["ollama", "nvidia_nim_free", "chinese_free", "anthropic", "gemini", "openai"]:
            quota = self.check_quota(provider_id)
            if quota["available"]:
                return self._build_result(provider_id, task_class, agent_name, quota,
                                           is_primary=False, fallback_from="ALL_EXHAUSTED")
        
        # Step 6: Everything exhausted
        return {
            "error": "All providers exhausted",
            "agent": agent_name,
            "task_class": task_class,
            "recommendation": "Wait for quota reset (top of hour) or check API keys",
        }
    
    def _tier_to_provider(self, tier: str) -> str:
        """Map tier letter to provider ID per Joseph's hierarchy"""
        tier_map = {
            "A": "nvidia_nim_free",   # Tier A: NVIDIA NIM FREE
            "B": "ollama",             # Tier B: Ollama (Your Subscription)
            "C": "chinese_free",       # Tier C: Chinese Models (Free)
            "D": "anthropic",          # Tier D: Anthropic (Paid)
            "E": "gemini",             # Tier E: Gemini (Paid)
            "F": "openai",             # Tier F: OpenAI (Paid)
        }
        return tier_map.get(tier, "ollama")
    
    def _build_result(self, provider_id: str, task_class: str, agent_name: str, 
                      quota: Dict, is_primary: bool, fallback_from: str) -> Dict:
        """Build comprehensive routing result"""
        provider = PROVIDERS[provider_id]
        
        # Select model variant
        models = provider["models"]
        if task_class == "critical":
            model_key = "ultra" if "ultra" in models else ("opus" if "opus" in models else list(models.keys())[0])
        elif task_class == "complex":
            model_key = "sonnet" if "sonnet" in models else ("super" if "super" in models else ("kimi_k2_6" if "kimi_k2_6" in models else list(models.keys())[0]))
        elif task_class == "standard":
            model_key = "flash" if "flash" in models else ("nano" if "nano" in models else ("qwen3_next" if "qwen3_next" in models else list(models.keys())[0]))
        else:
            model_key = list(models.keys())[0]
        
        model_id = models[model_key]
        
        return {
            "agent": agent_name,
            "task_class": task_class,
            "provider_id": provider_id,
            "provider_name": provider["name"],
            "tier": provider["tier"],
            "model_key": model_key,
            "model_id": model_id,
            "provider_api": provider["provider_id"],
            "cost_per_1m": provider["cost_per_1m"],
            "is_primary": is_primary,
            "fallback_from": fallback_from,
            "quota_remaining": {
                "rpm": quota.get("rpm_remaining", 0),
                "rpd": quota.get("rpd_remaining", 0),
            },
            "reasoning": f"{'PRIMARY' if is_primary else 'FALLBACK'}: {task_class} task → {provider['name']} ({model_key})",
            "rationale": TASK_PATTERNS[task_class]["rationale"],
            "provider_strengths": provider["strengths"],
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # USAGE LOGGING
    # ─────────────────────────────────────────────────────────────────────
    
    def log_usage(self, provider_id: str, model_id: str, agent_name: str, 
                  task_type: str, task_class: str, tokens_in: int = 0, 
                  tokens_out: int = 0, cost: float = 0.0, was_fallback: bool = False,
                  fallback_from: str = None, latency_ms: int = 0,
                  success: bool = True, error: str = None):
        """Log execution to database and update quotas"""
        c = self.db.cursor()
        
        # Log usage
        c.execute('''
            INSERT INTO provider_usage 
            (provider, model, agent_name, task_type, task_class, tokens_prompt, 
             tokens_completion, cost_usd, was_fallback, fallback_from, latency_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (provider_id, model_id, agent_name, task_type, task_class, tokens_in, 
              tokens_out, cost, 1 if was_fallback else 0, fallback_from, latency_ms,
              1 if success else 0, error))
        
        # Update quota state
        provider = PROVIDERS.get(provider_id, {})
        if provider.get("cost_per_1m", 0) > 0:
            # Paid provider: update cost
            c.execute('''
                UPDATE quota_state 
                SET requests_today = requests_today + 1,
                    requests_this_hour = requests_this_hour + 1,
                    tokens_today = tokens_today + ?,
                    cost_today = cost_today + ?,
                    cost_this_month = cost_this_month + ?
                WHERE provider = ?
            ''', (tokens_in + tokens_out, cost, cost, provider_id))
        else:
            # Free provider: update counts only
            c.execute('''
                UPDATE quota_state 
                SET requests_today = requests_today + 1,
                    requests_this_hour = requests_this_hour + 1,
                    tokens_today = tokens_today + ?
                WHERE provider = ?
            ''', (tokens_in + tokens_out, provider_id))
        
        self.db.commit()
    
    # ─────────────────────────────────────────────────────────────────────
    # REPORTING
    # ─────────────────────────────────────────────────────────────────────
    
    def get_usage_report(self, hours: int = 24) -> Dict:
        """Generate comprehensive usage report"""
        c = self.db.cursor()
        
        # By provider
        c.execute('''
            SELECT provider, 
                   COUNT(*) as calls, 
                   SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END) as fallback_calls,
                   SUM(tokens_prompt + tokens_completion) as tokens,
                   SUM(cost_usd) as cost,
                   AVG(success) as success_rate,
                   AVG(latency_ms) as avg_latency
            FROM provider_usage
            WHERE timestamp > datetime('now', '-{} hours')
            GROUP BY provider
            ORDER BY calls DESC
        '''.format(hours))
        
        by_provider = [dict(row) for row in c.fetchall()]
        
        # By task class
        c.execute('''
            SELECT task_class, COUNT(*) as calls, SUM(cost_usd) as cost
            FROM provider_usage
            WHERE timestamp > datetime('now', '-{} hours')
            GROUP BY task_class
        '''.format(hours))
        
        by_task_class = [dict(row) for row in c.fetchall()]
        
        # Totals
        c.execute('''
            SELECT COUNT(*) as total_calls, 
                   SUM(cost_usd) as total_cost,
                   SUM(tokens_prompt + tokens_completion) as total_tokens,
                   SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END) as total_fallbacks
            FROM provider_usage
            WHERE timestamp > datetime('now', '-{} hours')
        '''.format(hours))
        
        totals = dict(c.fetchone())
        
        # Current quotas
        quotas = {}
        for pid in PROVIDERS:
            quotas[pid] = self.check_quota(pid)
        
        return {
            "period_hours": hours,
            "by_provider": by_provider,
            "by_task_class": by_task_class,
            "totals": totals,
            "quotas": quotas,
        }
    
    def get_agent_routing_summary(self) -> Dict:
        """Get routing summary per agent"""
        c = self.db.cursor()
        c.execute('''
            SELECT agent_name, 
                   provider,
                   COUNT(*) as calls,
                   SUM(CASE WHEN was_fallback = 1 THEN 1 ELSE 0 END) as fallbacks
            FROM provider_usage
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY agent_name, provider
            ORDER BY agent_name, calls DESC
        ''')
        
        results = {}
        for row in c.fetchall():
            agent = row["agent_name"]
            if agent not in results:
                results[agent] = []
            results[agent].append({
                "provider": row["provider"],
                "calls": row["calls"],
                "fallbacks": row["fallbacks"],
            })
        
        return results
    
    def close(self):
        self.db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — Demonstration
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    router = IntelligentModelRouterV2()
    
    print("\n" + "═" * 80)
    print("INTELLIGENT MODEL ROUTER v2.0 — JOSEPH'S PRIORITY HIERARCHY")
    print("═" * 80)
    print("\nPriority Order:")
    print("  1. NVIDIA NIM FREE      — Reserve for critical")
    print("  2. OLLAMA (Your Sub)     — UNLIMITED, use liberally")
    print("  3. CHINESE MODELS (Free)  — Standard tasks, $0")
    print("  4. ANTHROPIC (Paid)      — CONSERVE — fallback only")
    print("  5. GEMINI (Paid)          — CONSERVE — fallback only")
    print("  6. OPENAI (Paid)          — LAST RESORT")
    print()
    
    # Test scenarios
    test_tasks = [
        ("CEO", "Strategic pivot: Should we enter B2B plant software?", "strategy", None),
        ("Code Specialist", "Refactor Stripe integration for multi-currency", "feature", None),
        ("Content Creator", "Generate 100 plant care tips for email sequence", "content", None),
        ("Quick Responder", "Triage: Customer asking about shipping", "triage", None),
        ("Research Analyst", "Deep competitor analysis: Bloomscape", "research", None),
        ("Social Media Manager", "Create 7 TikTok scripts for launch", "marketing", None),
        ("QA Reviewer", "Review PR #42: Authentication middleware", "bug", None),
        ("Customer Success", "Respond to refund request", "support", None),
        ("Pathfinder", "Find workaround for Muapi.ai rate limit", "problem-solving", None),
        ("DevOps Engineer", "Configure auto-scaling for store", "infrastructure", None),
    ]
    
    print("═" * 80)
    print("ROUTING DEMONSTRATION")
    print("═" * 80)
    print()
    
    for agent, title, issue_type, forced in test_tasks:
        result = router.select_model(agent, title, "", issue_type, force_class=forced)
        
        if "error" in result:
            print(f"❌ {agent:25s} | ERROR: {result['error']}")
            continue
        
        marker = "✅" if result["is_primary"] else "⚠️"
        tier_color = {
            "A": "👑",  # NVIDIA
            "B": "🔥",  # Ollama
            "C": "🆓",  # Chinese
            "D": "💰",  # Anthropic
            "E": "💎",  # Gemini
            "F": "⛽",  # OpenAI
        }.get(result["tier"], "?")
        
        print(f"{marker} {tier_color} {agent:25s} | {result['task_class']:10s} | {result['provider_name']:22s} | {result['model_key']}")
        print(f"    → {result['reasoning']}")
        if result["fallback_from"]:
            print(f"    → Fallback from: {result['fallback_from']}")
        print()
    
    # Quota state
    print("═" * 80)
    print("CURRENT QUOTA STATE")
    print("═" * 80)
    print()
    
    for provider_id in ["nvidia_nim_free", "ollama", "chinese_free", "anthropic", "gemini", "openai"]:
        quota = router.check_quota(provider_id)
        provider = PROVIDERS[provider_id]
        
        status = "✅ AVAILABLE" if quota.get("available") else "❌ EXHAUSTED"
        print(f"{status} {provider['name']} (Tier {provider['tier']})")
        
        if provider["cost_per_1m"] > 0:
            print(f"  Monthly: ${quota.get('monthly_cost', 0):.2f} / ${quota.get('monthly_budget', 999):.2f}")
        else:
            print(f"  RPM: {quota.get('rpm_used', 0)}/{quota.get('rpm_limit', 0)} | Remaining: {quota.get('rpm_remaining', 0)}")
            print(f"  RPD: {quota.get('rpd_used', 0)}/{quota.get('rpd_limit', 0)} | Remaining: {quota.get('rpd_remaining', 0)}")
        
        if quota.get("shared_pool_note"):
            print(f"  ⚠️  {quota['shared_pool_note']}")
        print()
    
    router.close()
    
    print("═" * 80)
    print("ROUTER v2.0 READY")
    print("═" * 80)
    print(f"\nDatabase: {DB_PATH}")
    print("\nIntegration:")
    print("  1. Call router.select_model(agent, title, desc, type) before each execution")
    print("  2. Call router.log_usage(...) after each completion")
    print("  3. Monitor via router.get_usage_report()")
    print("  4. Quotas reset automatically hourly/daily/monthly")
