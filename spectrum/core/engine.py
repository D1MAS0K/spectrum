"""Engine — the central orchestrator that wires everything together."""

from __future__ import annotations

from typing import Any

import structlog

from config.settings import Settings, get_settings
from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.core.pipeline import Pipeline, PipelineResult
from spectrum.core.scheduler import Scheduler

logger = structlog.get_logger()


class Engine:
    """Spectrum Engine — the main entry point.

    Manages:
    - Agent registry (all 17+ agents)
    - Pipeline execution with QA gates
    - Scheduled recurring tasks
    - Notifications on completion/failure
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.agents: dict[AgentRole, Agent] = {}
        self.scheduler = Scheduler()
        self.log = logger.bind(component="engine")

    def register(self, agent: Agent) -> None:
        self.agents[agent.role] = agent
        self.log.info("agent_registered", role=agent.role.value)

    def get_agent(self, role: AgentRole) -> Agent:
        if role not in self.agents:
            msg = f"Agent not registered: {role.value}"
            raise KeyError(msg)
        return self.agents[role]

    async def run_agent(self, role: AgentRole, context: dict[str, Any]) -> AgentResult:
        agent = self.get_agent(role)
        return await agent.run(context)

    async def run_pipeline(self, pipeline: Pipeline, context: dict[str, Any]) -> PipelineResult:
        self.log.info("pipeline_start", name=pipeline.name, steps=len(pipeline.steps))
        result = await pipeline.run(context)
        self.log.info(
            "pipeline_end",
            name=pipeline.name,
            success=result.success,
            score=result.final_score,
        )
        return result

    def setup_recurring_tasks(self) -> None:
        """Register all default scheduled jobs."""
        cfg = self.settings.system

        # Site health snapshot every N minutes
        if AgentRole.SITE_AUDITOR in self.agents:
            self.scheduler.add_interval(
                name="site_snapshot",
                func=self._run_site_audit,
                minutes=cfg.snapshot_interval_minutes,
            )

        # Rank tracking daily at 6 AM
        if AgentRole.RANK_TRACKER in self.agents:
            self.scheduler.add_cron(
                name="daily_rank_check",
                func=self._run_rank_tracking,
                hour=6,
                minute=0,
            )

        # Competitor analysis every 6 hours
        if AgentRole.COMPETITOR_EYE in self.agents:
            self.scheduler.add_interval(
                name="competitor_scan",
                func=self._run_competitor_scan,
                hours=6,
            )

        # GA4 daily report at 7 AM
        if AgentRole.GA4_ANALYST in self.agents:
            self.scheduler.add_cron(
                name="daily_analytics",
                func=self._run_analytics_report,
                hour=7,
                minute=0,
            )

    async def _run_site_audit(self) -> None:
        await self.run_agent(AgentRole.SITE_AUDITOR, {"mode": "snapshot"})

    async def _run_rank_tracking(self) -> None:
        await self.run_agent(AgentRole.RANK_TRACKER, {"mode": "daily"})

    async def _run_competitor_scan(self) -> None:
        await self.run_agent(AgentRole.COMPETITOR_EYE, {"mode": "scan"})

    async def _run_analytics_report(self) -> None:
        await self.run_agent(AgentRole.GA4_ANALYST, {"mode": "daily_report"})

    def start(self) -> None:
        """Boot the engine — start scheduler and recurring tasks."""
        self.log.info("engine_start", agents=len(self.agents))
        if self.settings.system.scheduler_enabled:
            self.setup_recurring_tasks()
            self.scheduler.start()

    def stop(self) -> None:
        self.log.info("engine_stop")
        self.scheduler.stop()
