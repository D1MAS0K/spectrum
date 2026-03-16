"""ContentFactory — generates long-form blog content (2000+ words) in Hebrew.

Creates SEO-optimized articles like:
- "מדריך מלא לבחירת אוכל לגורים"
- "10 צעצועים שכל כלב חייב"
- "איך לטפל בחתול בחורף"
"""

from __future__ import annotations

from typing import Any

import anthropic

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole

SYSTEM_PROMPT = """אתה כותב תוכן מקצועי לבלוג של DogsState — הסמכות #1 לחיות מחמד בישראל.

סגנון:
- עברית מושלמת, רהוטה, מדויקת
- גוף שני (אתה/את)
- טון: מומחה אבל נגיש, חם אבל מקצועי
- אורך: מינימום 2000 מילים

מבנה כל מאמר:
1. כותרת ראשית (H1) — כולל מילת מפתח
2. פתיח מרתק (150-200 מילים) — כולל את הבעיה/צורך
3. תוכן עניינים (Table of Contents)
4. 5-8 סעיפי H2 עם H3 משניים
5. תיבות המלצה/טיפ מעוצבות
6. טבלת השוואה (אם רלוונטי)
7. קטע FAQ (5-8 שאלות) עם Schema
8. סיכום + CTA לחנות
9. מקורות (אם רלוונטי)

SEO:
- מילת מפתח בכותרת, בפתיח, ב-H2, ובסיכום
- Internal linking לדפי מוצרים רלוונטיים באתר
- Alt text לכל תמונה (placeholder)
- Meta description של 155 תווים
"""


class ContentFactory(Agent):
    """Generates long-form blog articles for DogsState."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.CONTENT_FACTORY

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        topic = context.get("topic", "")
        target_keyword = context.get("target_keyword", topic)
        article_type = context.get("article_type", "guide")  # guide, listicle, comparison
        internal_links = context.get("internal_links", [])

        if not topic:
            return AgentResult(
                success=False, role=self.role, errors=["No topic provided"]
            )

        client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)

        prompt = self._build_prompt(topic, target_keyword, article_type, internal_links)

        try:
            response = await client.messages.create(
                model=settings.ai.content_model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            word_count = len(content.split())

            # Generate meta description
            meta_response = await client.messages.create(
                model=settings.ai.content_model,
                max_tokens=200,
                messages=[
                    {
                        "role": "user",
                        "content": f"כתוב meta description של בדיוק 155 תווים בעברית עבור מאמר בנושא: {topic}. מילת מפתח: {target_keyword}. רק את הטקסט, בלי גרשיים.",
                    }
                ],
            )
            meta_description = meta_response.content[0].text.strip()

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "html_content": content,
                    "meta_description": meta_description,
                    "yoast_title": f"{topic} | DogsState",
                    "focus_keyword": target_keyword,
                    "word_count": word_count,
                    "topic": topic,
                },
                score=100 if word_count >= 2000 else 60,
            )
        finally:
            await client.close()

    def _build_prompt(
        self,
        topic: str,
        target_keyword: str,
        article_type: str,
        internal_links: list[dict[str, str]],
    ) -> str:
        links_section = ""
        if internal_links:
            links_section = "\n\nקישורים פנימיים לשלב במאמר:\n"
            for link in internal_links:
                links_section += f"- [{link.get('text', '')}]({link.get('url', '')})\n"

        return f"""כתוב מאמר מסוג {article_type} בנושא:

נושא: {topic}
מילת מפתח: {target_keyword}
סוג: {article_type}

דרישות:
- מינימום 2000 מילים
- HTML מלא עם עיצוב (RTL)
- צבעי מותג: סגול (#6B2D8B), ירוק (#4CAF50)
- כלול תוכן עניינים עם עוגנים
- כלול FAQ Schema (application/ld+json)
- כלול טבלת השוואה אם רלוונטי
- כלול תיבות טיפ/המלצה
{links_section}"""

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not context.get("topic"):
            errors.append("topic is required")
        if not get_settings().ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY not configured")
        return errors
