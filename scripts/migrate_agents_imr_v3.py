#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
PAPERCLIP AGENT MIGRATION — IMR v3.0 (Based on Live Testing)
═══════════════════════════════════════════════════════════════════════════════

Live Test Results (2026-06-14):
  🏆 GLM-5.1:       4,241ms | 6/6 quality | ✅ Produces output | 1,404GB
  🥈 DeepSeek V3.2:  36,231ms | 6/6 quality | ✅ Produces output | 641GB
  ❌ Kimi K2.6:      7,356ms | 0/6 quality | ❌ Thinks only | 554GB
  ❌ MiniMax M3:     10,714ms | 0/6 quality | ❌ Thinks only | 448GB

New Hierarchy:
  Tier A: OLLAMA GLM-5.1      — Strategic agents (fast, frontier, ACTUALLY OUTPUTS)
  Tier A2: OLLAMA Kimi K2.6   — THINKING pipeline (planning agent, needs output wrapper)
  Tier B: OLLAMA DeepSeek V3.2 — Code agents (perfect 6/6, reliable)
  Tier C: OLLAMA DeepSeek V3.2 — Content/support agents (consistent quality)
  Tier D: NVIDIA NIM FREE      — Reserved overflow
  Tier E: CHINESE FREE         — Emergency fallback
  Tier F: ANTHROPIC/GEMINI     — Paid last resort

Key Changes from IMR v2:
  - GLM-5.1 replaces NVIDIA Ultra as strategic model (faster, bigger, output-guaranteed)
  - DeepSeek V3.2 is now the code workhorse (proven 6/6 quality)
  - Kimi K2.6 gets "thinking pipeline" mode (not direct agent use)
  - MiniMax M3 removed from agent pool (thinking-only trap)
  - NVIDIA NIM moved to Tier D (reserved overflow only)
  - Chinese models moved to Tier E (emergency only)
