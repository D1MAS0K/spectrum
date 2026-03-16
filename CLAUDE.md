# CLAUDE.md — Spectrum System Guide

## Project Overview

**Spectrum** is an AI-powered e-commerce automation platform built for **DogsState** (dogsstate.co.il) — Israel's #1 pet authority. It replaces and extends the "Claw" system with a professional, modular architecture.

**Goal:** Drive 100% organic traffic from Google and AI search engines (ChatGPT, Claude) through massive, high-quality content — zero ad spend.

## Architecture

Spectrum follows a 5-layer architecture:

```
CLI (spectrum/cli.py)
  -> Engine (spectrum/core/engine.py)     # Orchestrator
    -> Pipelines (spectrum/pipelines.py)  # Chained workflows with QA gates
      -> Agents (spectrum/agents/)        # 17 specialized AI agents
        -> Integrations (spectrum/integrations/)  # External API connectors
```

## Repository Structure

```
spectrum/
├── CLAUDE.md                          # This file
├── pyproject.toml                     # Project config, dependencies, scripts
├── .env.example                       # Environment variables template
├── .gitignore
├── config/
│   └── settings.py                    # Pydantic settings (loads .env)
├── spectrum/
│   ├── __init__.py
│   ├── cli.py                         # Typer CLI — all commands
│   ├── pipelines.py                   # Pre-built agent pipelines
│   ├── core/
│   │   ├── agent.py                   # Base Agent class, AgentRole enum, AgentResult
│   │   ├── engine.py                  # Central orchestrator
│   │   ├── pipeline.py               # Pipeline with QA gates (100/100 standard)
│   │   └── scheduler.py              # APScheduler wrapper for recurring tasks
│   ├── agents/
│   │   ├── product/
│   │   │   ├── rewriter.py           # AI product descriptions (5000+ chars)
│   │   │   ├── qa.py                 # Quality gate (100/100 or reject)
│   │   │   └── schema_guard.py       # JSON-LD structured data validation
│   │   ├── content/
│   │   │   ├── keyword_sniper.py     # Keyword research via Serper autocomplete
│   │   │   ├── content_factory.py    # Blog articles (2000+ words, Hebrew)
│   │   │   └── wp_publisher.py       # WordPress publishing with Yoast SEO
│   │   ├── intelligence/
│   │   │   ├── site_auditor.py       # Site health, PageSpeed, uptime
│   │   │   ├── competitor_eye.py     # Competitor SERP monitoring
│   │   │   └── rank_tracker.py       # Daily keyword position tracking
│   │   └── growth/
│   │       ├── link_builder.py       # Backlink opportunity discovery
│   │       ├── social_ops.py         # Facebook + Instagram posting
│   │       └── analytics_brain.py    # GA4 + GSC data analysis + AI insights
│   ├── integrations/
│   │   ├── wordpress.py              # WP REST API (posts, pages, media, Yoast)
│   │   ├── woocommerce.py            # WC REST API (products, orders, coupons)
│   │   ├── google_search_console.py  # GSC API (performance, indexing, sitemaps)
│   │   ├── google_analytics.py       # GA4 Data API (traffic, revenue, behavior)
│   │   ├── google_merchant.py        # Merchant Center (feeds, return policies)
│   │   ├── serper.py                 # Google SERP API (search, ranks, autocomplete)
│   │   └── social/
│   │       ├── facebook.py           # Facebook Graph API
│   │       └── instagram.py          # Instagram Graph API
│   ├── media/
│   │   ├── image_processor.py        # Image resize, optimize, alt text generation
│   │   └── gallery_manager.py        # Bulk upload, assign to products, audit
│   └── utils/
│       ├── logger.py                 # structlog configuration
│       └── notifications.py          # Telegram + WhatsApp alerts
└── tests/
```

## The 17 Agents (5 Divisions)

