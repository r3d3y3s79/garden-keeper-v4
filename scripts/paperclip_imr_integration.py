#!/usr/bin/env python3
"""
Paperclip Integration Layer for Intelligent Model Router
Wraps agent execution to route tasks through IMR before calling LLM.
"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Add router to path
sys.path.insert(0, '/root/the-garden-keeper/scripts')

from intelligent_model_router import IntelligentModelRouter, PROVIDERS, TASK_PATTERNS

class PaperclipModelRouter:
    """
    Integration between Paperclip adapter execution and IMR.
    Intercepts model selection and applies intelligent routing.
    """
    
    def __init__(self):
        self.router = IntelligentModelRouter()
        self.paperclip_db = "postgres://paperclip:paperclip@localhost:5432/paperclip"
    
    def route_agent_task(self, agent_name: str, issue_title: str, issue_body: str = "", issue_type: str = "") -> dict:
        """
        Called before every agent execution.
        Returns the optimal model configuration.
        """
        result = self.router.select_model(agent_name, issue_title, issue_body, issue_type)
        
        # Convert to Paperclip adapter_config format
        model_id = result["model_id"]
        provider = "openrouter"  # Most models route through OpenRouter
        
        # Special case: Ollama models don't use OpenRouter
        if result["provider"] == "ollama":
            provider = "ollama"
        
        return {
            "model": model_id,
            "provider": provider,
            "imr_routing": {
                "task_class": result["task_class"],
                "original_provider": result["provider_name"],
                "is_primary": result["is_primary"],
                "fallback_from": result["fallback_from"],
                "quota_remaining": result["quota_remaining"],
                "estimated_cost_per_1m": result["cost_per_1m"],
            }
        }
    
    def log_execution(self, agent_name: str, model_id: str, provider: str, 
                     task_type: str, tokens_in: int = 0, tokens_out: int = 0,
                     success: bool = True, error: str = None):
        """Log execution to IMR database"""
        # Map model_id back to provider_id
        provider_id = self._model_to_provider(model_id)
        self.router.log_usage(
            provider_id=provider_id,
            model_id=model_id,
            agent_name=agent_name,
            task_type=task_type,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            success=success,
            error=error
        )
    
    def _model_to_provider(self, model_id: str) -> str:
        """Reverse-map model ID to provider ID"""
        for pid, pconf in PROVIDERS.items():
            if model_id in pconf["models"].values():
                return pid
        return "unknown"
    
    def get_dashboard_data(self) -> dict:
        """Get current routing state for dashboard display"""
        report = self.router.get_usage_report(hours=24)
        
        quotas = {}
        for pid in ["nvidia_nim_free", "anthropic", "gemini", "openai", "chinese_free", "ollama"]:
            quotas[pid] = self.router.check_quota(pid)
        
        return {
            "usage_24h": report,
            "quotas": quotas,
            "provider_configs": {
                pid: {
                    "name": p["name"],
                    "tier": p["tier"],
                    "cost_per_1m": p["cost_per_1m"],
                    "strategy": p["strategy"],
                }
                for pid, p in PROVIDERS.items()
            }
        }
    
    def close(self):
        self.router.close()


# ═══════════════════════════════════════════════════════════════════
# PAPERCLIP ADAPTER PATCH INSTRUCTIONS
# ═══════════════════════════════════════════════════════════════════
"""
To integrate IMR into Paperclip:

1. PATCH execute.js (around line 330 where adapter_config is read):

   BEFORE:
   -----
   const adapterConfig = agent.adapter_config;
   const model = adapterConfig.model;
   const provider = adapterConfig.provider;
   
   AFTER:
   -----
   const { IntelligentModelRouter } = require('/root/the-garden-keeper/scripts/intelligent_model_router');
   const router = new IntelligentModelRouter();
   
   // Get issue details for classification
   const issue = await getIssueDetails(issueId);
   const routing = router.select_model(agent.name, issue.title, issue.body, issue.type);
   
   // Override model with IMR selection
   const model = routing.model_id;
   const provider = routing.provider === 'ollama' ? 'ollama' : 'openrouter';
   
   // Log the routing decision
   console.log(`[IMR] ${agent.name} → ${routing.provider_name} (${routing.model_key}) [${routing.task_class}]`);
   
   // After execution, log usage
   router.log_usage(...);

2. ALTERNATIVE: PostgreSQL trigger (simpler, no code changes):
   
   Create a BEFORE UPDATE trigger on issues table that sets
   the agent's adapter_config dynamically based on issue content.

3. RECOMMENDED: Paperclip Plugin
   
   Write a Paperclip plugin that hooks into the agent execution lifecycle:
   - preExecution: Call router.select_model()
   - postExecution: Call router.log_usage()
   - daily: Call router.get_usage_report() and alert
"""

if __name__ == "__main__":
    # Test the integration layer
    pmr = PaperclipModelRouter()
    
    print("Paperclip Model Router Integration Test")
    print("=" * 60)
    
    test = pmr.route_agent_task("CEO", "Strategic pivot analysis", "We need to decide...", "strategy")
    print(f"\nCEO Strategic Task:")
    print(json.dumps(test, indent=2))
    
    test2 = pmr.route_agent_task("Quick Responder", "Triage support ticket", "Customer says...", "triage")
    print(f"\nQuick Responder Routine Task:")
    print(json.dumps(test2, indent=2))
    
    pmr.close()
