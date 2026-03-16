"""Facebook Graph API client — page posts and insights."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class FacebookClient:
    """Facebook Graph API for page management.

    Capabilities (NEW — Claw couldn't do social):
    - Create posts (text, photo, link, video)
    - Schedule posts for future publication
    - Read page insights (reach, engagement)
    - Reply to comments
    - Manage page metadata
    """

    API_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, page_id: str, access_token: str) -> None:
        self.page_id = page_id
        self._client = httpx.AsyncClient(
            params={"access_token": access_token},
            timeout=30.0,
        )
        self.log = logger.bind(integration="facebook")

    async def close(self) -> None:
        await self._client.aclose()

    async def create_post(
        self,
        message: str,
        link: str = "",
        scheduled_time: int | None = None,
    ) -> dict[str, Any]:
        """Create or schedule a page post."""
        data: dict[str, Any] = {"message": message}
        if link:
            data["link"] = link
        if scheduled_time:
            data["scheduled_publish_time"] = scheduled_time
            data["published"] = False

        resp = await self._client.post(f"{self.API_URL}/{self.page_id}/feed", data=data)
        resp.raise_for_status()
        self.log.info("post_created", post_id=resp.json().get("id"))
        return resp.json()

    async def create_photo_post(
        self,
        image_url: str,
        caption: str = "",
    ) -> dict[str, Any]:
        """Post a photo to the page."""
        data: dict[str, Any] = {"url": image_url}
        if caption:
            data["caption"] = caption
        resp = await self._client.post(f"{self.API_URL}/{self.page_id}/photos", data=data)
        resp.raise_for_status()
        return resp.json()

    async def get_insights(
        self,
        metrics: list[str] | None = None,
        period: str = "day",
    ) -> dict[str, Any]:
        """Fetch page insights."""
        if metrics is None:
            metrics = [
                "page_impressions",
                "page_engaged_users",
                "page_post_engagements",
                "page_fans",
            ]
        resp = await self._client.get(
            f"{self.API_URL}/{self.page_id}/insights",
            params={"metric": ",".join(metrics), "period": period},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_posts(self, limit: int = 25) -> dict[str, Any]:
        resp = await self._client.get(
            f"{self.API_URL}/{self.page_id}/posts",
            params={"limit": limit, "fields": "message,created_time,shares,likes.summary(true)"},
        )
        resp.raise_for_status()
        return resp.json()

    async def reply_to_comment(self, comment_id: str, message: str) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self.API_URL}/{comment_id}/comments",
            data={"message": message},
        )
        resp.raise_for_status()
        return resp.json()
