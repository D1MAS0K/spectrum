"""RankTracker — daily position tracking for target keywords.

Combines Serper SERP data with GSC performance data for complete visibility.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.serper import SerperClient


class RankTracker(Agent):
    """Tracks daily search rankings for DogsState keywords."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.RANK_TRACKER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        keywords = context.get("keywords", [])

        if not keywords:
            return AgentResult(
                success=False, role=self.role, errors=["No keywords to track"]
            )

        serper = SerperClient(settings.seo.serper_api_key)

        try:
            rankings = await serper.bulk_rank_check(keywords)

            # Build tracking data
            tracking_data = {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "rankings": [
                    {"keyword": kw, "position": pos, "status": self._classify(pos)}
                    for kw, pos in rankings.items()
                ],
            }

            # Save to data dir
            data_dir = settings.system.data_dir / "rankings"
            data_dir.mkdir(parents=True, exist_ok=True)
            filepath = data_dir / f"ranks_{tracking_data['date']}.json"
            filepath.write_text(json.dumps(tracking_data, indent=2, ensure_ascii=False))

            # Summary
            total = len(rankings)
            top3 = sum(1 for p in rankings.values() if p and p <= 3)
            page1 = sum(1 for p in rankings.values() if p and p <= 10)
            not_found = sum(1 for p in rankings.values() if p is None)

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "rankings": tracking_data["rankings"],
                    "summary": {
                        "total": total,
                        "top_3": top3,
                        "page_1": page1,
                        "not_ranking": not_found,
                    },
                    "saved_to": str(filepath),
                },
                score=100,
            )
        finally:
            await serper.close()

    def _classify(self, position: int | None) -> str:
        if position is None:
            return "NOT_FOUND"
        if position <= 3:
            return "TOP_3"
        if position <= 10:
            return "PAGE_1"
        if position <= 20:
            return "PAGE_2"
        return "PAGE_3+"

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not context.get("keywords"):
            errors.append("keywords list is required")
        if not get_settings().seo.serper_api_key:
            errors.append("SERPER_API_KEY not configured")
        return errors
