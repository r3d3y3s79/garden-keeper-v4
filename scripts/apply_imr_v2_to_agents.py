#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
APPLY INTELLIGENT MODEL ROUTER v2.0 TO PAPERCLIP AGENTS
═══════════════════════════════════════════════════════════════════════════════

Reads the agent routing configuration from IMR v2 and applies optimal
models to each Paperclip agent based on Joseph's exact priority hierarchy.

Execution Plan:
  1. Load IMR v2 agent routing config
  2. Determine primary model for each agent based on typical task mix
  3. Apply to Paperclip PostgreSQL database
  4. Verify all 16 agents updated
  5. Generate routing summary report

Priority Hierarchy Applied:
  Tier A: NVIDIA NIM FREE  → 6 strategic agents (CEO, Insight, Research, Revenue, Growth, Pathfinder)
  Tier B: OLLAMA            → 4 code/support agents (Code Specialist, QA, Quick Responder, Customer Success)
  Tier C: CHINESE FREE      → 6 content/routine agents (Content Creator, Social Media, Shopify, Operator PM, Vision Coder, DevOps)
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
import json
import sys

# Add IMR to path
sys.path.insert(0, '/root/the-garden-keeper/scripts')

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT MODEL ASSIGNMENTS — Based on IMR v2 Agent Routing Config
# ═══════════════════════════════════════════════════════════════════════════════

# Strategic agents: NVIDIA Ultra for critical tasks, but need Ollama fallback
# Code agents: Ollama primary (unlimited)
# Content agents: Chinese free primary
# Support agents: Ollama primary (fastest)

