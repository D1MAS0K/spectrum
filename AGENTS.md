# AGENTS.md — Spectrum Operational Instructions

> הלוגיקה היומית המדויקת. סדר פעולות, כללי עיבוד, ותזמון.

## Operational Pipeline (סדר פעולות מוגדר)

```
1. Pull 3 products from WooCommerce API
2. Rewrite each product (HTML purple, Yoast, Attributes)
3. Execute PUT to update product
4. Execute GET to verify update was saved
5. Wait 30 seconds between batches (anti-throttle)
6. Log results and move to next batch
```

## Batch Processing Rules

| Parameter | Value | Reason |
|-----------|-------|--------|
| Batch size | 3 products | Prevents WooCommerce rate limiting |
| Delay between batches | 30 seconds | Anti-throttle protection |
| Verification | GET after every PUT | Prevents false-positive "success" |
| Retry on failure | Up to 3 times | With exponential backoff |

## The 13 Agents — Full Army Architecture (מרץ 2026: GOD LEVEL)

### Division 1: Product (מוצר)

| Agent # | Name | Role | Key Logic |
|---------|------|------|-----------|
| 1 | **ProductRewriter** | AI product descriptions | 5000+ chars, HTML purple, 7-part Gold Standard |
| 2 | **ProductQA** | Quality gate + visual testing | Playwright automation, 100/100 or reject |
| 3 | **SchemaGuard** | JSON-LD validation | Product + FAQ + Review schemas |

**Agent 1 — ProductRewriter Flow:**
```
Input: Raw WooCommerce product data
  → Build Strategy Card (audience, problem, USP)
  → Write Short Description (6 lines max, purple HTML)
  → Write Long Description (5000+ chars, 7 sections)
  → Generate FAQ (4+ questions targeting PAA)
  → Generate Schema markup (JSON-LD)
  → Set Yoast SEO fields (focus keyword + synonyms)
  → Assign categories (remove from "General")
  → Assign brand attribute
Output: AgentResult with score 0-100
```

**Agent 2 — ProductQA Flow:**
```
Input: Rewritten product data
  → Validate character count (5000+ long, 6 lines short)
  → Validate HTML structure (purple headers, bullets)
  → Validate Schema markup (JSON-LD valid)
  → Validate Yoast fields (keyword + synonyms present)
  → Validate categories (not in "General")
  → Validate brand attribute (assigned)
  → Visual test with Playwright (optional)
Output: Score 100/100 → pass, <100 → reject + feedback for retry
```

### Division 2: Content (תוכן)

| Agent # | Name | Role | Key Logic |
|---------|------|------|-----------|
| 4 | **KeywordSniper** | Keyword research | SEMrush + Serper autocomplete, Hebrew focus |
| 5 | **ContentFactory** | Blog article writing | 2000+ words, Hebrew, SEO-optimized |
| 6 | **WPPublisher** | WordPress publishing | Yoast SEO, categories, featured image |

**Content Pipeline:**
```
Agent 4 finds keyword → Agent 5 writes article → Agent 6 publishes to WordPress
```

### Division 3: Intelligence (מודיעין)

| Agent # | Name | Role | Key Logic |
|---------|------|------|-----------|
| 7 | **SiteAuditor** | Site health monitoring | PageSpeed, uptime, broken links |
| 8 | **CompetitorEye** | Competitor tracking | Monitors Zooloo + PetBest SERP positions |
| 9 | **RankTracker** | Keyword rank tracking | Daily position monitoring |

### Division 4: Growth (צמיחה)

| Agent # | Name | Role | Key Logic |
|---------|------|------|-----------|
| 10 | **LinkBuilder** | Backlink building | Israeli directories, niche sites |
| 11 | **SocialOps** | Social media posting | Facebook + Instagram automation |

## Agent Registration

When adding a new agent:
1. Create agent file in appropriate division directory
2. Extend `Agent` base class from `core/agent.py`
3. Implement `role`, `execute(context)`, and optionally `validate(context)`
4. Register in `cli.py:_build_engine()`
5. Add to pipeline in `pipelines.py` if part of a chain
6. Update this file with agent details

## Pipeline Assembly Logic

The system works as a **production line (פס ייצור)**, not a single monolithic AI:

```
Product Pipeline:
  KeywordSniper → ProductRewriter → SchemaGuard → ProductQA → [WooCommerce PUT]

Content Pipeline:
  KeywordSniper → ContentFactory → WPPublisher → [WordPress POST]

Intelligence Pipeline:
  SiteAuditor → CompetitorEye → RankTracker → [Report Generation]

Growth Pipeline:
  LinkBuilder → SocialOps → [External POST requests]
```

Each station (agent) receives input from the previous station, processes it, and passes output to the next. If any station returns a score below 100, the item is sent back for correction.

## Yoast SEO Field Handling

Critical fields to set via WooCommerce API:
- `yoast_head_json` — parsed for validation
- `meta_data` with keys:
  - `_yoast_wpseo_focuskw` — Primary focus keyword (Hebrew)
  - `_yoast_wpseo_keywordsynonyms` — Synonyms (Hebrew + English brand name)
  - `_yoast_wpseo_metadesc` — Meta description (Hebrew, 150-160 chars)
  - `_yoast_wpseo_title` — SEO title with brand

## WooCommerce Attribute Logic (Brand Assignment)

```
1. GET /wp-json/wc/v3/products/attributes → Find brand attribute ID
2. GET /wp-json/wc/v3/products/attributes/{id}/terms → Find specific brand term
3. If brand term doesn't exist → POST to create it
4. PUT /wp-json/wc/v3/products/{id} → Assign brand attribute with term ID
```

## HTML Encoding Note

WooCommerce API automatically removes semicolons (`;`) from inline HTML style tags:
- Input: `<span style="color: #6B2D8B;">`
- Output: `<span style="color: #6B2D8B">`

This is expected behavior. QA validation must account for this to prevent false negatives.
