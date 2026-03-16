"""Base agent framework — every Spectrum agent inherits from this."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


class AgentRole(str, Enum):
    """All agent roles in the Spectrum system."""

    # Product Division
    PRODUCT_REWRITER = "product_rewriter"
    PRODUCT_QA = "product_qa"
    SCHEMA_GUARD = "schema_guard"

    # Content Division
    KEYWORD_SNIPER = "keyword_sniper"
    CONTENT_FACTORY = "content_factory"
    WP_PUBLISHER = "wp_publisher"

    # Intelligence Division
    SITE_AUDITOR = "site_auditor"
    COMPETITOR_EYE = "competitor_eye"
    RANK_TRACKER = "rank_tracker"

    # Growth Division
    LINK_BUILDER = "link_builder"
    SOCIAL_OPS = "social_ops"
    ANALYTICS_BRAIN = "analytics_brain"

    # Media Division (NEW — solves Claw's image gap)
    IMAGE_PROCESSOR = "image_processor"
    GALLERY_MANAGER = "gallery_manager"

    # Google Division (NEW — solves Claw's Google gaps)
    GSC_MANAGER = "gsc_manager"
    GA4_ANALYST = "ga4_analyst"
    MERCHANT_MANAGER = "merchant_manager"

    # Site Maintenance Division (NEW — DogsState audit findings)
    BRAND_MANAGER = "brand_manager"
    SITE_FIXER = "site_fixer"
    BULK_UPGRADER = "bulk_upgrader"


@dataclass
class AgentResult:
    """Standardized result from any agent execution."""

    success: bool
    role: AgentRole
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: int = 0  # QA score 0-100
    duration_ms: int = 0

    @property
    def passed_qa(self) -> bool:
        return self.score >= 100


class Agent(ABC):
    """Base class for all Spectrum agents.

    Every agent must implement:
    - role: which AgentRole it fulfills
    - execute(): the main work method
    - validate(): optional pre-flight checks
    """

    def __init__(self) -> None:
        self.log = structlog.get_logger().bind(agent=self.role.value)

    @property
    @abstractmethod
    def role(self) -> AgentRole:
        ...

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Run the agent's main task."""
        ...

    async def validate(self, context: dict[str, Any]) -> list[str]:
        """Pre-flight validation. Returns list of error strings (empty = OK)."""
        return []

    async def run(self, context: dict[str, Any]) -> AgentResult:
        """Full execution cycle: validate -> execute -> log."""
        start = time.monotonic()

        errors = await self.validate(context)
        if errors:
            self.log.warning("validation_failed", errors=errors)
            return AgentResult(
                success=False,
                role=self.role,
                errors=errors,
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        try:
            self.log.info("executing")
            result = await self.execute(context)
            result.duration_ms = int((time.monotonic() - start) * 1000)
            self.log.info(
                "completed",
                success=result.success,
                score=result.score,
                duration_ms=result.duration_ms,
            )
            return result
        except Exception as exc:
            self.log.error("execution_failed", error=str(exc))
            return AgentResult(
                success=False,
                role=self.role,
                errors=[str(exc)],
                duration_ms=int((time.monotonic() - start) * 1000),
            )
