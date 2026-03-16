"""WooCommerce REST API client — products, orders, coupons."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import structlog

from config.settings import WooCommerceSettings, WordPressSettings

logger = structlog.get_logger()

# WooCommerce batch API needs a cooldown between calls to avoid 503 errors.
# Learned the hard way: rapid batch calls cause server overload.
BATCH_DELAY_SECONDS = 30


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

    async def update_product(
        self, product_id: int, data: dict[str, Any], *, verify: bool = True
    ) -> dict[str, Any]:
        """Update a product, then GET it back to verify changes persisted.

        WooCommerce sometimes returns 200 but silently drops fields.
        The verify GET catches this before we assume success.
        """
        resp = await self._client.put(f"{self._api}/products/{product_id}", json=data)
        resp.raise_for_status()
        self.log.info("product_updated", id=product_id)

        if not verify:
            return resp.json()

        # GET-after-PUT: verify the update actually persisted
        verified = await self.get_product(product_id)
        mismatches: list[str] = []
        for key in data:
            if key in verified and verified[key] != data[key]:
                # Skip complex nested objects (images, categories, meta_data)
                if isinstance(data[key], (list, dict)):
                    continue
                mismatches.append(key)

        if mismatches:
            self.log.warning(
                "update_verification_mismatch",
                product_id=product_id,
                fields=mismatches,
            )

        return verified

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
        """Batch create/update/delete up to 100 products per call.

        Includes a 30-second delay after each batch call to prevent
        WooCommerce 503 errors from rapid successive batches.
        """
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

        # Cooldown to prevent server overload on consecutive batch calls
        self.log.debug("batch_cooldown", seconds=BATCH_DELAY_SECONDS)
        await asyncio.sleep(BATCH_DELAY_SECONDS)

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

    # ── Product Attributes (for brand assignment) ────────

    async def get_attributes(self) -> list[dict[str, Any]]:
        """Get all product attributes (e.g., Brand, Color, Size)."""
        resp = await self._client.get(f"{self._api}/products/attributes")
        resp.raise_for_status()
        return resp.json()

    async def get_attribute_terms(
        self, attribute_id: int, per_page: int = 100
    ) -> list[dict[str, Any]]:
        """Get all terms for a given attribute (e.g., all brands)."""
        resp = await self._client.get(
            f"{self._api}/products/attributes/{attribute_id}/terms",
            params={"per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()

    async def create_attribute_term(
        self, attribute_id: int, name: str
    ) -> dict[str, Any]:
        """Create a new term under an attribute (e.g., add a new brand)."""
        resp = await self._client.post(
            f"{self._api}/products/attributes/{attribute_id}/terms",
            json={"name": name},
        )
        resp.raise_for_status()
        self.log.info("attribute_term_created", attribute_id=attribute_id, term=name)
        return resp.json()

    async def assign_brand_to_product(
        self, product_id: int, brand_name: str
    ) -> dict[str, Any]:
        """Multi-step brand assignment: find attribute → find/create term → assign.

        Steps:
        1. GET all attributes → find 'Brand' (or 'מותג')
        2. GET attribute terms → find brand_name
        3. If brand term doesn't exist → POST to create it
        4. PUT product with the brand attribute
        """
        # Step 1: Find the Brand attribute
        attributes = await self.get_attributes()
        brand_attr = None
        for attr in attributes:
            if attr["name"].lower() in ("brand", "מותג", "pa_brand"):
                brand_attr = attr
                break

        if not brand_attr:
            self.log.warning("brand_attribute_not_found")
            return {"error": "Brand attribute not found in WooCommerce"}

        # Step 2: Find or create the brand term
        terms = await self.get_attribute_terms(brand_attr["id"])
        brand_term = None
        for term in terms:
            if term["name"].lower() == brand_name.lower():
                brand_term = term
                break

        if not brand_term:
            # Step 3: Create the brand term
            brand_term = await self.create_attribute_term(brand_attr["id"], brand_name)

        # Step 4: Assign to product
        product = await self.get_product(product_id)
        existing_attrs = product.get("attributes", [])

        # Update or add the brand attribute
        updated = False
        for attr in existing_attrs:
            if attr.get("id") == brand_attr["id"]:
                attr["options"] = [brand_name]
                updated = True
                break

        if not updated:
            existing_attrs.append({
                "id": brand_attr["id"],
                "name": brand_attr["name"],
                "options": [brand_name],
                "visible": True,
            })

        return await self.update_product(product_id, {"attributes": existing_attrs})

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
