"""KeywordSniper — finds high-value keywords that competitors missed.

Uses Serper autocomplete + SERP analysis to find keyword opportunities
without requiring a paid SEMrush API key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.serper import SerperClient

from config.settings import get_settings


@dataclass
class KeywordOpportunity:
    keyword: str
    search_volume_estimate: str  # "high", "medium", "low"
    competition: str  # "high", "medium", "low"
    current_rank: int | None
    opportunity_score: int  # 0-100


class KeywordSniper(Agent):
    """Finds keyword opportunities for DogsState.

    Strategy:
    1. Take seed keywords (e.g., "אוכל לכלבים", "צעצועים לחתולים")
    2. Expand via Google Autocomplete
    3. Check current ranking for each
    4. Score opportunities (high impressions + not ranking = gold)
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.KEYWORD_SNIPER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        seed_keywords = context.get("seed_keywords", [])

        if not seed_keywords:
            return AgentResult(
                success=False, role=self.role, errors=["No seed_keywords provided"]
            )

        serper = SerperClient(settings.seo.serper_api_key)
        try:
            all_opportunities: list[dict[str, Any]] = []

            for seed in seed_keywords:
                # Get autocomplete expansions
                suggestions = await serper.get_autocomplete(seed)
                self.log.info("autocomplete", seed=seed, suggestions=len(suggestions))

                for suggestion in suggestions[:10]:
                    # Check if we rank for this keyword
                    rank = await serper.find_rank(suggestion)

                    # Score the opportunity
                    score = self._score_opportunity(rank)

                    all_opportunities.append({
                        "keyword": suggestion,
                        "seed": seed,
                        "current_rank": rank,
                        "opportunity_score": score,
                    })

            # Sort by opportunity score
            all_opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "opportunities": all_opportunities,
                    "total_found": len(all_opportunities),
                    "top_10": all_opportunities[:10],
                },
                score=100,
            )
        finally:
            await serper.close()

    def _score_opportunity(self, current_rank: int | None) -> int:
        """Score a keyword opportunity.

        Not ranking at all = highest opportunity (100)
        Ranking 11-50 = medium (can improve to page 1)
        Ranking 1-3 = low priority (already winning)
        """
        if current_rank is None:
            return 100  # Not ranking — fresh opportunity
        if current_rank > 50:
            return 90
        if current_rank > 20:
            return 70
        if current_rank > 10:
            return 60  # Page 2 — push to page 1
        if current_rank > 3:
            return 40  # Page 1 but not top 3
        return 10  # Already top 3

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not context.get("seed_keywords"):
            errors.append("seed_keywords list is required")
        if not get_settings().seo.serper_api_key:
            errors.append("SERPER_API_KEY not configured")
        return errors