| Division | Agent | Role | Status vs Claw |
|----------|-------|------|----------------|
| **Product** | ProductRewriter | AI product descriptions (5000+ chars, brand colors, FAQ, Schema) | Improved |
| | ProductQA | Quality gate — 100/100 or reject | Improved |
| | SchemaGuard | JSON-LD validation and generation | Improved |
| **Content** | KeywordSniper | Keyword research via Serper autocomplete | Same |
| | ContentFactory | Blog articles (2000+ words Hebrew) | Improved |
| | WPPublisher | WordPress publishing with Yoast SEO | Same |
| **Intelligence** | SiteAuditor | Health checks, PageSpeed, snapshots | Improved |
| | CompetitorEye | Competitor SERP monitoring | Same |
| | RankTracker | Daily keyword position tracking | Same |
| **Growth** | LinkBuilder | Backlink opportunity discovery | Same |
| | SocialOps | Facebook + Instagram posting | **NEW** |
| | AnalyticsBrain | GA4 + GSC analysis + AI insights | **NEW** |
| **Media** | ImageProcessor | Image resize, optimize, alt text | **NEW** |
| | GalleryManager | Bulk upload, assign, audit missing | **NEW** |

## Claw Gaps Solved by Spectrum

| Gap in Claw | Spectrum Solution |
|-------------|-------------------|
| No image handling | `media/image_processor.py` + `gallery_manager.py` |
| No Google Search Console | `integrations/google_search_console.py` — full API |
| No Google Analytics (GA4) | `integrations/google_analytics.py` — traffic + revenue |
| No Google Merchant Center | `integrations/google_merchant.py` — return policies fix |
| No social media posting | `integrations/social/` + `agents/growth/social_ops.py` |
| No bulk operations | WooCommerce batch API (100 products per call) |
| No automated scheduling | `core/scheduler.py` — cron + interval jobs |
| Manual QA cycle | `core/pipeline.py` — automated QA gates with retry |

## Tech Stack

- **Language:** Python 3.11+
- **AI:** Anthropic Claude API (content + analysis)
- **HTTP:** httpx (async)
- **Config:** pydantic-settings (loads .env)
- **CLI:** Typer + Rich
- **Scheduling:** APScheduler
- **Images:** Pillow
- **Logging:** structlog
- **Linting:** Ruff
- **Types:** mypy (strict)
- **Tests:** pytest + pytest-asyncio

## CLI Commands

```bash
spectrum status              # Show configured integrations
spectrum audit               # Run site health audit
spectrum rewrite-product 123 # Rewrite product through full pipeline
spectrum write-article "topic" --keyword "kw" --publish
spectrum track-ranks kw1 kw2 kw3
spectrum competitors         # Competitor SERP analysis
spectrum upload-images /path/to/folder
spectrum find-missing-images # Products without images
spectrum report weekly       # Analytics report
spectrum post-social "topic" --platforms facebook instagram
spectrum daemon              # Start all scheduled tasks
```

## Development Workflow

### Setup
```bash
cp .env.example .env         # Fill in API keys
pip install -e ".[dev]"      # Install with dev dependencies
```

### Code Quality
```bash
ruff check .                 # Lint
ruff format .                # Format
mypy spectrum/               # Type check
pytest                       # Tests
```

### Branching
- Feature branches: `claude/<description>-<id>`
- Never push directly to `main`
- Commit messages: imperative mood, explain "why"

### Git Operations
- Push: `git push -u origin <branch-name>`
- On network failure: retry up to 4 times with exponential backoff (2s, 4s, 8s, 16s)

## Key Design Patterns

### Agent Pattern
Every agent extends `Agent` (in `core/agent.py`) and must implement:
- `role` property returning an `AgentRole` enum value
- `execute(context)` async method returning `AgentResult`
- Optional `validate(context)` for pre-flight checks

### Pipeline Pattern
Pipelines chain agents with QA gates. If a step scores below `required_score` (default 100), it retries up to `retry_count` times, feeding errors back for self-correction. This enforces TheMainDog's "100/100 or reject" standard automatically.

### Configuration
All config flows through `config/settings.py` which reads `.env`. Never hardcode API keys or URLs.

## Brand Guidelines (DogsState)
- Primary color: Purple `#6B2D8B`
- Secondary color: Green `#4CAF50`
- Language: Hebrew (RTL)
- Tone: Expert but warm, loves animals
- Product descriptions: 5000+ chars minimum
- Blog articles: 2000+ words minimum
- All content includes FAQ Schema markup

## AI Assistant Notes

- Read this file at the start of every session
- Always verify the current branch before making changes
- When adding a new agent, register it in `cli.py:_build_engine()`
- When adding a new integration, add its settings to `config/settings.py`
- All agents must return `AgentResult` with a score (0-100)
- Never publish content that scores below 100/100
- Update this CLAUDE.md when adding new agents or integrations
