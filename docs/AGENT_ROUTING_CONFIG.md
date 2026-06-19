# Intelligent Model Router v2.0 — Agent Configuration
## Date: 2026-06-14

## Priority Hierarchy

1. **NVIDIA NIM FREE** — Reserve for critical tasks
2. **OLLAMA (Your Subscription)** — Unlimited, use liberally
3. **CHINESE MODELS (Free)** — Standard tasks, $0
4. **ANTHROPIC (Paid)** — Fallback only, conserve
5. **GEMINI (Paid)** — Fallback only, conserve
6. **OPENAI (Paid)** — Last resort

## Agent Assignments

### CEO
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** CEO makes strategic decisions. NVIDIA Ultra 550B for critical thinking. Falls back to Ollama for routine.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Insight Engine
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** Deep strategic analysis needs frontier model. NVIDIA Ultra for breakthrough insights.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Research Analyst
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** Market intelligence and competitive analysis. NVIDIA Ultra for deep research synthesis.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Revenue Specialist
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** Pricing and monetization strategy. NVIDIA Ultra for revenue-critical decisions.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Growth Operator
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** Growth experiments and strategy. NVIDIA Ultra for high-impact growth decisions.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Pathfinder
- **Tier:** A (NVIDIA NIM FREE)
- **Primary Model:** `nvidia/nemotron-3-ultra-550b-a55b:free`
- **Provider:** openrouter
- **Rationale:** Creative problem solving and workarounds. NVIDIA Ultra for unconventional solutions.
- **Fallback Chain:**
  - critical_model: `nvidia/nemotron-3-ultra-550b-a55b:free`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - routine_model: `ollama-cloud/kimi-k2.5`

### Code Specialist
- **Tier:** B (OLLAMA)
- **Primary Model:** `ollama-cloud/kimi-k2.6`
- **Provider:** ollama
- **Rationale:** Architecture and full-stack development. Ollama (unlimited) for bulk coding. Your subscription!
- **Fallback Chain:**
  - complex_model: `ollama-cloud/kimi-k2.6`
  - standard_model: `ollama-cloud/kimi-k2.5`
  - fallback_model: `nvidia/nemotron-3-super-120b-a12b:free`

### QA Reviewer
- **Tier:** B (OLLAMA)
- **Primary Model:** `ollama-cloud/kimi-k2.6`
- **Provider:** ollama
- **Rationale:** Code review and quality gates. Ollama for high-volume reviews. Your subscription!
- **Fallback Chain:**
  - complex_model: `ollama-cloud/kimi-k2.6`
  - standard_model: `ollama-cloud/kimi-k2.5`
  - fallback_model: `qwen/qwen3-coder:free`

### Quick Responder
- **Tier:** B (OLLAMA)
- **Primary Model:** `ollama-cloud/kimi-k2.5`
- **Provider:** ollama
- **Rationale:** Fast triage needs zero latency. Ollama (local-speed) for 2min SLA. Your subscription!
- **Fallback Chain:**
  - routine_model: `ollama-cloud/kimi-k2.5`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `qwen/qwen3-next-80b-a3b-instruct:free`

### Customer Success Agent
- **Tier:** B (OLLAMA)
- **Primary Model:** `ollama-cloud/kimi-k2.5`
- **Provider:** ollama
- **Rationale:** Support responses need speed. Ollama for instant replies. Your subscription!
- **Fallback Chain:**
  - routine_model: `ollama-cloud/kimi-k2.5`
  - standard_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `qwen/qwen3-next-80b-a3b-instruct:free`

### Content Creator
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-next-80b-a3b-instruct:free`
- **Provider:** openrouter
- **Rationale:** Content generation and image prompts. Chinese free handles bulk content. Falls back to Ollama.
- **Fallback Chain:**
  - standard_model: `qwen/qwen3-next-80b-a3b-instruct:free`
  - complex_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `deepseek/deepseek-v4-flash:free`

### Social Media Manager
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-next-80b-a3b-instruct:free`
- **Provider:** openrouter
- **Rationale:** Social posts and captions. Chinese free for daily volume. Falls back to Ollama.
- **Fallback Chain:**
  - standard_model: `qwen/qwen3-next-80b-a3b-instruct:free`
  - complex_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `deepseek/deepseek-v4-flash:free`

### Shopify AI Toolkit Specialist
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-coder:free`
- **Provider:** openrouter
- **Rationale:** Shopify Liquid and automation. Chinese coder model for templates. Falls back to Ollama.
- **Fallback Chain:**
  - standard_model: `qwen/qwen3-coder:free`
  - complex_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `deepseek/deepseek-v4-flash:free`

### Operator PM
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-next-80b-a3b-instruct:free`
- **Provider:** openrouter
- **Rationale:** Coordination and backlog management. Chinese free for routine PM work. Falls back to Ollama.
- **Fallback Chain:**
  - routine_model: `qwen/qwen3-next-80b-a3b-instruct:free`
  - standard_model: `ollama-cloud/kimi-k2.5`
  - fallback_model: `deepseek/deepseek-v4-flash:free`

### Vision Coder
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-coder:free`
- **Provider:** openrouter
- **Rationale:** UI/UX code generation. Chinese coder for HTML/CSS/JS. Falls back to Ollama.
- **Fallback Chain:**
  - standard_model: `qwen/qwen3-coder:free`
  - complex_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `nvidia/nemotron-3-super-120b-a12b:free`

### DevOps Engineer
- **Tier:** C (CHINESE FREE)
- **Primary Model:** `qwen/qwen3-coder:free`
- **Provider:** openrouter
- **Rationale:** Infrastructure and Docker configs. Chinese coder for DevOps scripts. Falls back to Ollama.
- **Fallback Chain:**
  - standard_model: `qwen/qwen3-coder:free`
  - complex_model: `ollama-cloud/kimi-k2.6`
  - fallback_model: `nvidia/nemotron-3-super-120b-a12b:free`

## Fallback Logic

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

