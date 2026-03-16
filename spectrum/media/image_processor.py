"""ImageProcessor — optimizes and processes product images for web.

Solves Claw's #1 gap: "hundreds of drafts waiting for images."
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import anthropic
import structlog
from PIL import Image

from config.settings import get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole

logger = structlog.get_logger()


class ImageProcessor(Agent):
    """Processes product images: resize, optimize, generate alt text, upload.

    Pipeline:
    1. Read image from file/URL
    2. Resize to standard product dimensions
    3. Optimize for web (quality/size balance)
    4. Generate Hebrew alt text via AI
    5. Upload to WordPress media library
    """

    PRODUCT_SIZES = {
        "full": (1200, 1200),
        "medium": (600, 600),
        "thumbnail": (300, 300),
    }

    @property
    def role(self) -> AgentRole:
        return AgentRole.IMAGE_PROCESSOR

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        image_path = context.get("image_path", "")
        product_name = context.get("product_name", "")
        target_size = context.get("target_size", "full")

        if not image_path:
            return AgentResult(
                success=False, role=self.role, errors=["No image_path provided"]
            )

        try:
            # Open and process image
            img = Image.open(image_path)
            original_size = img.size

            # Resize
            target_dims = self.PRODUCT_SIZES.get(target_size, self.PRODUCT_SIZES["full"])
            img = self._resize_smart(img, target_dims)

            # Convert to RGB if needed (for JPEG)
            if img.mode in ("RGBA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background

            # Optimize and get bytes
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            optimized_bytes = output.getvalue()
            output.close()

            # Generate alt text
            alt_text = await self._generate_alt_text(product_name, image_path)

            # Generate filename
            safe_name = product_name.replace(" ", "-").replace('"', "")[:50]
            filename = f"{safe_name}-dogsstate.jpg"

            return AgentResult(
                success=True,
                role=self.role,
                data={
                    "image_bytes": optimized_bytes,
                    "filename": filename,
                    "alt_text": alt_text,
                    "original_size": original_size,
                    "processed_size": img.size,
                    "file_size_kb": len(optimized_bytes) // 1024,
                },
                score=100,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                role=self.role,
                errors=[f"Image processing failed: {e}"],
            )

    def _resize_smart(self, img: Image.Image, target: tuple[int, int]) -> Image.Image:
        """Resize maintaining aspect ratio, then crop to exact target size."""
        img.thumbnail((target[0] * 2, target[1] * 2), Image.Resampling.LANCZOS)

        # Center crop to exact dimensions
        width, height = img.size
        left = (width - target[0]) // 2
        top = (height - target[1]) // 2
        right = left + target[0]
        bottom = top + target[1]

        if left >= 0 and top >= 0:
            img = img.crop((left, top, right, bottom))
        else:
            # Image is smaller than target — just resize
            img = img.resize(target, Image.Resampling.LANCZOS)

        return img

    async def _generate_alt_text(self, product_name: str, image_path: str) -> str:
        """Generate Hebrew alt text for the image using AI."""
        settings = get_settings()
        if not settings.ai.anthropic_api_key:
            return product_name  # Fallback

        client = anthropic.AsyncAnthropic(api_key=settings.ai.anthropic_api_key)
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": f"כתוב alt text קצר בעברית (עד 125 תווים) לתמונת מוצר: {product_name}. רק את הטקסט, בלי גרשיים.",
                }],
            )
            return response.content[0].text.strip()
        except Exception:
            return product_name
        finally:
            await client.close()
