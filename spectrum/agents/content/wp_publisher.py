"""WPPublisher — publishes content to WordPress without breaking the design."""

from __future__ import annotations

from typing import Any

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.wordpress import WordPressClient


class WPPublisher(Agent):
    """Publishes posts/products to WordPress via REST API.

    Handles:
    - Creating/updating posts with full HTML
    - Setting Yoast SEO fields
    - Assigning categories and tags
    - Setting featured images
    - Publishing or saving as draft
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.WP_PUBLISHER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        wp = WordPressClient(settings.wp)

        content_data = context.get("_step_output", {})
        publish_mode = context.get("publish_mode", "draft")  # "draft" or "publish"
        post_type = context.get("post_type", "post")  # "post" or "product"

        try:
            post_data: dict[str, Any] = {
                "title": content_data.get("yoast_title", content_data.get("topic", "")),
                "content": content_data.get("html_content", content_data.get("html_description", "")),
                "status": publish_mode,
            }

            # Set categories if provided
            categories = context.get("categories", [])
            if categories:
                post_data["categories"] = categories

            # Set tags
            tags = context.get("tags", [])
            if tags:
                post_data["tags"] = tags

            # Set featured image
            featured_image_id = context.get("featured_image_id")
            if featured_image_id:
                post_data["featured_media"] = featured_image_id

            # Create or update
            post_id = context.get("post_id")
            if post_id:
                result = await wp.update_post(post_id, post_data)
            else:
                result = await wp.create_post(post_data)
                post_id = result["id"]

            # Set Yoast SEO fields
            focus_keyword = content_data.get("focus_keyword", "")
            meta_desc = content_data.get("meta_description", "")
            if focus_keyword or meta_desc:
                await wp.update_yoast_meta(
                    post_id,
                    title=content_data.get("yoast_title", ""),
                    description=meta_desc,
                    focus_keyword=focus_keyword,
                )

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "post_id": post_id,
                    "status": publish_mode,
                    "url": result.get("link", ""),
                },
                score=100,
            )
        finally:
            await wp.close()

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        settings = get_settings()
        if not settings.wp.app_password:
            errors.append("WP_APP_PASSWORD not configured")
        if not context.get("_step_output"):
            errors.append("No content to publish (_step_output is empty)")
        return errors
