"""Instagram Graph API client — business account management."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class InstagramClient:
    """Instagram Graph API for business accounts.

    Capabilities (NEW — Claw couldn't do Instagram):
    - Create photo/carousel/reel posts
    - Read profile insights
    - Get media performance data
    - Reply to comments
    """

    API_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, business_id: str, access_token: str) -> None:
        self.business_id = business_id
        self._client = httpx.AsyncClient(
            params={"access_token": access_token},
            timeout=30.0,
        )
        self.log = logger.bind(integration="instagram")

    async def close(self) -> None:
        await self._client.aclose()

    async def create_media(
        self,
        image_url: str,
        caption: str = "",
        is_carousel_item: bool = False,
    ) -> str:
        """Step 1: Create a media container. Returns container ID."""
        data: dict[str, Any] = {"image_url": image_url}
        if caption:
            data["caption"] = caption
        if is_carousel_item:
            data["is_carousel_item"] = True

        resp = await self._client.post(
            f"{self.API_URL}/{self.business_id}/media", data=data
        )
        resp.raise_for_status()
        return resp.json()["id"]

    async def publish_media(self, creation_id: str) -> dict[str, Any]:
        """Step 2: Publish a media container."""
        resp = await self._client.post(
            f"{self.API_URL}/{self.business_id}/media_publish",
            data={"creation_id": creation_id},
        )
        resp.raise_for_status()
        self.log.info("media_published", media_id=resp.json()["id"])
        return resp.json()

    async def create_carousel(
        self,
        image_urls: list[str],
        caption: str = "",
    ) -> dict[str, Any]:
        """Create a carousel post from multiple images."""
        children_ids = []
        for url in image_urls:
            container_id = await self.create_media(url, is_carousel_item=True)
            children_ids.append(container_id)

        resp = await self._client.post(
            f"{self.API_URL}/{self.business_id}/media",
            data={
                "media_type": "CAROUSEL",
                "caption": caption,
                "children": ",".join(children_ids),
            },
        )
        resp.raise_for_status()
        carousel_id = resp.json()["id"]
        return await self.publish_media(carousel_id)

    async def get_insights(
        self,
        metrics: list[str] | None = None,
        period: str = "day",
    ) -> dict[str, Any]:
        if metrics is None:
            metrics = ["impressions", "reach", "profile_views", "follower_count"]
        resp = await self._client.get(
            f"{self.API_URL}/{self.business_id}/insights",
            params={"metric": ",".join(metrics), "period": period},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_media_list(self, limit: int = 25) -> dict[str, Any]:
        resp = await self._client.get(
            f"{self.API_URL}/{self.business_id}/media",
            params={"limit": limit, "fields": "caption,media_type,timestamp,like_count,comments_count"},
        )
        resp.raise_for_status()
        return resp.json()
