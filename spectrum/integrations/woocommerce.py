"""WooCommerce REST API client — products, orders, coupons."""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from httpx import DigestAuth

from config.settings import WooCommerceSettings, WordPressSettings

logger = structlog.get_logger()


class WooCommerceClient:
    """Full WooCommerce REST API v3 client.

    Handles all product operations that Claw does, plus:
    - Batch product operations (create/update/delete up to 100 at once)
    - Variation management for variable products
    - Order reading for analytics
    - Coupon management
    - Shipping class management
    - Product review management
    """

    def __init__(self, wp: WordPressSettings, wc: WooCommerceSettings) -> None:
        self.base_url = wp.base_url.rstrip("/")
        self._api = f"{self.base_url}/wp-json/wc/v3"
        self._auth = (wc.consumer_key, wc.consumer_secret)
        self._client = httpx.AsyncClient(
            auth=self._auth,
            timeout=30.0,
        )
        self.log = logger.bind(integration="woocommerce")

    async def close(self) -> None:
        await self._client.aclose()

    # ── Products ──────────────────────────────────────────

    async def get_products(
        self,
        status: str = "any",
        per_page: int = 100,
        page: int = 1,
        category: int | None = None,
        search: str = "",
        orderby: str = "date",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "status": status,
            "per_page": per_page,
            "page": page,
            "orderby": orderby,
        }
        if category:
            params["category"] = str(category)
        if search:
            params["search"] = search
        resp = await self._client.get(f"{self._api}/products", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_product(self, product_id: int) -> dict[str, Any]:
        resp = await self._client.get(f"{self._api}/products/{product_id}")
        resp.raise_for_status()
        return resp.json()

    async def create_product(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/products", json=data)
        resp.raise_for_status()
        self.log.info("product_created", id=resp.json()["id"])
        return resp.json()

    async def update_product(self, product_id: int, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.put(f"{self._api}/products/{product_id}", json=data)
        resp.raise_for_status()
        self.log.info("product_updated", id=product_id)
        return resp.json()

    async def delete_product(self, product_id: int, force: bool = False) -> dict[str, Any]:
        resp = await self._client.delete(
            f"{self._api}/products/{product_id}", params={"force": force}
        )
        resp.raise_for_status()
        self.log.info("product_deleted", id=product_id)
        return resp.json()

    # ── Batch Operations (Claw does one-by-one; Spectrum does 100 at once) ──

    async def batch_products(
        self,
        create: list[dict[str, Any]] | None = None,
        update: list[dict[str, Any]] | None = None,
        delete: list[int] | None = None,
    ) -> dict[str, Any]:
        """Batch create/update/delete up to 100 products per call."""
        payload: dict[str, Any] = {}
        if create:
            payload["create"] = create
        if update:
            payload["update"] = update
        if delete:
            payload["delete"] = delete

        resp = await self._client.post(f"{self._api}/products/batch", json=payload)
        resp.raise_for_status()
        result = resp.json()
        self.log.info(
            "batch_complete",
            created=len(result.get("create", [])),
            updated=len(result.get("update", [])),
            deleted=len(result.get("delete", [])),
        )
        return result

    # ── Product Variations ────────────────────────────────

    async def get_variations(
        self, product_id: int, per_page: int = 100
    ) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/products/{product_id}/variations",
            params={"per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()

    async def update_variation(
        self, product_id: int, variation_id: int, data: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await self._client.put(
            f"{self._api}/products/{product_id}/variations/{variation_id}",
            json=data,
        )
        resp.raise_for_status()
        return resp.json()

    # ── Categories ────────────────────────────────────────

    async def get_categories(self, per_page: int = 100) -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/products/categories", params={"per_page": per_page}
        )
        resp.raise_for_status()
        return resp.json()

    async def create_category(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/products/categories", json=data)
        resp.raise_for_status()
        return resp.json()

    # ── Orders (for analytics — NEW) ─────────────────────

    async def get_orders(
        self,
        status: str = "any",
        per_page: int = 100,
        page: int = 1,
        after: str = "",
        before: str = "",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "status": status,
            "per_page": per_page,
            "page": page,
        }
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        resp = await self._client.get(f"{self._api}/orders", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_order(self, order_id: int) -> dict[str, Any]:
        resp = await self._client.get(f"{self._api}/orders/{order_id}")
        resp.raise_for_status()
        return resp.json()

    # ── Coupons ───────────────────────────────────────────

    async def create_coupon(self, data: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._api}/coupons", json=data)
        resp.raise_for_status()
        return resp.json()

    # ── Reports ───────────────────────────────────────────

    async def get_sales_report(self, period: str = "week") -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/reports/sales", params={"period": period}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_top_sellers(self, period: str = "week") -> list[dict[str, Any]]:
        resp = await self._client.get(
            f"{self._api}/reports/top_sellers", params={"period": period}
        )
        resp.raise_for_status()
        return resp.json()
