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
"""


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

        client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)

        prompt = self._build_prompt(product, context)

        try:
            response = await client.messages.create(
                model=settings.ai.content_model,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text

            # Extract generated sections
            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "html_description": content,
                    "product_id": product.get("id"),
                    "product_name": product.get("name"),
                    "char_count": len(content),
                },
                score=100 if len(content) >= 5000 else 70,
            )
        finally:
            await client.close()

    def _build_prompt(self, product: dict[str, Any], context: dict[str, Any]) -> str:
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
            correction_note = f"\n\nשים לב — בניסיון הקודם היו הבעיות הבאות, תקן אותן:\n"
            correction_note += "\n".join(f"- {e}" for e in previous_errors)

        return f"""כתוב תיאור מוצר מלא עבור:

שם המוצר: {name}
מחיר: ₪{price}
קטגוריות: {', '.join(categories)}
תכונות: {attributes}
תיאור נוכחי: {current_desc[:500] if current_desc else 'אין'}
תיאור קצר: {short_desc[:300] if short_desc else 'אין'}
מילת מפתח מרכזית: {target_keyword}

הנחיות:
- צור HTML מלא עם עיצוב בצבעי המותג
- כלול טבלת מפרט טכני
- כלול קטע FAQ עם לפחות 5 שאלות
- כלול Schema markup מסוג FAQPage
- מינימום 5,000 תווים
{correction_note}"""

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not context.get("product"):
            errors.append("product is required in context")
        settings = get_settings()
        if not settings.ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not configured")
        return errors
