"""Scheduler — runs recurring tasks (site audits, rank tracking, snapshots)."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = structlog.get_logger()

AsyncTask = Callable[..., Coroutine[Any, Any, None]]


@dataclass
class ScheduledJob:
    """Definition of a recurring job."""

    name: str
    func: AsyncTask
    trigger: str  # "interval" or "cron"
    kwargs: dict[str, Any] = field(default_factory=dict)
    # For interval: minutes, hours, seconds
    # For cron: hour, minute, day_of_week, etc.


class Scheduler:
    """Wraps APScheduler for async recurring jobs.

    Replaces Claw's manual "check every 30 minutes" with proper scheduling.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._jobs: list[ScheduledJob] = []
        self.log = logger.bind(component="scheduler")

    def add_job(self, job: ScheduledJob) -> None:
        if job.trigger == "interval":
            trigger = IntervalTrigger(**job.kwargs)
        elif job.trigger == "cron":
            trigger = CronTrigger(**job.kwargs)
        else:
            msg = f"Unknown trigger type: {job.trigger}"
            raise ValueError(msg)

        self._scheduler.add_job(job.func, trigger, name=job.name)
        self._jobs.append(job)
        self.log.info("job_registered", name=job.name, trigger=job.trigger)

    def add_interval(self, name: str, func: AsyncTask, **kwargs: Any) -> None:
        self.add_job(ScheduledJob(name=name, func=func, trigger="interval", kwargs=kwargs))

    def add_cron(self, name: str, func: AsyncTask, **kwargs: Any) -> None:
        self.add_job(ScheduledJob(name=name, func=func, trigger="cron", kwargs=kwargs))

    def start(self) -> None:
        self.log.info("starting", jobs=len(self._jobs))
        self._scheduler.start()

    def stop(self) -> None:
        self.log.info("stopping")
        self._scheduler.shutdown(wait=False)