═══════════════════════════════════════════════════════════════════════════════
"""

import psycopg2
import json
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT MODEL ASSIGNMENTS — IMR v3.0 (Test-Verified)
# ═══════════════════════════════════════════════════════════════════════════════

AGENT_MODEL_ASSIGNMENTS = {
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER A: OLLAMA GLM-5.1 — Strategic Agents
    # Test winner: 4,241ms, 6/6 quality, 1,404GB frontier, ACTUALLY OUTPUTS
    # ═══════════════════════════════════════════════════════════════════
    "CEO": {
        "model": "ollama-cloud/glm-5.1",  # Ollama Cloud API
        "provider": "ollama",
        "tier": "A",
        "rationale": "CEO makes irreversible strategic decisions. GLM-5.1: 1,404GB, 4.2s, perfect output quality.",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",  # For complex multi-step reasoning
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    "Insight Engine": {
        "model": "ollama-cloud/glm-5.1",
        "provider": "ollama",
        "tier": "A",
        "rationale": "Deep strategic analysis needs frontier model that actually produces output. GLM-5.1 delivers.",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    "Research Analyst": {
        "model": "ollama-cloud/glm-5.1",
        "provider": "ollama",
        "tier": "A",
        "rationale": "Competitive intel requires fast, thorough analysis. GLM-5.1 is 3x faster than DeepSeek V3.2.",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    "Revenue Specialist": {
        "model": "ollama-cloud/glm-5.1",
        "provider": "ollama",
        "tier": "A",
        "rationale": "Pricing and monetization at 1,404GB frontier quality. 6x larger than NVIDIA Ultra (215GB).",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    "Growth Operator": {
        "model": "ollama-cloud/glm-5.1",
        "provider": "ollama",
        "tier": "A",
        "rationale": "Growth experiments demand speed. GLM-5.1 at 4.2s vs DeepSeek at 36s = 8.5x faster iteration.",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    "Pathfinder": {
        "model": "ollama-cloud/glm-5.1",
        "provider": "ollama",
        "tier": "A",
        "rationale": "Creative breakthroughs at frontier quality. GLM-5.1: 1,404GB + 4.2s = instant genius.",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "thinking_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER B: OLLAMA DeepSeek V3.2 — Code Agents
    # Test winner: 6/6 code quality, thorough, reliable
    # Slightly slower (36s) but the code quality justifies it
    # ═══════════════════════════════════════════════════════════════════
    "Code Specialist": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Perfect 6/6 code quality in tests. DeepSeek V3.2 at 641GB is the best code model on Ollama.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",  # For quick boilerplate
            "fallback_model": "ollama-cloud/qwen3-coder",
        }
    },
    "QA Reviewer": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Code review demands quality. DeepSeek V3.2 scored 6/6 including error handling and edge cases.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",
            "fallback_model": "ollama-cloud/qwen3-coder",
        }
    },
    "Vision Coder": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "B",
        "rationale": "UI/UX code needs type safety and error handling. DeepSeek V3.2 delivers both perfectly.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",
            "fallback_model": "nvidia/nemotron-3-super-120b-a12b:free",
        }
    },
    "DevOps Engineer": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "B",
        "rationale": "Infrastructure code needs precision. DeepSeek V3.2: 6/6 including edge case handling.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",
            "fallback_model": "nvidia/nemotron-3-super-120b-a12b:free",
        }
    },
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER C: OLLAMA DeepSeek V3.2 — Content + Support Agents
    # Consistent quality, reliable output
    # ═══════════════════════════════════════════════════════════════════
    "Content Creator": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "C",
        "rationale": "Content needs reliable output. DeepSeek V3.2 guarantees actual text, not just thinking.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "creative_model": "ollama-cloud/kimi-k2.6",  # Thinking may spark creativity
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    "Social Media Manager": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "C",
        "rationale": "Social posts must be delivered, not just contemplated. DeepSeek V3.2 guarantees output.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "creative_model": "ollama-cloud/kimi-k2.6",
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    "Shopify AI Toolkit Specialist": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "C",
        "rationale": "Liquid code is still code. DeepSeek V3.2 scored 6/6 on code quality.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fallback_model": "qwen/qwen3-coder:free",
        }
    },
    "Operator PM": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "C",
        "rationale": "Coordination and backlog management. DeepSeek V3.2 provides thorough, structured output.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    "Customer Success Agent": {
        "model": "ollama-cloud/deepseek-v3.2",
        "provider": "ollama",
        "tier": "C",
        "rationale": "Support needs reliable, empathetic output. DeepSeek V3.2 guarantees response delivery.",
        "imr_config": {
            "primary_model": "ollama-cloud/deepseek-v3.2",
            "fast_model": "ollama-cloud/glm-5.1",
            "fallback_model": "qwen/qwen3-next-80b-a3b-instruct:free",
        }
    },
    "Quick Responder": {
        "model": "ollama-cloud/glm-5.1",  # FASTEST model for SLA-critical agent
        "provider": "ollama",
        "tier": "A",  # Using GLM-5.1 for speed
        "rationale": "Quick Responder needs 2min SLA. GLM-5.1 at 4.2s is 8.5x faster than DeepSeek V3.2 (36s).",
        "imr_config": {
            "primary_model": "ollama-cloud/glm-5.1",
            "fallback_model": "ollama-cloud/deepseek-v3.2",
        }
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# THINKING MODEL PIPELINE — Kimi K2.6 (Thinking → Output wrapper)
# ═══════════════════════════════════════════════════════════════════════════════

THINKING_PIPELINE_CONFIG = {
    "enabled": True,
    "name": "Kimi K2.6 Thinking Pipeline",
    "description": "Kimi K2.6 thinks but doesn't output. This pipeline forces output after thinking.",
    "usage": "Complex multi-step tasks where deep reasoning matters more than speed.",
    "strategy": "Two-phase: Kimi K2.6 thinks → GLM-5.1 summarizes thinking into output",
    "pipeline": {
        "phase_1": {
            "model": "ollama-cloud/kimi-k2.6",
            "role": "Deep reasoner — thinks extensively about the problem",
            "prompt_template": "Think deeply about this problem. Analyze all angles. Consider edge cases. Plan the solution. DO NOT output the final answer — just think.",
            "max_thinking_tokens": 2000,
        },
        "phase_2": {
            "model": "ollama-cloud/glm-5.1",
            "role": "Output generator — reads thinking and produces final answer",
            "prompt_template": "Based on this thinking: {thinking}\n\nNow produce the final answer. Follow the user's original request exactly.",
            "max_output_tokens": 1000,
        },
    },
    "agents_using": ["CEO", "Insight Engine", "Research Analyst", "Revenue Specialist", "Pathfinder"],
    "trigger_condition": "Task is classified as 'critical' OR task requires multi-step reasoning with 3+ phases",
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE MIGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_agents():
    """Apply IMR v3.0 model assignments to Paperclip agents"""
    
    print("=" * 80)
    print("PAPERCLIP AGENT MIGRATION — IMR v3.0")
    print("Based on live testing: GLM-5.1 wins strategic, DeepSeek V3.2 wins code")
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
    
    # Track results
    updated = []
    failed = []
    
    print("Applying model assignments...\n")
    
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
        
        # Apply new configuration
        adapter_config["model"] = model
        adapter_config["provider"] = provider
        adapter_config["imr_version"] = "3.0"
        adapter_config["imr_tier"] = tier
        adapter_config["imr_rationale"] = rationale
        adapter_config["imr_fallback_config"] = config["imr_config"]
        adapter_config["imr_test_verified"] = True
        adapter_config["imr_test_date"] = "2026-06-14"
        adapter_config["imr_test_results"] = {
            "glm-5.1": {"latency_ms": 4241, "quality": "6/6", "output": True},
            "deepseek-v3.2": {"latency_ms": 36231, "quality": "6/6", "output": True},
            "kimi-k2.6": {"latency_ms": 7356, "quality": "0/6", "output": False, "note": "Thinking only"},
            "minimax-m3": {"latency_ms": 10714, "quality": "0/6", "output": False, "note": "Thinking only"},
        }
        
        # Add thinking pipeline config for strategic agents
        if agent_name in THINKING_PIPELINE_CONFIG["agents_using"]:
            adapter_config["thinking_pipeline"] = True
            adapter_config["thinking_pipeline_config"] = {
                "phase_1_model": "ollama-cloud/kimi-k2.6",
                "phase_2_model": "ollama-cloud/glm-5.1",
                "trigger": "critical tasks OR 3+ phase reasoning",
            }
        
        # Update database
        try:
            cur.execute(
                "UPDATE agents SET adapter_config = %s WHERE id = %s",
                (json.dumps(adapter_config), agent_id)
            )
            updated.append({
                "name": agent_name,
                "tier": tier,
                "model": model,
                "prev_model": prev_model,
                "has_thinking_pipeline": agent_name in THINKING_PIPELINE_CONFIG["agents_using"],
            })
            print(f"  ✅ {agent_name:30s} → {model}")
        except Exception as e:
            failed.append((agent_name, str(e)))
            print(f"  ❌ {agent_name:30s} → ERROR: {e}")
    
    # Commit changes
    conn.commit()
    cur.close()
    conn.close()
    
    # Print summary
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print()
    
    # Tier breakdown
    tier_counts = {}
    for u in updated:
        t = u["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1
    
    print(f"✅ Updated: {len(updated)} agents")
    print(f"❌ Failed: {len(failed)} agents")
    print()
    
    print("BY TIER:")
    tier_names = {
        "A": "GLM-5.1 (1,404GB — Strategic)",
        "B": "DeepSeek V3.2 (641GB — Code)",
        "C": "DeepSeek V3.2 (641GB — Content/Support)",
    }
    for tier, count in sorted(tier_counts.items()):
        print(f"  Tier {tier}: {count} agents — {tier_names.get(tier, tier)}")
    print()
    
    # Models used
    model_counts = {}
    for u in updated:
        m = u["model"]
        model_counts[m] = model_counts.get(m, 0) + 1
    
    print("MODELS IN USE:")
    for model, count in model_counts.items():
        print(f"  {model}: {count} agents")
    print()
    
    # Thinking pipeline
    thinking_agents = [u for u in updated if u["has_thinking_pipeline"]]
    print(f"🧠 Kimi K2.6 Thinking Pipeline: {len(thinking_agents)} strategic agents")
    print(f"   Phase 1: Kimi K2.6 thinks (2K tokens)")
    print(f"   Phase 2: GLM-5.1 outputs based on thinking")
    print(f"   Trigger: Critical tasks OR 3+ phase reasoning")
    print(f"   Agents: {', '.join(a['name'] for a in thinking_agents)}")
    print()
    
    # Cost
    print("=" * 80)
    print("COST: $0/month (all Ollama subscription)")
    print("  Fallback: NVIDIA FREE → Chinese FREE → Anthropic (conserved)")
    print("=" * 80)
    print()
    
    # Test verification
    print("=" * 80)
    print("TEST-VERIFIED QUALITY")
    print("=" * 80)
    print(f"  🏆 GLM-5.1:      4,241ms | 6/6 quality | ✅ Output")
    print(f"  🥈 DeepSeek V3.2: 36,231ms | 6/6 quality | ✅ Output")
    print(f"  ❌ Kimi K2.6:     7,356ms | 0/6 quality | ❌ Thinking only → Pipeline mode")
    print(f"  ❌ MiniMax M3:    10,714ms | 0/6 quality | ❌ Thinking only → Not used")
    print()
    
    return len(failed) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    success = migrate_agents()
    
    if success:
        print("\n✅ IMR v3.0 migration successful.")
        print("   GLM-5.1 is your new strategic model (1,404GB, 4.2s, 6/6)")
        print("   DeepSeek V3.2 is your code workhorse (641GB, 36s, 6/6)")
        print("   Kimi K2.6 enters 'thinking pipeline' mode (plans, doesn't execute)")
        print("   MiniMax M3 retired from agent pool (thinks only)")
        sys.exit(0)
    else:
        print("\n⚠️  Migration completed with warnings.")
        sys.exit(1)