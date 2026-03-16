"""Notification system — Telegram and WhatsApp alerts."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from config.settings import get_settings

logger = structlog.get_logger()


class Notifier:
    """Sends notifications via Telegram and WhatsApp.

    Used by the Engine to alert on:
    - Pipeline completion/failure
    - Site health issues
    - Ranking changes
    - Daily reports
    """

    def __init__(self) -> None:
        self.settings = get_settings().notifications
        self.log = logger.bind(component="notifier")

    async def send_telegram(self, message: str) -> bool:
        """Send a message via Telegram bot."""
        if not self.settings.telegram_bot_token or not self.settings.telegram_chat_id:
            self.log.warning("telegram_not_configured")
            return False

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json={
                    "chat_id": self.settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                },
            )
            if resp.status_code == 200:
                self.log.info("telegram_sent")
                return True
            self.log.error("telegram_failed", status=resp.status_code)
            return False

    async def send_whatsapp(self, message: str) -> bool:
        """Send a message via WhatsApp Business API."""
        if not self.settings.whatsapp_api_url or not self.settings.whatsapp_api_token:
            self.log.warning("whatsapp_not_configured")
            return False

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.settings.whatsapp_api_url,
                headers={"Authorization": f"Bearer {self.settings.whatsapp_api_token}"},
                json={"text": message},
            )
            return resp.status_code == 200

    async def alert(self, title: str, message: str, level: str = "info") -> None:
        """Send alert to all configured channels."""
        icons = {"info": "ℹ️", "warning": "⚠️", "error": "🚨", "success": "✅"}
        icon = icons.get(level, "ℹ️")
        formatted = f"{icon} <b>{title}</b>\n\n{message}"

        await self.send_telegram(formatted)

    async def report_pipeline_result(
        self, pipeline_name: str, success: bool, score: int, details: str = ""
    ) -> None:
        level = "success" if success else "error"
        title = f"Pipeline: {pipeline_name}"
        message = f"Status: {'הצלחה' if success else 'כישלון'}\nScore: {score}/100"
        if details:
            message += f"\n\n{details}"
        await self.alert(title, message, level)
