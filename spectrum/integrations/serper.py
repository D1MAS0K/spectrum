"""Serper.dev API client — Google SERP data for rank tracking and keyword research."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


class SerperClient:
    """Google SERP API via Serper.dev.

    Used by:
    - RankTracker: daily position monitoring
    - KeywordSniper: competitor keyword discovery
    - CompetitorEye: SERP analysis
    """

    API_URL = "https://google.serper.dev"

    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=20.0,
        )
        self.log = logger.bind(integration="serper")

    async def close(self) -> None:
        await self._client.aclose()

    async def search(
        self,
        query: str,
        gl: str = "il",
        hl: str = "he",
        num: int = 30,
    ) -> dict[str, Any]:
        """Run a Google search and return organic results."""
        resp = await self._client.post(
            f"{self.API_URL}/search",
            json={"q": query, "gl": gl, "hl": hl, "num": num},
        )
        resp.raise_for_status()
        return resp.json()

    async def search_news(self, query: str, gl: str = "il", hl: str = "he") -> dict[str, Any]:
        resp = await self._client.post(
            f"{self.API_URL}/news",
            json={"q": query, "gl": gl, "hl": hl},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_autocomplete(self, query: str, gl: str = "il", hl: str = "he") -> list[str]:
        """Get Google autocomplete suggestions — great for long-tail keywords."""
        resp = await self._client.post(
            f"{self.API_URL}/autocomplete",
            json={"q": query, "gl": gl, "hl": hl},
        )
        resp.raise_for_status()
        data = resp.json()
        return [s["value"] for s in data.get("suggestions", [])]

    async def find_rank(
        self,
        keyword: str,
        target_domain: str = "dogsstate.co.il",
        num: int = 100,
    ) -> int | None:
        """Find the ranking position of target_domain for a keyword.

        Returns position (1-based) or None if not found in top `num` results.
        """
        results = await self.search(keyword, num=num)
        for i, result in enumerate(results.get("organic", []), start=1):
            if target_domain in result.get("link", ""):
                return i
        return None

    async def bulk_rank_check(
        self,
        keywords: list[str],
        target_domain: str = "dogsstate.co.il",
    ) -> dict[str, int | None]:
        """Check rankings for multiple keywords."""
        rankings: dict[str, int | None] = {}
        for kw in keywords:
            rankings[kw] = await self.find_rank(kw, target_domain)
            self.log.info("rank_checked", keyword=kw, position=rankings[kw])
        return rankings
