"""GalleryManager — manages product image galleries and bulk uploads."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.integrations.wordpress import WordPressClient
from spectrum.integrations.woocommerce import WooCommerceClient
from spectrum.media.image_processor import ImageProcessor

logger = structlog.get_logger()


class GalleryManager(Agent):
    """Manages product image galleries — bulk upload, assign, and organize.

    Workflow:
    1. Scan a folder for product images
    2. Match images to products (by name/SKU pattern)
    3. Process each image (resize, optimize)
    4. Upload to WordPress
    5. Assign as product featured image or gallery image
    """

    @property
    def role(self) -> AgentRole:
        return AgentRole.GALLERY_MANAGER

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        settings = get_settings()
        action = context.get("action", "upload_folder")

        if action == "upload_folder":
            return await self._upload_folder(context, settings)
        elif action == "assign_image":
            return await self._assign_image(context, settings)
        elif action == "audit_missing":
            return await self._audit_missing_images(settings)
        else:
            return AgentResult(
                success=False, role=self.role, errors=[f"Unknown action: {action}"]
            )

    async def _upload_folder(self, context: dict[str, Any], settings: Any) -> AgentResult:
        """Upload all images from a folder, process them, and upload to WP."""
        folder_path = context.get("folder_path", "")
        if not folder_path:
            return AgentResult(
                success=False, role=self.role, errors=["No folder_path provided"]
            )

        folder = Path(folder_path)
        if not folder.exists():
            return AgentResult(
                success=False, role=self.role, errors=[f"Folder not found: {folder_path}"]
            )

        image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        image_files = [f for f in folder.iterdir() if f.suffix.lower() in image_extensions]

        if not image_files:
            return AgentResult(
                success=False, role=self.role, errors=["No images found in folder"]
            )

        wp = WordPressClient(settings.wp)
        processor = ImageProcessor()
        uploaded: list[dict[str, Any]] = []
        failed: list[str] = []

        try:
            for img_file in image_files:
                product_name = img_file.stem.replace("-", " ").replace("_", " ")

                # Process image
                result = await processor.run({
                    "image_path": str(img_file),
                    "product_name": product_name,
                })

                if not result.success:
                    failed.append(f"{img_file.name}: {result.errors}")
                    continue

                # Upload to WordPress
                media = await wp.upload_media(
                    file_data=result.data["image_bytes"],
                    filename=result.data["filename"],
                    alt_text=result.data["alt_text"],
                )

                uploaded.append({
                    "original_file": img_file.name,
                    "wp_media_id": media["id"],
                    "wp_url": media.get("source_url", ""),
                    "alt_text": result.data["alt_text"],
                })

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "uploaded": uploaded,
                    "failed": failed,
                    "total_processed": len(image_files),
                    "total_uploaded": len(uploaded),
                },
                score=100 if not failed else 80,
                warnings=[f"{len(failed)} images failed"] if failed else [],
            )
        finally:
            await wp.close()

    async def _assign_image(self, context: dict[str, Any], settings: Any) -> AgentResult:
        """Assign an uploaded image to a WooCommerce product."""
        product_id = context.get("product_id")
        media_id = context.get("media_id")
        as_featured = context.get("as_featured", True)

        if not product_id or not media_id:
            return AgentResult(
                success=False,
                role=self.role,
                errors=["product_id and media_id are required"],
            )

        wc = WooCommerceClient(settings.wp, settings.wc)
        try:
            product = await wc.get_product(product_id)
            images = product.get("images", [])

            if as_featured:
                # Set as first image (featured)
                images.insert(0, {"id": media_id})
            else:
                images.append({"id": media_id})

            await wc.update_product(product_id, {"images": images})

            return AgentResult(
                success=True,
                role=self.role,
                data={"product_id": product_id, "media_id": media_id, "featured": as_featured},
                score=100,
            )
        finally:
            await wc.close()

    async def _audit_missing_images(self, settings: Any) -> AgentResult:
        """Find all products that are missing images — the drafts Claw couldn't publish."""
        wc = WooCommerceClient(settings.wp, settings.wc)
        try:
            missing: list[dict[str, Any]] = []
            page = 1

            while True:
                products = await wc.get_products(status="any", per_page=100, page=page)
                if not products:
                    break

                for product in products:
                    images = product.get("images", [])
                    if not images:
                        missing.append({
                            "id": product["id"],
                            "name": product.get("name", ""),
                            "status": product.get("status", ""),
                            "sku": product.get("sku", ""),
                        })
                page += 1

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "missing_images": missing,
                    "total_missing": len(missing),
                },
                score=100,
            )
        finally:
            await wc.close()
