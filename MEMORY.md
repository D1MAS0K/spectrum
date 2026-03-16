# MEMORY.md — Spectrum Long-Term Memory

> נטען בכל תחילת סשן. מכיל את ההקשר העסקי, פרטי החנות, ומילון המותגים.

## Business Context

**Company:** DogsState (דוגס סטייט)
**URL:** dogsstate.co.il
**Position:** Israel's #1 Pet Authority
**Strategy:** 100% organic traffic — zero ad spend
**Target:** Google + AI search engines (ChatGPT, Claude)

## Brand Identity

- **Primary Color:** Purple `#6B2D8B`
- **Secondary Color:** Green `#4CAF50`
- **Language:** Hebrew (RTL)
- **Tone:** Expert but warm, loves animals
- **Voice:** Professional authority with empathy

## Brand Dictionary (מילון מותגים)

| Brand | Hebrew Name | Category | Notes |
|-------|-------------|----------|-------|
| Acana | אקאנה | מזון יבש פרימיום | קנדי, חלבון גבוה |
| N&D (Farmina) | אן אנד די | מזון טבעי | ללא דגנים, איטלקי |
| Royal Canin | רויאל קנין | מזון וטרינרי | גזעים ספציפיים |
| Hill's | היל'ס | מזון רפואי | Science Diet / Prescription |
| Orijen | אוריג'ן | מזון ביולוגי | חלבון 85%+ |
| Pro Plan | פרו פלאן | מזון מקצועי | Purina premium line |
| Brit | בריט | מזון צ'כי | יחס מחיר-ערך |
| Taste of the Wild | טייסט אוף דה ווילד | מזון טבעי | בשרות אקזוטיות |

## Gold Standard — מוצר מושלם (7 חלקים)

כל מוצר שעובר אופטימיזציה חייב לכלול את 7 החלקים הבאים:

### 1. Strategy Card (כרטיס אסטרטגיה)
- קהל יעד מוגדר (גזע, גודל, גיל, בעיה)
- בעיה מרכזית (אלרגיה, נשירה, עיכול, השמנה)
- מילת מפתח ראשית + מילים נרדפות
- USP (Unique Selling Proposition) של המוצר

### 2. Short Description (תיאור קצר — Above the Fold)
- HTML סגול (`#6B2D8B`) עם בולטים
- **מקסימום 6 שורות**
- משפט אחד בודד לכל בולט
- מטרה: המרה מיידית → "הוסף לסל" ללא גלילה
- פסיכולוגיית קריאה מהירה

### 3. Long Description (תיאור ארוך — SEO זנב ארוך)
- **5,000+ תווים מינימום**
- כולל H2/H3 headers מותאמים ל-SEO
- פסקאות קריאות עם מילות מפתח טבעיות

### 4. Benefits Table (טבלת יתרונות)
- טבלה ויזואלית ברורה
- יתרונות מרכזיים של המוצר
- השוואה למוצרים מתחרים (כשרלוונטי)

### 5. Trust Box (תיבת אמון)
- "למה לקנות ב-Dogs State?"
- משלוח חינם / מהיר
- שירות לקוחות מקצועי
- אחריות + החלפות

### 6. FAQ Accordion (שאלות נפוצות)
- מינימום 4 שאלות
- ממוקדות ב-Google "People Also Ask"
- תשובות קצרות וענייניות
- כולל Schema markup (FAQPage)

### 7. Schema Markup (JSON-LD)
- Product Schema
- FAQ Schema
- Review/AggregateRating (כשזמין)
- BreadcrumbList
- Brand + Offer structured data

## Content Standards

| Type | Minimum Length | Quality Gate |
|------|---------------|-------------|
| Product Description (Long) | 5,000+ chars | 100/100 or reject |
| Product Description (Short) | 3-6 lines | 100/100 or reject |
| Blog Article | 2,000+ words | 100/100 or reject |
| FAQ per product | 4+ questions | Must target PAA |
| Schema markup | Full JSON-LD | Valid via Google Rich Results Test |

## Category Hierarchy

Products must be assigned to specific categories — **never left in "General" (כללי).**

Required assignments per product:
1. **Animal type** (כלב / חתול / ציפור / דג / etc.)
2. **Product type** (מזון יבש / מזון רטוב / חטיפים / ציוד / etc.)
3. **Sub-category** (גזע / גודל / גיל / צורך מיוחד)
4. **Brand** (via WooCommerce Attributes)

## SEO Priorities

1. **Hebrew keyword optimization** — primary + synonyms
2. **URL slugs** — English only, lowercase, hyphens
3. **Yoast SEO** — Focus keyword + synonyms (Hebrew + English)
4. **Internal linking** — Between related products and blog posts
5. **Schema markup** — Every product, every article
6. **Image alt text** — Descriptive Hebrew text with keywords
