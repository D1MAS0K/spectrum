"""Google Merchant Center API — product feed management and diagnostics.

CRITICAL GAP FIX: Claw couldn't touch Merchant Center.
Spectrum can manage product feeds, fix disapprovals, and update return policies.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = structlog.get_logger()

SCOPES = ["https://www.googleapis.com/auth/content"]


class MerchantCenterClient:
    """Google Merchant Center Content API client.

    Solves the 3,150 restricted products problem by:
    - Managing return policies programmatically
    - Fixing product feed issues (missing fields, policy violations)
    - Bulk-updating product data
    - Reading account diagnostics
    """

    def __init__(self, service_account_json: str, merchant_id: str) -> None:
        self.merchant_id = merchant_id
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json, scopes=SCOPES
        )
        self._service = build("content", "v2.1", credentials=credentials)
        self.log = logger.bind(integration="merchant_center")

    # ── Products ──────────────────────────────────────────

    def list_products(self, max_results: int = 250) -> list[dict[str, Any]]:
        """List all products in the Merchant Center feed."""
        products = []
        request = self._service.products().list(
            merchantId=self.merchant_id, maxResults=max_results
        )
        while request:
            response = request.execute()
            products.extend(response.get("resources", []))
            request = self._service.products().list_next(request, response)
        self.log.info("products_listed", count=len(products))
        return products

    def get_product(self, product_id: str) -> dict[str, Any]:
        return (
            self._service.products()
            .get(merchantId=self.merchant_id, productId=product_id)
            .execute()
        )

    def insert_product(self, product_data: dict[str, Any]) -> dict[str, Any]:
        """Insert/update a product in the feed."""
        result = (
            self._service.products()
            .insert(merchantId=self.merchant_id, body=product_data)
            .execute()
        )
        self.log.info("product_inserted", id=result.get("id"))
        return result

    def delete_product(self, product_id: str) -> None:
        self._service.products().delete(
            merchantId=self.merchant_id, productId=product_id
        ).execute()
        self.log.info("product_deleted", id=product_id)

    def batch_insert_products(self, products: list[dict[str, Any]]) -> dict[str, Any]:
        """Batch insert/update products (up to 10,000 per call)."""
        entries = [
            {"batchId": i, "merchantId": self.merchant_id, "method": "insert", "product": p}
            for i, p in enumerate(products)
        ]
        result = (
            self._service.products()
            .custombatch(body={"entries": entries})
            .execute()
        )
        self.log.info("batch_insert", count=len(products))
        return result

    # ── Product Statuses (Diagnostics) ────────────────────

    def list_product_statuses(self, max_results: int = 250) -> list[dict[str, Any]]:
        """Get approval/disapproval status for all products."""
        statuses = []
        request = self._service.productstatuses().list(
            merchantId=self.merchant_id, maxResults=max_results
        )
        while request:
            response = request.execute()
            statuses.extend(response.get("resources", []))
            request = self._service.productstatuses().list_next(request, response)
        return statuses

    def get_disapproved_products(self) -> list[dict[str, Any]]:
        """Find all products that are disapproved or have issues."""
        statuses = self.list_product_statuses()
        disapproved = []
        for status in statuses:
            issues = status.get("itemLevelIssues", [])
            if any(i.get("servability") == "disapproved" for i in issues):
                disapproved.append(status)
        self.log.info("disapproved_found", count=len(disapproved))
        return disapproved

    def get_restricted_products(self) -> list[dict[str, Any]]:
        """Find products restricted due to missing return policy or other issues."""
        statuses = self.list_product_statuses()
        restricted = []
        for status in statuses:
            issues = status.get("itemLevelIssues", [])
            if any("return" in i.get("description", "").lower() for i in issues):
                restricted.append(status)
        self.log.info("restricted_found", count=len(restricted))
        return restricted

    # ── Return Policies (fixes the 3,150 restricted products) ──

    def list_return_policies(self) -> list[dict[str, Any]]:
        response = (
            self._service.returnpolicy()
            .list(merchantId=self.merchant_id)
            .execute()
        )
        return response.get("resources", [])

    def create_return_policy(
        self,
        name: str,
        return_days: int = 14,
        policy_type: str = "lastReturnDate",
        country: str = "IL",
    ) -> dict[str, Any]:
        """Create a return policy — this is what's missing for your 3,150 products."""
        policy = {
            "name": name,
            "country": country,
            "policy": {
                "type": policy_type,
                "lastReturnDate": f"P{return_days}D",
            },
        }
        result = (
            self._service.returnpolicy()
            .insert(merchantId=self.merchant_id, body=policy)
            .execute()
        )
        self.log.info("return_policy_created", name=name, days=return_days)
        return result

    # ── Account Diagnostics ───────────────────────────────

    def get_account_status(self) -> dict[str, Any]:
        """Get overall account health and issues."""
        return (
            self._service.accountstatuses()
            .get(merchantId=self.merchant_id, accountId=self.merchant_id)
            .execute()
        )
