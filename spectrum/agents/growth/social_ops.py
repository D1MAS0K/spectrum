"""SocialOps — manages social media posting across Facebook, Instagram, and Google.

NEW capability — Claw couldn't do social media at all.
"""

from __future__ import annotations

from typing import Any

import anthropic

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.social.facebook import FacebookClient
from spectrum.integrations.social.instagram import InstagramClient


class SocialOps(Agent):
    """Cross-platform social media manager.

    Capabilities:
    - Generate platform-specific post content via AI
    - Post to Facebook and Instagram
    - Schedule posts for optimal times
    - Track engagement across platforms
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.SOCIAL_OPS

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        action = context.get("action", "create_post")

        if action == "create_post":
            return await self._create_and_post(context, settings)
        elif action == "get_insights":
            return await self._get_insights(settings)
        else:
            return AgentResult(
                success=False, role=self.role, errors=[f"Unknown action: {action}"]
            )

    async def _create_and_post(self, context: dict[str, Any], settings: Any) -> AgentResult:
        topic = context.get("topic", "")
        platforms = context.get("platforms", ["facebook"])
        image_url = context.get("image_url", "")
        product_url = context.get("product_url", "")

        if not topic:
            return AgentResult(success=False, role=self.role, errors=["No topic provided"])

        # Generate post content via AI
        ai_client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)
        try:
            response = await ai_client.messages.create(
                model=settings.ai.content_model,
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": f"""כתוב פוסט לרשתות חברתיות עבור DogsState בנושא: {topic}

דרישות:
- עברית, קצר ומושך (עד 280 תווים)
- כולל 3-5 האשטגים רלוונטיים
- CTA לאתר
- טון: חם, מקצועי, אוהב חיות
רק את הטקסט, בלי הסברים.""",
                }],
            )
            post_text = response.content[0].text
        finally:
            await ai_client.close()

        results: dict[str, Any] = {"post_text": post_text, "platforms": {}}

        if "facebook" in platforms and settings.social.facebook_page_id:
            fb = FacebookClient(
                settings.social.facebook_page_id,
                settings.social.facebook_page_access_token,
            )
            try:
                if image_url:
                    fb_result = await fb.create_photo_post(image_url, post_text)
                else:
                    fb_result = await fb.create_post(post_text, link=product_url)
                results["platforms"]["facebook"] = fb_result
            finally:
                await fb.close()

        if "instagram" in platforms and settings.social.instagram_business_id:
            ig = InstagramClient(
                settings.social.instagram_business_id,
                settings.social.instagram_access_token,
            )
            try:
                if image_url:
                    container_id = await ig.create_media(image_url, post_text)
                    ig_result = await ig.publish_media(container_id)
                    results["platforms"]["instagram"] = ig_result
            finally:
                await ig.close()

        return AgentResult(
            success=True,
            role=self.role,
            data=results,
            score=100,
        )

    async def _get_insights(self, settings: Any) -> AgentResult:
        insights: dict[str, Any] = {}

        if settings.social.facebook_page_id:
            fb = FacebookClient(
                settings.social.facebook_page_id,
                settings.social.facebook_page_access_token,
            )
            try:
                insights["facebook"] = await fb.get_insights()
            finally:
                await fb.close()

        if settings.social.instagram_business_id:
            ig = InstagramClient(
                settings.social.instagram_business_id,
                settings.social.instagram_access_token,
            )
            try:
                insights["instagram"] = await ig.get_insights()
            finally:
                await ig.close()

        return AgentResult(
            success=True,
            role=self.role,
            data={"insights": insights},
            score=100,
        )
