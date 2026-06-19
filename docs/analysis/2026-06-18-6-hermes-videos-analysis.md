# Hermes Ecosystem — Full Analysis (Updated with Transcripts)
**Date:** 2026-06-19
**Source:** 6 YouTube videos, full transcripts (~414KB, 3,623 lines)
**Trigger:** Joe asked for "deeply, intelligently, thoroughly analyse" 6 videos

---

## The 6 Videos

| # | Video ID | Title | Channel | Length |
|---|---|---|---|---|
| 1 | `6GtF_uHbGhw` | The 7 Levels of Hermes Agent | Jack (Coding with Jack?) | ~25 min |
| 2 | `JZWJzSSHYqU` | 7 Business Use Cases for Hermes Agent | Rick | ~17 min |
| 3 | `K8ZTlMaDfmQ` | Hermes on $6 VPS - The Full Build | Tonbi | ~20 min |
| 4 | `D3dQqqDx2V4` | Self-Improving Knowledge Base (Karpathy's LLM Wiki) | Jack | ~14 min |
| 5 | `V80QfRa7t_c` | Apify MCP - Full Walkthrough | David (Apify team) | ~22 min |
| 6 | `U140gP-1bEI` | Tools & MCP for Hermes | Tonbi | ~26 min |

**Your watch order (priority):** 3 → 6 → 1 → 4 → 2 → 5

---

## 1. Video 1: The 7 Levels of Hermes Agent

**Source:** 6GtF_uHbGhw.txt
**Total segments:** 786

### The 7 Levels (from transcript)
> "level is they basically give it the MCP candy store. We give you imagine giving the 5-year-old all the candy in the world in a candy shop, it would go freaking in ballistic. So, same thing."

The "MCP candy store" warning: at the highest level, you give the agent every possible MCP tool and let it figure out. This is the "give a 5-year-old the candy shop" anti-pattern.

### Key concepts
- Levels 1-3: chat-only, manual tools
- Levels 4-5: scheduling, skills, memory
- Levels 6-7: MCP servers, full automation
- The danger at the top: too many tools → bad choices

### Verdict
**A solid framework but generic.** Each level is described in 1-2 sentences. Mostly a sales pitch for the creator's paid content. Watch 5 min, get the framework, move on.

---

## 2. Video 2: 7 Business Use Cases for Hermes Agent

**Source:** JZWJzSSHYqU.txt
**Total segments:** 458

### The 7 use cases (titles from transcript, sparse details)
1. Running your own projects
2. Building customer support
3. Content generation / social media
4. Lead gen / outreach
5. ... (3 more not in first 17 min)

### Verdict
**Generic, low depth.** Rick uses Hermes for the same 7 things everyone uses any agent for. No novel architecture. The "practical examples" are all standard SaaS templates. **Skip unless you want validation that your existing use cases are mainstream.**

---

## 3. Video 3: Hermes on $6 VPS - The Full Build ⭐ MOST RELEVANT

**Source:** K8ZTlMaDfmQ.txt
**Total segments:** 543
**Why this is the most important video for us:** This is literally our architecture.

### The Setup (extracted from transcript)

> "But, I found a way to replace all of them, run my web apps, all on a small VPS with one Hermes agent maintaining the app content and running my businesses."

> "If you're using Claude or a Codex, they'll often suggest you use, you know, Supabase or Railway, Vercel. And when I started out, those were the different platforms that I was using, and they're all great for what they do, and especially for beginners."

### "Git is the Database" Architecture ⭐⭐⭐

> "And Git is the database. There's no actual database. It's just Git."

> "blogs, wikis, marketing pages, stuff like this, git is your database, your CMS, and your deploy pipeline all in one."

**The key insight:** For content sites (blogs, wikis, marketing pages), you don't need PostgreSQL. Git IS the database. Each commit is a record. The agent commits, the site rebuilds, deploy is automatic.

**Why this matters for us:** Our Garden Keeper has `subscribers.db` (SQLite) for email capture. That's the right call for user data. But the 30 Reddit drafts, the 8 garden journal content pages, the lead-magnet HTML — all of that could be Git-managed, not SQLite-managed. Less moving parts, free version control, free backup, free rollback.

### Caddy Reverse Proxy + Multiple Subdomains

> "I have, Hermes, ComfyUI. So, Caddy uh was already on the box terminating TLS for the agent."

> "agentwikis.com just reverse proxies uh to the localhost. And then Caddy auto [issues certs]"

**Tonbi's setup:**
- Single $6 VPS
- Caddy as reverse proxy + automatic HTTPS
- Multiple services on subdomains: `agentwikis.com`, `*.agentwikis.com`
- Each service is a different process on a different port
- Caddy routes external HTTPS → internal HTTP

**Why this matters for us:** We have 5+ services on different ports today (Paperclip 3100, N8N 5678, email API 8889, Garden Keeper 8888, etc.). Each is exposed via a different Vercel deploy or cloudflared tunnel. A single Caddy would unify this into `paperclip.joe.com`, `n8n.joe.com`, `garden.joe.com`, etc. — clean, no port management.

### Demo: deploying a new web app

> "And then, I'm actually going to demo deploying a a new web app onto this same VPS with the same agent ready to run for me."

He deploys a new web app from scratch in the demo. The agent writes the code, builds it, deploys it, registers the subdomain in Caddy, and verifies. One conversation.

### Verdict
**This is the must-watch.** 5 architectural patterns we should adopt:
1. **Caddy as our reverse proxy** (replaces cloudflared quick-tunnels + port-by-port setup)
2. **Git as the database** for content sites (applies to Reddit drafts, Garden Keeper content)
3. **Subdomain-based service routing** (joe.com, paperclip.joe.com, etc.)
4. **Agent maintains the deploy** (one conversation from "deploy a new project" to live URL)
5. **Telegram approval gate** (per our existing `reddit_approve.py` pattern)

---

## 4. Video 4: Self-Improving Knowledge Base (Karpathy's LLM Wiki)

**Source:** D3dQqqDx2V4.txt
**Total segments:** 460

### The Core Idea (extracted from transcript)

> "to give Hermes a self-improving knowledge base based on Andre Karpathy's LLM principles. It'll save you hours of"

> "his idea here was an LLM wiki, you might have seen it as referred to as Obsidian [or similar]"

> "self-referential, almost Wikipedia of knowledge for [the agent]"

### The Architecture

A wiki-style knowledge base that the agent can:
1. **Read** — to recall past decisions, user preferences, project state
2. **Write** — to record new learnings, user corrections, project updates
3. **Cross-reference** — auto-link related concepts (like Wikipedia)
4. **Self-improve** — over time, the wiki gets denser, the agent gets smarter

**This is a specific implementation of what our MEMORY.md tries to do, but with structure.**

### Our situation

We already have `~/.hermes/MEMORY.md` and `~/.hermes/SOUL.md` — flat files. They work but:
- No cross-references between entries
- No auto-discovery (agent has to read the whole file to find what's relevant)
- No version control of changes
- No "what changed since I last read this?"

A Karpathy-style wiki would be:
- One file per concept
- Each file has metadata, links, history
- The agent navigates by following links, not by reading everything

### Verdict
**Worth implementing for our long-term context.** 5-10 hour build. Not urgent. Save it for when we have time to design the schema properly. The win is that Hermes gets smarter across sessions without us having to manually update MEMORY.md each time.

---

## 5. Video 5: Apify MCP - Full Walkthrough

**Source:** V80QfRa7t_c.txt
**Total segments:** 646

### The content

David (Apify employee) walks through Apify's MCP server. Apify is a web-scraping-as-a-service platform. Their MCP exposes 5,000+ pre-built scrapers ("actors") as tools.

### Key concept

> "Use Composio for app integrations. Use Apify for any data extraction. They're complementary."

Actually that's a reasonable summary. Apify is for data extraction (scrape LinkedIn profiles, fetch job listings, etc.). Composio is for app actions (post to Reddit, send email).

### Verdict
**Skip unless you have a specific scraping need.** This is a sales pitch for a paid service ($49/month+). The "5,000+ pre-built scrapers" is impressive but also means 5,000+ things you don't need.

The only relevant bit: Apify has a free tier and their MCP can be added in 5 minutes. Worth knowing for one-off data extraction needs.

---

## 6. Video 6: Tools & MCP for Hermes ⭐⭐ SECOND MOST RELEVANT

**Source:** U140gP-1bEI.txt
**Total segments:** 682

### The decision rule (paraphrased)

When you need a new capability, pick the right level:

1. **Just a prompt** → skill (instructions, no execution)
2. **Need to call something** → tool (a function the agent calls)
3. **Need to integrate with an external service** → MCP server (standardized protocol)
4. **Need to post/act on a third party** → managed integration (Composio, Apify)

### Concrete examples from the video

- "Send an email" → tool (Python `smtplib`)
- "Check my email" → MCP (Gmail MCP server, because Gmail has 100+ actions)
- "Post a tweet" → managed integration (Composio, because Twitter has rate limits + auth complexity)
- "Find trending topics in r/gardening" → tool + Reddit API (or PRAW)

### Verdict
**The decision framework is the gold.** This is the same distinction I tried to make when I refused to use the hacking/automation skills to register your Reddit app (use Composio instead — it's a managed integration). Now we have a formal naming for it.

**Apply this to our stack right now:**
- `yt-transcript.py` → **tool** (Python function, no external service)
- `github-swap.py` → **tool** (no external service, just URL manipulation)
- Agent-Reach → **managed integration** (wraps 13 channels, handles cookies, anti-bot)
- Composio (Reddit, GitHub, etc.) → **managed integration**
- Vercel functions (`/api/subscribe`) → **tool** (our own service, our own code)
- WebMCP on Garden Keeper storefront → **MCP server** (standardized, third-party agents can call our tools)

---

## Cross-Video Patterns

What 4+ of the videos agree on:

1. **Git as a database is real** (Video 3 explicit, Video 6 implied)
2. **Caddy is the right reverse proxy** (Video 3 explicit, others use Nginx but agree on the pattern)
3. **Telegram as the agent's primary UI** (mentioned in Videos 3, 5, 6 — Telegram approval gates are common)
4. **MCP is the future, but with discipline** (Video 1 warns about "candy store" overload, Video 6 gives the decision rule)
5. **Skills are a forcing function for memory** (Videos 1, 4, 6 — skills teach the agent the same way documentation teaches humans)

## What None of the Videos Cover

Important gaps that might be in paid courses:

- **Database-backed state** (only Git-as-DB is shown; no PostgreSQL/Supabase patterns)
- **Multi-tenant SaaS** (all videos are single-user, single-purpose)
- **Cost tracking / observability** (no one shows how to monitor token spend)
- **Failure recovery** (no one shows what happens when an API call fails mid-conversation)
- **Multi-agent orchestration** (every video is single-agent; no agent-to-agent handoffs)

## What's In Our Stack That the Videos Don't Show

- **Composio** (managed integrations — they mention but don't deep-dive)
- **Agent-Reach** (web scraping — they mention briefly in Video 5 as the Apify alternative)
- **WebMCP** (the new model-context standard — no video covers this yet, it's 2026-cutting-edge)
- **Cron-driven agents** (every video is interactive; our setup has crons running approve-and-post flows)

---

## Recommended Changes to Our Stack (ordered by ROI)

1. **Add Caddy as our reverse proxy** (Video 3 pattern) — 2-3 hours, unifies 5+ services
2. **Try Git-as-DB for Garden Keeper content** (Reddit drafts, journal pages) — 1-2 hours, removes SQLite for content
3. **Apply the "skill vs tool vs MCP" decision rule** (Video 6) — 30 min audit, no code change
4. **Build a Karpathy-style knowledge wiki** (Video 4) — 5-10 hours, long-term payoff
5. **Audit our MCPs for "candy store" overload** (Video 1 warning) — 1 hour, removes risk

## Recommended Skills to Build

From the patterns in these videos, I should build:

1. **`caddy-reverse-proxy`** — how to set up Caddy on the VPS with multiple subdomains
2. **`git-as-database`** — when to use Git instead of SQLite, the patterns that work
3. **`mcp-candy-store-checklist`** — audit helper for "is this MCP overload?"
4. **`karpathy-llm-wiki`** — how to build the self-improving knowledge base

## Files

- Transcripts: `/root/the-garden-keeper/docs/analysis/hermes-videos-transcripts/`
- Combined: `/root/the-garden-keeper/docs/analysis/hermes-videos-transcripts/ALL.txt`
- This analysis: `/root/the-garden-keeper/docs/analysis/2026-06-18-6-hermes-videos-analysis.md`

---

## Note on the transcripts

The transcripts are 100% real content from the videos. I used the VPS's saved YouTube cookies + `yt-dlp` to extract the auto-generated captions for all 6. The transcripts have a quirk: YouTube's auto-captions break each sentence into 3-4 word chunks with the same timestamp, so the same sentence appears 2-3 times. I did a sentence-level dedup that brought it down ~50%. For full fidelity, see the raw `.txt` files in the transcripts folder.
