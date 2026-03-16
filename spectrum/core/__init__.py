"""Core engine — orchestration, scheduling, and agent framework."""

from spectrum.core.agent import Agent, AgentResult, AgentRole
from spectrum.core.engine import Engine
from spectrum.core.pipeline import Pipeline, PipelineStep
from spectrum.core.scheduler import Scheduler

__all__ = [
    "Agent",
    "AgentResult",
    "AgentRole",
    "Engine",
    "Pipeline",
    "PipelineStep",
    "Scheduler",
]
