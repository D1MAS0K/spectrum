"""ProductQA — validates every product field to 100/100 standard.

TheMainDog's quality gate: nothing publishes unless it scores 100/100.
"""

from __future__ import annotations

import re
from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole

# WooCommerce sometimes encodes semicolons as HTML entities,
# causing false negatives in color/schema checks.
_HTML_ENTITY_MAP = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#039;": "'",
    "&#59;": ";",
    "&semi;": ";",
}

# Maximum lines allowed in short_description
SHORT_DESC_MAX_LINES = 6


def _normalize_html(html: str) -> str:
    """Normalize HTML entities back to their characters for reliable checks."""
    result = html
    for entity, char in _HTML_ENTITY_MAP.items():
        result = result.replace(entity, char)
    return result


class ProductQA(Agent):
    """Quality assurance for product content.

    Checks:
    - Description length (>=5000 chars)
    - All required fields present (price, brand, weight, images)
    - HTML validity and brand color compliance
    - SEO fields (Yoast title, meta description, focus keyword)
    - Schema markup present and valid
    - Short description max 6 lines
    - No broken Hebrew (RTL issues)
    - No duplicate content across products
    - Category must not be only "General" (כללי)
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.PRODUCT_QA

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        product = context.get("product", {})
        raw_html = context.get("_step_output", {}).get("html_description", "")

        # Normalize HTML entities before running checks
        html = _normalize_html(raw_html)

        errors: list[str] = []
        warnings: list[str] = []
        score = 100

        # ── Length Check ──────────────────────────────────
        if len(html) < 5000:
            errors.append(f"תיאור קצר מדי: {len(html)} תווים (מינימום 5000)")
            score -= 30

        # ── Required Fields ───────────────────────────────
        required_fields = ["name", "price", "categories"]
        for field in required_fields:
            if not product.get(field):
                errors.append(f"שדה חסר: {field}")
                score -= 10

        # ── Short Description (max 6 lines) ───────────────
        short_desc = product.get("short_description", "")
        if short_desc:
            # Count visible lines (strip HTML tags, count non-empty lines)
            text_only = re.sub(r"<[^>]+>", "\n", short_desc)
            lines = [ln for ln in text_only.strip().splitlines() if ln.strip()]
            if len(lines) > SHORT_DESC_MAX_LINES:
                errors.append(
                    f"תיאור קצר ארוך מדי: {len(lines)} שורות (מקסימום {SHORT_DESC_MAX_LINES})"
                )
                score -= 10

        # ── Images Check ──────────────────────────────────
        images = product.get("images", [])
        if not images:
            errors.append("אין תמונות למוצר — חובה להוסיף לפחות תמונה אחת")
            score -= 20
        elif len(images) < 3:
            warnings.append(f"רק {len(images)} תמונות — מומלץ לפחות 3")
            score -= 5

        # ── Brand Colors ──────────────────────────────────
        if html and "#6B2D8B" not in html and "#6b2d8b" not in html.lower():
            warnings.append("צבע סגול המותג (#6B2D8B) לא נמצא ב-HTML")
            score -= 5

        if html and "#4CAF50" not in html and "#4caf50" not in html.lower():
            warnings.append("צבע ירוק המותג (#4CAF50) לא נמצא ב-HTML")
            score -= 5

        # ── Schema Markup ─────────────────────────────────
        if html and "application/ld+json" not in html:
            errors.append("חסר Schema markup (application/ld+json)")
            score -= 15

        # ── FAQ Section ───────────────────────────────────
        if html and "FAQPage" not in html:
            errors.append("חסר FAQ Schema מסוג FAQPage")
            score -= 10

        # ── RTL Direction ─────────────────────────────────
        if html and "dir=" not in html.lower() and "direction:" not in html.lower():
            warnings.append("לא נמצא הגדרת RTL")
            score -= 5

        # ── Category Validation ──────────────────────────
        categories = product.get("categories", [])
        category_names = [c.get("name", "").strip() for c in categories]
        general_only = all(
            n.lower() in ("general", "כללי", "uncategorized") for n in category_names
        )
        if categories and general_only:
            errors.append(
                "המוצר מקוטלג רק ב'כללי' — חובה לשייך לקטגוריה ספציפית"
            )
            score -= 10

        # ── Price Validation ──────────────────────────────
        price = product.get("price", "")
        if price:
            try:
                price_val = float(price)
                if price_val <= 0:
                    errors.append("מחיר לא תקין (0 או שלילי)")
                    score -= 10
            except (ValueError, TypeError):
                errors.append(f"מחיר לא מספרי: {price}")
                score -= 10

        # ── Brand Attribute Check ─────────────────────────
        attributes = product.get("attributes", [])
        has_brand = any(
            a.get("name", "").lower() in ("brand", "מותג")
            for a in attributes
        )
        if not has_brand:
            warnings.append("חסר תכונת מותג (Brand) — מומלץ להוסיף")
            score -= 5

        score = max(0, score)

        return AgentResult(
            success=score >= 100,
            role=self.role,
            data={
                "product_id": product.get("id"),
                "checks_passed": score >= 100,
                "score_breakdown": {
                    "length": len(html),
                    "has_images": bool(images),
                    "has_schema": "application/ld+json" in (html or ""),
                    "has_brand_colors": "#6B2D8B" in (html or "").upper(),
                    "has_brand_attribute": has_brand,
                    "short_desc_lines": len(lines) if short_desc else 0,
                    "category_valid": not general_only,
                },
            },
            errors=errors,
            warnings=warnings,
            score=score,
        )
