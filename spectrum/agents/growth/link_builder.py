"""LinkBuilder — discovers and tracks backlink opportunities from Israeli sites."""

from __future__ import annotations

from typing import Any

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.serper import SerperClient


class LinkBuilder(Agent):
    """Finds backlink opportunities from relevant Israeli websites.

    Strategy:
    - Search for pet-related content on Israeli sites
    - Find blogs, forums, and directories that accept links
    - Track existing backlinks
    - Suggest outreach targets
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.LINK_BUILDER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        serper = SerperClient(settings.seo.serper_api_key)

        try:
            opportunities: list[dict[str, Any]] = []

            # Search for pet-related sites in Israel
            search_queries = [
                "בלוג חיות מחמד ישראל",
                "פורום כלבים ישראל",
                "מדריך חיות מחמד",
                "אתר וטרינר ישראל",
                "מגזין חיות מחמד",
            ]

            for query in search_queries:
                results = await serper.search(query, num=20)
                for result in results.get("organic", []):
                    link = result.get("link", "")
                    # Skip competitors and own site
                    if "dogsstate" in link:
                        continue
                    opportunities.append({
                        "url": link,
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "query": query,
                        "type": self._classify_opportunity(link, result),
                    })

            # Deduplicate by domain
            seen_domains: set[str] = set()
            unique_opps: list[dict[str, Any]] = []
            for opp in opportunities:
                domain = opp["url"].split("/")[2] if len(opp["url"].split("/")) > 2 else ""
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    unique_opps.append(opp)

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "opportunities": unique_opps,
                    "total_found": len(unique_opps),
                },
                score=100,
            )
        finally:
            await serper.close()

    def _classify_opportunity(self, url: str, result: dict[str, Any]) -> str:
        title = (result.get("title", "") + result.get("snippet", "")).lower()
        if "פורום" in title or "forum" in url:
            return "forum"
        if "בלוג" in title or "blog" in url:
            return "blog"
        if "וטרינר" in title or "vet" in url:
            return "veterinary"
        if "מדריך" in title:
            return "guide"
        return "general"

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not get_settings().seo.serper_api_key:
            errors.append("SERPER_API_KEY not configured")
        return errors
