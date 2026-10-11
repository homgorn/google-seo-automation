# AGENTS.md - Google SEO Automation Project Agent Routing

## Project Overview
This project automates Google Analytics 4, Google Tag Manager, Google Search Console, Google Ads, Microsoft Advertising, and AI Overviews optimization through a unified API layer with an internal LLM wiki and OpenChamber synchronization.

## Agent Routing

Delegate by task shape, not by habit:

- **Documentation research, API exploration, "where is X", "how does Y work"** → `explorer` (read-only, cheap model)
- **Running builds, test suites, noisy operations** → `runner` (read-only, cheap model; report only failures)
- **Before marking any feature done** → `verifier` (mandatory, read-only, proves feature works end-to-end)
- **Fan out independent opinions on one question** → `critic` x N in parallel (strong model)
- **Bulk mechanical edits across N files (migrations, schema updates)** → `migrator`, each in isolated copy
- **Complex multi-API workflows, integration debugging** → `implementer` (scoped writes)
- **OpenChamber session management, scheduling** → `orchestrator` (read-only coordination)

---

## Agent Definitions

### explorer
**Location:** `.opencode/agents/explorer.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free (cheap/fast)  
**Tools:** read, grep, glob, websearch, webfetch  
**Description:** Read-only codebase mapping and API documentation research. Answers "where is X", "how does Y work". Never writes files.

### runner
**Location:** `.opencode/agents/runner.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free (cheap/fast)  
**Tools:** shell, read, grep  
**Description:** Owns noisy output of builds, test suites, API bulk operations. Reports only failures and summary stats. Never implements fixes.

### verifier
**Location:** `.opencode/agents/verifier.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free  
**Tools:** read, grep, glob, shell, execute  
**Description:** **MANDATORY** - Proves a feature works end-to-end in the real environment before `passes: true`. Executes each step in `steps` literally as a user would. Never fixes anything - only reports verdict.

### critic
**Location:** `.opencode/agents/critic.md`  
**Model:** openrouter/anthropic/claude-3.5-sonnet (strong)  
**Tools:** read, grep, glob, websearch  
**Description:** Adversarial review - finds blind spots, challenges assumptions, stress-tests designs. Run multiple in parallel for independent opinions.

### migrator
**Location:** `.opencode/agents/migrator.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free  
**Tools:** read, edit, write, glob, shell  
**Description:** Bulk mechanical edits across N files (schema migrations, API version updates, bulk doc updates). Each runs in isolated worktree copy.

### implementer
**Location:** `.opencode/agents/implementer.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free  
**Tools:** read, write, edit, shell, execute, grep, glob  
**Description:** Makes the change for the current feature. Scoped writes only. Implements one feature at a time from feature_list.json.

### orchestrator
**Location:** `.opencode/agents/orchestrator.md`  
**Model:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free  
**Tools:** read, write, shell, openchamber  
**Description:** Coordinates OpenChamber sessions, schedules recurring tasks, manages bi-directional wiki sync. Read-only coordination.

---

## Subagent Invocation Rules

1. **Every feature requires verifier sign-off** before marking `passes: true`
2. **Explorer first** for any unknown API or codebase area
3. **Runner for test execution** - never run test suites in main thread
4. **Critic for design decisions** - before implementing complex integrations
5. **Migrator for bulk changes** - isolated copies mandatory
6. **Orchestrator for scheduling** - all recurring automations go through it

---

## OpenChamber Integration

### Session Structure
```
Project: google-seo-automation
├── Sessions (per feature)
│   ├── F001-wiki-documentation
│   ├── F002-wiki-database
│   ├── F003-ga4-automation
│   ├── F004-gtm-automation
│   ├── F005-gsc-automation
│   ├── F006-google-ads-automation
│   ├── F007-bing-ads-automation
│   ├── F008-ai-overviews-aeo
│   ├── F009-openchamber-sync
│   ├── F010-testing-framework
│   └── F011-runbooks
├── Scheduled Tasks (recurring)
│   ├── daily-ga4-reporting
│   ├── daily-gsc-indexing
│   ├── weekly-wiki-sync
│   ├── weekly-aeo-audit
│   ├── monthly-api-doc-refresh
│   └── quarterly-full-audit
└── Templates
    ├── api-integration-template
    ├── audit-template
    └── reporting-template
```

### Sync Protocol
- **Wiki → OpenChamber**: Push updated documentation as session context
- **OpenChamber → Wiki**: Pull decisions, audit findings, configuration changes
- **Bi-weekly full sync**: Complete wiki refresh from official API sources
- **Event-driven sync**: On API version changes, quota alerts, breaking changes

---

## MCP Servers Required

| Server | Purpose | Status |
|--------|---------|--------|
| hyper (Hyper MCP) | Google Ads, GA4, GTM, GSC, BigQuery via Hyper toolkit | Required |
| google-analytics | GA4 Data API, Admin API | Optional (via Hyper) |
| google-tag-manager | GTM API v2 | Optional (via Hyper) |
| google-search-console | Search Console API | Optional (via Hyper) |
| google-ads | Google Ads API v18 | Optional (via Hyper) |
| openchamber | Session management, scheduling | Required |
| filesystem | Local wiki/database operations | Built-in |

---

## Skill Profile (from skill-fit)

Active skills for this project:
- `seo-research-hyperfx` - SEO research and keyword analysis
- `seo-audit-mia` - Technical SEO auditing
- `analytics-insights-hyperfx` - GA4, GTM, GSC, BigQuery operations
- `google-ads-hyperfx` - Google Ads campaign management
- `programmatic-seo-alireza` - Programmatic SEO at scale
- `schema-markup-alireza` - Structured data implementation
- `site-architecture-alireza` - Site architecture and internal linking
- `aeo-alireza` - Answer Engine Optimization (AI citations)
- `deep-research-alireza` - Deep research methodology
- `universal-scraping-architect-alireza` - API documentation scraping
- `project-init-corey` - Project initialization
- `agent-fit-corey` - Agent generation
- `openclaw-mia` - OpenClaw/OpenChamber integration patterns

---

## Verification Checklist (per feature)

Before marking any feature `passes: true`, verifier must confirm:

- [ ] `init.sh` runs successfully and environment is up
- [ ] Each step in `steps` array executes literally as written
- [ ] For visual/interactive features: drove real app/UI, not unit test
- [ ] Evidence recorded for each step: pass/fail/blocked
- [ ] No steps skipped or assumed working
- [ ] Verdict format: `VERDICT: PASS | FAIL | BLOCKED` with per-step evidence

---

## Communication Protocol

- **Main thread**: High-level decisions, feature prioritization, architecture
- **Subagents**: Structured output only (verdict, evidence, findings)
- **No prose in subagent returns** - use declared output formats
- **Parallel fan-out**: Only for genuinely independent work
- **Isolated copies**: Mandatory when multiple agents write

---

## Guardrails

- Never overwrite existing agent files - extend or create sibling
- Never create more than 7 agents - if needed, decomposition is wrong
- If project already has agents, fit into them rather than replacing
- Report which roles created, which skipped, and why
- Never mark feature `passes: true` - only verifier may do that
- Never let init touch implementation files - scaffold only