"""Google Search Console API — indexing, performance, and sitemap management.

THIS IS A CRITICAL GAP FIX: Claw had no GSC access.
Spectrum connects directly to GSC API for:
- Performance data (clicks, impressions, CTR, position)
- URL inspection (is a page indexed?)
- Sitemap submission
- Index request for new pages
"""

from __future__ import annotations

from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/webmasters"]


class SearchConsoleClient:
    """Google Search Console API client.

    Solves Claw's biggest blind spot: no visibility into what Google sees.
    """

    def __init__(self, service_account_json: str, site_url: str) -> None:
        self.site_url = site_url
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json, scopes=SCOPES
        )
        self._service = build("searchconsole", "v1", credentials=credentials)
        self.log = logger.bind(integration="gsc")

    # ── Performance Data ──────────────────────────────────

    def get_performance(
        self,
        start_date: str,
        end_date: str,
        dimensions: list[str] | None = None,
        row_limit: int = 1000,
        dimension_filter_groups: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Query search performance (clicks, impressions, CTR, position).

        dimensions: ["query", "page", "country", "device", "date"]
        """
        if dimensions is None:
            dimensions = ["query", "page"]

        body: dict[str, Any] = {
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": dimensions,
            "rowLimit": row_limit,
        }
        if dimension_filter_groups:
            body["dimensionFilterGroups"] = dimension_filter_groups

        response = (
            self._service.searchanalytics()
            .query(siteUrl=self.site_url, body=body)
            .execute()
        )
        rows = response.get("rows", [])
        self.log.info("performance_fetched", rows=len(rows))
        return rows

    def get_top_queries(
        self, start_date: str, end_date: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get top search queries by clicks."""
        return self.get_performance(
            start_date, end_date, dimensions=["query"], row_limit=limit
        )

    def get_page_performance(
        self, page_url: str, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """Get performance data for a specific page."""
        return self.get_performance(
            start_date,
            end_date,
            dimensions=["query"],
            dimension_filter_groups=[
                {
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "equals",
                            "expression": page_url,
                        }
                    ]
                }
            ],
        )

    # ── URL Inspection ────────────────────────────────────

    def inspect_url(self, url: str) -> dict[str, Any]:
        """Check if a URL is indexed, has errors, or needs attention."""
        body = {"inspectionUrl": url, "siteUrl": self.site_url}
        result = self._service.urlInspection().index().inspect(body=body).execute()
        inspection = result.get("inspectionResult", {})
        self.log.info(
            "url_inspected",
            url=url,
            verdict=inspection.get("indexStatusResult", {}).get("verdict"),
        )
        return inspection

    def request_indexing(self, url: str) -> dict[str, Any]:
        """Request Google to (re-)index a URL.

        Note: Uses URL Inspection API — limited to ~200 requests/day.
        """
        body = {"inspectionUrl": url, "siteUrl": self.site_url}
        result = self._service.urlInspection().index().inspect(body=body).execute()
        self.log.info("indexing_requested", url=url)
        return result

    # ── Sitemaps ──────────────────────────────────────────

    def list_sitemaps(self) -> list[dict[str, Any]]:
        response = self._service.sitemaps().list(siteUrl=self.site_url).execute()
        return response.get("sitemap", [])

    def submit_sitemap(self, sitemap_url: str) -> None:
        """Submit a sitemap to Google."""
        self._service.sitemaps().submit(
            siteUrl=self.site_url, feedpath=sitemap_url
        ).execute()
        self.log.info("sitemap_submitted", url=sitemap_url)

    # ── Analytics Helpers ─────────────────────────────────

    def get_zero_click_pages(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Find pages with impressions but zero clicks — optimization targets."""
        rows = self.get_performance(
            start_date, end_date, dimensions=["page"], row_limit=500
        )
        return [r for r in rows if r.get("clicks", 0) == 0 and r.get("impressions", 0) > 10]

    def get_low_ctr_queries(
        self, start_date: str, end_date: str, ctr_threshold: float = 0.02
    ) -> list[dict[str, Any]]:
        """Find queries with high impressions but low CTR — title/meta optimization targets."""
        rows = self.get_performance(
            start_date, end_date, dimensions=["query"], row_limit=500
        )
        return [
            r
            for r in rows
            if r.get("ctr", 0) < ctr_threshold and r.get("impressions", 0) > 50
        ]
