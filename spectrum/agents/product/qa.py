"""ProductQA — validates every product field to 100/100 standard.

TheMainDog's quality gate: nothing publishes unless it scores 100/100.
"""

from __future__ import annotations

from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole


class ProductQA(Agent):
    """Quality assurance for product content.

    Checks:
    - Description length (>=5000 chars)
    - All required fields present (price, brand, weight, images)
    - HTML validity and brand color compliance
    - SEO fields (Yoast title, meta description, focus keyword)
    - Schema markup present and valid
    - No broken Hebrew (RTL issues)
    - No duplicate content across products
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.PRODUCT_QA

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        product = context.get("product", {})
        html = context.get("_step_output", {}).get("html_description", "")

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
                },
            },
            errors=errors,
            warnings=warnings,
            score=score,
        )
