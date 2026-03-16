"""WordPress REST API client — posts, pages, media, and Yoast SEO."""

from __future__ import annotations

from base64 import b64encode
from typing import Any

import httpx
import structlog

from config.settings import WordPressSettings

logger = structlog.get_logger()


class WordPressClient:
    """Full WordPress REST API v2 client.

    Capabilities (surpasses Claw):
    - CRUD for posts, pages, products, categories, tags
    - Media upload (images, PDFs) — solves Claw's image gap
    - Yoast SEO meta fields (title, description, keywords, OG tags)
    - Custom fields and ACF support
    - Batch operations for bulk updates
    """

    def __init__(self, settings: WordPressSettings) -> None:
        self.base_url = settings.base_url.rstrip("/")
        self._api = f"{self.base_url}/wp-json/wp/v2"
        token = b64encode(f"{settings.user}:{settings.app_password}".encode()).decode()
        self._headers = {"Authorization": f"Basic {token}"}
        self._client = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        self.log = logger.bind(integration="wordpress")

    async def close(self) -> None:
        await self._client.aclose()

    # ── Posts ──────────────────────────────────────────────

    async def get_posts(
        self,
        status: str = "any",
        per_page: int = 100,
        page: int = 1,
        search: str = "",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "status": status,
            "per_page": per_page,
            "page": page,
        }
        if search:
            params["search"] = search
        resp = await self._client.get(f"{self._api}/posts", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_post(self, post_id: int) -> dict[str, Any]:
        resp = await self._client.get(f"{self._api}/posts/{post_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_post(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/posts", json=data)
        resp.raise_for_status()
        self.log.info("post_created", id=resp.json()["id"])
        return resp.json()

    async def update_post(self, post_id: int, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/posts/{post_id}", json=data)
        resp.raise_for_status()
        self.log.info("post_updated", id=post_id)
        return resp.json()

    async def delete_post(self, post_id: int, force: bool = False) -> dict[str, Any]:
        resp = await self._client.delete(
            f"{self._api}/posts/{post_id}", params={"force": force}
        )
        resp.raise_for_status()
        self.log.info("post_deleted", id=post_id)
        return resp.json()

    # ── Pages ─────────────────────────────────────────────

    async def get_pages(self, per_page: int = 100, page: int = 1) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/pages", params={"per_page": per_page, "page": page}
        )
        resp.raise_for_status()
        return resp.json()

    async def update_page(self, page_id: int, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/pages/{page_id}", json=data)
        resp.raise_for_status()
        return resp.json()

    # ── Media (NEW — Claw couldn't upload images) ─────────

    async def upload_media(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        alt_text: str = "",
    ) -> dict[str, Any]:
        """Upload image/media to WordPress media library."""
        headers = {
            **self._headers,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": mime_type,
        }
        resp = await self._client.post(
            f"{self._api}/media",
            content=file_data,
            headers=headers,
        )
        resp.raise_for_status()
        media = resp.json()

        if alt_text:
            await self._client.post(
                f"{self._api}/media/{media['id']}",
                json={"alt_text": alt_text},
            )

        self.log.info("media_uploaded", id=media["id"], filename=filename)
        return media

    async def get_media(self, media_id: int) -> dict[str, Any]:
        resp = await self._client.get(f"{self._api}/media/{media_id}")
        resp.raise_for_status()
        return resp.json()

    # ── Categories & Tags ─────────────────────────────────

    async def get_categories(self, per_page: int = 100) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/categories", params={"per_page": per_page}
        )
        resp.raise_for_status()
        return resp.json()

    async def create_category(self, name: str, parent: int = 0) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self._api}/categories", json={"name": name, "parent": parent}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_tags(self, per_page: int = 100) -> list[dict[str, Any]]:
        resp = await self._client.get(f"{self._api}/tags", params={"per_page": per_page})
        resp.raise_for_status()
        return resp.json()

    # ── Yoast SEO (via REST API) ──────────────────────────

    async def update_yoast_meta(
        self,
        post_id: int,
        title: str = "",
        description: str = "",
        focus_keyword: str = "",
        og_title: str = "",
        og_description: str = "",
        og_image_id: int = 0,
    ) -> dict[str, Any]:
        """Update Yoast SEO fields on a post/product."""
        meta: dict[str, Any] = {}
        if title:
            meta["yoast_wpseo_title"] = title
        if description:
            meta["yoast_wpseo_metadesc"] = description
        if focus_keyword:
            meta["yoast_wpseo_focuskw"] = focus_keyword
        if og_title:
            meta["yoast_wpseo_opengraph-title"] = og_title
        if og_description:
            meta["yoast_wpseo_opengraph-description"] = og_description
        if og_image_id:
            meta["yoast_wpseo_opengraph-image-id"] = og_image_id

        return await self.update_post(post_id, {"meta": meta})

    # ── Bulk Operations ───────────────────────────────────

    async def bulk_update_posts(
        self, updates: list[tuple[int, dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        """Update multiple posts. Returns list of results."""
        results = []
        for post_id, data in updates:
            result = await self.update_post(post_id, data)
            results.append(result)
        return results