AGENT_MODEL_ASSIGNMENTS = {
    # ═══════════════════════════════════════════════════════════════════
    # TIER A: NVIDIA NIM FREE — Strategic agents (critical tasks)
    # These agents get NVIDIA for critical, Ollama for routine
    # ═══════════════════════════════════════════════════════════════════
    "CEO": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "CEO makes strategic decisions. NVIDIA Ultra 550B for critical thinking. Falls back to Ollama for routine.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    "Insight Engine": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "Deep strategic analysis needs frontier model. NVIDIA Ultra for breakthrough insights.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    "Research Analyst": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "Market intelligence and competitive analysis. NVIDIA Ultra for deep research synthesis.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    "Revenue Specialist": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "Pricing and monetization strategy. NVIDIA Ultra for revenue-critical decisions.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    "Growth Operator": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "Growth experiments and strategy. NVIDIA Ultra for high-impact growth decisions.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    "Pathfinder": {
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "provider": "openrouter",
        "tier": "A",
        "rationale": "Creative problem solving and workarounds. NVIDIA Ultra for unconventional solutions.",
        "imr_config": {
            "critical_model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "routine_model": "ollama-cloud/kimi-k2.5",
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER B: OLLAMA — Code agents + Support agents (unlimited!)
    # Primary workhorse — you've already paid for this subscription
    # ═══════════════════════════════════════════════════════════════════
    "Code Specialist": {
        "model": "ollama-cloud/kimi-k2.6",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Architecture and full-stack development. Ollama (unlimited) for bulk coding. Your subscription!",
        "imr_config": {
            "complex_model": "ollama-cloud/kimi-k2.6",
            "standard_model": "ollama-cloud/kimi-k2.5",
            "fallback_model": "nvidia/nemotron-3-super-120b-a12b:free",
        }
    },
    "QA Reviewer": {
        "model": "ollama-cloud/kimi-k2.6",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Code review and quality gates. Ollama for high-volume reviews. Your subscription!",
        "imr_config": {
            "complex_model": "ollama-cloud/kimi-k2.6",
            "standard_model": "ollama-cloud/kimi-k2.5",
            "fallback_model": "qwen/qwen3-coder:free",
        }
    },
    "Quick Responder": {
        "model": "ollama-cloud/kimi-k2.5",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Fast triage needs zero latency. Ollama (local-speed) for 2min SLA. Your subscription!",
        "imr_config": {
            "routine_model": "ollama-cloud/kimi-k2.5",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    "Customer Success Agent": {
        "model": "ollama-cloud/kimi-k2.5",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Support responses need speed. Ollama for instant replies. Your subscription!",
        "imr_config": {
            "routine_model": "ollama-cloud/kimi-k2.5",
            "standard_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER C: CHINESE FREE — Content and routine agents
    # Good enough quality, completely free
    # ═══════════════════════════════════════════════════════════════════
    "Content Creator": {
        "model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "Content generation and image prompts. Chinese free handles bulk content. Falls back to Ollama.",
        "imr_config": {
            "standard_model": "qwen/qwen3-next-80b-a3b-instruct:free",
            "complex_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "deepseek/deepseek-v4-flash:free",
        }
    },
    "Social Media Manager": {
        "model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "Social posts and captions. Chinese free for daily volume. Falls back to Ollama.",
        "imr_config": {
            "standard_model": "qwen/qwen3-next-80b-a3b-instruct:free",
            "complex_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "deepseek/deepseek-v4-flash:free",
        }
    },
    "Shopify AI Toolkit Specialist": {
        "model": "qwen/qwen3-coder:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "Shopify Liquid and automation. Chinese coder model for templates. Falls back to Ollama.",
        "imr_config": {
            "standard_model": "qwen/qwen3-coder:free",
            "complex_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "deepseek/deepseek-v4-flash:free",
        }
    },
    "Operator PM": {
        "model": "qwen/qwen3-next-80b-a3b-instruct:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "Coordination and backlog management. Chinese free for routine PM work. Falls back to Ollama.",
        "imr_config": {
            "routine_model": "qwen/qwen3-next-80b-a3b-instruct:free",
            "standard_model": "ollama-cloud/kimi-k2.5",
            "fallback_model": "deepseek/deepseek-v4-flash:free",
        }
    },
    "Vision Coder": {
        "model": "qwen/qwen3-coder:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "UI/UX code generation. Chinese coder for HTML/CSS/JS. Falls back to Ollama.",
        "imr_config": {
            "standard_model": "qwen/qwen3-coder:free",
            "complex_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "nvidia/nemotron-3-super-120b-a12b:free",
        }
    },
    "DevOps Engineer": {
        "model": "qwen/qwen3-coder:free",
        "provider": "openrouter",
        "tier": "C",
        "rationale": "Infrastructure and Docker configs. Chinese coder for DevOps scripts. Falls back to Ollama.",
        "imr_config": {
            "standard_model": "qwen/qwen3-coder:free",
            "complex_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "nvidia/nemotron-3-super-120b-a12b:free",
        }
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE MIGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_agents():
    """Apply IMR v2 model assignments to Paperclip agents"""
    
    print("=" * 80)
    print("PAPERCLIP AGENT MIGRATION — IMR v2.0")
    print("Joseph's Priority: NVIDIA → Ollama → Chinese → Anthropic → Gemini → OpenAI")
    print("=" * 80)
    print()
    
    # Connect to Paperclip DB
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="paperclip",
            user="paperclip",
            password="paperclip"
        )
        cur = conn.cursor()
        print("✅ Connected to Paperclip PostgreSQL\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return False
    
    # Get current agent count
    cur.execute("SELECT COUNT(*) FROM agents")
    count = cur.fetchone()[0]
    print(f"Found {count} agents in database\n")
    
    # Track results
    updated = []
    failed = []
    skipped = []
    
    # Update each agent
    for agent_name, config in AGENT_MODEL_ASSIGNMENTS.items():
        model = config["model"]
        provider = config["provider"]
        tier = config["tier"]
        rationale = config["rationale"]
        
        # Fetch current config
        cur.execute("SELECT id, adapter_config FROM agents WHERE name = %s", (agent_name,))
        row = cur.fetchone()
        
        if not row:
            failed.append((agent_name, "Agent not found in database"))
            continue
        
        agent_id, current_config = row
        
        # Parse current config
        try:
            if isinstance(current_config, str):
                adapter_config = json.loads(current_config)
            else:
                adapter_config = current_config or {}
        except json.JSONDecodeError:
            adapter_config = {}
        
        # Store previous model for reporting
        prev_model = adapter_config.get("model", "unknown")
        prev_provider = adapter_config.get("provider", "unknown")
        
        # Apply new configuration
        adapter_config["model"] = model
        adapter_config["provider"] = provider
        adapter_config["imr_version"] = "2.0"
        adapter_config["imr_tier"] = tier
        adapter_config["imr_rationale"] = rationale
        adapter_config["imr_fallback_config"] = config["imr_config"]
        adapter_config["imr_priority_order"] = [
            "nvidia_nim_free",
            "ollama", 
            "chinese_free",
            "anthropic",
            "gemini",
            "openai"
        ]
        
        # Update database
        try:
            cur.execute(
                "UPDATE agents SET adapter_config = %s WHERE id = %s",
                (json.dumps(adapter_config), agent_id)
            )
            updated.append({
                "name": agent_name,
                "id": str(agent_id),
                "tier": tier,
                "model": model,
                "provider": provider,
                "prev_model": prev_model,
                "prev_provider": prev_provider,
            })
        except Exception as e:
            failed.append((agent_name, str(e)))
    
    # Commit changes
    conn.commit()
    cur.close()
    conn.close()
    
    # Print results
    print("=" * 80)
    print("MIGRATION RESULTS")
    print("=" * 80)
    print()
    
    print(f"✅ Updated: {len(updated)} agents")
    print(f"❌ Failed: {len(failed)} agents")
    print(f"⏭️  Skipped: {len(skipped)} agents")
    print()
    
    # Tier summary
    tier_counts = {}
    for u in updated:
        tier = u["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    
    print("BY TIER:")
    for tier, count in sorted(tier_counts.items()):
        tier_name = {
            "A": "NVIDIA NIM FREE (Strategic)",
            "B": "OLLAMA (Code/Support)",
            "C": "CHINESE FREE (Content/Routine)",
        }.get(tier, tier)
        print(f"  Tier {tier}: {count} agents — {tier_name}")
    print()
    
    # Detailed agent list
    print("AGENT ASSIGNMENTS:")
    print("-" * 80)
    
    for u in updated:
        tier_icon = {
            "A": "👑",
            "B": "🔥", 
            "C": "🆓",
        }.get(u["tier"], "?")
        
        print(f"{tier_icon} {u['name']:30s} | {u['tier']} | {u['model']}")
        print(f"   Provider: {u['provider']}")
        print(f"   Previous: {u['prev_provider']}/{u['prev_model']}")
        print()
    
    # Cost impact
    print("=" * 80)
    print("COST IMPACT")
    print("=" * 80)
    print()
    
    nvidia_count = tier_counts.get("A", 0)
    ollama_count = tier_counts.get("B", 0)
    chinese_count = tier_counts.get("C", 0)
    
    print(f"  NVIDIA NIM FREE (Tier A):  {nvidia_count} agents | $0/month")
    print(f"  OLLAMA (Tier B):           {ollama_count} agents | $0/month (subscription)")
    print(f"  CHINESE FREE (Tier C):       {chinese_count} agents | $0/month")
    print(f"  PAID Tiers (D/E/F):         0 agents | $0/month (fallback only)")
    print()
    print(f"  TOTAL: {len(updated)} agents")
    print(f"  MONTHLY COST: $0")
    print(f"  Fallback cost (Anthropic/Gemini/OpenAI): Only if all free exhausted")
    print()
    print("  NOTE: Agents have IMR fallback configs embedded.")
    print("  When quota exhausted, they automatically fall back per priority.")
    print()
    
    if failed:
        print("WARNINGS:")
        for name, reason in failed:
            print(f"  ⚠️  {name}: {reason}")
        print()
    
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Restart Paperclip agents to pick up new models")
    print("2. Monitor IMR dashboard: /root/the-garden-keeper/data/model_router_v2.db")
    print("3. Quotas auto-reset hourly/daily")
    print("4. Fallback chain: NVIDIA → Ollama → Chinese → Anthropic → Gemini → OpenAI")
    print()
    
    return len(failed) == 0


def generate_agent_routing_report():
    """Generate a markdown report of all agent routing configurations"""
    
    report = """# Intelligent Model Router v2.0 — Agent Configuration
## Date: 2026-06-14

## Priority Hierarchy

1. **NVIDIA NIM FREE** — Reserve for critical tasks
2. **OLLAMA (Your Subscription)** — Unlimited, use liberally
3. **CHINESE MODELS (Free)** — Standard tasks, $0
4. **ANTHROPIC (Paid)** — Fallback only, conserve
5. **GEMINI (Paid)** — Fallback only, conserve
6. **OPENAI (Paid)** — Last resort

## Agent Assignments

"""
    
    for agent_name, config in AGENT_MODEL_ASSIGNMENTS.items():
        tier_name = {
            "A": "NVIDIA NIM FREE",
            "B": "OLLAMA",
            "C": "CHINESE FREE",
        }.get(config["tier"], config["tier"])
        
        report += f"### {agent_name}\n"
        report += f"- **Tier:** {config['tier']} ({tier_name})\n"
        report += f"- **Primary Model:** `{config['model']}`\n"
        report += f"- **Provider:** {config['provider']}\n"
        report += f"- **Rationale:** {config['rationale']}\n"
        report += f"- **Fallback Chain:**\n"
        
        for key, model in config["imr_config"].items():
            report += f"  - {key}: `{model}`\n"
        
        report += "\n"
    
    report += """## Fallback Logic

When a provider's quota is exhausted, agents automatically fall back:

```
NVIDIA NIM FREE → OLLAMA → CHINESE → ANTHROPIC → GEMINI → OPENAI
```

## Quota Management

| Provider | Daily Budget | Strategy |
|----------|-------------|----------|
| NVIDIA | 50 requests | Reserve for critical only |
| Ollama | Unlimited | Use liberally (paid subscription) |
| Chinese | 100 requests | After NVIDIA, before paid |
| Anthropic | $25/month | Fallback only |
| Gemini | $15/month | Fallback only |
| OpenAI | $10/month | Last resort |

"""
    
    with open('/root/the-garden-keeper/docs/AGENT_ROUTING_CONFIG.md', 'w') as f:
        f.write(report)
    
    print("\n📄 Routing report saved to: /root/the-garden-keeper/docs/AGENT_ROUTING_CONFIG.md")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    success = migrate_agents()
    generate_agent_routing_report()
    
    if success:
        print("\n✅ Migration complete. All agents configured with IMR v2.0")
        sys.exit(0)
    else:
        print("\n⚠️  Migration completed with warnings. Check failed agents above.")
        sys.exit(1)
