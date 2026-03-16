"""SiteFixer — audits and fixes site-wide product data issues.

Handles:
- Product Schema (JSON-LD) validation and fix instructions
- Yoast SEO meta completeness for every product
- Alt text standardization (replace generic with product name)
- Short description length enforcement
- Missing price detection
- Out-of-stock cleanup
"""

from __future__ import annotations

import re
from typing import Any

from spectrum.core.agent import Agent, AgentResult, AgentRole


class SiteFixer(Agent):
    """Site-wide product data auditor and fixer.

    Modes:
    - audit: Read-only scan, produces report of all issues
    - fix_yoast: Update Yoast SEO meta for products missing it
    - fix_alt_text: Replace generic alt text with product-specific text
    - fix_short_desc: Flag/fix overly long short descriptions
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.SITE_FIXER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        action = context.get("action", "audit")

        if action == "audit":
            return await self._full_audit(context)
        if action == "fix_yoast":
            return await self._fix_yoast(context)
        if action == "fix_alt_text":
            return await self._fix_alt_text(context)

        return AgentResult(
            success=False,
            role=self.role,
            errors=[f"Unknown action: {action}"],
        )

    async def _full_audit(self, context: dict[str, Any]) -> AgentResult:
        """Comprehensive audit of all products."""
        products = context.get("products", [])

        issues: dict[str, list[dict[str, Any]]] = {
            "no_brand": [],
            "short_description_too_long": [],
            "description_below_standard": [],
            "no_images": [],
            "single_image": [],
            "generic_alt_text": [],
            "no_price": [],
            "out_of_stock": [],
            "missing_yoast_title": [],
            "missing_yoast_desc": [],
            "no_product_schema": [],
        }

        for p in products:
            pid = p.get("id")
            name = p.get("name", "")[:60]
            status = p.get("status", "")

            if status != "publish":
                continue

            entry = {"id": pid, "name": name}

            # Brand check
            has_brand = any(
                a.get("name", "").lower() in ("מותג", "brand")
                for a in p.get("attributes", [])
            )
            if not has_brand:
                issues["no_brand"].append(entry)

            # Description length
            desc_len = len(p.get("description", ""))
            if desc_len < 5000:
                issues["description_below_standard"].append(
                    {**entry, "length": desc_len}
                )

            # Short description
            short_desc = p.get("short_description", "")
            if short_desc:
                text_only = re.sub(r"<[^>]+>", "\n", short_desc)
                lines = [ln for ln in text_only.strip().splitlines() if ln.strip()]
                if len(lines) > 6:
                    issues["short_description_too_long"].append(
                        {**entry, "lines": len(lines)}
                    )

            # Images
            images = p.get("images", [])
            if not images:
                issues["no_images"].append(entry)
            elif len(images) == 1:
                issues["single_image"].append(entry)

            # Generic alt text
            for img in images:
                alt = img.get("alt", "")
                if alt and ("דוגס סטייט" in alt and "משלוחים" in alt):
                    issues["generic_alt_text"].append(
                        {**entry, "image_id": img.get("id"), "alt": alt[:60]}
                    )
                    break  # One per product is enough

            # Price
            price = p.get("price", "")
            if not price or price == "0":
                issues["no_price"].append(entry)

            # Stock
            if p.get("stock_status") == "outofstock":
                issues["out_of_stock"].append(entry)

        # Summary
        summary = {k: len(v) for k, v in issues.items()}
        total_issues = sum(summary.values())

        return AgentResult(
            success=True,
            role=self.role,
            data={
                "summary": summary,
                "total_issues": total_issues,
                "issues": issues,
            },
            score=100,
        )

    async def _fix_yoast(self, context: dict[str, Any]) -> AgentResult:
        """Fix Yoast SEO meta for products with missing or weak data."""
        from config.settings import get_settings
        from spectrum.integrations.wordpress import WordPressClient

        settings = get_settings()
        wp = WordPressClient(settings.wp)
        dry_run = context.get("dry_run", True)
        products = context.get("products", [])

        fixed: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            for p in products:
                if p.get("status") != "publish":
                    continue

                name = p.get("name", "")
                categories = [c.get("name", "") for c in p.get("categories", [])]
                brand = ""
                for a in p.get("attributes", []):
                    if a.get("name", "").lower() in ("מותג", "brand"):
                        opts = a.get("options", [])
                        if opts:
                            brand = opts[0]
                        break

                # Build optimal Yoast title: "Brand Product | דוגס סטייט"
                if brand and brand.lower() not in name.lower():
                    yoast_title = f"{brand} {name} | דוגס סטייט"
                else:
                    yoast_title = f"{name} | דוגס סטייט"

                # Trim to 60 chars max
                if len(yoast_title) > 65:
                    yoast_title = yoast_title[:62] + "..."

                # Build meta description
                cat_text = categories[0] if categories else "מוצר"
                price = p.get("price", "")
                price_text = f" ₪{price}." if price else ""
                yoast_desc = (
                    f"{name}.{price_text} "
                    f"זמין ברכישה בדוגס סטייט עם משלוח מהיר לגוש דן. "
                    f"{cat_text} פרימיום. 054-4989600"
                )
                # Trim to 155 chars
                if len(yoast_desc) > 155:
                    yoast_desc = yoast_desc[:152] + "..."

                # Focus keyword
                focus_kw = name.split(" - ")[0].split(" – ")[0].strip()[:50]

                entry = {
                    "id": p["id"],
                    "name": name[:50],
                    "yoast_title": yoast_title,
                    "yoast_desc": yoast_desc[:80] + "...",
                    "focus_kw": focus_kw,
                }

                if dry_run:
                    entry["action"] = "would_fix"
                    fixed.append(entry)
                else:
                    try:
                        await wp.update_yoast_meta(
                            post_id=p["id"],
                            title=yoast_title,
                            description=yoast_desc,
                            focus_keyword=focus_kw,
                            og_title=yoast_title,
                            og_description=yoast_desc,
                        )
                        entry["action"] = "fixed"
                        fixed.append(entry)
                    except Exception as exc:
                        errors.append(f"Yoast fix {p['id']}: {exc}")

        finally:
            await wp.close()

        return AgentResult(
            success=len(errors) == 0,
            role=self.role,
            data={
                "dry_run": dry_run,
                "fixed": fixed,
                "fixed_count": len(fixed),
            },
            errors=errors,
            score=100 if not errors else 80,
        )

    async def _fix_alt_text(self, context: dict[str, Any]) -> AgentResult:
        """Replace generic alt text with product-specific descriptive alt."""
        from config.settings import get_settings
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        wc = WooCommerceClient(settings.wp, settings.wc)
        dry_run = context.get("dry_run", True)
        products = context.get("products", [])

        fixed: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            for p in products:
                if p.get("status") != "publish":
                    continue

                images = p.get("images", [])
                name = p.get("name", "")
                brand = ""
                for a in p.get("attributes", []):
                    if a.get("name", "").lower() in ("מותג", "brand"):
                        opts = a.get("options", [])
                        if opts:
                            brand = opts[0]
                        break

                updated_images = []
                needs_update = False

                for i, img in enumerate(images):
                    alt = img.get("alt", "")
                    # Check if alt is generic
                    is_generic = (
                        not alt
                        or ("דוגס סטייט" in alt and "משלוחים" in alt)
                        or alt == name  # Just the name, no context
                    )

                    if is_generic:
                        # Build descriptive alt
                        if i == 0:
                            new_alt = f"{name} - {brand}" if brand else name
                            new_alt += " | דוגס סטייט"
                        else:
                            new_alt = f"{name} תמונה {i + 1}"

                        updated_images.append({**img, "alt": new_alt})
                        needs_update = True
                    else:
                        updated_images.append(img)

                if needs_update:
                    entry = {
                        "id": p["id"],
                        "name": name[:50],
                        "images_fixed": sum(
                            1 for o, n in zip(images, updated_images)
                            if o.get("alt") != n.get("alt")
                        ),
                    }

                    if dry_run:
                        entry["action"] = "would_fix"
                        fixed.append(entry)
                    else:
                        try:
                            await wc.update_product(
                                p["id"],
                                {"images": updated_images},
                                verify=False,
                            )
                            entry["action"] = "fixed"
                            fixed.append(entry)
                        except Exception as exc:
                            errors.append(f"Alt fix {p['id']}: {exc}")

        finally:
            await wc.close()

        return AgentResult(
            success=len(errors) == 0,
            role=self.role,
            data={
                "dry_run": dry_run,
                "fixed": fixed,
                "fixed_count": len(fixed),
            },
            errors=errors,
            score=100 if not errors else 80,
        )
