"""CompetitorEye — monitors competitors (Zoolu, PetBest, etc.) in search results."""

from __future__ import annotations

from typing import Any

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.serper import SerperClient

COMPETITORS = [
    {"name": "Zoolu", "domain": "zoolu.co.il"},
    {"name": "PetBest", "domain": "petbest.co.il"},
    {"name": "PetShop", "domain": "petshop.co.il"},
    {"name": "AllForPet", "domain": "allforpet.co.il"},
]

TRACKED_KEYWORDS = [
    "אוכל לכלבים",
    "אוכל לחתולים",
    "צעצועים לכלבים",
    "מזון יבש לכלבים",
    "חטיפים לכלבים",
    "מיטה לכלב",
    "רתמה לכלב",
    "שמפו לכלבים",
    "חול לחתולים",
    "אביזרים לכלבים",
]


class CompetitorEye(Agent):
    """Tracks competitor rankings and identifies opportunities."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.COMPETITOR_EYE

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        keywords = context.get("keywords", TRACKED_KEYWORDS)
        competitors = context.get("competitors", COMPETITORS)

        serper = SerperClient(settings.seo.serper_api_key)

        try:
            analysis: list[dict[str, Any]] = []

            for keyword in keywords:
                serp_data = await serper.search(keyword, num=30)
                organic = serp_data.get("organic", [])

                keyword_result: dict[str, Any] = {
                    "keyword": keyword,
                    "dogsstate_rank": None,
                    "competitors": {},
                    "opportunity": "",
                }

                for i, result in enumerate(organic, 1):
                    link = result.get("link", "")

                    if "dogsstate.co.il" in link:
                        keyword_result["dogsstate_rank"] = i

                    for comp in competitors:
                        if comp["domain"] in link:
                            keyword_result["competitors"][comp["name"]] = i

                # Analyze opportunity
                our_rank = keyword_result["dogsstate_rank"]
                if our_rank is None:
                    keyword_result["opportunity"] = "NOT_RANKING — create content now"
                elif our_rank > 10:
                    keyword_result["opportunity"] = f"PAGE_2+ (rank {our_rank}) — optimize"
                elif our_rank > 3:
                    keyword_result["opportunity"] = f"PAGE_1 (rank {our_rank}) — push to top 3"
                else:
                    keyword_result["opportunity"] = f"TOP_3 (rank {our_rank}) — maintain"

                analysis.append(keyword_result)

            # Summary stats
            not_ranking = sum(1 for a in analysis if a["dogsstate_rank"] is None)
            page_one = sum(
                1 for a in analysis if a["dogsstate_rank"] and a["dogsstate_rank"] <= 10
            )

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "analysis": analysis,
                    "summary": {
                        "total_keywords": len(keywords),
                        "not_ranking": not_ranking,
                        "page_one": page_one,
                        "competitors_tracked": len(competitors),
                    },
                },
                score=100,
            )
        finally:
            await serper.close()

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not get_settings().seo.serper_api_key:
            errors.append("SERPER_API_KEY not configured")
        return errors
