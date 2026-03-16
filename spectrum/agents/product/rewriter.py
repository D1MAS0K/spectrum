"""ProductRewriter — writes premium product descriptions with sales psychology and SEO.

Replaces Claw's ProductRewriter with:
- Structured prompt engineering via Anthropic Claude API
- Brand-consistent HTML output (purple #6B2D8B + green #4CAF50)
- Automatic FAQ generation
- Comparison tables
- Hebrew RTL formatting
"""

from __future__ import annotations

from typing import Any

import anthropic

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole

SYSTEM_PROMPT = """אתה כותב תוכן מוצרים מקצועי לחנות חיות מחמד פרימיום בישראל — DogsState.
אתה כותב בעברית מושלמת, ברמת מומחה.

כללים:
1. כל תיאור מוצר חייב להיות לפחות 5,000 תווים
2. חובה לכלול: סקירה כללית, יתרונות מרכזיים, למי זה מתאים, טבלת מפרט, שאלות נפוצות (FAQ)
3. השתמש ב-HTML מעוצב עם צבעי המותג: סגול (#6B2D8B) וירוק (#4CAF50)
4. כתוב בגוף שני ("אתה תרגיש", "הכלב שלך יאהב")
5. שלב מילות מפתח באופן טבעי — לא keyword stuffing
6. כל FAQ חייב לכלול Schema markup (application/ld+json)
7. RTL direction בכל האלמנטים
8. התיאור הקצר (short_description) — מקסימום 6 שורות, תמציתי ומכירתי
9. אם המוצר מקוטלג רק ב"כללי" — הצע קטגוריה ספציפית מתאימה
"""

# Categories that should be replaced with specific ones
GENERAL_CATEGORIES = {"general", "כללי", "uncategorized"}


class ProductRewriter(Agent):
    """Rewrites WooCommerce product descriptions to Gold Standard."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.PRODUCT_REWRITER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        product = context.get("product", {})

        if not product:
            return AgentResult(
                success=False, role=self.role, errors=["No product provided in context"]
            )

        # Flag products stuck in "General" category
        categories = product.get("categories", [])
        needs_recategorization = all(
            c.get("name", "").strip().lower() in GENERAL_CATEGORIES
            for c in categories
        ) if categories else False

        client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)

        prompt = self._build_prompt(product, context, needs_recategorization)

        try:
            response = await client.messages.create(
                model=settings.ai.content_model,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text

            # Generate Yoast keyword synonyms from product context
            target_kw = context.get("target_keyword", product.get("name", ""))
            yoast_synonyms = self._generate_keyword_synonyms(
                product, target_kw
            )

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "html_description": content,
                    "product_id": product.get("id"),
                    "product_name": product.get("name"),
                    "char_count": len(content),
                    "needs_recategorization": needs_recategorization,
                    "yoast_keyword_synonyms": yoast_synonyms,
                },
                score=100 if len(content) >= 5000 else 70,
            )
        finally:
            await client.close()

    def _build_prompt(
        self,
        product: dict[str, Any],
        context: dict[str, Any],
        needs_recategorization: bool = False,
    ) -> str:
        name = product.get("name", "")
        current_desc = product.get("description", "")
        short_desc = product.get("short_description", "")
        price = product.get("price", "")
        categories = [c.get("name", "") for c in product.get("categories", [])]
        attributes = product.get("attributes", [])
        target_keyword = context.get("target_keyword", name)

        # If we have errors from a previous attempt, include them for self-correction
        previous_errors = context.get("_previous_errors", [])
        correction_note = ""
        if previous_errors:
            correction_note = "\n\nשים לב — בניסיון הקודם היו הבעיות הבאות, תקן אותן:\n"
            correction_note += "\n".join(f"- {e}" for e in previous_errors)

        recategorization_note = ""
        if needs_recategorization:
            recategorization_note = (
                "\n\nהמוצר מקוטלג כרגע רק ב'כללי'. "
                "בתגובתך, הוסף שורה: SUGGESTED_CATEGORY: <קטגוריה מוצעת>"
            )

        return f"""כתוב תיאור מוצר מלא עבור:

שם המוצר: {name}
מחיר: ₪{price}
קטגוריות: {', '.join(categories)}
תכונות: {attributes}
תיאור נוכחי: {current_desc[:500] if current_desc else 'אין'}
תיאור קצר (מקסימום 6 שורות): {short_desc[:300] if short_desc else 'אין'}
מילת מפתח מרכזית: {target_keyword}

הנחיות:
- צור HTML מלא עם עיצוב בצבעי המותג
- כלול טבלת מפרט טכני
- כלול קטע FAQ עם לפחות 5 שאלות
- כלול Schema markup מסוג FAQPage
- מינימום 5,000 תווים
- התיאור הקצר חייב להיות עד 6 שורות בלבד
{correction_note}{recategorization_note}"""

    def _generate_keyword_synonyms(
        self, product: dict[str, Any], target_keyword: str
    ) -> str:
        """Generate Yoast-compatible keyword synonyms.

        Yoast SEO stores synonyms as a comma-separated string in
        the `_yoast_wpseo_keywordsynonyms` meta field. This builds
        that string from product attributes and name variants.
        """
        synonyms: list[str] = []

        # Brand + product type
        brand = ""
        for attr in product.get("attributes", []):
            if attr.get("name", "").lower() in ("brand", "מותג"):
                options = attr.get("options", [])
                if options:
                    brand = options[0]
                    break

        name = product.get("name", "")
        if brand and brand.lower() not in target_keyword.lower():
            synonyms.append(f"{brand} {name}")

        # Without brand if target has brand
        if brand and brand.lower() in target_keyword.lower():
            no_brand = target_keyword.lower().replace(brand.lower(), "").strip()
            if no_brand:
                synonyms.append(no_brand)

        # Category-based synonym
        categories = [c.get("name", "") for c in product.get("categories", [])]
        for cat in categories:
            if cat.lower() not in GENERAL_CATEGORIES and cat not in synonyms:
                synonyms.append(f"{cat} {name}" if cat.lower() not in name.lower() else cat)

        # Deduplicate and limit
        seen: set[str] = set()
        unique: list[str] = []
        for s in synonyms:
            if s.lower() not in seen and s.lower() != target_keyword.lower():
                seen.add(s.lower())
                unique.append(s)

        return ",".join(unique[:5])

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not context.get("product"):
            errors.append("product is required in context")
        settings = get_settings()
        if not settings.ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not configured")
        return errors
