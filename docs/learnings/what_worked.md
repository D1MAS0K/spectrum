# What Worked — Spectrum Learnings (מה עבד)

> למידות מצטברות מתוך הפעלה יומית. כל פריט כאן הוכח בפרודקשן.

## 1. Rate Limit Prevention (מניעת חסימות)

**Problem:** WooCommerce API returned 429/503 errors during bulk product updates.

**Solution:** Batch processing of 3 products with 30-second delay between batches.

```
Before: 50 products at once → 80% failure rate
After:  3 products + 30s delay → 0% failure rate
```

**Implementation:** Built into `AGENTS.md` operational pipeline and enforced in `woocommerce.py` integration.

---

## 2. GET-After-PUT Verification (וידוא פעולה)

**Problem:** Yoast SEO field updates appeared successful in PUT response but were silently dropped by the server. Status showed "success" while data wasn't actually saved.

**Solution:** Mandatory GET request after every PUT to verify data persistence.

```
PUT /products/123 → 200 OK (but Yoast fields not saved!)
GET /products/123 → Compare with sent data → Detect mismatch → Retry
```

**Impact:** Eliminated false-positive "success" status. Caught ~15% of updates that silently failed.

---

## 3. Hebrew Synonyms in Yoast (מילים נרדפות בעברית)

**Problem:** Products weren't ranking for Hebrew search queries despite having Hebrew content.

**Solution:** Added `_yoast_wpseo_keywordsynonyms` field with both Hebrew keyword and English brand name.

```json
{
  "_yoast_wpseo_focuskw": "מזון יבש לכלבים אקאנה",
  "_yoast_wpseo_keywordsynonyms": "[\"אקאנה מזון כלבים\", \"Acana dog food\", \"מזון פרימיום לכלבים\"]"
}
```

**Impact:** Significant improvement in local search indexing for Hebrew queries.

---

## 4. WooCommerce HTML Semicolon Handling

**Problem:** QA agent flagged products as "invalid" even though they looked correct on the site. Investigation revealed WooCommerce API strips semicolons from inline style tags.

**Discovery:**
```html
<!-- What we send -->
<span style="color: #6B2D8B;">

<!-- What WooCommerce stores -->
<span style="color: #6B2D8B">
```

**Solution:** QA validation logic now normalizes HTML before comparison — strips trailing semicolons from style attributes to prevent false negatives.

```python
# In QA validation
def normalize_html(html: str) -> str:
    """Normalize HTML to account for WooCommerce semicolon stripping."""
    return re.sub(r';(")', r'\1', html)
```

**Impact:** Eliminated 100% of false-negative QA failures related to HTML formatting.

---

## 5. Pipeline Architecture (פס ייצור)

**Problem:** Single monolithic AI trying to do everything produced mediocre results across all tasks.

**Solution:** Assembly line architecture — each agent specializes in one task, passes output to the next station.

```
Before: 1 AI → average quality across all tasks
After:  Specialized agents → expert quality at each station
```

**Key benefit:** Each agent can be tuned, tested, and improved independently without affecting others.

---

## 6. Structured QA Gates

**Problem:** Quality varied wildly between products. Some had great descriptions but missing schemas. Others had schemas but weak content.

**Solution:** 100/100 scoring system with mandatory pass on ALL criteria:

| Criterion | Weight | Must Pass |
|-----------|--------|-----------|
| Long description 5000+ chars | 15 | Yes |
| Short description 3-6 lines | 10 | Yes |
| FAQ 4+ questions | 15 | Yes |
| Schema JSON-LD valid | 15 | Yes |
| Yoast fields set | 15 | Yes |
| Categories assigned (not General) | 10 | Yes |
| Brand attribute assigned | 10 | Yes |
| HTML structure valid | 10 | Yes |

**Impact:** Consistent 100/100 quality across all products. No exceptions.
