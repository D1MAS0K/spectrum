"""AnalyticsBrain — aggregates data from all sources and produces actionable insights.

The "TheBrain" equivalent from Claw, but now with actual data access (GA4, GSC, WooCommerce).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.google_analytics import GA4Client
from spectrum.integrations.google_search_console import SearchConsoleClient


class AnalyticsBrain(Agent):
    """Analyzes all data sources and produces strategic recommendations."""

    @property
    def role(self) -> AgentRole:
        return AgentRole.ANALYTICS_BRAIN

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        report_type = context.get("report_type", "weekly")

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if report_type == "daily":
            start = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
        elif report_type == "weekly":
            start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        else:
            start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")

        collected_data: dict[str, Any] = {"period": f"{start} to {today}"}

        # Collect GA4 data if available
        if settings.google.service_account_json and settings.ga4.property_id:
            ga4 = GA4Client(settings.google.service_account_json, settings.ga4.property_id)
            collected_data["traffic"] = ga4.get_traffic_overview(start, today)
            collected_data["traffic_sources"] = ga4.get_traffic_by_source(start, today)
            collected_data["top_pages"] = ga4.get_top_pages(start, today)
            collected_data["ecommerce"] = ga4.get_ecommerce_overview(start, today)
            collected_data["top_products"] = ga4.get_top_products(start, today)

        # Collect GSC data if available
        if settings.google.service_account_json and settings.google.search_console_site_url:
            gsc = SearchConsoleClient(
                settings.google.service_account_json,
                settings.google.search_console_site_url,
            )
            collected_data["search_queries"] = gsc.get_top_queries(start, today)
            collected_data["zero_click_pages"] = gsc.get_zero_click_pages(start, today)
            collected_data["low_ctr_queries"] = gsc.get_low_ctr_queries(start, today)

        # Generate AI analysis
        ai_client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)
        try:
            analysis = await ai_client.messages.create(
                model=settings.ai.qa_model,
                max_tokens=4000,
                system="אתה אנליסט דיגיטלי בכיר של DogsState. נתח את הנתונים ותן 5 המלצות אסטרטגיות קונקרטיות.",
                messages=[{
                    "role": "user",
                    "content": f"נתח את הנתונים הבאים ותן המלצות:\n\n{collected_data}",
                }],
            )
            recommendations = analysis.content[0].text
        finally:
            await ai_client.close()

        return AgentResult(
            success=True,
            role=self.role,
            data={
                "collected_data": collected_data,
                "recommendations": recommendations,
                "report_type": report_type,
            },
            score=100,
        )

    async def validate(self, context: dict[str, Any]) -> list[str]:
        errors = []
        if not get_settings().ai.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required for analysis")
        return errors
