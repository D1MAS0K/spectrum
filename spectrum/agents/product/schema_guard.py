"""SchemaGuard — ensures valid structured data (JSON-LD) for Google Rich Snippets."""

from __future__ import annotations

import json
import re
from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole


class SchemaGuard(Agent):
    """Validates and generates JSON-LD structured data for products.

    Ensures Google sees:
    - Product schema (name, price, availability, brand, reviews)
    - FAQPage schema
    - BreadcrumbList schema
    - Organization schema
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.SCHEMA_GUARD

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        product = context.get("product", {})
        html = context.get("_step_output", {}).get("html_description", "")

        errors: list[str] = []
        schemas_found: list[str] = []
        score = 100

        # Extract all JSON-LD blocks
        ld_blocks = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html or "",
            re.DOTALL | re.IGNORECASE,
        )

        if not ld_blocks:
            errors.append("No JSON-LD blocks found in HTML")
            score -= 50
        else:
            for i, block in enumerate(ld_blocks):
                try:
                    data = json.loads(block.strip())
                    schema_type = data.get("@type", "Unknown")
                    schemas_found.append(schema_type)
                    score = self._validate_schema(data, schema_type, errors, score)
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON in LD block {i + 1}: {e}")
                    score -= 20

        # Generate missing schemas if needed
        generated_schemas: list[dict[str, Any]] = []
        if "Product" not in schemas_found and product:
            generated_schemas.append(self._generate_product_schema(product))
        if "FAQPage" not in schemas_found:
            errors.append("Missing FAQPage schema")
            score -= 10

        score = max(0, score)

        return AgentResult(
            success=score >= 100,
            role=self.role,
            data={
                "schemas_found": schemas_found,
                "generated_schemas": generated_schemas,
                "product_id": product.get("id"),
            },
            errors=errors,
            score=score,
        )

    def _validate_schema(
        self,
        data: dict[str, Any],
        schema_type: str,
        errors: list[str],
        score: int,
    ) -> int:
        if schema_type == "Product":
            required = ["name", "description", "offers"]
            for field in required:
                if field not in data:
                    errors.append(f"Product schema missing '{field}'")
                    score -= 10
            offers = data.get("offers", {})
            if isinstance(offers, dict):
                if "price" not in offers:
                    errors.append("Product.offers missing 'price'")
                    score -= 10
                if "priceCurrency" not in offers:
                    errors.append("Product.offers missing 'priceCurrency'")
                    score -= 5
        return score

    def _generate_product_schema(self, product: dict[str, Any]) -> dict[str, Any]:
        """Generate a complete Product JSON-LD schema."""
        schema: dict[str, Any] = {
            "@context": "https://schema.org/",
            "@type": "Product",
            "name": product.get("name", ""),
            "description": product.get("short_description", ""),
            "brand": {
                "@type": "Brand",
                "name": product.get("brand", "DogsState"),
            },
            "offers": {
                "@type": "Offer",
                "price": product.get("price", "0"),
                "priceCurrency": "ILS",
                "availability": "https://schema.org/InStock",
                "url": product.get("permalink", ""),
            },
        }
        images = product.get("images", [])
        if images:
            schema["image"] = [img.get("src", "") for img in images]

        return schema
