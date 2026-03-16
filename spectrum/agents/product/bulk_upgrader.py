"""BulkUpgrader — batch-upgrades product descriptions to Spectrum standard.

Takes products with descriptions < 5000 chars and rewrites them using
the ProductRewriter pipeline with QA gate. Processes in batches with
cooldown to avoid server overload.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from spectrum.core.agent import Agent, AgentResult, AgentRole

logger = structlog.get_logger()

# Process N products per batch, with cooldown between batches
BATCH_SIZE = 5
BATCH_COOLDOWN_SECONDS = 10


class BulkUpgrader(Agent):
    """Upgrades product descriptions in bulk.

    Modes:
    - scan: Report which products need upgrading
    - upgrade: Run ProductRewriter + QA on each product
    - upgrade_and_publish: Rewrite + QA + push to WooCommerce
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.BULK_UPGRADER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        action = context.get("action", "scan")

        if action == "scan":
            return await self._scan(context)
        if action in ("upgrade", "upgrade_and_publish"):
            return await self._upgrade(context, publish=action == "upgrade_and_publish")

        return AgentResult(
            success=False,
            role=self.role,
            errors=[f"Unknown action: {action}"],
        )

    async def _scan(self, context: dict[str, Any]) -> AgentResult:
        """Report products needing description upgrade."""
        products = context.get("products", [])
        min_length = context.get("min_length", 5000)

        needs_upgrade: list[dict[str, Any]] = []
        already_good: list[dict[str, Any]] = []

        for p in products:
            if p.get("status") != "publish":
                continue

            desc_len = len(p.get("description", ""))
            entry = {
                "id": p["id"],
                "name": p.get("name", "")[:60],
                "current_length": desc_len,
            }

            if desc_len < min_length:
                entry["gap"] = min_length - desc_len
                needs_upgrade.append(entry)
            else:
                already_good.append(entry)

        # Sort by shortest description first (biggest improvement potential)
        needs_upgrade.sort(key=lambda x: x["current_length"])

        return AgentResult(
            success=True,
            role=self.role,
            data={
                "needs_upgrade": needs_upgrade,
                "needs_upgrade_count": len(needs_upgrade),
                "already_good_count": len(already_good),
                "total_scanned": len(needs_upgrade) + len(already_good),
            },
            score=100,
        )

    async def _upgrade(
        self, context: dict[str, Any], *, publish: bool = False
    ) -> AgentResult:
        """Rewrite descriptions using ProductRewriter + QA pipeline."""
        from config.settings import get_settings
        from spectrum.integrations.woocommerce import WooCommerceClient

        settings = get_settings()
        products = context.get("products", [])
        limit = context.get("limit", 10)
        min_length = context.get("min_length", 5000)
        dry_run = context.get("dry_run", True)

        # Filter to products that need upgrading
        to_upgrade = [
            p for p in products
            if p.get("status") == "publish"
            and len(p.get("description", "")) < min_length
        ]
        to_upgrade.sort(key=lambda x: len(x.get("description", "")))
        to_upgrade = to_upgrade[:limit]

        self.log.info(
            "bulk_upgrade_start",
            total=len(to_upgrade),
            limit=limit,
            dry_run=dry_run,
        )

        upgraded: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []

        if dry_run:
            for p in to_upgrade:
                upgraded.append({
                    "id": p["id"],
                    "name": p.get("name", "")[:50],
                    "current_length": len(p.get("description", "")),
                    "action": "would_upgrade",
                })

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "dry_run": True,
                    "would_upgrade": upgraded,
                    "count": len(upgraded),
                },
                score=100,
            )

        # Real upgrade — import pipeline components
        from spectrum.agents.product.qa import ProductQA
        from spectrum.agents.product.rewriter import ProductRewriter
        from spectrum.core.pipeline import Pipeline, PipelineStep

        rewriter = ProductRewriter()
        qa = ProductQA()
        wc = WooCommerceClient(settings.wp, settings.wc)

        try:
            for i in range(0, len(to_upgrade), BATCH_SIZE):
                batch = to_upgrade[i : i + BATCH_SIZE]
                self.log.info(
                    "batch_start",
                    batch_num=i // BATCH_SIZE + 1,
                    size=len(batch),
                )

                for p in batch:
                    pipeline = Pipeline(
                        name=f"upgrade_{p['id']}",
                        steps=[
                            PipelineStep(agent=rewriter),
                            PipelineStep(agent=qa, required_score=100),
                        ],
                    )

                    result = await pipeline.run({"product": p})

                    if result.success:
                        html = result.results[0].data.get("html_description", "")
                        yoast_synonyms = result.results[0].data.get(
                            "yoast_keyword_synonyms", ""
                        )

                        entry = {
                            "id": p["id"],
                            "name": p.get("name", "")[:50],
                            "old_length": len(p.get("description", "")),
                            "new_length": len(html),
                            "qa_score": result.final_score,
                        }

                        if publish:
                            try:
                                update_data: dict[str, Any] = {
                                    "description": html,
                                }
                                # Add Yoast synonyms to meta_data
                                if yoast_synonyms:
                                    update_data["meta_data"] = [
                                        {
                                            "key": "_yoast_wpseo_keywordsynonyms",
                                            "value": yoast_synonyms,
                                        }
                                    ]
                                await wc.update_product(p["id"], update_data)
                                entry["action"] = "published"
                            except Exception as exc:
                                entry["action"] = "write_failed"
                                entry["error"] = str(exc)
                                failed.append(entry)
                                continue

                        else:
                            entry["action"] = "upgraded_not_published"

                        upgraded.append(entry)
                    else:
                        failed.append({
                            "id": p["id"],
                            "name": p.get("name", "")[:50],
                            "action": "qa_failed",
                            "score": result.final_score,
                            "errors": [
                                e for r in result.results for e in r.errors
                            ],
                        })

                # Cooldown between batches
                if i + BATCH_SIZE < len(to_upgrade):
                    self.log.debug("batch_cooldown", seconds=BATCH_COOLDOWN_SECONDS)
                    await asyncio.sleep(BATCH_COOLDOWN_SECONDS)

        finally:
            await wc.close()

        return AgentResult(
            success=len(failed) == 0,
            role=self.role,
            data={
                "dry_run": False,
                "upgraded": upgraded,
                "upgraded_count": len(upgraded),
                "failed": failed,
                "failed_count": len(failed),
            },
            errors=[f"Failed: {e['id']} - {e.get('errors', [])}" for e in failed],
            score=100 if not failed else max(0, 100 - len(failed) * 5),
        )
