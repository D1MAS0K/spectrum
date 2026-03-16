"""Pipeline — chains agents together with QA gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from spectrum.core.agent import Agent, AgentResult

logger = structlog.get_logger()


@dataclass
class PipelineStep:
    """A single step in a pipeline."""

    agent: Agent
    required_score: int = 100  # Minimum QA score to proceed
    retry_count: int = 2
    context_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Aggregated result of a full pipeline run."""

    steps_completed: int = 0
    total_steps: int = 0
    results: list[AgentResult] = field(default_factory=list)
    success: bool = False

    @property
    def final_score(self) -> int:
        if not self.results:
            return 0
        return min(r.score for r in self.results)


class Pipeline:
    """Executes a sequence of agents with QA gates between them.

    If a step fails QA (score < required_score), it retries up to
    retry_count times. If it still fails, the pipeline halts and
    returns partial results. This enforces the "100/100 or reject"
    standard from TheMainDog.
    """

    def __init__(self, name: str, steps: list[PipelineStep]) -> None:
        self.name = name
        self.steps = steps
        self.log = logger.bind(pipeline=name)

    async def run(self, context: dict[str, Any]) -> PipelineResult:
        result = PipelineResult(total_steps=len(self.steps))

        for i, step in enumerate(self.steps):
            merged_ctx = {**context, **step.context_overrides}
            self.log.info("step_start", step=i + 1, agent=step.agent.role.value)

            agent_result: AgentResult | None = None
            for attempt in range(1, step.retry_count + 1):
                agent_result = await step.agent.run(merged_ctx)

                if agent_result.success and agent_result.score >= step.required_score:
                    break

                self.log.warning(
                    "step_retry",
                    step=i + 1,
                    attempt=attempt,
                    score=agent_result.score,
                    required=step.required_score,
                )
                # Feed errors back into context for self-correction
                merged_ctx["_previous_errors"] = agent_result.errors
                merged_ctx["_previous_score"] = agent_result.score

            assert agent_result is not None
            result.results.append(agent_result)

            if not agent_result.success or agent_result.score < step.required_score:
                self.log.error(
                    "pipeline_halted",
                    step=i + 1,
                    score=agent_result.score,
                )
                return result

            result.steps_completed = i + 1
            # Pass output forward
            context["_step_output"] = agent_result.data

        result.success = True
        self.log.info("pipeline_complete", score=result.final_score)
        return result
