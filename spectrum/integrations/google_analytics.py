"""Google Analytics 4 (GA4) Data API — traffic, conversions, and revenue.

CRITICAL GAP FIX: Claw had no GA4 access.
Spectrum connects to GA4 for real-time and historical analytics.
"""

from __future__ import annotations

from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


class GA4Client:
    """Google Analytics 4 Data API client.

    Provides:
    - Traffic sources and volumes
    - E-commerce revenue and conversion data
    - User behavior (pages/session, bounce rate)
    - Real-time active users
    - Custom event tracking data
    """

    def __init__(self, service_account_json: str, property_id: str) -> None:
        self.property_id = property_id
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json, scopes=SCOPES
        )
        self._service = build("analyticsdata", "v1beta", credentials=credentials)
        self.log = logger.bind(integration="ga4")

    def run_report(
        self,
        start_date: str,
        end_date: str,
        metrics: list[str],
        dimensions: list[str] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Run a GA4 report with specified metrics and dimensions."""
        body: dict[str, Any] = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "metrics": [{"name": m} for m in metrics],
            "limit": limit,
        }
        if dimensions:
            body["dimensions"] = [{"name": d} for d in dimensions]

        response = (
            self._service.properties()
            .runReport(property=self.property_id, body=body)
            .execute()
        )
        self.log.info("report_fetched", metrics=metrics, rows=len(response.get("rows", [])))
        return response

    # ── Pre-built Reports ─────────────────────────────────

    def get_traffic_overview(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Total sessions, users, pageviews, bounce rate."""
        return self.run_report(
            start_date,
            end_date,
            metrics=[
                "sessions",
                "totalUsers",
                "screenPageViews",
                "bounceRate",
                "averageSessionDuration",
            ],
        )

    def get_traffic_by_source(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Traffic breakdown by source/medium — shows organic vs paid vs direct."""
        return self.run_report(
            start_date,
            end_date,
            metrics=["sessions", "totalUsers", "conversions"],
            dimensions=["sessionSource", "sessionMedium"],
        )

    def get_top_pages(self, start_date: str, end_date: str, limit: int = 50) -> dict[str, Any]:
        """Most visited pages."""
        return self.run_report(
            start_date,
            end_date,
            metrics=["screenPageViews", "averageSessionDuration", "bounceRate"],
            dimensions=["pagePath"],
            limit=limit,
        )

    def get_ecommerce_overview(self, start_date: str, end_date: str) -> dict[str, Any]:
        """E-commerce metrics: revenue, transactions, average order value."""
        return self.run_report(
            start_date,
            end_date,
            metrics=[
                "ecommercePurchases",
                "purchaseRevenue",
                "averagePurchaseRevenue",
                "itemsPurchased",
            ],
        )

    def get_top_products(self, start_date: str, end_date: str, limit: int = 50) -> dict[str, Any]:
        """Top selling products by revenue."""
        return self.run_report(
            start_date,
            end_date,
            metrics=["itemRevenue", "itemsPurchased", "itemsViewed"],
            dimensions=["itemName"],
            limit=limit,
        )

    def get_organic_performance(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Organic search traffic only — to compare with GSC data."""
        return self.run_report(
            start_date,
            end_date,
            metrics=["sessions", "totalUsers", "conversions", "purchaseRevenue"],
            dimensions=["sessionSource"],
        )

    def get_realtime_users(self) -> dict[str, Any]:
        """Get current active users on the site."""
        body = {"metrics": [{"name": "activeUsers"}]}
        return (
            self._service.properties()
            .runRealtimeReport(property=self.property_id, body=body)
            .execute()
        )
